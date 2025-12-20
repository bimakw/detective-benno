"""GitHub integration for Detective Benno."""

from detective_benno.github.api import GitHubAPI
from detective_benno.github.inline_comments import InlineReviewer

__all__ = ["GitHubAPI", "InlineReviewer"]
