"""Generation-side data models — what ends up in the CSV."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TestCase:
    """One row in the Copilot Studio Agent Evaluation import CSV."""

    topic_id: str
    topic_name: str
    mode: str
    user_input: str
    expected_response: str
    grader: str = "Compare meaning"
    keywords: list[str] = field(default_factory=list)
    rationale: str = ""

    # Tell pytest not to try to collect this dataclass as a test class.
    __test__ = False
