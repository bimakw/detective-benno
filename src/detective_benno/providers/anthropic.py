"""Anthropic Claude provider for Detective Benno."""

import json
import os

from anthropic import Anthropic

from detective_benno.models import FileChange, ReviewComment, ReviewConfig
from detective_benno.providers.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider for code review.

    Supports models: claude-sonnet-4-20250514, claude-opus-4-5-20251101,
    claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            model: Model to use. Defaults to claude-sonnet-4-20250514.
            base_url: Optional base URL for API (for proxies/alternatives).
        """
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._model = model or "claude-sonnet-4-20250514"
        self._base_url = base_url
        self._client: Anthropic | None = None

    @property
    def name(self) -> str:
        """Return provider name."""
        return "anthropic"

    @property
    def default_model(self) -> str:
        """Return default model."""
        return "claude-sonnet-4-20250514"

    @property
    def client(self) -> Anthropic:
        """Get or create Anthropic client."""
        if self._client is None:
            kwargs: dict = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = Anthropic(**kwargs)
        return self._client

    def validate_config(self) -> bool:
        """Validate that API key is available."""
        return bool(self._api_key)

    def review(
        self,
        file: FileChange,
        config: ReviewConfig,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[list[ReviewComment], int]:
        """Execute code review using Anthropic Claude.

        Args:
            file: The file to review.
            config: Review configuration.
            system_prompt: System prompt for the LLM.
            user_prompt: User prompt with file content.

        Returns:
            Tuple of (list of review comments, tokens used).
        """
        model = config.model if config.model else self._model

        response = self.client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )

        # Calculate tokens used
        tokens_used = (response.usage.input_tokens or 0) + (
            response.usage.output_tokens or 0
        )

        # Extract content from response
        content = ""
        if response.content and len(response.content) > 0:
            content = response.content[0].text or "{}"

        try:
            data = json.loads(content)
            comments = self._parse_response(data, file.path)
        except json.JSONDecodeError:
            comments = []

        return comments, tokens_used
