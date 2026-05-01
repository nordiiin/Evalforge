"""Anthropic provider — uses Claude with strict tool use for typed output.

Defaults from the claude-api skill:
- `claude-opus-4-7`, adaptive thinking, `effort: medium`.
- Strict tool use with forced `tool_choice` for guaranteed schema compliance.
- Prompt caching on the system prompt block (tools render before system, so
  this caches both tools + system together; per-topic user message varies).
- Streaming via `messages.stream()` and `get_final_message()` to avoid HTTP
  timeouts when adaptive thinking burns extra time.
"""

from __future__ import annotations

import anthropic

from evalforge.generation.modes import get_mode
from evalforge.generation.prompt import build_user_message
from evalforge.parser.models import KnowledgeSource, Tool, Topic
from evalforge.providers.base import GeneratedCase

DEFAULT_ANTHROPIC_MODEL = "claude-opus-4-7"


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

    def generate(
        self,
        *,
        mode_name: str,
        topic: Topic,
        knowledge_sources: list[KnowledgeSource],
        tools: list[Tool],
        count: int,
        seed: int | None,
    ) -> list[GeneratedCase]:
        spec = get_mode(mode_name)
        user_prompt = build_user_message(
            topic=topic,
            knowledge_sources=knowledge_sources,
            tools=tools,
            count=count,
            seed=seed,
            mode_name=mode_name,
        )
        tool_definition = {
            "name": spec.tool_name,
            "description": spec.tool_description,
            "strict": True,
            "input_schema": spec.schema,
        }
        with self._client.messages.stream(
            model=self.model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            system=[
                {
                    "type": "text",
                    "text": spec.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[tool_definition],
            tool_choice={"type": "tool", "name": spec.tool_name},
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            message = stream.get_final_message()

        for block in message.content:
            if block.type == "tool_use" and block.name == spec.tool_name:
                return spec.parse(block.input or {})
        raise RuntimeError(
            f"Model did not call {spec.tool_name!r} (stop_reason={message.stop_reason!r}). "
            "This usually means the request was refused or hit max_tokens."
        )
