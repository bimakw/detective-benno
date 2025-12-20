"""Tests for inline review comments."""

from unittest.mock import MagicMock, patch

import pytest

from detective_benno.github.inline_comments import InlineReviewer
from detective_benno.models import ReviewComment, ReviewResult, Severity


class TestInlineReviewer:
    """Tests for InlineReviewer class."""

    @pytest.fixture
    def reviewer(self):
        """Create an InlineReviewer with mocked API."""
        with patch("detective_benno.github.inline_comments.GitHubAPI") as mock_api:
            mock_api_instance = MagicMock()
            mock_api.return_value = mock_api_instance
            reviewer = InlineReviewer(token="test-token", repo="owner/repo")
            reviewer.api = mock_api_instance
            yield reviewer

    @pytest.fixture
    def sample_result(self):
        """Create a sample review result."""
        return ReviewResult(
            files_reviewed=2,
            comments=[
                ReviewComment(
                    file_path="src/main.py",
                    line_start=10,
                    severity=Severity.CRITICAL,
                    category="security",
                    message="SQL injection vulnerability",
                    suggestion="Use parameterized queries",
                ),
                ReviewComment(
                    file_path="src/utils.py",
                    line_start=25,
                    line_end=30,
                    severity=Severity.WARNING,
                    category="performance",
                    message="O(n^2) complexity",
                    suggestion="Consider using a hash map",
                ),
                ReviewComment(
                    file_path="src/config.py",
                    line_start=5,
                    severity=Severity.SUGGESTION,
                    category="style",
                    message="Consider using a constant",
                    suggested_code="MAX_RETRIES = 3",
                ),
            ],
            model_used="gpt-4o",
            tokens_used=500,
        )

    @pytest.fixture
    def empty_result(self):
        """Create an empty review result."""
        return ReviewResult(
            files_reviewed=1,
            comments=[],
            model_used="gpt-4o",
            tokens_used=100,
        )

    def test_post_review_with_commit_sha(self, reviewer, sample_result):
        """Test posting a review with explicit commit SHA."""
        reviewer.api.create_review.return_value = {"id": 1}

        result = reviewer.post_review(
            pr_number=123,
            result=sample_result,
            commit_sha="abc123",
        )

        assert result == {"id": 1}
        reviewer.api.create_review.assert_called_once()

        call_args = reviewer.api.create_review.call_args
        assert call_args[1]["pr_number"] == 123
        assert call_args[1]["commit_sha"] == "abc123"
        assert call_args[1]["event"] == "REQUEST_CHANGES"  # Has critical issues
        assert len(call_args[1]["comments"]) == 3

    def test_post_review_fetches_commit_sha(self, reviewer, sample_result):
        """Test fetching commit SHA when not provided."""
        reviewer.api.get_pr_commits.return_value = [
            {"sha": "commit1"},
            {"sha": "commit2"},
        ]
        reviewer.api.create_review.return_value = {"id": 1}

        reviewer.post_review(pr_number=123, result=sample_result)

        reviewer.api.get_pr_commits.assert_called_once_with(123)
        call_args = reviewer.api.create_review.call_args
        assert call_args[1]["commit_sha"] == "commit2"  # Latest commit

    def test_post_review_no_commits_raises(self, reviewer, sample_result):
        """Test error when no commits found."""
        reviewer.api.get_pr_commits.return_value = []

        with pytest.raises(ValueError, match="Could not determine commit SHA"):
            reviewer.post_review(pr_number=123, result=sample_result)

    def test_post_review_event_comment_on_warnings(self, reviewer):
        """Test review event is COMMENT when only warnings."""
        result = ReviewResult(
            files_reviewed=1,
            comments=[
                ReviewComment(
                    file_path="test.py",
                    line_start=1,
                    severity=Severity.WARNING,
                    category="test",
                    message="Warning message",
                )
            ],
        )

        reviewer.api.create_review.return_value = {"id": 1}

        reviewer.post_review(pr_number=123, result=result, commit_sha="abc123")

        call_args = reviewer.api.create_review.call_args
        assert call_args[1]["event"] == "COMMENT"

    def test_post_review_event_comment_on_suggestions(self, reviewer):
        """Test review event is COMMENT when only suggestions."""
        result = ReviewResult(
            files_reviewed=1,
            comments=[
                ReviewComment(
                    file_path="test.py",
                    line_start=1,
                    severity=Severity.SUGGESTION,
                    category="test",
                    message="Suggestion message",
                )
            ],
        )

        reviewer.api.create_review.return_value = {"id": 1}

        reviewer.post_review(pr_number=123, result=result, commit_sha="abc123")

        call_args = reviewer.api.create_review.call_args
        assert call_args[1]["event"] == "COMMENT"

    def test_post_summary_comment(self, reviewer, sample_result):
        """Test posting a summary comment."""
        reviewer.api.post_comment.return_value = {"id": 1}

        result = reviewer.post_summary_comment(pr_number=123, result=sample_result)

        assert result == {"id": 1}
        reviewer.api.post_comment.assert_called_once()

        call_args = reviewer.api.post_comment.call_args
        assert call_args[0][0] == 123
        assert "Detective Benno" in call_args[0][1]

    def test_build_summary_with_critical(self, reviewer, sample_result):
        """Test summary building with critical issues."""
        summary = reviewer._build_summary(sample_result)

        assert "REQUIRES ATTENTION" in summary
        assert "**Files Investigated:** 2" in summary
        assert "1 critical" in summary

    def test_build_summary_no_issues(self, reviewer, empty_result):
        """Test summary building with no issues."""
        summary = reviewer._build_summary(empty_result)

        assert "Looking Good" in summary

    def test_build_inline_comments(self, reviewer, sample_result):
        """Test building inline comments format."""
        comments = reviewer._build_inline_comments(sample_result.comments)

        assert len(comments) == 3

        # Check first comment (critical)
        assert comments[0]["path"] == "src/main.py"
        assert comments[0]["line"] == 10
        assert "CRITICAL" in comments[0]["body"]
        assert "SQL injection" in comments[0]["body"]
        assert "Recommendation:" in comments[0]["body"]

        # Check second comment (multi-line)
        assert comments[1]["start_line"] == 25
        assert comments[1]["line"] == 30

        # Check third comment (with suggested code)
        assert "```suggestion" in comments[2]["body"]
        assert "MAX_RETRIES = 3" in comments[2]["body"]

    def test_build_inline_comment_with_emoji(self, reviewer):
        """Test emoji mapping in inline comments."""
        comments = [
            ReviewComment(
                file_path="test.py",
                line_start=1,
                severity=Severity.CRITICAL,
                category="test",
                message="Critical issue",
            ),
            ReviewComment(
                file_path="test.py",
                line_start=2,
                severity=Severity.WARNING,
                category="test",
                message="Warning issue",
            ),
            ReviewComment(
                file_path="test.py",
                line_start=3,
                severity=Severity.SUGGESTION,
                category="test",
                message="Suggestion",
            ),
            ReviewComment(
                file_path="test.py",
                line_start=4,
                severity=Severity.INFO,
                category="test",
                message="Info",
            ),
        ]

        inline_comments = reviewer._build_inline_comments(comments)

        assert ":rotating_light:" in inline_comments[0]["body"]
        assert ":warning:" in inline_comments[1]["body"]
        assert ":bulb:" in inline_comments[2]["body"]
        assert ":information_source:" in inline_comments[3]["body"]

    def test_build_full_report_empty(self, reviewer, empty_result):
        """Test full report with no findings."""
        report = reviewer._build_full_report(empty_result)

        assert "Detective Benno" in report
        assert "No issues found" in report

    def test_build_full_report_with_findings(self, reviewer, sample_result):
        """Test full report with findings."""
        report = reviewer._build_full_report(sample_result)

        assert "Detective Benno" in report
        assert "CRITICAL" in report
        assert "WARNING" in report
        assert "SUGGESTION" in report
        assert "SQL injection" in report
        assert "O(n^2)" in report

    def test_build_full_report_status_critical(self, reviewer, sample_result):
        """Test report status with critical issues."""
        report = reviewer._build_full_report(sample_result)

        assert "REQUIRES IMMEDIATE ATTENTION" in report

    def test_build_full_report_status_warnings(self, reviewer):
        """Test report status with only warnings."""
        result = ReviewResult(
            files_reviewed=1,
            comments=[
                ReviewComment(
                    file_path="test.py",
                    line_start=1,
                    severity=Severity.WARNING,
                    category="test",
                    message="Warning",
                )
            ],
        )

        report = reviewer._build_full_report(result)

        assert "REQUIRES ATTENTION" in report
        assert "IMMEDIATE" not in report

    def test_build_full_report_status_minor(self, reviewer):
        """Test report status with only suggestions."""
        result = ReviewResult(
            files_reviewed=1,
            comments=[
                ReviewComment(
                    file_path="test.py",
                    line_start=1,
                    severity=Severity.SUGGESTION,
                    category="test",
                    message="Suggestion",
                )
            ],
        )

        report = reviewer._build_full_report(result)

        assert "MINOR ISSUES" in report

    def test_close(self, reviewer):
        """Test closing the reviewer."""
        reviewer.close()

        reviewer.api.close.assert_called_once()

    def test_context_manager(self):
        """Test using reviewer as context manager."""
        with patch("detective_benno.github.inline_comments.GitHubAPI") as mock_api:
            mock_api_instance = MagicMock()
            mock_api.return_value = mock_api_instance

            with InlineReviewer(token="test", repo="owner/repo"):
                pass

            mock_api_instance.close.assert_called_once()
