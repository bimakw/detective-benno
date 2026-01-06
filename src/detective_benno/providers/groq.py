"""Groq provider for Detective Benno."""

import json
import os

from groq import Groq

from detective_benno.models import FileChange, ReviewComment, ReviewConfig
from detective_benno.providers.base import LLMProvider


class GroqProvider(LLMProvider):
    """Groq provider for code review.

    Supports models: llama-3.3-70b-versatile, mixtral-8x7b-32768, gemma2-9b-it
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize Groq provider.

        Args:
            api_key: Groq API key. Falls back to GROQ_API_KEY env var.
            model: Model to use. Defaults to llama-3.3-70b-versatile.
        """
        self._api_key = api_key or os.environ.get("GROQ_API_KEY")
        self._model = model or "llama-3.3-70b-versatile"
        self._client: Groq | None = None

    @property
    def name(self) -> str:
        """Return provider name."""
        return "groq"

    @property
    def default_model(self) -> str:
        """Return default model."""
        return "llama-3.3-70b-versatile"

    @property
    def client(self) -> Groq:
        """Get or create Groq client."""
        if self._client is None:
            self._client = Groq(api_key=self._api_key)
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
        """Execute code review using Groq.

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
