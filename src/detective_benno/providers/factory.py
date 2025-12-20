"""Provider factory for creating LLM providers."""

from typing import Any

from detective_benno.providers.base import LLMProvider


class ProviderFactory:
    """Factory for creating LLM provider instances.

    Supports registration of custom providers for extensibility.
    """

    _providers: dict[str, type[LLMProvider]] = {}

    @classmethod
    def _ensure_registered(cls) -> None:
        """Ensure default providers are registered."""
        if not cls._providers:
            from detective_benno.providers.ollama import OllamaProvider
            from detective_benno.providers.openai import OpenAIProvider

            cls._providers = {
                "openai": OpenAIProvider,
                "ollama": OllamaProvider,
            }

    @classmethod
    def create(cls, provider_name: str, **kwargs: Any) -> LLMProvider:
        """Create a provider instance by name.

        Args:
            provider_name: Name of the provider (openai, ollama, etc.)
            **kwargs: Provider-specific configuration.

        Returns:
            Configured LLMProvider instance.

        Raises:
            ValueError: If provider is not registered.
        """
        cls._ensure_registered()

        provider_name = provider_name.lower()
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown provider '{provider_name}'. Available: {available}"
            )

        provider_class = cls._providers[provider_name]
        return provider_class(**kwargs)

    @classmethod
    def register(cls, name: str, provider_class: type[LLMProvider]) -> None:
        """Register a custom provider.

        Args:
            name: Provider name identifier.
            provider_class: Provider class to register.
        """
        cls._ensure_registered()
        cls._providers[name.lower()] = provider_class

    @classmethod
    def available_providers(cls) -> list[str]:
        """Get list of available provider names.

        Returns:
            List of registered provider names.
        """
        cls._ensure_registered()
        return list(cls._providers.keys())

    @classmethod
    def get_provider_class(cls, name: str) -> type[LLMProvider] | None:
        """Get provider class by name.

        Args:
            name: Provider name.

        Returns:
            Provider class or None if not found.
        """
        cls._ensure_registered()
        return cls._providers.get(name.lower())
