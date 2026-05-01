"""Anthropic provider — uses Claude with strict tool use for typed output.

Key design choices, all from the claude-api skill:

- Default model is `claude-opus-4-7`. Override via `--model`.
- Adaptive thinking on (`thinking={"type": "adaptive"}`) and effort `medium`
  — this is structured generation, so we want some reasoning but not the
  full Opus xhigh budget.
- Strict tool use (`strict: True`) on a forced `tool_choice` for guaranteed
  schema compliance — never parse free text.
- Prompt caching on the system prompt block. Tools render before system, so
  this caches both tools and system together and the per-topic user message
  is the only thing that varies.
- Streaming via `messages.stream()` and `get_final_message()` to avoid HTTP
  timeouts when adaptive thinking burns extra time.
"""

from __future__ import annotations

import anthropic

from evalforge.generation.prompt import HAPPY_PATH_SYSTEM, build_happy_path_prompt
from evalforge.parser.models import KnowledgeSource, Tool, Topic
from evalforge.providers.base import GeneratedCase

DEFAULT_ANTHROPIC_MODEL = "claude-opus-4-7"
TOOL_NAME = "submit_test_cases"

_TOOL_DEFINITION: dict = {
    "name": TOOL_NAME,
    "description": "Submit the generated test cases for this topic.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "test_cases": {
                "type": "array",
                "description": "The generated test cases. MUST contain exactly the requested count.",
                "items": {
                    "type": "object",
                    "properties": {
                        "user_input": {
                            "type": "string",
                            "description": (
                                "A realistic phrasing of the trigger intent in a "
                                "user's voice. Avoid paraphrasing trigger phrases."
                            ),
                        },
                        "expected_response": {
                            "type": "string",
                            "description": (
                                "The response the agent should give to user_input. "
                                "Align with the topic's message nodes when present, "
                                "or with what the connected knowledge source / tool "
                                "would produce."
                            ),
                        },
                        "rationale": {
                            "type": "string",
                            "description": (
                                "One short sentence on what variation this case "
                                "tests (e.g. 'polite phrasing', 'partial info')."
                            ),
                        },
                    },
                    "required": ["user_input", "expected_response", "rationale"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["test_cases"],
        "additionalProperties": False,
    },
}


class AnthropicProvider:
    """LLM provider backed by Anthropic's Claude via the official SDK."""

    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_ANTHROPIC_MODEL,
    ) -> None:
        self.model = model
        # Reads ANTHROPIC_API_KEY from env if api_key is None.
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    def generate_happy_path(
        self,
        *,
        topic: Topic,
        knowledge_sources: list[KnowledgeSource],
        tools: list[Tool],
        count: int,
        seed: int | None,
    ) -> list[GeneratedCase]:
        user_prompt = build_happy_path_prompt(
            topic=topic,
            knowledge_sources=knowledge_sources,
            tools=tools,
            count=count,
            seed=seed,
        )
        with self._client.messages.stream(
            model=self.model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            system=[
                {
                    "type": "text",
                    "text": HAPPY_PATH_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[_TOOL_DEFINITION],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            message = stream.get_final_message()

        for block in message.content:
            if block.type == "tool_use" and block.name == TOOL_NAME:
                payload = block.input or {}
                items = payload.get("test_cases") or []
                return [
                    GeneratedCase(
                        user_input=str(item.get("user_input", "")).strip(),
                        expected_response=str(item.get("expected_response", "")).strip(),
                        rationale=str(item.get("rationale", "")).strip(),
                    )
                    for item in items
                ]
        raise RuntimeError(
            f"Model did not call {TOOL_NAME!r} (stop_reason={message.stop_reason!r}). "
            "This usually means the request was refused or hit max_tokens."
        )
