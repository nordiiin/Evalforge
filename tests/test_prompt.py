"""Tests for prompt construction and SendActivity extraction."""

from __future__ import annotations

from evalforge.generation.prompt import (
    build_happy_path_prompt,
    extract_send_activities,
)
from evalforge.parser.models import KnowledgeSource, Tool, Topic


def _topic(**overrides) -> Topic:
    base = dict(
        id="t",
        name="Store Hours",
        description="Tells the user our opening hours.",
        trigger_phrases=["When are you open?", "What are your hours?"],
        knowledge_source_ids=[],
        tool_ids=[],
        raw_yaml="",
        is_system=False,
        source_path="",
    )
    base.update(overrides)
    return Topic(**base)


def test_prompt_includes_topic_name_description_triggers():
    prompt = build_happy_path_prompt(
        topic=_topic(), knowledge_sources=[], tools=[], count=3, seed=None
    )
    assert "Store Hours" in prompt
    assert "Tells the user our opening hours." in prompt
    assert "When are you open?" in prompt
    assert "Generate 3 happy-path test case(s)" in prompt


def test_prompt_includes_knowledge_sources_and_tools():
    ks = KnowledgeSource(id="k", name="Catalog", description="Product info", kind="SharePoint")
    tool = Tool(id="x", name="Lookup", description="Looks up orders.")
    prompt = build_happy_path_prompt(
        topic=_topic(), knowledge_sources=[ks], tools=[tool], count=1, seed=None
    )
    assert "Catalog" in prompt
    assert "SharePoint" in prompt
    assert "Lookup" in prompt
    assert "Looks up orders." in prompt


def test_prompt_includes_seed_when_given():
    p_with = build_happy_path_prompt(
        topic=_topic(), knowledge_sources=[], tools=[], count=1, seed=42
    )
    p_without = build_happy_path_prompt(
        topic=_topic(), knowledge_sources=[], tools=[], count=1, seed=None
    )
    assert "seed: 42" in p_with
    assert "seed:" not in p_without


def test_prompt_includes_send_activity_text():
    yaml = (
        "kind: AdaptiveDialog\n"
        "displayName: Store Hours\n"
        "beginDialog:\n"
        "  kind: OnRecognizedIntent\n"
        "  actions:\n"
        "    - kind: SendActivity\n"
        "      activity: We are open Mon-Fri 9-5.\n"
    )
    prompt = build_happy_path_prompt(
        topic=_topic(raw_yaml=yaml), knowledge_sources=[], tools=[], count=1, seed=None
    )
    assert "Topic message nodes" in prompt
    assert "We are open Mon-Fri 9-5." in prompt


def test_extract_send_activities_strips_power_fx():
    yaml = (
        "kind: AdaptiveDialog\n"
        "actions:\n"
        "  - kind: SendActivity\n"
        "    activity: Hello ={User.Name}!\n"
    )
    activities = extract_send_activities(yaml)
    assert activities == ["Hello !"]


def test_extract_send_activities_handles_list_activities():
    yaml = (
        "kind: AdaptiveDialog\n"
        "actions:\n"
        "  - kind: SendActivity\n"
        "    activity:\n"
        "      - First message.\n"
        "      - Second message.\n"
    )
    activities = extract_send_activities(yaml)
    assert "First message." in activities
    assert "Second message." in activities


def test_extract_send_activities_handles_malformed_yaml():
    assert extract_send_activities("not: : : valid") == []
