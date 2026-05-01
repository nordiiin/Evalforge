"""Tests for the provider factory and provider stubs."""

from __future__ import annotations

import pytest

from evalforge.providers.factory import make_provider


def test_unknown_provider_raises_value_error():
    with pytest.raises(ValueError, match="Unknown provider"):
        make_provider("llama")


def test_openai_provider_stub_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="M3"):
        make_provider("openai")


def test_azure_provider_stub_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="M3"):
        make_provider("azure")


def test_anthropic_provider_built_with_dummy_key(monkeypatch):
    """Anthropic provider should construct without hitting the network."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    provider = make_provider("anthropic", model="claude-opus-4-7")
    assert provider.name == "anthropic"
    assert provider.model == "claude-opus-4-7"
