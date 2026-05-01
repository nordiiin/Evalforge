"""Build the per-topic user message and extract message-node text.

The user message is the same shape across modes — what varies between modes
is the SYSTEM prompt and tool schema, both owned by the mode registry.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from evalforge.parser.models import KnowledgeSource, Tool, Topic


def build_user_message(
    *,
    topic: Topic,
    knowledge_sources: list[KnowledgeSource],
    tools: list[Tool],
    count: int,
    seed: int | None,
    mode_name: str,
) -> str:
    """Render the per-topic user message. Identical structure across modes."""
    parts: list[str] = [f"# Topic: {topic.name}", f"Mode: {mode_name}"]
    if topic.description:
        parts.append(f"\nDescription: {topic.description}")

    if topic.trigger_phrases:
        parts.append("\n## Trigger phrases")
        parts.extend(f"- {phrase}" for phrase in topic.trigger_phrases)

    if knowledge_sources:
        parts.append("\n## Connected knowledge sources")
        for ks in knowledge_sources:
            desc = ks.description or "no description"
            parts.append(f"- **{ks.name}** ({ks.kind}): {desc}")

    if tools:
        parts.append("\n## Connected tools / actions")
        for tool in tools:
            desc = tool.description or "no description"
            parts.append(f"- **{tool.name}**: {desc}")

    activities = extract_send_activities(topic.raw_yaml)
    if activities:
        parts.append("\n## Topic message nodes")
        parts.append("Verbatim text the agent says for this topic:")
        for activity in activities:
            parts.append(f"- {activity!r}")

    parts.append("\n## Task")
    parts.append(f"Generate {count} {mode_name} test case(s) for this topic.")
    if seed is not None:
        parts.append(
            f"\n(Generation seed: {seed}. Used for cache keying — this run "
            "should be reproducible across re-runs with the same seed.)"
        )
    return "\n".join(parts)


def extract_send_activities(raw_yaml: str) -> list[str]:
    """Pull text from `kind: SendActivity` nodes in a topic YAML."""
    try:
        data = yaml.safe_load(raw_yaml)
    except yaml.YAMLError:
        return []
    if not isinstance(data, (dict, list)):
        return []

    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if str(node.get("kind", "")).lower() == "sendactivity":
                activity = node.get("activity")
                if isinstance(activity, str):
                    text = _strip_power_fx(activity).strip()
                    if text:
                        found.append(text)
                elif isinstance(activity, list):
                    for item in activity:
                        if isinstance(item, str):
                            text = _strip_power_fx(item).strip()
                            if text:
                                found.append(text)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return found


def _strip_power_fx(text: str) -> str:
    """Remove Power Fx interpolation markers like `={...}` from message text."""
    return re.sub(r"=\{[^}]*\}", "", text)
