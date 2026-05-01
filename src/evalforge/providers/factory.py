"""Build LLM providers by name."""

from __future__ import annotations

from evalforge.providers.base import LLMProvider

SUPPORTED_PROVIDERS = ("anthropic", "openai", "azure")


def make_provider(
    name: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    endpoint: str | None = None,
    api_version: str | None = None,
) -> LLMProvider:
    """Build a provider. `endpoint` and `api_version` are Azure-only."""
    if name == "anthropic":
        # Lazy import keeps each SDK off the import path for callers that
        # only need name validation (e.g. dry-run CLI tests).
        from evalforge.providers.anthropic_ import (
            DEFAULT_ANTHROPIC_MODEL,
            AnthropicProvider,
        )

        return AnthropicProvider(api_key=api_key, model=model or DEFAULT_ANTHROPIC_MODEL)
    if name == "openai":
        from evalforge.providers.openai_ import DEFAULT_OPENAI_MODEL, OpenAIProvider

        return OpenAIProvider(api_key=api_key, model=model or DEFAULT_OPENAI_MODEL)
    if name == "azure":
        from evalforge.providers.openai_ import AzureOpenAIProvider

        return AzureOpenAIProvider(
            api_key=api_key,
            model=model,
            endpoint=endpoint,
            api_version=api_version,
        )
    raise ValueError(
        f"Unknown provider: {name!r}. Choose one of: {', '.join(SUPPORTED_PROVIDERS)}."
    )
