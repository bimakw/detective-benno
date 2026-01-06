"""Tests for Groq provider."""

import json
from unittest.mock import MagicMock, patch

from detective_benno.models import FileChange, ReviewConfig
from detective_benno.providers.groq import GroqProvider


class TestGroqProvider:
    """Tests for GroqProvider."""

    def test_provider_name(self):
        """Test provider name."""
        provider = GroqProvider(api_key="test-key")
        assert provider.name == "groq"

    def test_default_model(self):
        """Test default model."""
        provider = GroqProvider(api_key="test-key")
        assert provider.default_model == "llama-3.3-70b-versatile"

    def test_validate_config_with_key(self):
        """Test config validation with API key."""
        provider = GroqProvider(api_key="test-key")
        assert provider.validate_config() is True

    def test_validate_config_without_key(self):
        """Test config validation without API key."""
        with patch.dict("os.environ", {}, clear=True):
            provider = GroqProvider(api_key=None)
            assert provider.validate_config() is False

    def test_custom_model(self):
        """Test custom model configuration."""
        provider = GroqProvider(api_key="test-key", model="mixtral-8x7b-32768")
        assert provider._model == "mixtral-8x7b-32768"

    def test_review_success(
        self,
        mock_groq_client: MagicMock,
        sample_python_file: FileChange,
        groq_config: ReviewConfig,
    ):
        """Test successful code review."""
        provider = GroqProvider(api_key="test-key")
        provider._client = mock_groq_client

        comments, tokens = provider.review(
            file=sample_python_file,
            config=groq_config,
            system_prompt="You are a code reviewer.",
            user_prompt="Review this code.",
        )

        assert len(comments) == 2
        assert tokens == 500
        assert comments[0].severity.value == "critical"
        assert "SQL injection" in comments[0].message

    def test_review_empty_response(
        self,
        sample_python_file: FileChange,
        groq_config: ReviewConfig,
    ):
        """Test review with empty LLM response."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({"comments": []})

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(total_tokens=100)

        mock_client.chat.completions.create.return_value = mock_response

        provider = GroqProvider(api_key="test-key")
        provider._client = mock_client

        comments, tokens = provider.review(
            file=sample_python_file,
            config=groq_config,
            system_prompt="You are a code reviewer.",
            user_prompt="Review this code.",
        )

        assert len(comments) == 0
        assert tokens == 100

    def test_review_invalid_json_response(
        self,
        sample_python_file: FileChange,
        groq_config: ReviewConfig,
    ):
        """Test review with invalid JSON response."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "This is not valid JSON"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(total_tokens=50)

        mock_client.chat.completions.create.return_value = mock_response

        provider = GroqProvider(api_key="test-key")
        provider._client = mock_client

        comments, tokens = provider.review(
            file=sample_python_file,
            config=groq_config,
            system_prompt="You are a code reviewer.",
            user_prompt="Review this code.",
        )

        assert len(comments) == 0
        assert tokens == 50

    def test_review_uses_config_temperature(
        self,
        sample_python_file: FileChange,
    ):
        """Test that review uses temperature from config."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({"comments": []})

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(total_tokens=100)

        mock_client.chat.completions.create.return_value = mock_response

        provider = GroqProvider(api_key="test-key")
        provider._client = mock_client

        config = ReviewConfig(temperature=0.7)

        provider.review(
            file=sample_python_file,
            config=config,
            system_prompt="Test",
            user_prompt="Test",
        )

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    def test_review_uses_config_model(
        self,
        sample_python_file: FileChange,
    ):
        """Test that review uses model from config when provided."""
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({"comments": []})

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(total_tokens=100)

        mock_client.chat.completions.create.return_value = mock_response

        provider = GroqProvider(api_key="test-key")
        provider._client = mock_client

        config = ReviewConfig(model="gemma2-9b-it")

        provider.review(
            file=sample_python_file,
            config=config,
            system_prompt="Test",
            user_prompt="Test",
        )

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gemma2-9b-it"

    def test_env_var_fallback(self):
        """Test that API key falls back to environment variable."""
        with patch.dict("os.environ", {"GROQ_API_KEY": "env-api-key"}):
            provider = GroqProvider()
            assert provider._api_key == "env-api-key"
            assert provider.validate_config() is True
