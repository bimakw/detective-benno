"""Google Gemini provider for Detective Benno."""

import json
import os

import google.generativeai as genai

from detective_benno.models import FileChange, ReviewComment, ReviewConfig
from detective_benno.providers.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini provider for code review.

    Supports models: gemini-2.0-flash-exp, gemini-1.5-pro, gemini-1.5-flash
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        """Initialize Gemini provider.

        Args:
            api_key: Google API key. Falls back to GOOGLE_API_KEY env var.
            model: Model to use. Defaults to gemini-2.0-flash-exp.
        """
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self._model = model or "gemini-2.0-flash-exp"
        self._client: genai.GenerativeModel | None = None

        # Configure the API key
        if self._api_key:
            genai.configure(api_key=self._api_key)

    @property
    def name(self) -> str:
        """Return provider name."""
        return "gemini"

    @property
    def default_model(self) -> str:
        """Return default model."""
        return "gemini-2.0-flash-exp"

    @property
    def client(self) -> genai.GenerativeModel:
        """Get or create Gemini client."""
        if self._client is None:
            # Configure safety settings to be permissive for code review
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE",
                },
            ]

            generation_config = {
                "response_mime_type": "application/json",
            }

            self._client = genai.GenerativeModel(
                model_name=self._model,
                safety_settings=safety_settings,
                generation_config=generation_config,
            )
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
        """Execute code review using Google Gemini.

        Args:
            file: The file to review.
            config: Review configuration.
            system_prompt: System prompt for the LLM.
            user_prompt: User prompt with file content.

        Returns:
            Tuple of (list of review comments, tokens used).
        """
        # If model is specified in config, recreate client with new model
        model_name = config.model if config.model else self._model
        if model_name != self._model:
            self._model = model_name
            self._client = None  # Force recreation of client

        # Combine system prompt and user prompt for Gemini
        # Gemini doesn't have a separate system prompt API like OpenAI
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Update generation config with temperature
        generation_config = {
            "response_mime_type": "application/json",
            "temperature": config.temperature,
        }

        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config,
        )

        # Calculate tokens used from usage metadata
        tokens_used = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens_used = (
                getattr(response.usage_metadata, "prompt_token_count", 0)
                + getattr(response.usage_metadata, "candidates_token_count", 0)
            )

        # Extract content from response
        content = "{}"
        if response.text:
            content = response.text

        try:
            data = json.loads(content)
            comments = self._parse_response(data, file.path)
        except json.JSONDecodeError:
            comments = []

        return comments, tokens_used
