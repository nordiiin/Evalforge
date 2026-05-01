"""Parse Copilot Studio solution `.zip` exports and topic YAML directories.

The Copilot Studio solution format is a Power Platform solution zip that contains
component YAML files under ``bots/<bot>/botcomponents/<component>/<component>.yaml``.
Each component has a top-level ``kind`` field that tells us whether it's a topic
(``AdaptiveDialog``), a knowledge source (``KnowledgeSource``), or a tool / skill
(``AISkill`` and friends). Real exports vary, so the parser is intentionally
lenient — it walks the archive and routes any YAML doc with a recognised ``kind``
into the right slot.
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from evalforge.parser.models import KnowledgeSource, Solution, Tool, Topic

# Well-known system topic display names. Shipped Copilot Studio bots include
# these by default; users typically don't want eval cases for them.
SYSTEM_TOPIC_NAMES: frozenset[str] = frozenset(
    {
        "Conversation Start",
        "Greeting",
        "Goodbye",
        "End of Conversation",
        "Reset Conversation",
        "Escalate",
        "On Error",
        "Fallback",
        "Start Over",
        "Multiple Topics Matched",
        "Confirmed Success",
        "Confirmed Failure",
        "Thank You",
    }
)

_TOOL_KINDS = {"aiskill", "skill", "connectoraction", "connectoractionskill"}


def parse_input(path: Path) -> Solution:
    """Parse either a ``.zip`` solution export or a directory of YAML files."""
    if path.is_file() and path.suffix.lower() == ".zip":
        return parse_zip(path)
    if path.is_dir():
        return parse_directory(path)
    raise ValueError(
        f"Input must be a .zip solution export or a directory of YAML files: {path}"
    )


def parse_zip(zip_path: Path) -> Solution:
    """Parse a Copilot Studio solution zip in-memory (no extraction to disk)."""
    solution = Solution(source=str(zip_path))
    with zipfile.ZipFile(zip_path, "r") as z:
        members = [m for m in z.infolist() if not m.is_dir()]
        for info in members:
            name = info.filename
            if not name.lower().endswith((".yaml", ".yml")):
                continue
            try:
                raw = z.read(info).decode("utf-8")
            except UnicodeDecodeError:
                continue
            data = _safe_load(raw)
            if data is None:
                continue
            _maybe_set_bot_name(solution, name, data)
            _ingest(solution, data, raw, name)
    _resolve_references(solution)
    return solution


def parse_directory(dir_path: Path) -> Solution:
    """Parse a directory of YAML files. Each YAML is treated as one component."""
    solution = Solution(source=str(dir_path))
    for yaml_path in sorted(dir_path.rglob("*.y*ml")):
        if not yaml_path.is_file():
            continue
        try:
            raw = yaml_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        data = _safe_load(raw)
        if data is None:
            continue
        rel = str(yaml_path.relative_to(dir_path))
        _maybe_set_bot_name(solution, rel, data)
        _ingest(solution, data, raw, rel)
    _resolve_references(solution)
    return solution


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_load(raw: str) -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _maybe_set_bot_name(solution: Solution, path: str, data: dict[str, Any]) -> None:
    """If this YAML looks like the top-level bot manifest, capture its name."""
    lower = path.lower().replace("\\", "/")
    is_bot_manifest = lower.endswith("/bot.yaml") or lower.endswith("/bot.yml")
    if not is_bot_manifest:
        return
    name = data.get("displayName") or data.get("name")
    if name and not solution.bot_name:
        solution.bot_name = str(name)


def _ingest(
    solution: Solution,
    data: dict[str, Any],
    raw: str,
    source_path: str,
) -> None:
    kind = str(data.get("kind") or data.get("Kind") or "").strip()
    kind_l = kind.lower()
    if kind_l == "adaptivedialog":
        topic = _topic_from_yaml(data, raw, source_path)
        if topic is not None:
            solution.topics.append(topic)
    elif "knowledgesource" in kind_l:
        ks = _ks_from_yaml(data, raw, source_path)
        if ks is not None:
            solution.knowledge_sources.append(ks)
    elif kind_l in _TOOL_KINDS:
        tool = _tool_from_yaml(data, raw, source_path)
        if tool is not None:
            solution.tools.append(tool)


def _topic_from_yaml(data: dict[str, Any], raw: str, path: str) -> Topic | None:
    name = data.get("displayName") or data.get("name") or _name_from_path(path)
    if not name:
        return None
    name_str = str(name)
    return Topic(
        id=str(data.get("id") or _name_from_path(path)),
        name=name_str,
        description=_str_or_none(data.get("description")),
        trigger_phrases=_extract_triggers(data),
        raw_yaml=raw,
        is_system=name_str in SYSTEM_TOPIC_NAMES,
        source_path=path,
    )


def _ks_from_yaml(data: dict[str, Any], raw: str, path: str) -> KnowledgeSource | None:
    name = data.get("displayName") or data.get("name") or _name_from_path(path)
    if not name:
        return None
    return KnowledgeSource(
        id=str(data.get("id") or _name_from_path(path)),
        name=str(name),
        description=_str_or_none(data.get("description")),
        kind=str(data.get("knowledgeSourceType") or data.get("sourceType") or "Unknown"),
        raw_yaml=raw,
        source_path=path,
    )


def _tool_from_yaml(data: dict[str, Any], raw: str, path: str) -> Tool | None:
    name = data.get("displayName") or data.get("name") or _name_from_path(path)
    if not name:
        return None
    return Tool(
        id=str(data.get("id") or _name_from_path(path)),
        name=str(name),
        description=_str_or_none(data.get("description")),
        kind=str(data.get("kind") or "Unknown"),
        raw_yaml=raw,
        source_path=path,
    )


def _extract_triggers(data: dict[str, Any]) -> list[str]:
    """Recursively find ``triggerQueries`` anywhere in the topic dict."""
    found: list[str] = []
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "triggerQueries" and isinstance(value, list):
                    for query in value:
                        text = _query_text(query)
                        if text and text not in seen:
                            seen.add(text)
                            found.append(text)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return found


def _query_text(query: Any) -> str | None:
    if isinstance(query, str):
        return query
    if isinstance(query, dict):
        for key in ("phrase", "text", "value"):
            value = query.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _resolve_references(solution: Solution) -> None:
    """Link topics to knowledge sources and tools they reference.

    Real Copilot Studio dialogs reference components by ID inside specific node
    types (``SearchAndSummarizeContent``, ``InvokeAISkill``, ``InvokeConnectorAction``).
    Rather than enumerate every node kind, we collect the known IDs / names and
    scan each topic's tree for any string match.
    """
    ks_lookup = _name_lookup(solution.knowledge_sources)
    tool_lookup = _name_lookup(solution.tools)

    for topic in solution.topics:
        data = _safe_load(topic.raw_yaml)
        if data is None:
            continue
        ks_hits: set[str] = set()
        tool_hits: set[str] = set()
        for value in _walk_strings(data):
            ks_id = ks_lookup.get(value)
            if ks_id is not None:
                ks_hits.add(ks_id)
            tool_id = tool_lookup.get(value)
            if tool_id is not None:
                tool_hits.add(tool_id)
        topic.knowledge_source_ids = sorted(ks_hits)
        topic.tool_ids = sorted(tool_hits)


def _name_lookup(items: Iterable[Any]) -> dict[str, str]:
    """Map both id and name to canonical id, for cheap reverse lookup."""
    lookup: dict[str, str] = {}
    for item in items:
        if item.id:
            lookup[item.id] = item.id
        if item.name and item.name not in lookup:
            lookup[item.name] = item.id
    return lookup


def _walk_strings(node: Any) -> Iterable[str]:
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk_strings(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_strings(item)
    elif isinstance(node, str):
        yield node


def _name_from_path(path: str) -> str:
    return Path(path).stem


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
