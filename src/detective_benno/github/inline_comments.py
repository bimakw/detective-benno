"""Inline review comments for GitHub PRs."""

from typing import Any

from detective_benno.github.api import GitHubAPI
from detective_benno.models import ReviewComment, ReviewResult, Severity


class InlineReviewer:
    """Posts inline code review comments on GitHub PRs.

    Converts Detective Benno findings into GitHub PR review comments
    with proper line positioning and severity indicators.
    """

    SEVERITY_EMOJI = {
        Severity.CRITICAL: ":rotating_light:",
        Severity.WARNING: ":warning:",
        Severity.SUGGESTION: ":bulb:",
        Severity.INFO: ":information_source:",
    }

    def __init__(
        self,
        token: str | None = None,
        repo: str | None = None,
    ) -> None:
        """Initialize inline reviewer.

        Args:
            token: GitHub token.
            repo: Repository in format "owner/repo".
        """
        self.api = GitHubAPI(token=token, repo=repo)

    def post_review(
        self,
        pr_number: int,
        result: ReviewResult,
        commit_sha: str | None = None,
    ) -> dict[str, Any]:
        """Post a review with inline comments.

        Args:
            pr_number: Pull request number.
            result: Review result from Detective Benno.
            commit_sha: Commit SHA to review. If None, uses latest.

        Returns:
            Created review object.
        """
        if commit_sha is None:
            commits = self.api.get_pr_commits(pr_number)
            if commits:
                commit_sha = commits[-1]["sha"]
            else:
                raise ValueError("Could not determine commit SHA")

        # Build summary
        summary = self._build_summary(result)

        # Convert comments to GitHub format
        inline_comments = self._build_inline_comments(result.comments)

        # Determine review event based on findings
        if result.has_critical_issues:
            event = "REQUEST_CHANGES"
        elif result.warning_count > 0:
            event = "COMMENT"
        else:
            event = "COMMENT"

        return self.api.create_review(
            pr_number=pr_number,
            commit_sha=commit_sha,
            body=summary,
            event=event,
            comments=inline_comments if inline_comments else None,
        )

    def post_summary_comment(
        self,
        pr_number: int,
        result: ReviewResult,
    ) -> dict[str, Any]:
        """Post a summary comment (without inline comments).

        Args:
            pr_number: Pull request number.
            result: Review result from Detective Benno.

        Returns:
            Created comment object.
        """
        body = self._build_full_report(result)
        return self.api.post_comment(pr_number, body)

    def _build_summary(self, result: ReviewResult) -> str:
        """Build review summary message."""
        lines = [
            "## :mag: Detective Benno Investigation Report",
            "",
            f"**Files Investigated:** {result.files_reviewed}",
            f"**Findings:** {len(result.comments)} "
            f"({result.critical_count} critical, "
            f"{result.warning_count} warnings, "
            f"{result.suggestion_count} suggestions)",
            "",
        ]

        if result.has_critical_issues:
            lines.append(":rotating_light: **Status: REQUIRES ATTENTION**")
        elif result.warning_count > 0:
            lines.append(":warning: **Status: Review Recommended**")
        else:
            lines.append(":white_check_mark: **Status: Looking Good**")

        lines.extend([
            "",
            f"_Model: {result.model_used} | Tokens: {result.tokens_used}_",
        ])

        return "\n".join(lines)

    def _build_inline_comments(
        self,
        comments: list[ReviewComment],
    ) -> list[dict[str, Any]]:
        """Convert review comments to GitHub inline comment format."""
        inline_comments = []

        for comment in comments:
            emoji = self.SEVERITY_EMOJI.get(comment.severity, "")
            body_parts = [
                f"{emoji} **{comment.severity.value.upper()}** ({comment.category})",
                "",
                comment.message,
            ]

            if comment.suggestion:
                body_parts.extend([
                    "",
                    f"**Recommendation:** {comment.suggestion}",
                ])

            if comment.suggested_code:
                # Format as GitHub suggestion for one-click apply
                body_parts.extend([
                    "",
                    "```suggestion",
                    comment.suggested_code,
                    "```",
                ])

            inline_comment: dict[str, Any] = {
                "path": comment.file_path,
                "line": comment.line_start,
                "body": "\n".join(body_parts),
            }

            # Add side for multi-line comments
            if comment.line_end and comment.line_end != comment.line_start:
                inline_comment["start_line"] = comment.line_start
                inline_comment["line"] = comment.line_end

            inline_comments.append(inline_comment)

        return inline_comments

    def _build_full_report(self, result: ReviewResult) -> str:
        """Build full report as markdown comment."""
        lines = [
            "## :mag: Detective Benno Investigation Report",
            "",
            "```",
            "============================================",
            "   DETECTIVE BENNO - INVESTIGATION REPORT",
            "============================================",
            "",
            f"Files Investigated: {result.files_reviewed}",
            f"Findings: {len(result.comments)} "
            f"({result.critical_count} critical, "
            f"{result.warning_count} warnings, "
            f"{result.suggestion_count} suggestions)",
            "============================================",
            "```",
            "",
        ]

        if not result.comments:
            lines.append(":white_check_mark: **Case closed - No issues found!**")
            return "\n".join(lines)

        # Group by severity
        for severity in [Severity.CRITICAL, Severity.WARNING, Severity.SUGGESTION, Severity.INFO]:
            severity_comments = [c for c in result.comments if c.severity == severity]
            if not severity_comments:
                continue

            emoji = self.SEVERITY_EMOJI.get(severity, "")
            lines.extend([
                f"### {emoji} {severity.value.upper()}",
                "",
            ])

            for comment in severity_comments:
                lines.extend([
                    f"**`{comment.file_path}:{comment.line_range}`** ({comment.category})",
                    "",
                    f"> {comment.message}",
                    "",
                ])

                if comment.suggestion:
                    lines.append(f"*Recommendation:* {comment.suggestion}")
                    lines.append("")

                if comment.suggested_code:
                    lines.extend([
                        "<details>",
                        "<summary>Suggested fix</summary>",
                        "",
                        "```",
                        comment.suggested_code,
                        "```",
                        "</details>",
                        "",
                    ])

        # Status
        lines.append("---")
        if result.has_critical_issues:
            lines.append(":rotating_light: **Case Status: REQUIRES IMMEDIATE ATTENTION**")
        elif result.warning_count > 0:
            lines.append(":warning: **Case Status: REQUIRES ATTENTION**")
        else:
            lines.append(":white_check_mark: **Case Status: MINOR ISSUES**")

        lines.extend([
            "",
            f"_Investigated with {result.model_used}_",
        ])

        return "\n".join(lines)

    def close(self) -> None:
        """Close API client."""
        self.api.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
