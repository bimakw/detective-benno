"""Tests for Anthropic Claude provider."""

import json
from unittest.mock import MagicMock, patch

from detective_benno.models import FileChange, ReviewConfig
from detective_benno.providers.anthropic import AnthropicProvider


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def test_provider_name(self):
        """Test provider name."""
        provider = AnthropicProvider(api_key="test-key")
        assert provider.name == "anthropic"

    def test_default_model(self):
        """Test default model."""
        provider = AnthropicProvider(api_key="test-key")
        assert provider.default_model == "claude-sonnet-4-20250514"

    def test_validate_config_with_key(self):
        """Test config validation with API key."""
        provider = AnthropicProvider(api_key="test-key")
        assert provider.validate_config() is True

    def test_validate_config_without_key(self):
        """Test config validation without API key."""
        with patch.dict("os.environ", {}, clear=True):
            provider = AnthropicProvider(api_key=None)
            assert provider.validate_config() is False

    def test_custom_model(self):
        """Test custom model configuration."""
        provider = AnthropicProvider(api_key="test-key", model="claude-3-5-haiku-20241022")
        assert provider._model == "claude-3-5-haiku-20241022"

    def test_custom_base_url(self):
        """Test custom base URL configuration."""
        provider = AnthropicProvider(
            api_key="test-key",
            base_url="https://custom.anthropic.com",
        )
        assert provider._base_url == "https://custom.anthropic.com"

    def test_review_success(
        self,
        mock_anthropic_client: MagicMock,
        sample_python_file: FileChange,
        anthropic_config: ReviewConfig,
    ):
        """Test successful code review."""
        provider = AnthropicProvider(api_key="test-key")
        provider._client = mock_anthropic_client

        comments, tokens = provider.review(
            file=sample_python_file,
            config=anthropic_config,
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
        anthropic_config: ReviewConfig,
    ):
        """Test review with empty LLM response."""
        mock_client = MagicMock()

        mock_content_block = MagicMock()
        mock_content_block.text = json.dumps({"comments": []})

        mock_usage = MagicMock()
        mock_usage.input_tokens = 50
        mock_usage.output_tokens = 50

        mock_response = MagicMock()
        mock_response.content = [mock_content_block]
        mock_response.usage = mock_usage

        mock_client.messages.create.return_value = mock_response

        provider = AnthropicProvider(api_key="test-key")
        provider._client = mock_client

        comments, tokens = provider.review(
            file=sample_python_file,
            config=anthropic_config,
            system_prompt="You are a code reviewer.",
            user_prompt="Review this code.",
        )

        assert len(comments) == 0
        assert tokens == 100

    def test_review_invalid_json_response(
        self,
        sample_python_file: FileChange,
        anthropic_config: ReviewConfig,
    ):
        """Test review with invalid JSON response."""
        mock_client = MagicMock()

        mock_content_block = MagicMock()
        mock_content_block.text = "This is not valid JSON"

        mock_usage = MagicMock()
        mock_usage.input_tokens = 25
        mock_usage.output_tokens = 25

        mock_response = MagicMock()
        mock_response.content = [mock_content_block]
        mock_response.usage = mock_usage

        mock_client.messages.create.return_value = mock_response

        provider = AnthropicProvider(api_key="test-key")
        provider._client = mock_client

        comments, tokens = provider.review(
            file=sample_python_file,
            config=anthropic_config,
            system_prompt="You are a code reviewer.",
            user_prompt="Review this code.",
        )

        assert len(comments) == 0
        assert tokens == 50

    def test_review_uses_config_model(
        self,
        sample_python_file: FileChange,
    ):
        """Test that review uses model from config."""
        mock_client = MagicMock()

        mock_content_block = MagicMock()
        mock_content_block.text = json.dumps({"comments": []})

        mock_usage = MagicMock()
        mock_usage.input_tokens = 50
        mock_usage.output_tokens = 50

        mock_response = MagicMock()
        mock_response.content = [mock_content_block]
        mock_response.usage = mock_usage

        mock_client.messages.create.return_value = mock_response

        provider = AnthropicProvider(api_key="test-key")
        provider._client = mock_client

        config = ReviewConfig(model="claude-3-5-haiku-20241022")

        provider.review(
            file=sample_python_file,
            config=config,
            system_prompt="Test",
            user_prompt="Test",
        )

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-5-haiku-20241022"
