"""Tests for the provider factory."""

from __future__ import annotations

import pytest

from evalforge.providers.factory import make_provider


def test_unknown_provider_raises_value_error():
    with pytest.raises(ValueError, match="Unknown provider"):
        make_provider("llama")


def test_anthropic_provider_built_with_dummy_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    provider = make_provider("anthropic", model="claude-opus-4-7")
    assert provider.name == "anthropic"
    assert provider.model == "claude-opus-4-7"


def test_openai_provider_built_with_dummy_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    provider = make_provider("openai", model="gpt-4o")
    assert provider.name == "openai"
    assert provider.model == "gpt-4o"


def test_azure_provider_requires_model(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    with pytest.raises(ValueError, match="deployment name"):
        make_provider("azure")


def test_azure_provider_requires_endpoint(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
        make_provider("azure", model="my-deployment")


def test_azure_provider_built_with_dummy_creds(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-not-real")
    provider = make_provider(
        "azure",
        model="my-deployment",
        endpoint="https://example.openai.azure.com",
        api_version="2024-08-01-preview",
    )
    assert provider.name == "azure"
    assert provider.model == "my-deployment"
