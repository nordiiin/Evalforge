"""Tests for the rule-based grader assigner."""

from __future__ import annotations

from evalforge.generation.grader import (
    GRADER_COMPARE_MEANING,
    GRADER_EXACT_MATCH,
    GRADER_GENERAL_QUALITY,
    GRADER_KEYWORD_MATCH,
    assign_grader,
)
from evalforge.providers.base import GeneratedCase


def _case(**overrides) -> GeneratedCase:
    base = dict(
        user_input="q",
        expected_response="a",
        rationale="r",
        suggested_grader=None,
        keywords=[],
    )
    base.update(overrides)
    return GeneratedCase(**base)


def test_honors_valid_suggestion():
    grader, kws = assign_grader(
        case=_case(suggested_grader=GRADER_GENERAL_QUALITY),
        mode="happy_path",
        topic_send_activities=[],
    )
    assert grader == GRADER_GENERAL_QUALITY
    assert kws == []


def test_keyword_match_without_keywords_falls_back():
    grader, _ = assign_grader(
        case=_case(suggested_grader=GRADER_KEYWORD_MATCH, keywords=[]),
        mode="happy_path",
        topic_send_activities=[],
    )
    # Falls through to mode default (Compare meaning for happy_path).
    assert grader == GRADER_COMPARE_MEANING


def test_keyword_match_with_keywords_passes_through():
    grader, kws = assign_grader(
        case=_case(suggested_grader=GRADER_KEYWORD_MATCH, keywords=["sorry", "cant"]),
        mode="hallucination",
        topic_send_activities=[],
    )
    assert grader == GRADER_KEYWORD_MATCH
    assert kws == ["sorry", "cant"]


def test_happy_path_promotes_to_exact_match_when_response_matches_send_activity():
    case = _case(
        suggested_grader=GRADER_COMPARE_MEANING,  # LLM suggested compare; rule overrides.
        expected_response="We are open Mon-Fri 9-5.",
    )
    grader, kws = assign_grader(
        case=case,
        mode="happy_path",
        topic_send_activities=["We are open Mon-Fri 9-5."],
    )
    assert grader == GRADER_EXACT_MATCH
    assert kws == []


def test_exact_match_suggestion_demoted_when_response_does_not_match():
    case = _case(
        suggested_grader=GRADER_EXACT_MATCH,
        expected_response="Something off-script.",
    )
    grader, _ = assign_grader(
        case=case,
        mode="happy_path",
        topic_send_activities=["We are open Mon-Fri 9-5."],
    )
    assert grader == GRADER_COMPARE_MEANING


def test_hallucination_default_softens_to_general_quality_without_keywords():
    grader, _ = assign_grader(
        case=_case(suggested_grader=None, keywords=[]),
        mode="hallucination",
        topic_send_activities=[],
    )
    assert grader == GRADER_GENERAL_QUALITY


def test_hallucination_default_uses_keyword_match_with_keywords():
    grader, kws = assign_grader(
        case=_case(suggested_grader=None, keywords=["I don't have", "couldn't find"]),
        mode="hallucination",
        topic_send_activities=[],
    )
    assert grader == GRADER_KEYWORD_MATCH
    assert kws == ["I don't have", "couldn't find"]


def test_unknown_suggestion_falls_back_to_mode_default():
    grader, _ = assign_grader(
        case=_case(suggested_grader="Vibe check"),
        mode="edge_case",
        topic_send_activities=[],
    )
    assert grader == GRADER_GENERAL_QUALITY  # edge_case default
