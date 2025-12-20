"""Ollama provider for Detective Benno.

Ollama allows running LLMs locally without API keys.
Supports models like codellama, deepseek-coder, mistral, etc.
"""

import json
import os

import httpx

from detective_benno.models import FileChange, ReviewComment, ReviewConfig
from detective_benno.providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider for code review.

    Supports any model available in Ollama:
    - codellama (recommended for code review)
    - deepseek-coder
    - mistral
    - llama3
    - and more...

    Requires Ollama to be running locally or accessible via network.
    """

    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_MODEL = "codellama"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        """Initialize Ollama provider.

        Args:
            model: Model to use. Defaults to codellama.
            base_url: Ollama API URL. Defaults to http://localhost:11434.
                      Can also be set via OLLAMA_HOST env var.
            timeout: Request timeout in seconds.
        """
        self._model = model or self.DEFAULT_MODEL
        self._base_url = (
            base_url
            or os.environ.get("OLLAMA_HOST")
            or self.DEFAULT_BASE_URL
        )
        self._timeout = timeout
        self._client: httpx.Client | None = None

    @property
    def name(self) -> str:
        """Return provider name."""
        return "ollama"

    @property
    def default_model(self) -> str:
        """Return default model."""
        return self.DEFAULT_MODEL

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._client

    def validate_config(self) -> bool:
        """Validate that Ollama is accessible.

        Returns:
            True if Ollama is running and accessible.
        """
        try:
            response = self.client.get("/api/tags")
            return response.status_code == 200
        except httpx.RequestError:
            return False

    def is_model_available(self, model: str | None = None) -> bool:
        """Check if a model is available in Ollama.

        Args:
            model: Model name to check. Uses configured model if not specified.

        Returns:
            True if model is available.
        """
        model = model or self._model
        try:
            response = self.client.get("/api/tags")
            if response.status_code != 200:
                return False
            data = response.json()
            models = [m.get("name", "").split(":")[0] for m in data.get("models", [])]
            return model in models or f"{model}:latest" in [m.get("name") for m in data.get("models", [])]
        except (httpx.RequestError, json.JSONDecodeError):
            return False

    def review(
        self,
        file: FileChange,
        config: ReviewConfig,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[list[ReviewComment], int]:
        """Execute code review using Ollama.

        Args:
            file: The file to review.
            config: Review configuration.
            system_prompt: System prompt for the LLM.
            user_prompt: User prompt with file content.

        Returns:
            Tuple of (list of review comments, tokens used).
        """
        model = config.model if config.model else self._model

        # Combine system and user prompts for Ollama
        # Add explicit JSON instruction since Ollama doesn't have response_format
        combined_prompt = f"""{system_prompt}

IMPORTANT: You must respond with valid JSON only. No other text.

{user_prompt}"""

        payload = {
            "model": model,
            "prompt": combined_prompt,
            "stream": False,
            "options": {
                "temperature": config.temperature,
            },
        }

        try:
            response = self.client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract response text
            content = data.get("response", "{}")

            # Try to extract JSON from the response
            # Ollama might include extra text around the JSON
            content = self._extract_json(content)

            # Parse response
            parsed = json.loads(content)
            comments = self._parse_response(parsed, file.path)

            # Ollama provides eval_count as approximate token count
            tokens_used = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

            return comments, tokens_used

        except httpx.RequestError as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e
        except json.JSONDecodeError:
            # Return empty if response isn't valid JSON
            return [], 0

    def _extract_json(self, text: str) -> str:
        """Extract JSON object from text that might contain extra content.

        Args:
            text: Text that should contain JSON.

        Returns:
            Extracted JSON string.
        """
        # Try to find JSON object in the text
        start = text.find("{")
        if start == -1:
            return "{}"

        # Find matching closing brace
        depth = 0
        for i, char in enumerate(text[start:], start):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

        return "{}"

    def pull_model(self, model: str | None = None) -> bool:
        """Pull a model from Ollama registry.

        Args:
            model: Model to pull. Uses configured model if not specified.

        Returns:
            True if pull was successful.
        """
        model = model or self._model
        try:
            response = self.client.post(
                "/api/pull",
                json={"name": model},
                timeout=600.0,  # Pulling can take a while
            )
            return response.status_code == 200
        except httpx.RequestError:
            return False
