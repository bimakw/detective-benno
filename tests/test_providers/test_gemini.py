"""Tests for Google Gemini provider."""

import json
from unittest.mock import MagicMock, patch

from detective_benno.models import FileChange, ReviewConfig
from detective_benno.providers.gemini import GeminiProvider


class TestGeminiProvider:
    """Tests for GeminiProvider."""

    def test_provider_name(self):
        """Test provider name."""
        provider = GeminiProvider(api_key="test-key")
        assert provider.name == "gemini"

    def test_default_model(self):
        """Test default model."""
        provider = GeminiProvider(api_key="test-key")
        assert provider.default_model == "gemini-2.0-flash-exp"

    def test_validate_config_with_key(self):
        """Test config validation with API key."""
        provider = GeminiProvider(api_key="test-key")
        assert provider.validate_config() is True

    def test_validate_config_without_key(self):
        """Test config validation without API key."""
        with patch.dict("os.environ", {}, clear=True):
            provider = GeminiProvider(api_key=None)
            assert provider.validate_config() is False

    def test_custom_model(self):
        """Test custom model configuration."""
        provider = GeminiProvider(api_key="test-key", model="gemini-1.5-pro")
        assert provider._model == "gemini-1.5-pro"

    @patch("detective_benno.providers.gemini.genai.GenerativeModel")
    def test_review_success(
        self,
        mock_model_class: MagicMock,
        sample_python_file: FileChange,
        gemini_config: ReviewConfig,
        mock_review_response_critical: dict,
    ):
        """Test successful code review."""
        # Setup mock
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 200
        mock_usage.candidates_token_count = 300

        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_review_response_critical)
        mock_response.usage_metadata = mock_usage

        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key")

        comments, tokens = provider.review(
            file=sample_python_file,
            config=gemini_config,
            system_prompt="You are a code reviewer.",
            user_prompt="Review this code.",
        )

        assert len(comments) == 2
        assert tokens == 500
        assert comments[0].severity.value == "critical"
        assert "SQL injection" in comments[0].message

    @patch("detective_benno.providers.gemini.genai.GenerativeModel")
    def test_review_empty_response(
        self,
        mock_model_class: MagicMock,
        sample_python_file: FileChange,
        gemini_config: ReviewConfig,
    ):
        """Test review with empty LLM response."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 50
        mock_usage.candidates_token_count = 50

        mock_response = MagicMock()
        mock_response.text = json.dumps({"comments": []})
        mock_response.usage_metadata = mock_usage

        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key")

        comments, tokens = provider.review(
            file=sample_python_file,
            config=gemini_config,
            system_prompt="You are a code reviewer.",
            user_prompt="Review this code.",
        )

        assert len(comments) == 0
        assert tokens == 100

    @patch("detective_benno.providers.gemini.genai.GenerativeModel")
    def test_review_invalid_json_response(
        self,
        mock_model_class: MagicMock,
        sample_python_file: FileChange,
        gemini_config: ReviewConfig,
    ):
        """Test review with invalid JSON response."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 25
        mock_usage.candidates_token_count = 25

        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON"
        mock_response.usage_metadata = mock_usage

        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key")

        comments, tokens = provider.review(
            file=sample_python_file,
            config=gemini_config,
            system_prompt="You are a code reviewer.",
            user_prompt="Review this code.",
        )

        assert len(comments) == 0
        assert tokens == 50

    @patch("detective_benno.providers.gemini.genai.GenerativeModel")
    def test_review_uses_config_temperature(
        self,
        mock_model_class: MagicMock,
        sample_python_file: FileChange,
    ):
        """Test that review uses temperature from config."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 50
        mock_usage.candidates_token_count = 50

        mock_response = MagicMock()
        mock_response.text = json.dumps({"comments": []})
        mock_response.usage_metadata = mock_usage

        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key")

        config = ReviewConfig(temperature=0.7)

        provider.review(
            file=sample_python_file,
            config=config,
            system_prompt="Test",
            user_prompt="Test",
        )

        call_kwargs = mock_model.generate_content.call_args[1]
        assert call_kwargs["generation_config"]["temperature"] == 0.7

    @patch("detective_benno.providers.gemini.genai.GenerativeModel")
    def test_review_no_usage_metadata(
        self,
        mock_model_class: MagicMock,
        sample_python_file: FileChange,
        gemini_config: ReviewConfig,
    ):
        """Test review when usage_metadata is not available."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps({"comments": []})
        mock_response.usage_metadata = None

        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key")

        comments, tokens = provider.review(
            file=sample_python_file,
            config=gemini_config,
            system_prompt="Test",
            user_prompt="Test",
        )

        assert len(comments) == 0
        assert tokens == 0

    @patch("detective_benno.providers.gemini.genai.GenerativeModel")
    def test_model_switching(
        self,
        mock_model_class: MagicMock,
        sample_python_file: FileChange,
    ):
        """Test that provider correctly switches models when config differs."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 50
        mock_usage.candidates_token_count = 50

        mock_response = MagicMock()
        mock_response.text = json.dumps({"comments": []})
        mock_response.usage_metadata = mock_usage

        mock_model.generate_content.return_value = mock_response

        provider = GeminiProvider(api_key="test-key", model="gemini-2.0-flash-exp")

        # Use a different model in config
        config = ReviewConfig(model="gemini-1.5-pro")

        provider.review(
            file=sample_python_file,
            config=config,
            system_prompt="Test",
            user_prompt="Test",
        )

        # Model should be updated
        assert provider._model == "gemini-1.5-pro"
