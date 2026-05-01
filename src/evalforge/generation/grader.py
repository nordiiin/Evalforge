"""Grader labels and per-mode default grader assignment.

The four labels match Copilot Studio's UI exactly. Will gain rule-based
logic in M3 (e.g. fixed-message-node topic → Exact match).
"""

GRADER_COMPARE_MEANING = "Compare meaning"
GRADER_KEYWORD_MATCH = "Keyword match"
GRADER_GENERAL_QUALITY = "General quality"
GRADER_EXACT_MATCH = "Exact match"

ALL_GRADERS = frozenset(
    {
        GRADER_COMPARE_MEANING,
        GRADER_KEYWORD_MATCH,
        GRADER_GENERAL_QUALITY,
        GRADER_EXACT_MATCH,
    }
)


def default_grader_for_mode(mode: str) -> str:
    if mode == "happy_path":
        return GRADER_COMPARE_MEANING
    if mode == "edge_case":
        return GRADER_GENERAL_QUALITY
    if mode == "hallucination":
        return GRADER_KEYWORD_MATCH
    return GRADER_COMPARE_MEANING
