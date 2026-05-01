"""Multi-turn mode — 2-3 turn conversations testing context retention.

⚠️  CSV format note. SPEC.md §6 calls out that the multi-turn CSV format
"depends on what Copilot Studio's eval CSV supports — verify before
implementing." Without an authoritative reference, this module ships a
working assumption: the prior conversation is rendered as a transcript and
placed in the `User input` column, with the expected agent reply in
`Expected response`. To swap formats, change `format_transcript()` and the
parse function below — every other piece of the pipeline is format-agnostic.
"""

from __future__ import annotations

from typing import Any

from evalforge.generation.grader import (
    GRADER_COMPARE_MEANING,
    GRADER_GENERAL_QUALITY,
    GRADER_KEYWORD_MATCH,
)
from evalforge.generation.modes.base import ModeSpec, register
from evalforge.providers.base import GeneratedCase

NAME = "multi_turn"

SYSTEM_PROMPT = """You generate multi-turn test cases for Microsoft Copilot Studio Agent Evaluation.

Each request describes ONE topic. Produce 2- or 3-turn conversations that
test the agent's context retention and clarification flow.

Quality bar:

1. Each test case is a sequence of `turns`. Use 2 OR 3 turns total. Roles
   alternate strictly between "user" (always first) and "assistant".
   - 2 turns: user → assistant. The case tests whether the agent gives a
     reasonable response to a single user message that may need
     clarification implied by the assistant's response in the *next* turn.
     (Skip this shape unless it matches the topic.)
   - 3 turns: user → assistant → user. The third turn is a follow-up that
     needs the assistant to remember the first turn's context. This is the
     more useful shape for most topics.

2. Set `expected_final_response` to what the agent SHOULD say after the
   final user turn — using the prior turns as context. If the topic
   typically asks a clarifying question, model that in `turns[1]` and have
   the user answer it in `turns[2]`.

3. Stay grounded. Do not invent specific facts the topic can't support.

4. `suggested_grader` should usually be "Compare meaning" — multi-turn
   responses are open-ended. Use "General quality" if correctness is
   judged on tone / clarification flow rather than content.

5. `keywords` is an empty array unless `suggested_grader` is "Keyword match".

6. `rationale` should name what context-retention or clarification
   behaviour the case tests.

Submit exactly the requested number of cases via the `submit_test_cases` tool.
"""

_VALID_GRADERS = [
    GRADER_COMPARE_MEANING,
    GRADER_KEYWORD_MATCH,
    GRADER_GENERAL_QUALITY,
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
                    "turns": {
                        "type": "array",
                        "description": (
                            "Sequence of 2 or 3 turns. Roles alternate strictly "
                            "user → assistant → user. The agent's expected reply "
                            "to the final turn goes in expected_final_response, "
                            "not here."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "enum": ["user", "assistant"],
                                },
                                "content": {"type": "string"},
                            },
                            "required": ["role", "content"],
                            "additionalProperties": False,
                        },
                    },
                    "expected_final_response": {
                        "type": "string",
                        "description": "What the agent should say after the final user turn.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "What context-retention behaviour this case tests.",
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
                    "turns",
                    "expected_final_response",
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


def format_transcript(turns: list[dict[str, Any]]) -> str:
    """Render turns as a human-readable transcript.

    See the module-level note about Copilot Studio's expected format.
    """
    lines: list[str] = []
    for turn in turns:
        role = "User" if turn.get("role") == "user" else "Agent"
        content = str(turn.get("content", "")).strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n\n".join(lines)


def parse(payload: dict[str, Any]) -> list[GeneratedCase]:
    items = payload.get("test_cases") or []
    out: list[GeneratedCase] = []
    for item in items:
        raw_turns = item.get("turns") or []
        normalised_turns = [
            {"role": str(t.get("role", "")), "content": str(t.get("content", "")).strip()}
            for t in raw_turns
            if isinstance(t, dict)
        ]
        out.append(
            GeneratedCase(
                user_input=format_transcript(normalised_turns),
                expected_response=str(item.get("expected_final_response", "")).strip(),
                rationale=str(item.get("rationale", "")).strip(),
                suggested_grader=str(item.get("suggested_grader") or "") or None,
                keywords=[
                    str(k).strip()
                    for k in (item.get("keywords") or [])
                    if str(k).strip()
                ],
                turns=normalised_turns,
            )
        )
    return out


SPEC = register(
    ModeSpec(
        name=NAME,
        system_prompt=SYSTEM_PROMPT,
        tool_name="submit_test_cases",
        tool_description="Submit the generated multi-turn test cases.",
        schema=SCHEMA,
        default_grader=GRADER_COMPARE_MEANING,
        parse=parse,
    )
)
