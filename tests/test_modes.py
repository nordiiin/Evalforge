"""Tests for the mode registry and per-mode parse functions."""

from __future__ import annotations

import pytest

from evalforge.generation.modes import ALL_MODE_NAMES, get_mode
from evalforge.generation.modes.multi_turn import format_transcript


def test_registry_contains_all_single_turn_modes():
    for name in ("happy_path", "edge_case", "hallucination", "multi_turn"):
        spec = get_mode(name)
        assert spec.name == name
        assert spec.system_prompt
        assert spec.tool_name == "submit_test_cases"
        assert spec.schema["type"] == "object"
        assert "test_cases" in spec.schema["properties"]


def test_all_mode_names_includes_mixed():
    assert "mixed" in ALL_MODE_NAMES


def test_get_mode_unknown_raises():
    with pytest.raises(KeyError, match="Unknown mode"):
        get_mode("nope")


def test_strict_schemas_have_required_and_no_additional_props():
    for name in ("happy_path", "edge_case", "hallucination", "multi_turn"):
        spec = get_mode(name)
        item_schema = spec.schema["properties"]["test_cases"]["items"]
        assert item_schema["additionalProperties"] is False
        assert set(item_schema["required"]) == set(item_schema["properties"].keys())


def test_happy_path_parse_handles_typical_payload():
    spec = get_mode("happy_path")
    cases = spec.parse(
        {
            "test_cases": [
                {
                    "user_input": "When?",
                    "expected_response": "9-5.",
                    "rationale": "direct",
                    "suggested_grader": "Compare meaning",
                    "keywords": [],
                }
            ]
        }
    )
    assert len(cases) == 1
    assert cases[0].user_input == "When?"
    assert cases[0].suggested_grader == "Compare meaning"
    assert cases[0].keywords == []


def test_hallucination_parse_keeps_keywords():
    spec = get_mode("hallucination")
    cases = spec.parse(
        {
            "test_cases": [
                {
                    "user_input": "Where's order 99?",
                    "expected_response": "I can't find that order.",
                    "rationale": "fake order",
                    "suggested_grader": "Keyword match",
                    "keywords": ["can't find", "I don't have"],
                }
            ]
        }
    )
    assert cases[0].keywords == ["can't find", "I don't have"]
    assert cases[0].suggested_grader == "Keyword match"


def test_multi_turn_parse_renders_transcript_and_keeps_turns():
    spec = get_mode("multi_turn")
    cases = spec.parse(
        {
            "test_cases": [
                {
                    "turns": [
                        {"role": "user", "content": "What time?"},
                        {"role": "assistant", "content": "Which day?"},
                        {"role": "user", "content": "Sunday."},
                    ],
                    "expected_final_response": "Closed Sundays.",
                    "rationale": "carry-context",
                    "suggested_grader": "Compare meaning",
                    "keywords": [],
                }
            ]
        }
    )
    assert len(cases) == 1
    assert "User: What time?" in cases[0].user_input
    assert "Agent: Which day?" in cases[0].user_input
    assert "User: Sunday." in cases[0].user_input
    assert cases[0].expected_response == "Closed Sundays."
    assert len(cases[0].turns) == 3


def test_format_transcript_skips_empty_turns():
    rendered = format_transcript(
        [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "still there?"},
        ]
    )
    assert "User: hi" in rendered
    assert "Agent: " not in rendered
    assert "User: still there?" in rendered
