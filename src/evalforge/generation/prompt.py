"""Prompt construction for the happy-path generation mode.

The system prompt is frozen across all topics so it caches well — keep
volatile content out of it. Per-topic context goes in the user message.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from evalforge.parser.models import KnowledgeSource, Tool, Topic

HAPPY_PATH_SYSTEM = """You generate test cases for Microsoft Copilot Studio Agent Evaluation.

Each request describes ONE topic from a Copilot Studio bot. Your job is to
produce realistic happy-path test cases for that topic — examples of what real
users would say to invoke the topic, paired with the response the agent
should give.

Quality bar:

1. Realistic phrasings, not paraphrases. Vary how the user expresses the
   intent: short and curt, polite and formal, with extra context, with
   typos, with partial information, framed as a statement vs. a question.
   Do NOT simply rewrite the topic's trigger phrases with synonyms — that
   produces tautological tests with no signal.

2. Stay in scope. Each user input should clearly trigger THIS topic and not
   a sibling topic. Avoid inputs that span multiple intents.

3. Expected responses align with the topic's actual behavior. If the topic
   has explicit message nodes (SendActivity activities), the expected
   response should align with those messages. If the topic answers from a
   knowledge source, write a plausible answer the source could provide.
   If the topic invokes a tool / connector, describe the action the agent
   would take or the kind of result it would return.

4. Rationale. For each case, write a short note explaining what variation
   it tests (e.g. "polite phrasing", "indirect framing", "typo tolerance",
   "partial information").

Submit your output via the `submit_test_cases` tool. Always submit exactly
the number of cases requested — no more, no fewer.
"""


def build_happy_path_prompt(
    *,
    topic: Topic,
    knowledge_sources: list[KnowledgeSource],
    tools: list[Tool],
    count: int,
    seed: int | None,
) -> str:
    """Render the per-topic user message for happy-path generation."""
    parts: list[str] = [f"# Topic: {topic.name}"]
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
    parts.append(f"Generate {count} happy-path test case(s) for this topic.")
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
