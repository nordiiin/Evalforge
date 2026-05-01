"""OpenAI and Azure OpenAI providers — strict structured outputs via JSON Schema.

OpenAI's `response_format={"type": "json_schema", "json_schema": {..., "strict": true}}`
gives us the same guarantee as Anthropic's strict tool use: the model returns
JSON conforming to our schema. Both providers use it identically; Azure
differs only in client construction (deployment name, endpoint, api_version).

Default OpenAI model is `gpt-4o`. For Azure, the user must pass `--model
<deployment-name>` since deployment names are tenant-specific.
"""

from __future__ import annotations

import json
import os
from typing import Any

from evalforge.generation.modes import get_mode
from evalforge.generation.prompt import build_user_message
from evalforge.parser.models import KnowledgeSource, Tool, Topic
from evalforge.providers.base import GeneratedCase

DEFAULT_OPENAI_MODEL = "gpt-4o"
RESPONSE_FORMAT_NAME = "test_cases_response"


class OpenAIProvider:
    """LLM provider backed by OpenAI's chat completions with json_schema strict."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = DEFAULT_OPENAI_MODEL,
    ) -> None:
        from openai import OpenAI

        self.model = model
        self._client = OpenAI(api_key=api_key) if api_key else OpenAI()

    def generate(
        self,
        *,
        mode_name: str,
        topic: Topic,
        knowledge_sources: list[KnowledgeSource],
        tools: list[Tool],
        count: int,
        seed: int | None,
    ) -> list[GeneratedCase]:
        return _generate_via_json_schema(
            client=self._client,
            model=self.model,
            mode_name=mode_name,
            topic=topic,
            knowledge_sources=knowledge_sources,
            tools=tools,
            count=count,
            seed=seed,
        )


class AzureOpenAIProvider:
    """Azure OpenAI provider. Reuses the same json_schema strict path.

    Azure requires `--model <deployment-name>` (the deployment is the routable
    name, not the underlying model). Auth comes from environment variables:
        AZURE_OPENAI_API_KEY      — API key
        AZURE_OPENAI_ENDPOINT     — e.g. https://my-resource.openai.azure.com
        OPENAI_API_VERSION        — e.g. 2024-08-01-preview (or pass --api-version)
    """

    name = "azure"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        endpoint: str | None = None,
        api_version: str | None = None,
    ) -> None:
        from openai import AzureOpenAI

        if not model:
            raise ValueError(
                "Azure requires --model set to your deployment name "
                "(e.g. 'gpt-4o-prod')."
            )
        endpoint = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        if not endpoint:
            raise ValueError(
                "Azure requires AZURE_OPENAI_ENDPOINT (or pass --endpoint)."
            )
        api_version = api_version or os.environ.get("OPENAI_API_VERSION", "2024-08-01-preview")
        api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        self.model = model
        self._client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
        )

    def generate(
        self,
        *,
        mode_name: str,
        topic: Topic,
        knowledge_sources: list[KnowledgeSource],
        tools: list[Tool],
        count: int,
        seed: int | None,
    ) -> list[GeneratedCase]:
        return _generate_via_json_schema(
            client=self._client,
            model=self.model,
            mode_name=mode_name,
            topic=topic,
            knowledge_sources=knowledge_sources,
            tools=tools,
            count=count,
            seed=seed,
        )


def _generate_via_json_schema(
    *,
    client: Any,
    model: str,
    mode_name: str,
    topic: Topic,
    knowledge_sources: list[KnowledgeSource],
    tools: list[Tool],
    count: int,
    seed: int | None,
) -> list[GeneratedCase]:
    spec = get_mode(mode_name)
    user_prompt = build_user_message(
        topic=topic,
        knowledge_sources=knowledge_sources,
        tools=tools,
        count=count,
        seed=seed,
        mode_name=mode_name,
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": spec.system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": RESPONSE_FORMAT_NAME,
                "schema": spec.schema,
                "strict": True,
            },
        },
        seed=seed,
    )
    text = response.choices[0].message.content
    if text is None:
        finish_reason = getattr(response.choices[0], "finish_reason", None)
        raise RuntimeError(
            f"OpenAI/Azure returned no content (finish_reason={finish_reason!r}). "
            "This usually means the request was refused or hit the token limit."
        )
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"OpenAI/Azure returned invalid JSON despite strict mode: {exc}"
        ) from exc
    return spec.parse(payload)
