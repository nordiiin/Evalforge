"""Shared pytest fixtures."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_DIR = FIXTURES / "sample_solution"


@pytest.fixture(scope="session")
def sample_solution_dir() -> Path:
    """Path to the on-disk sample solution tree."""
    assert SAMPLE_DIR.is_dir(), f"missing fixture: {SAMPLE_DIR}"
    return SAMPLE_DIR


@pytest.fixture()
def sample_solution_zip(tmp_path: Path, sample_solution_dir: Path) -> Path:
    """Zip the sample solution tree into a temp .zip and return its path."""
    zip_path = tmp_path / "sample_solution.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for item in sample_solution_dir.rglob("*"):
            if item.is_file():
                z.write(item, item.relative_to(sample_solution_dir))
    return zip_path
