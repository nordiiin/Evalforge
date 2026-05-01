"""LLM provider interface and provider-side data shape."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from evalforge.parser.models import KnowledgeSource, Tool, Topic


@dataclass
class GeneratedCase:
    """One test case as returned by a provider, before grader assignment."""

    user_input: str = ""
    expected_response: str = ""
    rationale: str = ""
    suggested_grader: str | None = None
    keywords: list[str] = field(default_factory=list)
    turns: list[dict[str, Any]] = field(default_factory=list)


class LLMProvider(Protocol):
    """The contract all LLM providers satisfy."""

    name: str
    model: str

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
        ...
