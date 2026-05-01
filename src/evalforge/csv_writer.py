"""Writes generated test cases to a CSV in Copilot Studio Agent Evaluation format.

⚠️  WORKING ASSUMPTION — VERIFY BEFORE PRODUCTION USE
SPEC.md §5 notes that the canonical column schema lives in Philip's
`copilot-studio-eval` skill. That skill was not available when this file was
written, so the columns and grader labels below are a best-effort working
assumption based on:

  - The four documented Copilot Studio grader types: Compare meaning,
    Keyword match, General quality, Exact match.
  - Typical Power Platform CSV import shapes.

Confirm the columns and grader labels against an actual Copilot Studio Agent
Evaluation import before relying on the output. To update, edit `CSV_COLUMNS`
and the `GRADER_*` constants below — every other module references these.
"""

from __future__ import annotations

import csv
from pathlib import Path

from evalforge.generation.grader import (
    ALL_GRADERS,
    GRADER_KEYWORD_MATCH,
)
from evalforge.generation.models import TestCase

CSV_COLUMNS = [
    "Test case name",
    "User input",
    "Expected response",
    "Grader",
    "Keywords",
]


def write_csv(path: Path, cases: list[TestCase]) -> None:
    """Validate every row, then write the CSV.

    Uses `utf-8-sig` (UTF-8 with BOM) and CRLF line terminators — both are
    what Excel and Power Platform tooling expect for clean imports.
    """
    rows = [_to_row(case, idx) for idx, case in enumerate(cases, start=1)]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        writer.writerow(CSV_COLUMNS)
        writer.writerows(rows)


def _to_row(case: TestCase, idx: int) -> list[str]:
    _validate_row(case, idx)
    return [
        f"{case.topic_name} #{idx}",
        case.user_input,
        case.expected_response,
        case.grader,
        ", ".join(case.keywords),
    ]


def _validate_row(case: TestCase, idx: int) -> None:
    if not case.user_input.strip():
        raise ValueError(
            f"Test case #{idx} for topic {case.topic_name!r} has an empty user_input."
        )
    if not case.expected_response.strip():
        raise ValueError(
            f"Test case #{idx} for topic {case.topic_name!r} has an empty expected_response."
        )
    if case.grader not in ALL_GRADERS:
        raise ValueError(
            f"Test case #{idx} for topic {case.topic_name!r} has unknown grader "
            f"{case.grader!r}. Must be one of {sorted(ALL_GRADERS)}."
        )
    if case.grader == GRADER_KEYWORD_MATCH and not case.keywords:
        raise ValueError(
            f"Test case #{idx} for topic {case.topic_name!r} uses "
            f"{GRADER_KEYWORD_MATCH!r} grader but has no keywords."
        )
