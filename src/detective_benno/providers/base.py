"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any

from detective_benno.models import FileChange, ReviewComment, ReviewConfig


class LLMProvider(ABC):
    """Abstract base class for all LLM providers.

    Each provider must implement the review method to analyze code
    and return findings.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name identifier."""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model for this provider."""
        ...

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration.

        Returns:
            True if configuration is valid, False otherwise.
        """
        ...

    @abstractmethod
    def review(
        self,
        file: FileChange,
        config: ReviewConfig,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[list[ReviewComment], int]:
        """Execute code review using this provider.

        Args:
            file: The file to review.
            config: Review configuration.
            system_prompt: System prompt for the LLM.
            user_prompt: User prompt with file content.

        Returns:
            Tuple of (list of review comments, tokens used).
        """
        ...

    def _parse_response(self, response: dict[str, Any], file_path: str) -> list[ReviewComment]:
        """Parse LLM response into ReviewComment objects.

        Args:
            response: Parsed JSON response from LLM.
            file_path: Path to the reviewed file.

        Returns:
            List of ReviewComment objects.
        """
        from detective_benno.models import Severity

        comments = []
        for item in response.get("comments", []):
            try:
                comment = ReviewComment(
                    file_path=file_path,
                    line_start=item.get("line_start", 1),
                    line_end=item.get("line_end"),
                    severity=Severity(item.get("severity", "suggestion")),
                    category=item.get("category", "best-practice"),
                    message=item.get("message", ""),
                    suggestion=item.get("suggestion"),
                    suggested_code=item.get("suggested_code"),
                )
                comments.append(comment)
            except (ValueError, KeyError):
                continue
        return comments
