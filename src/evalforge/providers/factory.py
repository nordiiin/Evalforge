"""Build LLM providers by name. Anthropic works in M2; OpenAI/Azure stubbed."""

from __future__ import annotations

from evalforge.providers.base import LLMProvider

SUPPORTED_PROVIDERS = ("anthropic", "openai", "azure")


def make_provider(
    name: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
) -> LLMProvider:
    if name == "anthropic":
        # Lazy import keeps `anthropic` SDK off the import path for callers
        # that only need the factory's name validation (e.g. dry-run CLI tests).
        from evalforge.providers.anthropic_ import (
            DEFAULT_ANTHROPIC_MODEL,
            AnthropicProvider,
        )

        return AnthropicProvider(api_key=api_key, model=model or DEFAULT_ANTHROPIC_MODEL)
    if name in {"openai", "azure"}:
        raise NotImplementedError(
            f"The {name!r} provider is stubbed in M2 and lands in M3. "
            "Use --provider anthropic for now."
        )
    raise ValueError(
        f"Unknown provider: {name!r}. Choose one of: {', '.join(SUPPORTED_PROVIDERS)}."
    )
