"""Edge-case mode — typos, partial info, wrong language, multi-intent inputs."""

from __future__ import annotations

from typing import Any

from evalforge.generation.grader import (
    GRADER_COMPARE_MEANING,
    GRADER_EXACT_MATCH,
    GRADER_GENERAL_QUALITY,
    GRADER_KEYWORD_MATCH,
)
from evalforge.generation.modes.base import ModeSpec, register
from evalforge.providers.base import GeneratedCase

NAME = "edge_case"

SYSTEM_PROMPT = """You generate edge-case test cases for Microsoft Copilot Studio Agent Evaluation.

Each request describes ONE topic. Produce edge-case test cases that probe the
topic's robustness — inputs the agent should still handle correctly even
though they are noisier or partial.

Quality bar:

1. Vary the kind of edge in each case. Use a mix of:
   - Typos and misspellings (light-to-moderate, still recognisable).
   - Partial information (the user omits something the topic usually expects).
   - Wrong language (write the user input in a language different from the
     topic's apparent language — e.g. Swedish input to an English topic).
   - Multi-intent inputs (the user input touches THIS topic plus another
     concern in the same message).
   - Indirect framings (the user describes the goal without naming it).
   - Non-standard register (very casual, slang, or overly formal).

2. The expected response should be what a well-grounded agent SHOULD do —
   answer if the input is clear enough, ask for clarification if not, or
   address the in-scope intent and acknowledge anything off-topic.

3. For `suggested_grader`:
   - "General quality" when correctness is judged by tone / handling rather
     than exact content.
   - "Compare meaning" when there's a clear semantic answer.
   - Avoid "Exact match" for edge cases unless you have a strong reason.

4. Set `keywords` to an empty list unless `suggested_grader` is "Keyword match".

5. In `rationale`, name the kind of edge (e.g. "typo: 'mispeled'", "wrong
   language: Spanish into English-only topic", "multi-intent: hours + return
   policy"). Diversity across the set matters.

Submit exactly the requested number of cases via the `submit_test_cases` tool.
"""

_VALID_GRADERS = [
    GRADER_COMPARE_MEANING,
    GRADER_KEYWORD_MATCH,
    GRADER_GENERAL_QUALITY,
    GRADER_EXACT_MATCH,
]

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "test_cases": {
            "type": "array",
            "description": "MUST contain exactly the requested count.",
            "items": {
                "type": "object",
                "properties": {
                    "user_input": {
                        "type": "string",
                        "description": "An edge-case phrasing — typos, partial info, wrong language, multi-intent, etc.",
                    },
                    "expected_response": {
                        "type": "string",
                        "description": "What a robust agent should respond.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Name the kind of edge this case tests.",
                    },
                    "suggested_grader": {
                        "type": "string",
                        "enum": _VALID_GRADERS,
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "user_input",
                    "expected_response",
                    "rationale",
                    "suggested_grader",
                    "keywords",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["test_cases"],
    "additionalProperties": False,
}


def parse(payload: dict[str, Any]) -> list[GeneratedCase]:
    items = payload.get("test_cases") or []
    return [
        GeneratedCase(
            user_input=str(item.get("user_input", "")).strip(),
            expected_response=str(item.get("expected_response", "")).strip(),
            rationale=str(item.get("rationale", "")).strip(),
            suggested_grader=str(item.get("suggested_grader") or "") or None,
            keywords=[str(k).strip() for k in (item.get("keywords") or []) if str(k).strip()],
        )
        for item in items
    ]


SPEC = register(
    ModeSpec(
        name=NAME,
        system_prompt=SYSTEM_PROMPT,
        tool_name="submit_test_cases",
        tool_description="Submit the generated edge-case test cases.",
        schema=SCHEMA,
        default_grader=GRADER_GENERAL_QUALITY,
        parse=parse,
    )
)
