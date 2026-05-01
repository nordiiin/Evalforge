"""Tests for the on-disk response cache."""

from __future__ import annotations

from pathlib import Path

from evalforge.cache import ResponseCache, cache_key, default_cache_dir, topic_fingerprint
from evalforge.parser.models import Topic
from evalforge.providers.base import GeneratedCase


def _topic(name: str = "T", **overrides) -> Topic:
    base = dict(
        id="t",
        name=name,
        description="d",
        trigger_phrases=["hi", "hello"],
        knowledge_source_ids=[],
        tool_ids=[],
        raw_yaml="kind: AdaptiveDialog\n",
        is_system=False,
        source_path="t.yaml",
    )
    base.update(overrides)
    return Topic(**base)


def test_cache_set_then_get(tmp_path: Path):
    cache = ResponseCache(tmp_path)
    key = "abc123"
    cases = [GeneratedCase(user_input="q", expected_response="a", rationale="r")]
    cache.set(key, cases)
    out = cache.get(key)
    assert out is not None
    assert len(out) == 1
    assert out[0].user_input == "q"
    assert out[0].expected_response == "a"
    assert out[0].rationale == "r"


def test_cache_get_missing_returns_none(tmp_path: Path):
    cache = ResponseCache(tmp_path)
    assert cache.get("nonexistent") is None


def test_cache_get_corrupt_returns_none(tmp_path: Path):
    cache = ResponseCache(tmp_path)
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    assert cache.get("bad") is None


def test_cache_key_stable_for_same_inputs():
    topic = _topic()
    k1 = cache_key(provider="anthropic", model="m", mode="happy_path", count=3, seed=7, topic=topic)
    k2 = cache_key(provider="anthropic", model="m", mode="happy_path", count=3, seed=7, topic=topic)
    assert k1 == k2


def test_cache_key_changes_for_different_seed():
    topic = _topic()
    k1 = cache_key(provider="anthropic", model="m", mode="happy_path", count=3, seed=7, topic=topic)
    k2 = cache_key(provider="anthropic", model="m", mode="happy_path", count=3, seed=8, topic=topic)
    assert k1 != k2


def test_cache_key_changes_for_different_topic_yaml():
    a = _topic(raw_yaml="kind: A\n")
    b = _topic(raw_yaml="kind: B\n")
    k1 = cache_key(provider="anthropic", model="m", mode="happy_path", count=3, seed=None, topic=a)
    k2 = cache_key(provider="anthropic", model="m", mode="happy_path", count=3, seed=None, topic=b)
    assert k1 != k2


def test_cache_key_changes_for_different_model():
    topic = _topic()
    k1 = cache_key(provider="anthropic", model="m1", mode="happy_path", count=3, seed=None, topic=topic)
    k2 = cache_key(provider="anthropic", model="m2", mode="happy_path", count=3, seed=None, topic=topic)
    assert k1 != k2


def test_topic_fingerprint_ignores_trigger_phrase_order():
    a = _topic(trigger_phrases=["hi", "hello"])
    b = _topic(trigger_phrases=["hello", "hi"])
    assert topic_fingerprint(a) == topic_fingerprint(b)


def test_default_cache_dir_respects_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("EVALFORGE_CACHE_DIR", str(tmp_path / "x"))
    assert default_cache_dir() == tmp_path / "x"
