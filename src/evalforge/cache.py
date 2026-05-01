"""On-disk cache for LLM responses.

Re-running the same generate command should cost zero tokens. The cache key
is a SHA-256 of the canonical JSON of (provider, model, mode, count, seed,
topic-fingerprint). Each entry is a JSON file under the cache directory.

Cache invalidates whenever any input that affects the response changes:
parser fingerprint, mode, count, seed, model, or provider.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from evalforge.parser.models import Topic
from evalforge.providers.base import GeneratedCase

_CACHE_VERSION = 1


def default_cache_dir() -> Path:
    """`~/.cache/evalforge/` by default; overridable via EVALFORGE_CACHE_DIR."""
    env = os.environ.get("EVALFORGE_CACHE_DIR")
    if env:
        return Path(env)
    return Path.home() / ".cache" / "evalforge"


def topic_fingerprint(topic: Topic) -> str:
    """A stable hash of the parts of a topic that affect generation."""
    payload = {
        "id": topic.id,
        "name": topic.name,
        "description": topic.description or "",
        "trigger_phrases": sorted(topic.trigger_phrases),
        "knowledge_source_ids": sorted(topic.knowledge_source_ids),
        "tool_ids": sorted(topic.tool_ids),
        "raw_yaml": topic.raw_yaml,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def cache_key(
    *,
    provider: str,
    model: str,
    mode: str,
    count: int,
    seed: int | None,
    topic: Topic,
) -> str:
    payload = {
        "v": _CACHE_VERSION,
        "provider": provider,
        "model": model,
        "mode": mode,
        "count": count,
        "seed": seed,
        "topic": topic_fingerprint(topic),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


class ResponseCache:
    """JSON-file-per-key cache. Atomic writes, no locking (one writer)."""

    def __init__(self, cache_dir: Path) -> None:
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def directory(self) -> Path:
        return self._dir

    def get(self, key: str) -> list[GeneratedCase] | None:
        path = self._dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        cases = data.get("cases")
        if not isinstance(cases, list):
            return None
        return [
            GeneratedCase(
                user_input=str(c.get("user_input", "")),
                expected_response=str(c.get("expected_response", "")),
                rationale=str(c.get("rationale", "")),
            )
            for c in cases
            if isinstance(c, dict)
        ]

    def set(self, key: str, cases: list[GeneratedCase]) -> None:
        path = self._dir / f"{key}.json"
        payload = {"v": _CACHE_VERSION, "cases": [asdict(c) for c in cases]}
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=self._dir,
            suffix=".tmp",
        ) as tmp:
            json.dump(payload, tmp)
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, path)
