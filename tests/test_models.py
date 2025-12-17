"""Tests for data models."""


from detective_benno.models import (
    FileChange,
    ReviewComment,
    ReviewConfig,
    ReviewResult,
    Severity,
)


class TestSeverity:
    """Tests for Severity enum."""

    def test_severity_values(self):
        assert Severity.CRITICAL.value == "critical"
        assert Severity.WARNING.value == "warning"
        assert Severity.SUGGESTION.value == "suggestion"
        assert Severity.INFO.value == "info"


class TestReviewComment:
    """Tests for ReviewComment model."""

    def test_create_comment(self):
        comment = ReviewComment(
            file_path="src/main.py",
            line_start=10,
            severity=Severity.WARNING,
            category="security",
            message="Potential issue found",
        )
        assert comment.file_path == "src/main.py"
        assert comment.line_start == 10
        assert comment.severity == Severity.WARNING

    def test_line_range_single(self):
        comment = ReviewComment(
            file_path="test.py",
            line_start=5,
            severity=Severity.INFO,
            category="style",
            message="Test",
        )
        assert comment.line_range == "5"

    def test_line_range_multiple(self):
        comment = ReviewComment(
            file_path="test.py",
            line_start=5,
            line_end=10,
            severity=Severity.INFO,
            category="style",
            message="Test",
        )
        assert comment.line_range == "5-10"


class TestReviewResult:
    """Tests for ReviewResult model."""

    def test_empty_result(self):
        result = ReviewResult()
        assert result.files_reviewed == 0
        assert result.comments == []
        assert result.critical_count == 0
        assert not result.has_critical_issues

    def test_result_with_comments(self):
        comments = [
            ReviewComment(
                file_path="a.py",
                line_start=1,
                severity=Severity.CRITICAL,
                category="security",
                message="Critical issue",
            ),
            ReviewComment(
                file_path="b.py",
                line_start=2,
                severity=Severity.WARNING,
                category="performance",
                message="Warning",
            ),
            ReviewComment(
                file_path="c.py",
                line_start=3,
                severity=Severity.SUGGESTION,
                category="style",
                message="Suggestion",
            ),
        ]
        result = ReviewResult(files_reviewed=3, comments=comments)

        assert result.critical_count == 1
        assert result.warning_count == 1
        assert result.suggestion_count == 1
        assert result.has_critical_issues


class TestReviewConfig:
    """Tests for ReviewConfig model."""

    def test_default_config(self):
        config = ReviewConfig()
        assert config.level == "standard"
        assert config.max_comments == 10
        assert config.model == "gpt-4o"
        assert config.temperature == 0.3

    def test_custom_config(self):
        config = ReviewConfig(
            level="detailed",
            max_comments=20,
            guidelines=["Check for SQL injection"],
        )
        assert config.level == "detailed"
        assert config.max_comments == 20
        assert "Check for SQL injection" in config.guidelines


class TestFileChange:
    """Tests for FileChange model."""

    def test_file_with_content(self):
        file = FileChange(
            path="src/main.py",
            content="print('hello')",
            language="python",
        )
        assert file.path == "src/main.py"
        assert file.content == "print('hello')"
        assert file.language == "python"

    def test_file_with_diff(self):
        file = FileChange(
            path="src/main.py",
            diff="+added line\n-removed line",
        )
        assert file.diff == "+added line\n-removed line"
