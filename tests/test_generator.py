"""Tests for the generator orchestration: provider call + cache wiring."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from evalforge.cache import ResponseCache
from evalforge.generation.generator import generate_for_topic, resolve_referenced
from evalforge.generation.grader import GRADER_COMPARE_MEANING
from evalforge.parser.models import KnowledgeSource, Solution, Tool, Topic
from evalforge.providers.base import GeneratedCase


@dataclass
class FakeProvider:
    name: str = "fake"
    model: str = "fake-model"
    cases_by_mode: dict = field(default_factory=dict)
    default_cases: list = field(
        default_factory=lambda: [
            GeneratedCase(user_input="q1", expected_response="a1", rationale="r1"),
            GeneratedCase(user_input="q2", expected_response="a2", rationale="r2"),
        ]
    )
    calls: list = field(default_factory=list)

    def generate(self, *, mode_name: str, **kwargs) -> list[GeneratedCase]:
        self.calls.append(mode_name)
        cases = self.cases_by_mode.get(mode_name, self.default_cases)
        return [GeneratedCase(**c.__dict__) for c in cases]


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
    cases, hits = generate_for_topic(
        topic=_topic(),
        knowledge_sources=[],
        tools=[],
        provider=provider,
        mode="happy_path",
        count=2,
        seed=None,
        cache=None,
    )
    assert hits == {"happy_path": False}
    assert len(cases) == 2
    assert all(c.grader == GRADER_COMPARE_MEANING for c in cases)
    assert all(c.mode == "happy_path" for c in cases)
    assert provider.calls == ["happy_path"]


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

    _, first_hits = generate_for_topic(**kwargs)
    _, second_hits = generate_for_topic(**kwargs)

    assert first_hits == {"happy_path": False}
    assert second_hits == {"happy_path": True}
    assert provider.calls == ["happy_path"]


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
    assert provider.calls == ["happy_path", "happy_path"]


def test_generate_for_topic_unknown_mode_raises():
    with pytest.raises(NotImplementedError):
        generate_for_topic(
            topic=_topic(),
            knowledge_sources=[],
            tools=[],
            provider=FakeProvider(),
            mode="never_heard_of_it",
            count=1,
            seed=None,
            cache=None,
        )


def test_generate_mixed_invokes_all_four_modes():
    provider = FakeProvider(
        cases_by_mode={
            mode: [GeneratedCase(user_input=f"{mode}-q", expected_response=f"{mode}-a")]
            for mode in ("happy_path", "edge_case", "hallucination", "multi_turn")
        },
        default_cases=[GeneratedCase(user_input="q", expected_response="a")],
    )
    cases, hits = generate_for_topic(
        topic=_topic(),
        knowledge_sources=[],
        tools=[],
        provider=provider,
        mode="mixed",
        count=10,
        seed=None,
        cache=None,
    )
    # 40/30/20/10 split → 4/3/2/1, each mode returns one case in the fake.
    assert sorted(provider.calls) == sorted(
        ["happy_path", "edge_case", "hallucination", "multi_turn"]
    )
    seen_modes = {c.mode for c in cases}
    assert seen_modes == {"happy_path", "edge_case", "hallucination", "multi_turn"}
    assert set(hits) == {"happy_path", "edge_case", "hallucination", "multi_turn"}


def test_generate_mixed_skips_zero_allocation_submodes():
    provider = FakeProvider()
    _, hits = generate_for_topic(
        topic=_topic(),
        knowledge_sources=[],
        tools=[],
        provider=provider,
        mode="mixed",
        count=1,  # 40/30/20/10 of 1 → only happy_path gets the slot
        seed=None,
        cache=None,
    )
    assert hits == {"happy_path": False}
    assert provider.calls == ["happy_path"]


def test_resolve_referenced_pulls_kss_and_tools_by_id():
    ks = KnowledgeSource(id="ks1", name="Catalog", kind="SharePoint")
    tool = Tool(id="tl1", name="Lookup")
    solution = Solution(topics=[], knowledge_sources=[ks], tools=[tool])
    topic = _topic(knowledge_source_ids=["ks1", "missing"], tool_ids=["tl1"])
    kss, tools = resolve_referenced(solution, topic)
    assert [k.name for k in kss] == ["Catalog"]
    assert [t.name for t in tools] == ["Lookup"]
