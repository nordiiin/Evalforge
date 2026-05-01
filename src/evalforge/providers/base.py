"""LLM provider interface and provider-side data shape."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from evalforge.parser.models import KnowledgeSource, Tool, Topic


@dataclass
class GeneratedCase:
    """One test case as returned by a provider, before grader assignment."""

    user_input: str
    expected_response: str
    rationale: str = ""


class LLMProvider(Protocol):
    """The contract all LLM providers satisfy."""

    name: str
    model: str

    def generate_happy_path(
        self,
        *,
        topic: Topic,
        knowledge_sources: list[KnowledgeSource],
        tools: list[Tool],
        count: int,
        seed: int | None,
    ) -> list[GeneratedCase]:
        ...
