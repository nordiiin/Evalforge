"""Tests for the generator orchestration: provider call + cache wiring."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from evalforge.cache import ResponseCache
from evalforge.generation.grader import GRADER_COMPARE_MEANING
from evalforge.generation.generator import generate_for_topic, resolve_referenced
from evalforge.parser.models import KnowledgeSource, Solution, Tool, Topic
from evalforge.providers.base import GeneratedCase


@dataclass
class FakeProvider:
    name: str = "fake"
    model: str = "fake-model"
    cases: list[GeneratedCase] = field(
        default_factory=lambda: [
            GeneratedCase("q1", "a1", "r1"),
            GeneratedCase("q2", "a2", "r2"),
        ]
    )
    calls: int = 0

    def generate_happy_path(self, **kwargs) -> list[GeneratedCase]:
        self.calls += 1
        return list(self.cases)


def _topic(name: str = "T", **overrides) -> Topic:
    base = dict(
        id="t",
        name=name,
        description="d",
        trigger_phrases=["hi"],
        knowledge_source_ids=[],
        tool_ids=[],
        raw_yaml="kind: AdaptiveDialog\n",
        is_system=False,
        source_path="",
    )
    base.update(overrides)
    return Topic(**base)


def test_generate_for_topic_returns_test_cases_with_default_grader():
    provider = FakeProvider()
    cases, was_cached = generate_for_topic(
        topic=_topic(),
        knowledge_sources=[],
        tools=[],
        provider=provider,
        mode="happy_path",
        count=2,
        seed=None,
        cache=None,
    )
    assert was_cached is False
    assert len(cases) == 2
    assert all(c.grader == GRADER_COMPARE_MEANING for c in cases)
    assert all(c.mode == "happy_path" for c in cases)
    assert all(c.topic_name == "T" for c in cases)
    assert provider.calls == 1


def test_generate_for_topic_uses_cache_on_second_call(tmp_path: Path):
    cache = ResponseCache(tmp_path)
    provider = FakeProvider()
    kwargs = dict(
        topic=_topic(),
        knowledge_sources=[],
        tools=[],
        provider=provider,
        mode="happy_path",
        count=2,
        seed=42,
        cache=cache,
    )

    first, was_cached_first = generate_for_topic(**kwargs)
    second, was_cached_second = generate_for_topic(**kwargs)

    assert was_cached_first is False
    assert was_cached_second is True
    assert provider.calls == 1, "second call should hit the cache, not the provider"
    assert [c.user_input for c in first] == [c.user_input for c in second]


def test_generate_for_topic_cache_invalidates_on_seed_change(tmp_path: Path):
    cache = ResponseCache(tmp_path)
    provider = FakeProvider()
    base = dict(
        topic=_topic(),
        knowledge_sources=[],
        tools=[],
        provider=provider,
        mode="happy_path",
        count=2,
        cache=cache,
    )

    generate_for_topic(**base, seed=1)
    generate_for_topic(**base, seed=2)
    assert provider.calls == 2


def test_generate_for_topic_unsupported_mode_raises():
    with pytest.raises(NotImplementedError):
        generate_for_topic(
            topic=_topic(),
            knowledge_sources=[],
            tools=[],
            provider=FakeProvider(),
            mode="edge_case",
            count=1,
            seed=None,
            cache=None,
        )


def test_resolve_referenced_pulls_kss_and_tools_by_id():
    ks = KnowledgeSource(id="ks1", name="Catalog", kind="SharePoint")
    tool = Tool(id="tl1", name="Lookup")
    solution = Solution(
        topics=[],
        knowledge_sources=[ks],
        tools=[tool],
    )
    topic = _topic(knowledge_source_ids=["ks1", "missing"], tool_ids=["tl1"])
    kss, tools = resolve_referenced(solution, topic)
    assert [k.name for k in kss] == ["Catalog"]
    assert [t.name for t in tools] == ["Lookup"]
