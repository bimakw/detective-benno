"""Tests for GitHub API wrapper."""

from unittest.mock import MagicMock

import httpx

from detective_benno.github.api import GitHubAPI


class TestGitHubAPI:
    """Tests for GitHubAPI class."""

    def test_init_with_token(self):
        """Test initialization with explicit token."""
        api = GitHubAPI(token="test-token", repo="owner/repo")

        assert api._token == "test-token"
        assert api._repo == "owner/repo"
        assert api._client is None

    def test_init_from_env(self, monkeypatch):
        """Test initialization from environment variables."""
        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "env-owner/env-repo")

        api = GitHubAPI()

        assert api._token == "env-token"
        assert api._repo == "env-owner/env-repo"

    def test_client_lazy_initialization(self):
        """Test HTTP client is lazily initialized."""
        api = GitHubAPI(token="test-token", repo="owner/repo")

        assert api._client is None
        client = api.client
        assert client is not None
        assert isinstance(client, httpx.Client)

        # Same client returned on subsequent calls
        assert api.client is client

    def test_client_headers(self):
        """Test client has correct headers."""
        api = GitHubAPI(token="test-token", repo="owner/repo")

        client = api.client
        assert client.headers["Accept"] == "application/vnd.github.v3+json"
        assert client.headers["Authorization"] == "Bearer test-token"

    def test_get_pr_diff(self):
        """Test getting PR diff."""
        api = GitHubAPI(token="test-token", repo="owner/repo")

        mock_response = MagicMock()
        mock_response.text = "diff --git a/file.py b/file.py\n+new line"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        api._client = mock_client

        diff = api.get_pr_diff(123)

        assert diff == mock_response.text
        mock_client.get.assert_called_once_with(
            "/repos/owner/repo/pulls/123",
            headers={"Accept": "application/vnd.github.v3.diff"},
        )

    def test_get_pr_files(self):
        """Test getting PR files list."""
        api = GitHubAPI(token="test-token", repo="owner/repo")

        expected_files = [
            {"filename": "file1.py", "status": "modified"},
            {"filename": "file2.py", "status": "added"},
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = expected_files
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        api._client = mock_client

        files = api.get_pr_files(123)

        assert files == expected_files
        mock_client.get.assert_called_once_with(
            "/repos/owner/repo/pulls/123/files"
        )

    def test_get_pr_commits(self):
        """Test getting PR commits."""
        api = GitHubAPI(token="test-token", repo="owner/repo")

        expected_commits = [
            {"sha": "abc123", "message": "First commit"},
            {"sha": "def456", "message": "Second commit"},
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = expected_commits
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        api._client = mock_client

        commits = api.get_pr_commits(123)

        assert commits == expected_commits

    def test_post_comment(self):
        """Test posting a PR comment."""
        api = GitHubAPI(token="test-token", repo="owner/repo")

        expected_comment = {"id": 1, "body": "Test comment"}

        mock_response = MagicMock()
        mock_response.json.return_value = expected_comment
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        api._client = mock_client

        comment = api.post_comment(123, "Test comment")

        assert comment == expected_comment
        mock_client.post.assert_called_once_with(
            "/repos/owner/repo/issues/123/comments",
            json={"body": "Test comment"},
        )

    def test_create_review(self):
        """Test creating a PR review."""
        api = GitHubAPI(token="test-token", repo="owner/repo")

        expected_review = {"id": 1, "state": "COMMENTED"}

        mock_response = MagicMock()
        mock_response.json.return_value = expected_review
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        api._client = mock_client

        review = api.create_review(
            pr_number=123,
            commit_sha="abc123",
            body="Review summary",
            event="COMMENT",
            comments=[{"path": "file.py", "line": 10, "body": "Issue here"}],
        )

        assert review == expected_review
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/repos/owner/repo/pulls/123/reviews"
        assert call_args[1]["json"]["commit_id"] == "abc123"
        assert call_args[1]["json"]["event"] == "COMMENT"
        assert len(call_args[1]["json"]["comments"]) == 1

    def test_create_review_without_comments(self):
        """Test creating a review without inline comments."""
        api = GitHubAPI(token="test-token", repo="owner/repo")

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        api._client = mock_client

        api.create_review(
            pr_number=123,
            commit_sha="abc123",
            body="LGTM",
            event="APPROVE",
        )

        call_args = mock_client.post.call_args
        assert "comments" not in call_args[1]["json"]

    def test_create_check_run(self):
        """Test creating a check run."""
        api = GitHubAPI(token="test-token", repo="owner/repo")

        expected_check = {"id": 1, "name": "Detective Benno"}

        mock_response = MagicMock()
        mock_response.json.return_value = expected_check
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        api._client = mock_client

        check = api.create_check_run(
            name="Detective Benno",
            head_sha="abc123",
            status="in_progress",
        )

        assert check == expected_check
        mock_client.post.assert_called_once()

    def test_update_check_run(self):
        """Test updating a check run."""
        api = GitHubAPI(token="test-token", repo="owner/repo")

        expected_check = {"id": 1, "status": "completed", "conclusion": "success"}

        mock_response = MagicMock()
        mock_response.json.return_value = expected_check
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.patch.return_value = mock_response
        api._client = mock_client

        check = api.update_check_run(
            check_run_id=1,
            status="completed",
            conclusion="success",
        )

        assert check == expected_check
        mock_client.patch.assert_called_once()

    def test_close(self):
        """Test closing the client."""
        api = GitHubAPI(token="test-token", repo="owner/repo")

        # Initialize client
        _ = api.client
        assert api._client is not None

        # Close
        api.close()
        assert api._client is None

    def test_context_manager(self):
        """Test using API as context manager."""
        with GitHubAPI(token="test-token", repo="owner/repo") as api:
            _ = api.client
            assert api._client is not None

        assert api._client is None
