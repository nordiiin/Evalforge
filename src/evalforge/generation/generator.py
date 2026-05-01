"""Per-topic generation orchestration: provider call + cache + grader assignment."""

from __future__ import annotations

from evalforge.cache import ResponseCache, cache_key
from evalforge.generation.allocation import allocate
from evalforge.generation.grader import assign_grader
from evalforge.generation.models import TestCase
from evalforge.generation.modes import ALL_MODE_NAMES, SINGLE_TURN_MODES
from evalforge.generation.prompt import extract_send_activities
from evalforge.parser.models import KnowledgeSource, Solution, Tool, Topic
from evalforge.providers.base import LLMProvider

SUPPORTED_MODES: tuple[str, ...] = ALL_MODE_NAMES


def generate_for_topic(
    *,
    topic: Topic,
    knowledge_sources: list[KnowledgeSource],
    tools: list[Tool],
    provider: LLMProvider,
    mode: str,
    count: int,
    seed: int | None,
    cache: ResponseCache | None,
) -> tuple[list[TestCase], dict[str, bool]]:
    """Generate test cases for one topic.

    Returns (cases, cache_hits) where `cache_hits` maps each invoked sub-mode
    to whether the cache served the request. For single-mode runs the dict
    has one entry; for "mixed" it has up to four.
    """
    if mode == "mixed":
        return _generate_mixed(
            topic=topic,
            knowledge_sources=knowledge_sources,
            tools=tools,
            provider=provider,
            count=count,
            seed=seed,
            cache=cache,
        )

    if mode not in SINGLE_TURN_MODES and mode != "multi_turn":
        raise NotImplementedError(
            f"Mode {mode!r} is not implemented. Supported: {SUPPORTED_MODES}"
        )

    raw_cases, was_cached = _generate_single_mode(
        topic=topic,
        knowledge_sources=knowledge_sources,
        tools=tools,
        provider=provider,
        mode=mode,
        count=count,
        seed=seed,
        cache=cache,
    )
    send_activities = extract_send_activities(topic.raw_yaml)
    cases = [
        _to_test_case(raw, topic=topic, mode=mode, send_activities=send_activities)
        for raw in raw_cases
    ]
    return cases, {mode: was_cached}


def _generate_mixed(
    *,
    topic: Topic,
    knowledge_sources: list[KnowledgeSource],
    tools: list[Tool],
    provider: LLMProvider,
    count: int,
    seed: int | None,
    cache: ResponseCache | None,
) -> tuple[list[TestCase], dict[str, bool]]:
    counts = allocate(count)
    send_activities = extract_send_activities(topic.raw_yaml)
    all_cases: list[TestCase] = []
    cache_hits: dict[str, bool] = {}
    for sub_mode, sub_count in counts.items():
        if sub_count <= 0:
            continue
        raw, was_cached = _generate_single_mode(
            topic=topic,
            knowledge_sources=knowledge_sources,
            tools=tools,
            provider=provider,
            mode=sub_mode,
            count=sub_count,
            seed=seed,
            cache=cache,
        )
        cache_hits[sub_mode] = was_cached
        all_cases.extend(
            _to_test_case(rc, topic=topic, mode=sub_mode, send_activities=send_activities)
            for rc in raw
        )
    return all_cases, cache_hits


def _generate_single_mode(
    *,
    topic: Topic,
    knowledge_sources: list[KnowledgeSource],
    tools: list[Tool],
    provider: LLMProvider,
    mode: str,
    count: int,
    seed: int | None,
    cache: ResponseCache | None,
):
    key = cache_key(
        provider=provider.name,
        model=provider.model,
        mode=mode,
        count=count,
        seed=seed,
        topic=topic,
    )
    cached = cache.get(key) if cache is not None else None
    if cached is not None:
        return cached, True

    raw = provider.generate(
        mode_name=mode,
        topic=topic,
        knowledge_sources=knowledge_sources,
        tools=tools,
        count=count,
        seed=seed,
    )
    if cache is not None:
        cache.set(key, raw)
    return raw, False


def _to_test_case(raw, *, topic: Topic, mode: str, send_activities: list[str]) -> TestCase:
    grader, keywords = assign_grader(
        case=raw,
        mode=mode,
        topic_send_activities=send_activities,
    )
    return TestCase(
        topic_id=topic.id,
        topic_name=topic.name,
        mode=mode,
        user_input=raw.user_input,
        expected_response=raw.expected_response,
        rationale=raw.rationale,
        grader=grader,
        keywords=keywords,
        turns=list(raw.turns),
    )


def resolve_referenced(
    solution: Solution, topic: Topic
) -> tuple[list[KnowledgeSource], list[Tool]]:
    """Look up the knowledge sources / tools a topic references."""
    ks_by_id = {ks.id: ks for ks in solution.knowledge_sources}
    tool_by_id = {t.id: t for t in solution.tools}
    return (
        [ks_by_id[i] for i in topic.knowledge_source_ids if i in ks_by_id],
        [tool_by_id[i] for i in topic.tool_ids if i in tool_by_id],
    )
