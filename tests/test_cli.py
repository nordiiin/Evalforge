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


# ---------------------------------------------------------------------------
# generate command
# ---------------------------------------------------------------------------


def test_generate_dry_run_prints_prompts(sample_solution_dir: Path, tmp_path: Path):
    out = tmp_path / "out.csv"
    result = runner.invoke(
        app,
        [
            "generate",
            str(sample_solution_dir),
            "-o",
            str(out),
            "--dry-run",
            "--count",
            "2",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output
    assert "Store Hours" in result.output
    assert "Generate 2 happy-path test case(s)" in result.output
    assert not out.exists(), "dry-run must not write the CSV"


def test_generate_dry_run_filters_topics(sample_solution_dir: Path, tmp_path: Path):
    result = runner.invoke(
        app,
        [
            "generate",
            str(sample_solution_dir),
            "-o",
            str(tmp_path / "x.csv"),
            "--dry-run",
            "--topic",
            "Store Hours",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Store Hours" in result.output
    # Other topics should not appear in dry-run output
    assert "── Order Status ──" not in result.output
    assert "── Product Info ──" not in result.output


def test_generate_unknown_provider_errors(sample_solution_dir: Path, tmp_path: Path):
    result = runner.invoke(
        app,
        [
            "generate",
            str(sample_solution_dir),
            "-o",
            str(tmp_path / "x.csv"),
            "--provider",
            "llama",
            "--dry-run",
        ],
    )
    assert result.exit_code != 0
    assert "Unknown provider" in result.output


def test_generate_unsupported_mode_errors(sample_solution_dir: Path, tmp_path: Path):
    result = runner.invoke(
        app,
        [
            "generate",
            str(sample_solution_dir),
            "-o",
            str(tmp_path / "x.csv"),
            "--mode",
            "edge_case",
            "--dry-run",
        ],
    )
    assert result.exit_code != 0
    assert "not implemented" in result.output.lower()


def test_generate_missing_api_key_errors(
    sample_solution_dir: Path, tmp_path: Path, monkeypatch
):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(
        app,
        [
            "generate",
            str(sample_solution_dir),
            "-o",
            str(tmp_path / "x.csv"),
        ],
    )
    assert result.exit_code != 0
    assert "ANTHROPIC_API_KEY" in result.output


def test_generate_no_topics_match_errors(sample_solution_dir: Path, tmp_path: Path):
    result = runner.invoke(
        app,
        [
            "generate",
            str(sample_solution_dir),
            "-o",
            str(tmp_path / "x.csv"),
            "--topic",
            "DoesNotExist",
            "--dry-run",
        ],
    )
    assert result.exit_code != 0
    assert "No topics match" in result.output


def test_validate_command_is_placeholder(tmp_path: Path):
    csv_file = tmp_path / "x.csv"
    csv_file.write_text("dummy")
    result = runner.invoke(app, ["validate", str(csv_file)])
    assert result.exit_code != 0
    assert "M4" in result.output


def test_init_command_is_placeholder():
    result = runner.invoke(app, ["init"])
    assert result.exit_code != 0
    assert "M4" in result.output
