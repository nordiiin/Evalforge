"""Mode registry. Each mode declares its system prompt, JSON schema, and parser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from evalforge.providers.base import GeneratedCase

ParseFn = Callable[[dict[str, Any]], list[GeneratedCase]]


@dataclass(frozen=True)
class ModeSpec:
    """Everything provider code needs to call the LLM for one generation mode.

    `schema` is the JSON Schema body for the structured output (an `object`
    with a `test_cases` array). It must be strict-mode-compatible: every field
    `required`, `additionalProperties: false` everywhere. Both Anthropic
    (`tools[].input_schema` + strict) and OpenAI (`response_format.json_schema`
    + strict) accept the same body.
    """

    name: str
    system_prompt: str
    tool_name: str
    tool_description: str
    schema: dict[str, Any]
    default_grader: str
    parse: ParseFn


_REGISTRY: dict[str, ModeSpec] = {}


def register(spec: ModeSpec) -> ModeSpec:
    if spec.name in _REGISTRY:
        raise ValueError(f"Mode {spec.name!r} is already registered")
    _REGISTRY[spec.name] = spec
    return spec


def get_mode(name: str) -> ModeSpec:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown mode {name!r}. Registered modes: {sorted(_REGISTRY)}")
    return _REGISTRY[name]
