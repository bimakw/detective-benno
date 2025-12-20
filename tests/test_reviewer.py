"""Tests for CodeReviewer."""

from typing import Any
from unittest.mock import patch

from detective_benno.models import (
    FileChange,
    ProviderConfig,
    ReviewConfig,
    Severity,
)
from detective_benno.providers.base import LLMProvider
from detective_benno.reviewer import CodeReviewer


class MockProvider(LLMProvider):
    """Mock provider for testing."""

    def __init__(self, responses: list[dict[str, Any]] | None = None):
        self._responses = responses or []
        self._call_count = 0

    @property
    def name(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "mock-model"

    def validate_config(self) -> bool:
        return True

    def review(self, file, config, system_prompt, user_prompt):
        if self._call_count < len(self._responses):
            response = self._responses[self._call_count]
            self._call_count += 1
            comments = self._parse_response(response, file.path)
            return comments, 100
        return [], 0


class TestCodeReviewer:
    """Tests for CodeReviewer class."""

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        reviewer = CodeReviewer()

        assert reviewer.config is not None
        assert reviewer.config.level == "standard"

    def test_init_with_custom_config(self, openai_config: ReviewConfig):
        """Test initialization with custom config."""
        reviewer = CodeReviewer(config=openai_config)

        assert reviewer.config == openai_config
        assert reviewer.config.provider.name == "openai"

    def test_init_with_provider(self):
        """Test initialization with custom provider."""
        mock_provider = MockProvider()
        reviewer = CodeReviewer(provider=mock_provider)

        assert reviewer.provider == mock_provider

    def test_provider_created_from_config(self, openai_config: ReviewConfig):
        """Test that provider is created from config when not provided."""
        with patch("detective_benno.reviewer.ProviderFactory") as mock_factory:
            mock_provider = MockProvider()
            mock_factory.create.return_value = mock_provider

            reviewer = CodeReviewer(config=openai_config)
            _ = reviewer.provider  # Access to trigger creation

            mock_factory.create.assert_called_once()

    def test_review_files_empty_list(self):
        """Test reviewing empty file list."""
        reviewer = CodeReviewer(provider=MockProvider())
        result = reviewer.review_files([])

        assert result.files_reviewed == 0
        assert len(result.comments) == 0

    def test_review_files_single_file(
        self,
        sample_python_file: FileChange,
        mock_review_response_critical: dict[str, Any],
    ):
        """Test reviewing a single file."""
        mock_provider = MockProvider(responses=[mock_review_response_critical])
        reviewer = CodeReviewer(provider=mock_provider)

        result = reviewer.review_files([sample_python_file])

        assert result.files_reviewed == 1
        assert len(result.comments) == 2
        assert result.comments[0].severity == Severity.CRITICAL

    def test_review_files_multiple_files(
        self,
        sample_python_file: FileChange,
        mock_review_response_critical: dict[str, Any],
        mock_review_response_warnings: dict[str, Any],
    ):
        """Test reviewing multiple files."""
        file2 = FileChange(
            path="src/utils.py",
            content="def helper(): pass",
            language="python",
        )

        mock_provider = MockProvider(
            responses=[
                mock_review_response_critical,
                mock_review_response_warnings,
            ]
        )
        reviewer = CodeReviewer(provider=mock_provider)

        result = reviewer.review_files([sample_python_file, file2])

        assert result.files_reviewed == 2
        assert len(result.comments) == 3  # 2 critical + 1 warning

    def test_review_files_respects_max_comments(
        self,
        sample_python_file: FileChange,
        mock_review_response_critical: dict[str, Any],
    ):
        """Test that max_comments limit is respected."""
        config = ReviewConfig(max_comments=1)
        mock_provider = MockProvider(responses=[mock_review_response_critical])
        reviewer = CodeReviewer(config=config, provider=mock_provider)

        result = reviewer.review_files([sample_python_file])

        assert len(result.comments) == 1

    def test_review_files_ignores_patterns(
        self,
        mock_review_response_critical: dict[str, Any],
    ):
        """Test that ignored files are skipped."""
        config = ReviewConfig(ignore_files=["*.md", "test_*.py"])
        mock_provider = MockProvider(responses=[mock_review_response_critical])
        reviewer = CodeReviewer(config=config, provider=mock_provider)

        ignored_file = FileChange(
            path="README.md",
            content="# Readme",
            language="markdown",
        )
        ignored_test = FileChange(
            path="test_something.py",
            content="def test(): pass",
            language="python",
        )
        normal_file = FileChange(
            path="src/main.py",
            content="print('hello')",
            language="python",
        )

        result = reviewer.review_files([ignored_file, ignored_test, normal_file])

        # Only normal_file should be reviewed
        assert result.files_reviewed == 1
        assert mock_provider._call_count == 1

    def test_review_diff(self, sample_diff: str):
        """Test reviewing a git diff."""
        mock_provider = MockProvider(
            responses=[{"comments": []}]
        )
        reviewer = CodeReviewer(provider=mock_provider)

        result = reviewer.review_diff(sample_diff)

        assert result.files_reviewed == 1

    def test_review_file_reads_from_disk(self, temp_python_file):
        """Test that review_file reads content from disk."""
        mock_provider = MockProvider(responses=[{"comments": []}])
        reviewer = CodeReviewer(provider=mock_provider)

        result = reviewer.review_file(str(temp_python_file))

        assert result.files_reviewed == 1

    def test_review_file_with_content(self):
        """Test review_file with provided content."""
        mock_provider = MockProvider(responses=[{"comments": []}])
        reviewer = CodeReviewer(provider=mock_provider)

        result = reviewer.review_file("fake.py", content="x = 1")

        assert result.files_reviewed == 1

    def test_detect_language_python(self):
        """Test language detection for Python files."""
        reviewer = CodeReviewer(provider=MockProvider())

        assert reviewer._detect_language("main.py") == "python"
        assert reviewer._detect_language("test.PY") == "python"
        assert reviewer._detect_language("/path/to/script.py") == "python"

    def test_detect_language_javascript(self):
        """Test language detection for JavaScript files."""
        reviewer = CodeReviewer(provider=MockProvider())

        assert reviewer._detect_language("app.js") == "javascript"
        assert reviewer._detect_language("component.jsx") == "javascript"

    def test_detect_language_typescript(self):
        """Test language detection for TypeScript files."""
        reviewer = CodeReviewer(provider=MockProvider())

        assert reviewer._detect_language("app.ts") == "typescript"
        assert reviewer._detect_language("component.tsx") == "typescript"

    def test_detect_language_go(self):
        """Test language detection for Go files."""
        reviewer = CodeReviewer(provider=MockProvider())

        assert reviewer._detect_language("main.go") == "go"

    def test_detect_language_rust(self):
        """Test language detection for Rust files."""
        reviewer = CodeReviewer(provider=MockProvider())

        assert reviewer._detect_language("lib.rs") == "rust"

    def test_detect_language_unknown(self):
        """Test language detection for unknown extensions."""
        reviewer = CodeReviewer(provider=MockProvider())

        assert reviewer._detect_language("file.xyz") == "unknown"
        assert reviewer._detect_language("noextension") == "unknown"

    def test_parse_diff_single_file(self, sample_diff: str):
        """Test parsing diff with single file."""
        reviewer = CodeReviewer(provider=MockProvider())

        files = reviewer._parse_diff(sample_diff)

        assert len(files) == 1
        assert files[0].path == "src/main.py"
        assert files[0].diff is not None

    def test_parse_diff_multiple_files(self):
        """Test parsing diff with multiple files."""
        multi_diff = """diff --git a/file1.py b/file1.py
--- a/file1.py
+++ b/file1.py
@@ -1 +1 @@
-old
+new
diff --git a/file2.py b/file2.py
--- a/file2.py
+++ b/file2.py
@@ -1 +1 @@
-foo
+bar"""

        reviewer = CodeReviewer(provider=MockProvider())
        files = reviewer._parse_diff(multi_diff)

        assert len(files) == 2
        assert files[0].path == "file1.py"
        assert files[1].path == "file2.py"

    def test_system_prompt_includes_guidelines(self):
        """Test that system prompt includes custom guidelines."""
        config = ReviewConfig(
            guidelines=[
                "Check for SQL injection",
                "Look for hardcoded secrets",
            ]
        )
        reviewer = CodeReviewer(config=config, provider=MockProvider())

        prompt = reviewer._get_system_prompt()

        assert "SQL injection" in prompt
        assert "hardcoded secrets" in prompt
        assert "Additional investigation guidelines" in prompt

    def test_system_prompt_base_content(self):
        """Test that system prompt contains base instructions."""
        reviewer = CodeReviewer(provider=MockProvider())

        prompt = reviewer._get_system_prompt()

        assert "Detective Benno" in prompt
        assert "Security vulnerabilities" in prompt
        assert "JSON" in prompt

    def test_result_includes_model_info(
        self,
        sample_python_file: FileChange,
    ):
        """Test that result includes model information."""
        config = ReviewConfig(
            provider=ProviderConfig(name="openai", model="gpt-4o-mini")
        )
        mock_provider = MockProvider(responses=[{"comments": []}])
        reviewer = CodeReviewer(config=config, provider=mock_provider)

        result = reviewer.review_files([sample_python_file])

        assert result.model_used == "gpt-4o-mini"

    def test_tokens_accumulated(
        self,
        sample_python_file: FileChange,
    ):
        """Test that tokens are accumulated across files."""
        file2 = FileChange(path="f2.py", content="x=1", language="python")

        mock_provider = MockProvider(
            responses=[{"comments": []}, {"comments": []}]
        )
        reviewer = CodeReviewer(provider=mock_provider)

        result = reviewer.review_files([sample_python_file, file2])

        assert result.tokens_used == 200  # 100 per file
