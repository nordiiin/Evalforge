"""Data models for parsed Copilot Studio components."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Topic:
    """A Copilot Studio topic (AdaptiveDialog component)."""

    id: str
    name: str
    description: str | None = None
    trigger_phrases: list[str] = field(default_factory=list)
    knowledge_source_ids: list[str] = field(default_factory=list)
    tool_ids: list[str] = field(default_factory=list)
    raw_yaml: str = ""
    is_system: bool = False
    source_path: str = ""


@dataclass
class KnowledgeSource:
    """A knowledge source attached to the bot (SharePoint, web, file, ...)."""

    id: str
    name: str
    description: str | None = None
    kind: str = "Unknown"
    raw_yaml: str = ""
    source_path: str = ""


@dataclass
class Tool:
    """A tool / skill / connector action callable by the bot."""

    id: str
    name: str
    description: str | None = None
    kind: str = "Unknown"
    raw_yaml: str = ""
    source_path: str = ""


@dataclass
class Solution:
    """A parsed Copilot Studio solution export."""

    source: str = ""
    bot_name: str | None = None
    topics: list[Topic] = field(default_factory=list)
    knowledge_sources: list[KnowledgeSource] = field(default_factory=list)
    tools: list[Tool] = field(default_factory=list)
