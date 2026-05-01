"""Tests for the EvalForge CLI."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from evalforge.cli import app

runner = CliRunner()


def test_inspect_directory_prints_summary(sample_solution_dir: Path):
    result = runner.invoke(app, ["inspect", str(sample_solution_dir)])
    assert result.exit_code == 0, result.output
    assert "EvalForge Test Bot" in result.output
    assert "Store Hours" in result.output
    assert "Product Info" in result.output
    assert "Order Status" in result.output
    assert "Product Catalog" in result.output
    assert "Orders Lookup" in result.output
    # System topic hidden by default
    assert "Greeting" not in result.output
    assert "system topic" in result.output.lower()


def test_inspect_zip_prints_summary(sample_solution_zip: Path):
    result = runner.invoke(app, ["inspect", str(sample_solution_zip)])
    assert result.exit_code == 0, result.output
    assert "Store Hours" in result.output
    assert "Product Catalog" in result.output


def test_inspect_include_system(sample_solution_dir: Path):
    result = runner.invoke(
        app, ["inspect", str(sample_solution_dir), "--include-system"]
    )
    assert result.exit_code == 0, result.output
    assert "Greeting" in result.output


def test_inspect_show_triggers(sample_solution_dir: Path):
    result = runner.invoke(
        app, ["inspect", str(sample_solution_dir), "--show-triggers"]
    )
    assert result.exit_code == 0, result.output
    assert "When are you open?" in result.output
    assert "Track my package" in result.output


def test_inspect_missing_path_errors(tmp_path: Path):
    result = runner.invoke(app, ["inspect", str(tmp_path / "does-not-exist")])
    assert result.exit_code != 0


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "evalforge" in result.output.lower()
