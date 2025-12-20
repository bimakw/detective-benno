"""Tests for ProviderFactory."""

import pytest

from detective_benno.providers.factory import ProviderFactory
from detective_benno.providers.ollama import OllamaProvider
from detective_benno.providers.openai import OpenAIProvider


class TestProviderFactory:
    """Tests for ProviderFactory."""

    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        provider = ProviderFactory.create("openai", api_key="test-key")

        assert isinstance(provider, OpenAIProvider)
        assert provider.name == "openai"

    def test_create_ollama_provider(self):
        """Test creating Ollama provider."""
        provider = ProviderFactory.create("ollama", model="codellama")

        assert isinstance(provider, OllamaProvider)
        assert provider.name == "ollama"

    def test_create_provider_case_insensitive(self):
        """Test that provider names are case-insensitive."""
        provider1 = ProviderFactory.create("OpenAI", api_key="test")
        provider2 = ProviderFactory.create("OLLAMA")

        assert isinstance(provider1, OpenAIProvider)
        assert isinstance(provider2, OllamaProvider)

    def test_create_unknown_provider_raises_error(self):
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ProviderFactory.create("unknown_provider")

        assert "Unknown provider" in str(exc_info.value)
        assert "unknown_provider" in str(exc_info.value)

    def test_available_providers(self):
        """Test listing available providers."""
        providers = ProviderFactory.available_providers()

        assert "openai" in providers
        assert "ollama" in providers
        assert len(providers) >= 2

    def test_get_provider_class(self):
        """Test getting provider class by name."""
        openai_class = ProviderFactory.get_provider_class("openai")
        ollama_class = ProviderFactory.get_provider_class("ollama")
        unknown_class = ProviderFactory.get_provider_class("unknown")

        assert openai_class == OpenAIProvider
        assert ollama_class == OllamaProvider
        assert unknown_class is None

    def test_provider_with_kwargs(self):
        """Test creating provider with custom kwargs."""
        provider = ProviderFactory.create(
            "openai",
            api_key="custom-key",
            model="gpt-4o-mini",
            base_url="https://custom.api.com",
        )

        assert isinstance(provider, OpenAIProvider)
        assert provider._api_key == "custom-key"
        assert provider._model == "gpt-4o-mini"
        assert provider._base_url == "https://custom.api.com"
