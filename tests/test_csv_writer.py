"""Tests for the CSV writer."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from evalforge.csv_writer import CSV_COLUMNS, write_csv
from evalforge.generation.grader import GRADER_COMPARE_MEANING, GRADER_KEYWORD_MATCH
from evalforge.generation.models import TestCase


def _case(**overrides) -> TestCase:
    base = dict(
        topic_id="t1",
        topic_name="Store Hours",
        mode="happy_path",
        user_input="When are you open?",
        expected_response="We are open Mon-Fri 9-5.",
        grader=GRADER_COMPARE_MEANING,
        keywords=[],
        rationale="direct phrasing",
    )
    base.update(overrides)
    return TestCase(**base)


def test_write_csv_round_trips(tmp_path: Path):
    out = tmp_path / "out.csv"
    write_csv(out, [_case(), _case(user_input="What time?", expected_response="9-5.")])
    rows = _read_csv(out)
    assert rows[0] == CSV_COLUMNS
    assert len(rows) == 3
    assert rows[1][0] == "Store Hours #1"
    assert rows[1][1] == "When are you open?"
    assert rows[2][0] == "Store Hours #2"


def test_write_csv_uses_utf8_bom(tmp_path: Path):
    out = tmp_path / "out.csv"
    write_csv(out, [_case()])
    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "expected UTF-8 BOM for clean Excel/PowerPlatform import"


def test_write_csv_uses_crlf(tmp_path: Path):
    out = tmp_path / "out.csv"
    write_csv(out, [_case()])
    raw = out.read_bytes()
    assert b"\r\n" in raw


def test_write_csv_serializes_keywords_comma_separated(tmp_path: Path):
    out = tmp_path / "out.csv"
    write_csv(
        out,
        [_case(grader=GRADER_KEYWORD_MATCH, keywords=["sorry", "cannot help"])],
    )
    rows = _read_csv(out)
    assert rows[1][3] == GRADER_KEYWORD_MATCH
    assert rows[1][4] == "sorry, cannot help"


def test_write_csv_rejects_empty_user_input(tmp_path: Path):
    out = tmp_path / "out.csv"
    with pytest.raises(ValueError, match="empty user_input"):
        write_csv(out, [_case(user_input="   ")])


def test_write_csv_rejects_empty_expected_response(tmp_path: Path):
    out = tmp_path / "out.csv"
    with pytest.raises(ValueError, match="empty expected_response"):
        write_csv(out, [_case(expected_response="")])


def test_write_csv_rejects_unknown_grader(tmp_path: Path):
    out = tmp_path / "out.csv"
    with pytest.raises(ValueError, match="unknown grader"):
        write_csv(out, [_case(grader="Vibe check")])


def test_write_csv_rejects_keyword_match_without_keywords(tmp_path: Path):
    out = tmp_path / "out.csv"
    with pytest.raises(ValueError, match="no keywords"):
        write_csv(out, [_case(grader=GRADER_KEYWORD_MATCH, keywords=[])])


def _read_csv(path: Path) -> list[list[str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))
