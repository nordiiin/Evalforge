"""Tests for the Copilot Studio solution parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from evalforge.parser import parse_directory, parse_input, parse_zip
from evalforge.parser.models import Solution


def _topic(solution: Solution, name: str):
    matches = [t for t in solution.topics if t.name == name]
    assert len(matches) == 1, f"expected one topic named {name!r}, found {len(matches)}"
    return matches[0]


# ---------------------------------------------------------------------------
# Directory parsing
# ---------------------------------------------------------------------------


def test_parse_directory_finds_all_components(sample_solution_dir: Path):
    solution = parse_directory(sample_solution_dir)
    assert solution.bot_name == "EvalForge Test Bot"
    names = {t.name for t in solution.topics}
    assert names == {"Store Hours", "Product Info", "Order Status", "Greeting"}
    assert {ks.name for ks in solution.knowledge_sources} == {"Product Catalog"}
    assert {tool.name for tool in solution.tools} == {"Orders Lookup"}


def test_parse_directory_extracts_trigger_phrases(sample_solution_dir: Path):
    solution = parse_directory(sample_solution_dir)
    store_hours = _topic(solution, "Store Hours")
    assert store_hours.trigger_phrases == [
        "When are you open?",
        "What are your store hours?",
        "Are you open on Sunday?",
    ]


def test_parse_directory_marks_system_topics(sample_solution_dir: Path):
    solution = parse_directory(sample_solution_dir)
    greeting = _topic(solution, "Greeting")
    assert greeting.is_system is True
    store_hours = _topic(solution, "Store Hours")
    assert store_hours.is_system is False


def test_parse_directory_resolves_knowledge_source_references(sample_solution_dir: Path):
    solution = parse_directory(sample_solution_dir)
    product_info = _topic(solution, "Product Info")
    assert product_info.knowledge_source_ids == ["ks_product_catalog"]
    store_hours = _topic(solution, "Store Hours")
    assert store_hours.knowledge_source_ids == []


def test_parse_directory_resolves_tool_references(sample_solution_dir: Path):
    solution = parse_directory(sample_solution_dir)
    order_status = _topic(solution, "Order Status")
    assert order_status.tool_ids == ["tool_orders_lookup"]
    store_hours = _topic(solution, "Store Hours")
    assert store_hours.tool_ids == []


def test_parse_directory_preserves_raw_yaml(sample_solution_dir: Path):
    solution = parse_directory(sample_solution_dir)
    store_hours = _topic(solution, "Store Hours")
    assert "triggerQueries" in store_hours.raw_yaml
    assert "When are you open?" in store_hours.raw_yaml


def test_parse_directory_captures_descriptions(sample_solution_dir: Path):
    solution = parse_directory(sample_solution_dir)
    catalog = next(ks for ks in solution.knowledge_sources if ks.name == "Product Catalog")
    assert catalog.kind == "SharePoint"
    assert catalog.description and "SharePoint" in catalog.description


# ---------------------------------------------------------------------------
# Zip parsing
# ---------------------------------------------------------------------------


def test_parse_zip_matches_directory(sample_solution_zip: Path, sample_solution_dir: Path):
    from_zip = parse_zip(sample_solution_zip)
    from_dir = parse_directory(sample_solution_dir)

    assert from_zip.bot_name == from_dir.bot_name
    assert sorted(t.name for t in from_zip.topics) == sorted(t.name for t in from_dir.topics)
    assert sorted(k.name for k in from_zip.knowledge_sources) == sorted(
        k.name for k in from_dir.knowledge_sources
    )
    assert sorted(t.name for t in from_zip.tools) == sorted(t.name for t in from_dir.tools)


def test_parse_zip_resolves_references(sample_solution_zip: Path):
    solution = parse_zip(sample_solution_zip)
    product_info = _topic(solution, "Product Info")
    assert product_info.knowledge_source_ids == ["ks_product_catalog"]
    order_status = _topic(solution, "Order Status")
    assert order_status.tool_ids == ["tool_orders_lookup"]


# ---------------------------------------------------------------------------
# Input dispatch / errors
# ---------------------------------------------------------------------------


def test_parse_input_dispatches_zip(sample_solution_zip: Path):
    solution = parse_input(sample_solution_zip)
    assert len(solution.topics) == 4


def test_parse_input_dispatches_directory(sample_solution_dir: Path):
    solution = parse_input(sample_solution_dir)
    assert len(solution.topics) == 4


def test_parse_input_rejects_other_files(tmp_path: Path):
    bogus = tmp_path / "thing.txt"
    bogus.write_text("not a solution")
    with pytest.raises(ValueError, match="must be a .zip"):
        parse_input(bogus)


def test_parse_directory_skips_non_yaml(tmp_path: Path):
    (tmp_path / "readme.txt").write_text("hello")
    (tmp_path / "topic.yaml").write_text(
        "kind: AdaptiveDialog\ndisplayName: T\nbeginDialog:\n  intent:\n    triggerQueries: [hi]\n"
    )
    solution = parse_directory(tmp_path)
    assert [t.name for t in solution.topics] == ["T"]


def test_parse_directory_tolerates_malformed_yaml(tmp_path: Path):
    (tmp_path / "broken.yaml").write_text("kind: AdaptiveDialog\n  : : :\n")
    (tmp_path / "topic.yaml").write_text(
        "kind: AdaptiveDialog\ndisplayName: Good\nbeginDialog: {}\n"
    )
    solution = parse_directory(tmp_path)
    assert [t.name for t in solution.topics] == ["Good"]
