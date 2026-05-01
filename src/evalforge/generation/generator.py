"""Per-topic generation orchestration: provider call + cache + grader."""

from __future__ import annotations

from evalforge.cache import ResponseCache, cache_key
from evalforge.generation.grader import default_grader_for_mode
from evalforge.generation.models import TestCase
from evalforge.parser.models import KnowledgeSource, Solution, Tool, Topic
from evalforge.providers.base import LLMProvider

SUPPORTED_MODES = {"happy_path"}


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
) -> tuple[list[TestCase], bool]:
    """Generate test cases for one topic. Returns (cases, was_cached)."""
    if mode not in SUPPORTED_MODES:
        raise NotImplementedError(
            f"Mode {mode!r} is not implemented yet. M2 supports: {sorted(SUPPORTED_MODES)}"
        )

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
        raw_cases = cached
        was_cached = True
    else:
        raw_cases = provider.generate_happy_path(
            topic=topic,
            knowledge_sources=knowledge_sources,
            tools=tools,
            count=count,
            seed=seed,
        )
        if cache is not None:
            cache.set(key, raw_cases)
        was_cached = False

    grader = default_grader_for_mode(mode)
    cases = [
        TestCase(
            topic_id=topic.id,
            topic_name=topic.name,
            mode=mode,
            user_input=raw.user_input,
            expected_response=raw.expected_response,
            rationale=raw.rationale,
            grader=grader,
        )
        for raw in raw_cases
    ]
    return cases, was_cached


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
