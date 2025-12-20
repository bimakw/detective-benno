"""OpenAI provider for Detective Benno."""

import json
import os

from openai import OpenAI

from detective_benno.models import FileChange, ReviewComment, ReviewConfig
from detective_benno.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider for code review.

    Supports models: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            model: Model to use. Defaults to gpt-4o.
            base_url: Optional base URL for API (for proxies/alternatives).
        """
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._model = model or "gpt-4o"
        self._base_url = base_url
        self._client: OpenAI | None = None

    @property
    def name(self) -> str:
        """Return provider name."""
        return "openai"

    @property
    def default_model(self) -> str:
        """Return default model."""
        return "gpt-4o"

    @property
    def client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            kwargs: dict = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = OpenAI(**kwargs)
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
        """Execute code review using OpenAI.

        Args:
            file: The file to review.
            config: Review configuration.
            system_prompt: System prompt for the LLM.
            user_prompt: User prompt with file content.

        Returns:
            Tuple of (list of review comments, tokens used).
        """
        model = config.model if config.model else self._model

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=config.temperature,
            response_format={"type": "json_object"},
        )

        tokens_used = response.usage.total_tokens if response.usage else 0
        content = response.choices[0].message.content or "{}"

        try:
            data = json.loads(content)
            comments = self._parse_response(data, file.path)
        except json.JSONDecodeError:
            comments = []

        return comments, tokens_used
