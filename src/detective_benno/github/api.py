"""GitHub API wrapper for Detective Benno."""

import os
from typing import Any

import httpx


class GitHubAPI:
    """Lightweight GitHub API client using httpx.

    Uses GitHub REST API v3 for:
    - Posting PR review comments
    - Creating check runs
    - Getting PR diff information
    """

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: str | None = None,
        repo: str | None = None,
    ) -> None:
        """Initialize GitHub API client.

        Args:
            token: GitHub token. Falls back to GITHUB_TOKEN env var.
            repo: Repository in format "owner/repo".
        """
        self._token = token or os.environ.get("GITHUB_TOKEN")
        self._repo = repo or os.environ.get("GITHUB_REPOSITORY")
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

            self._client = httpx.Client(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    def get_pr_diff(self, pr_number: int) -> str:
        """Get the diff for a pull request.

        Args:
            pr_number: Pull request number.

        Returns:
            Diff content as string.
        """
        response = self.client.get(
            f"/repos/{self._repo}/pulls/{pr_number}",
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        response.raise_for_status()
        return response.text

    def get_pr_files(self, pr_number: int) -> list[dict[str, Any]]:
        """Get list of files changed in a pull request.

        Args:
            pr_number: Pull request number.

        Returns:
            List of file change objects.
        """
        response = self.client.get(
            f"/repos/{self._repo}/pulls/{pr_number}/files"
        )
        response.raise_for_status()
        return response.json()

    def get_pr_commits(self, pr_number: int) -> list[dict[str, Any]]:
        """Get commits in a pull request.

        Args:
            pr_number: Pull request number.

        Returns:
            List of commit objects.
        """
        response = self.client.get(
            f"/repos/{self._repo}/pulls/{pr_number}/commits"
        )
        response.raise_for_status()
        return response.json()

    def post_comment(self, pr_number: int, body: str) -> dict[str, Any]:
        """Post a general comment on a pull request.

        Args:
            pr_number: Pull request number.
            body: Comment body (markdown supported).

        Returns:
            Created comment object.
        """
        response = self.client.post(
            f"/repos/{self._repo}/issues/{pr_number}/comments",
            json={"body": body},
        )
        response.raise_for_status()
        return response.json()

    def create_review(
        self,
        pr_number: int,
        commit_sha: str,
        body: str,
        event: str = "COMMENT",
        comments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a pull request review with inline comments.

        Args:
            pr_number: Pull request number.
            commit_sha: The SHA of the commit to review.
            body: Top-level comment for the review.
            event: Review action (COMMENT, APPROVE, REQUEST_CHANGES).
            comments: List of inline comments with path, line, body.

        Returns:
            Created review object.
        """
        payload: dict[str, Any] = {
            "commit_id": commit_sha,
            "body": body,
            "event": event,
        }

        if comments:
            payload["comments"] = comments

        response = self.client.post(
            f"/repos/{self._repo}/pulls/{pr_number}/reviews",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def create_check_run(
        self,
        name: str,
        head_sha: str,
        status: str = "in_progress",
        output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a check run.

        Args:
            name: Name of the check.
            head_sha: The SHA of the commit.
            status: Check status (queued, in_progress, completed).
            output: Optional output with title, summary, annotations.

        Returns:
            Created check run object.
        """
        payload: dict[str, Any] = {
            "name": name,
            "head_sha": head_sha,
            "status": status,
        }

        if output:
            payload["output"] = output

        response = self.client.post(
            f"/repos/{self._repo}/check-runs",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def update_check_run(
        self,
        check_run_id: int,
        status: str | None = None,
        conclusion: str | None = None,
        output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update a check run.

        Args:
            check_run_id: ID of the check run to update.
            status: New status (queued, in_progress, completed).
            conclusion: Conclusion if completed (success, failure, etc.).
            output: Optional output with title, summary, annotations.

        Returns:
            Updated check run object.
        """
        payload: dict[str, Any] = {}

        if status:
            payload["status"] = status
        if conclusion:
            payload["conclusion"] = conclusion
        if output:
            payload["output"] = output

        response = self.client.patch(
            f"/repos/{self._repo}/check-runs/{check_run_id}",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
