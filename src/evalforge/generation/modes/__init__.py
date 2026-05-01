"""Generation modes — each mode owns its system prompt, output schema, and parser.

Importing this package registers every mode's ModeSpec.
"""

from evalforge.generation.modes.base import ModeSpec, get_mode

# Side-effect imports: each module calls `register(...)` at import time.
from evalforge.generation.modes import (  # noqa: F401, E402
    edge_case,
    hallucination,
    happy_path,
    multi_turn,
)

SINGLE_TURN_MODES: tuple[str, ...] = ("happy_path", "edge_case", "hallucination")
ALL_MODE_NAMES: tuple[str, ...] = SINGLE_TURN_MODES + ("multi_turn", "mixed")

__all__ = ["ALL_MODE_NAMES", "SINGLE_TURN_MODES", "ModeSpec", "get_mode"]
