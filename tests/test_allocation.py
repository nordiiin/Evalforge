"""Tests for mixed-mode allocation."""

from __future__ import annotations

import pytest

from evalforge.generation.allocation import MIXED_ALLOCATION, allocate


def test_allocate_zero():
    assert allocate(0) == {m: 0 for m, _ in MIXED_ALLOCATION}


def test_allocate_ten_matches_spec_split():
    # 40/30/20/10 of 10 = exactly 4/3/2/1
    assert allocate(10) == {
        "happy_path": 4,
        "edge_case": 3,
        "hallucination": 2,
        "multi_turn": 1,
    }


def test_allocate_total_always_matches_input():
    for n in range(0, 100):
        out = allocate(n)
        assert sum(out.values()) == n


def test_allocate_one_goes_to_happy_path():
    assert allocate(1) == {
        "happy_path": 1,
        "edge_case": 0,
        "hallucination": 0,
        "multi_turn": 0,
    }


def test_allocate_five_distributes_proportionally():
    out = allocate(5)
    # Largest-remainder: 0.4*5=2.0, 0.3*5=1.5, 0.2*5=1.0, 0.1*5=0.5
    # → floors 2,1,1,0; remainder 1 → biggest fractional remainder is edge_case (0.5)
    assert out["happy_path"] == 2
    assert out["edge_case"] == 2
    assert out["hallucination"] + out["multi_turn"] == 1


def test_allocate_negative_rejects():
    with pytest.raises(ValueError):
        allocate(-1)
