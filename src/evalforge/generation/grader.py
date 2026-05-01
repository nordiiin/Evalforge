"""Grader labels and rule-based grader assignment.

Per SPEC.md §6, the LLM may *suggest* a grader per case and a rule-based
assigner has the final say. Rules:

- A bad fit suggestion (Keyword match without keywords) is overridden.
- For happy-path cases whose expected response matches a SendActivity node
  verbatim, prefer Exact match.
- Hallucination cases default to Keyword match when refusal keywords are
  present, else General quality.
- Otherwise honour the model's suggestion when valid.
- Final fallback: the mode's `default_grader`.
"""

from __future__ import annotations

from evalforge.providers.base import GeneratedCase

GRADER_COMPARE_MEANING = "Compare meaning"
GRADER_KEYWORD_MATCH = "Keyword match"
GRADER_GENERAL_QUALITY = "General quality"
GRADER_EXACT_MATCH = "Exact match"

ALL_GRADERS = frozenset(
    {
        GRADER_COMPARE_MEANING,
        GRADER_KEYWORD_MATCH,
        GRADER_GENERAL_QUALITY,
        GRADER_EXACT_MATCH,
    }
)


def default_grader_for_mode(mode: str) -> str:
    """Per-mode default. Used when no suggestion is provided."""
    if mode == "happy_path":
        return GRADER_COMPARE_MEANING
    if mode == "edge_case":
        return GRADER_GENERAL_QUALITY
    if mode == "hallucination":
        return GRADER_KEYWORD_MATCH
    if mode == "multi_turn":
        return GRADER_COMPARE_MEANING
    return GRADER_COMPARE_MEANING


def assign_grader(
    *,
    case: GeneratedCase,
    mode: str,
    topic_send_activities: list[str],
) -> tuple[str, list[str]]:
    """Choose a (grader, keywords) for a generated case."""
    suggestion = case.suggested_grader if case.suggested_grader in ALL_GRADERS else None
    keywords = list(case.keywords)

    # Override 1: Keyword match without keywords is invalid — drop suggestion.
    if suggestion == GRADER_KEYWORD_MATCH and not keywords:
        suggestion = None

    # Override 2: Exact match is only sensible when the expected response
    # exactly matches a topic message node.
    if suggestion == GRADER_EXACT_MATCH:
        if case.expected_response.strip() not in topic_send_activities:
            suggestion = None

    # Override 3: Happy-path cases that DO match a SendActivity verbatim are
    # better tested with Exact match, regardless of the LLM's suggestion.
    if (
        mode == "happy_path"
        and case.expected_response.strip()
        and case.expected_response.strip() in topic_send_activities
    ):
        return GRADER_EXACT_MATCH, []

    if suggestion is not None:
        if suggestion != GRADER_KEYWORD_MATCH:
            keywords = []
        return suggestion, keywords

    # Mode default fallback.
    fallback = default_grader_for_mode(mode)
    if fallback == GRADER_KEYWORD_MATCH and not keywords:
        # Hallucination case with no keywords — soften to General quality.
        return GRADER_GENERAL_QUALITY, []
    if fallback != GRADER_KEYWORD_MATCH:
        keywords = []
    return fallback, keywords
