"""Tests for Ollama provider."""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from detective_benno.models import FileChange, ReviewConfig
from detective_benno.providers.ollama import OllamaProvider


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def test_provider_name(self):
        """Test provider name."""
        provider = OllamaProvider()
        assert provider.name == "ollama"

    def test_default_model(self):
        """Test default model."""
        provider = OllamaProvider()
        assert provider.default_model == "codellama"

    def test_default_base_url(self):
        """Test default base URL."""
        provider = OllamaProvider()
        assert provider._base_url == "http://localhost:11434"

    def test_custom_model(self):
        """Test custom model configuration."""
        provider = OllamaProvider(model="mistral")
        assert provider._model == "mistral"

    def test_custom_base_url(self):
        """Test custom base URL configuration."""
        provider = OllamaProvider(base_url="http://remote:11434")
        assert provider._base_url == "http://remote:11434"

    def test_base_url_from_env(self):
        """Test base URL from OLLAMA_HOST env var."""
        with patch.dict("os.environ", {"OLLAMA_HOST": "http://env-host:11434"}):
            provider = OllamaProvider()
            assert provider._base_url == "http://env-host:11434"

    def test_validate_config_success(self):
        """Test config validation when Ollama is available."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client.get.return_value = mock_response

        provider = OllamaProvider()
        provider._client = mock_client

        assert provider.validate_config() is True
        mock_client.get.assert_called_with("/api/tags")

    def test_validate_config_failure(self):
        """Test config validation when Ollama is not available."""
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.RequestError("Connection refused")

        provider = OllamaProvider()
        provider._client = mock_client

        assert provider.validate_config() is False

    def test_is_model_available_true(self):
        """Test model availability check when model exists."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "codellama:latest"},
                {"name": "mistral:latest"},
            ]
        }
        mock_client.get.return_value = mock_response

        provider = OllamaProvider(model="codellama")
        provider._client = mock_client

        assert provider.is_model_available() is True

    def test_is_model_available_false(self):
        """Test model availability check when model doesn't exist."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama2:latest"},
            ]
        }
        mock_client.get.return_value = mock_response

        provider = OllamaProvider(model="codellama")
        provider._client = mock_client

        assert provider.is_model_available() is False

    def test_review_success(
        self,
        mock_ollama_response: dict[str, Any],
        sample_python_file: FileChange,
        ollama_config: ReviewConfig,
    ):
        """Test successful code review."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_ollama_response

        mock_client.post.return_value = mock_response

        provider = OllamaProvider()
        provider._client = mock_client

        comments, tokens = provider.review(
            file=sample_python_file,
            config=ollama_config,
            system_prompt="You are a code reviewer.",
            user_prompt="Review this code.",
        )

        assert len(comments) == 2
        assert tokens == 500  # 300 + 200
        assert comments[0].severity.value == "critical"

    def test_review_with_extra_text(
        self,
        sample_python_file: FileChange,
        ollama_config: ReviewConfig,
    ):
        """Test review when response contains extra text around JSON."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200

        # Response with extra text around JSON
        response_text = '''Here is my analysis:

{"comments": [{"line_start": 1, "severity": "warning", "category": "best-practice", "message": "Test issue"}]}

That's my review.'''

        mock_response.json.return_value = {
            "response": response_text,
            "eval_count": 100,
            "prompt_eval_count": 50,
        }
        mock_client.post.return_value = mock_response

        provider = OllamaProvider()
        provider._client = mock_client

        comments, tokens = provider.review(
            file=sample_python_file,
            config=ollama_config,
            system_prompt="Test",
            user_prompt="Test",
        )

        assert len(comments) == 1
        assert comments[0].message == "Test issue"

    def test_review_invalid_json(
        self,
        sample_python_file: FileChange,
        ollama_config: ReviewConfig,
    ):
        """Test review with invalid JSON response."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": "This is not valid JSON at all",
            "eval_count": 50,
        }
        mock_client.post.return_value = mock_response

        provider = OllamaProvider()
        provider._client = mock_client

        comments, tokens = provider.review(
            file=sample_python_file,
            config=ollama_config,
            system_prompt="Test",
            user_prompt="Test",
        )

        # No comments should be parsed from invalid JSON
        assert len(comments) == 0
        # Tokens still reported (eval_count + prompt_eval_count)
        # Since no prompt_eval_count, only eval_count is used
        assert tokens == 50

    def test_review_request_error(
        self,
        sample_python_file: FileChange,
        ollama_config: ReviewConfig,
    ):
        """Test review when request fails."""
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.RequestError("Connection refused")

        provider = OllamaProvider()
        provider._client = mock_client

        with pytest.raises(RuntimeError) as exc_info:
            provider.review(
                file=sample_python_file,
                config=ollama_config,
                system_prompt="Test",
                user_prompt="Test",
            )

        assert "Ollama request failed" in str(exc_info.value)

    def test_extract_json_simple(self):
        """Test JSON extraction from simple response."""
        provider = OllamaProvider()

        result = provider._extract_json('{"key": "value"}')
        assert result == '{"key": "value"}'

    def test_extract_json_with_prefix(self):
        """Test JSON extraction with text prefix."""
        provider = OllamaProvider()

        result = provider._extract_json('Some text {"key": "value"}')
        assert result == '{"key": "value"}'

    def test_extract_json_with_suffix(self):
        """Test JSON extraction with text suffix."""
        provider = OllamaProvider()

        result = provider._extract_json('{"key": "value"} more text')
        assert result == '{"key": "value"}'

    def test_extract_json_nested(self):
        """Test JSON extraction with nested objects."""
        provider = OllamaProvider()

        result = provider._extract_json('prefix {"outer": {"inner": "value"}} suffix')
        assert result == '{"outer": {"inner": "value"}}'

    def test_extract_json_no_json(self):
        """Test JSON extraction when no JSON present."""
        provider = OllamaProvider()

        result = provider._extract_json("No JSON here")
        assert result == "{}"

    def test_pull_model_success(self):
        """Test successful model pull."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client.post.return_value = mock_response

        provider = OllamaProvider()
        provider._client = mock_client

        result = provider.pull_model("codellama")

        assert result is True
        mock_client.post.assert_called_once()

    def test_pull_model_failure(self):
        """Test failed model pull."""
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.RequestError("Network error")

        provider = OllamaProvider()
        provider._client = mock_client

        result = provider.pull_model("codellama")

        assert result is False
