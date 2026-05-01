"""Mixed-mode allocation. Spec §6 suggests 40/30/20/10."""

from __future__ import annotations

# (mode, weight) — sum is 1.0. Order matters for tie-breaking the rounding.
MIXED_ALLOCATION: tuple[tuple[str, float], ...] = (
    ("happy_path", 0.40),
    ("edge_case", 0.30),
    ("hallucination", 0.20),
    ("multi_turn", 0.10),
)


def allocate(total: int) -> dict[str, int]:
    """Distribute `total` cases across the four sub-modes.

    Uses the largest-remainder method so the integer counts add up to
    `total` exactly. Modes with the largest fractional remainders pick up
    the leftover slots; ties broken by the order in `MIXED_ALLOCATION`.

    Examples (with the spec's 40/30/20/10 split):
        allocate(10) -> {happy_path: 4, edge_case: 3, hallucination: 2, multi_turn: 1}
        allocate(5)  -> {happy_path: 2, edge_case: 2, hallucination: 1, multi_turn: 0}
        allocate(1)  -> {happy_path: 1, edge_case: 0, hallucination: 0, multi_turn: 0}
    """
    if total < 0:
        raise ValueError(f"total must be >= 0, got {total}")

    raw = [(mode, weight * total) for mode, weight in MIXED_ALLOCATION]
    floor_counts = [(mode, int(value)) for mode, value in raw]
    remaining = total - sum(c for _, c in floor_counts)

    if remaining > 0:
        ordered = sorted(
            range(len(raw)),
            key=lambda i: (-(raw[i][1] - floor_counts[i][1]), i),
        )
        floor_list = [list(item) for item in floor_counts]
        for idx in ordered[:remaining]:
            floor_list[idx][1] += 1
        floor_counts = [(name, count) for name, count in floor_list]

    return dict(floor_counts)
