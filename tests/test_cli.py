"""Tests for CLI interface."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from detective_benno.cli import main
from detective_benno.models import ReviewComment, ReviewResult, Severity


class TestCLI:
    """Tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    def test_help_message(self, runner: CliRunner):
        """Test --help shows usage information."""
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Detective Benno" in result.output
        assert "investigate" in result.output or "staged" in result.output

    def test_version_command(self, runner: CliRunner):
        """Test version subcommand."""
        result = runner.invoke(main, ["version"])

        assert result.exit_code == 0
        assert "Detective Benno" in result.output
        assert "v" in result.output

    def test_init_command(self, runner: CliRunner, tmp_path: Path):
        """Test init subcommand creates config file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init"])

            assert result.exit_code == 0
            assert Path(".benno.yaml").exists()

            content = Path(".benno.yaml").read_text()
            assert "provider:" in content
            assert "openai" in content

    def test_init_command_no_overwrite(self, runner: CliRunner, tmp_path: Path):
        """Test init doesn't overwrite without confirmation."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create existing config
            Path(".benno.yaml").write_text("existing: config")

            # Answer 'n' to overwrite prompt
            runner.invoke(main, ["init"], input="n\n")

            # Original content preserved
            assert Path(".benno.yaml").read_text() == "existing: config"

    def test_investigate_command_with_file(self, runner: CliRunner, tmp_path: Path):
        """Test investigate command with file argument."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("test.py").write_text("print('hello')")

            with patch("detective_benno.cli.CodeReviewer") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.review_files.return_value = ReviewResult(
                    files_reviewed=1,
                    comments=[],
                )
                mock_instance._detect_language.return_value = "python"
                mock_reviewer.return_value = mock_instance

                result = runner.invoke(main, ["investigate", "--quiet", "test.py"])

                assert result.exit_code == 0

    def test_investigate_json_output(self, runner: CliRunner, tmp_path: Path):
        """Test --json outputs valid JSON."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("test.py").write_text("print('hello')")

            with patch("detective_benno.cli.CodeReviewer") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.review_files.return_value = ReviewResult(
                    files_reviewed=1,
                    comments=[
                        ReviewComment(
                            file_path="test.py",
                            line_start=1,
                            severity=Severity.INFO,
                            category="test",
                            message="Test message",
                        )
                    ],
                )
                mock_instance._detect_language.return_value = "python"
                mock_reviewer.return_value = mock_instance

                result = runner.invoke(main, ["investigate", "--json", "test.py"])

                # Should be valid JSON
                output = json.loads(result.output)
                assert output["files_reviewed"] == 1
                assert len(output["comments"]) == 1

    def test_investigate_provider_flag(self, runner: CliRunner, tmp_path: Path):
        """Test --provider flag overrides config."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("test.py").write_text("x = 1")

            with patch("detective_benno.cli.CodeReviewer") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.review_files.return_value = ReviewResult(
                    files_reviewed=1, comments=[]
                )
                mock_instance._detect_language.return_value = "python"
                mock_reviewer.return_value = mock_instance

                runner.invoke(
                    main, ["investigate", "--quiet", "--provider", "ollama", "test.py"]
                )

                # Check that CodeReviewer was called with ollama provider
                call_args = mock_reviewer.call_args
                config = call_args[1]["config"]
                assert config.provider.name == "ollama"

    def test_investigate_model_flag(self, runner: CliRunner, tmp_path: Path):
        """Test --model flag overrides config."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("test.py").write_text("x = 1")

            with patch("detective_benno.cli.CodeReviewer") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.review_files.return_value = ReviewResult(
                    files_reviewed=1, comments=[]
                )
                mock_instance._detect_language.return_value = "python"
                mock_reviewer.return_value = mock_instance

                runner.invoke(
                    main, ["investigate", "--quiet", "--model", "gpt-4o-mini", "test.py"]
                )

                call_args = mock_reviewer.call_args
                config = call_args[1]["config"]
                assert config.provider.model == "gpt-4o-mini"

    def test_investigate_level_flag(self, runner: CliRunner, tmp_path: Path):
        """Test --level flag sets investigation level."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("test.py").write_text("x = 1")

            with patch("detective_benno.cli.CodeReviewer") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.review_files.return_value = ReviewResult(
                    files_reviewed=1, comments=[]
                )
                mock_instance._detect_language.return_value = "python"
                mock_reviewer.return_value = mock_instance

                runner.invoke(
                    main, ["investigate", "--quiet", "--level", "detailed", "test.py"]
                )

                call_args = mock_reviewer.call_args
                config = call_args[1]["config"]
                assert config.level == "detailed"

    def test_exit_code_on_critical(self, runner: CliRunner, tmp_path: Path):
        """Test exit code 1 when critical issues found."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("test.py").write_text("x = 1")

            with patch("detective_benno.cli.CodeReviewer") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.review_files.return_value = ReviewResult(
                    files_reviewed=1,
                    comments=[
                        ReviewComment(
                            file_path="test.py",
                            line_start=1,
                            severity=Severity.CRITICAL,
                            category="security",
                            message="Critical issue",
                        )
                    ],
                )
                mock_instance._detect_language.return_value = "python"
                mock_reviewer.return_value = mock_instance

                result = runner.invoke(main, ["investigate", "--quiet", "test.py"])

                assert result.exit_code == 1

    def test_exit_code_success(self, runner: CliRunner, tmp_path: Path):
        """Test exit code 0 when no critical issues."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("test.py").write_text("x = 1")

            with patch("detective_benno.cli.CodeReviewer") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.review_files.return_value = ReviewResult(
                    files_reviewed=1,
                    comments=[
                        ReviewComment(
                            file_path="test.py",
                            line_start=1,
                            severity=Severity.WARNING,
                            category="test",
                            message="Warning only",
                        )
                    ],
                )
                mock_instance._detect_language.return_value = "python"
                mock_reviewer.return_value = mock_instance

                result = runner.invoke(main, ["investigate", "--quiet", "test.py"])

                assert result.exit_code == 0

    def test_config_file_flag(self, runner: CliRunner, tmp_path: Path):
        """Test --config flag loads custom config."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create custom config
            config_content = """
provider:
  name: ollama
  model: mistral
investigation:
  level: minimal
"""
            Path("custom.yaml").write_text(config_content)
            Path("test.py").write_text("x = 1")

            with patch("detective_benno.cli.CodeReviewer") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.review_files.return_value = ReviewResult(
                    files_reviewed=1, comments=[]
                )
                mock_instance._detect_language.return_value = "python"
                mock_reviewer.return_value = mock_instance

                runner.invoke(
                    main, ["investigate", "--quiet", "--config", "custom.yaml", "test.py"]
                )

                call_args = mock_reviewer.call_args
                config = call_args[1]["config"]
                assert config.provider.name == "ollama"

    def test_investigate_nonexistent_file(self, runner: CliRunner, tmp_path: Path):
        """Test error when file doesn't exist."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["investigate", "--quiet", "nonexistent.py"])

            assert result.exit_code == 1
            assert "not found" in result.output.lower()

    def test_staged_command(self, runner: CliRunner, tmp_path: Path):
        """Test staged command."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("detective_benno.cli._investigate_staged_changes") as mock_staged:
                mock_staged.return_value = ReviewResult(files_reviewed=0, comments=[])

                with patch("detective_benno.cli.CodeReviewer") as mock_reviewer:
                    mock_instance = MagicMock()
                    mock_reviewer.return_value = mock_instance

                    result = runner.invoke(main, ["staged", "--quiet"])

                    # Command should be recognized
                    assert "Error: Missing argument" not in result.output

    def test_diff_command(self, runner: CliRunner, tmp_path: Path):
        """Test diff command."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            with patch("detective_benno.cli.CodeReviewer") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.review_diff.return_value = ReviewResult(
                    files_reviewed=1, comments=[]
                )
                mock_reviewer.return_value = mock_instance

                result = runner.invoke(
                    main, ["diff", "--quiet"],
                    input="diff --git a/test.py b/test.py\n+hello"
                )

                # Should process the diff
                assert result.exit_code == 0
