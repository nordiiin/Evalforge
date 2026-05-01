"""Happy-path mode — realistic phrasings of the trigger intent."""

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

NAME = "happy_path"

SYSTEM_PROMPT = """You generate happy-path test cases for Microsoft Copilot Studio Agent Evaluation.

Each request describes ONE topic. Produce realistic happy-path test cases:
examples of what real users would say to invoke the topic, paired with the
response the agent should give.

Quality bar:

1. Realistic phrasings, not paraphrases. Vary how the user expresses the
   intent: short and curt, polite and formal, with extra context, framed as
   a statement vs. a question. Do NOT just rewrite the trigger phrases with
   synonyms — that produces tautological tests with no signal.

2. Stay in scope. Each user input should clearly trigger THIS topic.

3. Expected responses align with the topic's actual behavior. If the topic
   has explicit message nodes, align with them. If it answers from a
   knowledge source, write a plausible answer. If it invokes a tool,
   describe the action / kind of result.

4. For each case, set `suggested_grader` thoughtfully:
   - "Exact match" only when the topic has a fixed message node and the user
     input clearly leads to that exact response.
   - "Compare meaning" for open-ended responses (knowledge-source answers,
     tool results) — this is the most common choice for happy-path.
   - "Keyword match" only if you also provide `keywords`.
   - "General quality" if the response is open-ended and accuracy can't be
     measured against a fixed answer.

5. Set `keywords` to an empty list unless `suggested_grader` is "Keyword match".

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
                        "description": (
                            "A realistic phrasing of the trigger intent in a user's voice. "
                            "Avoid paraphrasing trigger phrases with synonyms."
                        ),
                    },
                    "expected_response": {
                        "type": "string",
                        "description": "The agent's expected response.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "One short sentence on what variation this case tests.",
                    },
                    "suggested_grader": {
                        "type": "string",
                        "enum": _VALID_GRADERS,
                        "description": "Your best guess at the right grader for this case.",
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Required keywords if suggested_grader is 'Keyword match'. "
                            "Otherwise an empty array."
                        ),
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
        tool_description="Submit the generated happy-path test cases.",
        schema=SCHEMA,
        default_grader=GRADER_COMPARE_MEANING,
        parse=parse,
    )
)
