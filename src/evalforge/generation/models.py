"""Generation-side data models — what ends up in the CSV."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TestCase:
    """One row in the Copilot Studio Agent Evaluation import CSV.

    For single-turn modes, `user_input` is the user's message and `turns` is
    empty. For multi-turn cases, `user_input` is the rendered transcript
    (see `generation.modes.multi_turn.format_transcript`) and `turns` carries
    the structured turn list for any consumer that wants the raw form.
    """

    topic_id: str
    topic_name: str
    mode: str
    user_input: str
    expected_response: str
    grader: str = "Compare meaning"
    keywords: list[str] = field(default_factory=list)
    rationale: str = ""
    turns: list[dict[str, Any]] = field(default_factory=list)

    # Tell pytest not to try to collect this dataclass as a test class.
    __test__ = False

    @property
    def is_multi_turn(self) -> bool:
        return bool(self.turns)
