#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""LLM client built on pydantic-ai.

Supports any OpenAI-compatible endpoint (OpenAI, Anthropic via
pydantic-ai's AnthropicModel, Azure OpenAI, DeepSeek, Moonshot, Qwen,
self-hosted vLLM / Ollama, LiteLLM gateway, ...). Provider selection
is driven by [AI] LLM_PROVIDER + LLM_MODEL + LLM_BASE_URL.

Maintains TWO Agent instances:
- text_agent   : text-only conversation, tool calling, RAG
- vision_agent : handles messages with image attachments (separate model)
"""

import inspect
import logging
import os
from functools import lru_cache

# Disable pydantic-ai startup banner
os.environ["PYDANTIC_AI_NO_BANNER"] = "1"

from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel

# pydantic-ai >= 0.2 renamed OpenAIModel -> OpenAIChatModel
try:
    from pydantic_ai.models.openai import OpenAIChatModel as OpenAIModel
except ImportError:
    from pydantic_ai.models.openai import OpenAIModel

from pydantic_ai.providers.openai import OpenAIProvider

from wy_qcos.ai.llm.prompts import (
    build_system_prompt,
    build_vision_system_prompt,
)
from wy_qcos.common.config import Config

logger = logging.getLogger(__name__)

# pydantic-ai added the `instrument` Agent kwarg in a recent release;
# older versions raise TypeError on it. Detect support once at import
# time so deployments pinned to either version work.
_AGENT_SUPPORTS_INSTRUMENT = (
    "instrument" in inspect.signature(Agent.__init__).parameters
)
# pydantic-ai added `model_settings` Agent kwarg in v0.4+; older
# versions raise TypeError. Detect support once at import time.
_AGENT_SUPPORTS_MODEL_SETTINGS = (
    "model_settings" in inspect.signature(Agent.__init__).parameters
)

# AnthropicModel: newer pydantic-ai takes a pre-built
# `anthropic_client`, older versions accepted `api_key`/`timeout`
# kwargs directly. Probe the constructor once so both APIs work.
_ANTHROPIC_MODEL_TAKES_CLIENT = (
    "anthropic_client" in inspect.signature(AnthropicModel.__init__).parameters
)
_ANTHROPIC_MODEL_TAKES_TIMEOUT = (
    "timeout" in inspect.signature(AnthropicModel.__init__).parameters
)

# OpenAIProvider: the kwarg used to inject a pre-built AsyncOpenAI
# client has been renamed across pydantic-ai releases (`client` ->
# `openai_client`); some releases only accept `api_key`/`base_url`.
# Probe the constructor once so all supported versions work.
_OPENAI_PROVIDER_PARAMS = set(
    inspect.signature(OpenAIProvider.__init__).parameters
)
_OPENAI_PROVIDER_TAKES_CLIENT = "client" in _OPENAI_PROVIDER_PARAMS
_OPENAI_PROVIDER_TAKES_OPENAI_CLIENT = (
    "openai_client" in _OPENAI_PROVIDER_PARAMS
)


def _build_openai_provider(
    base_url: str | None,
    api_key: str,
    timeout: float,
) -> OpenAIProvider:
    """Build an OpenAIProvider compatible with the installed pydantic-ai ver.

    Preference order:
    1. Pass a pre-built AsyncOpenAI client via whichever kwarg the
       installed version supports (so `timeout` is honoured).
    2. Fall back to `api_key`/`base_url` kwargs (timeout not
       configurable on these versions).
    """
    client = AsyncOpenAI(
        base_url=base_url or None,
        api_key=api_key or "sk-empty",
        timeout=timeout,
    )
    if _OPENAI_PROVIDER_TAKES_CLIENT:
        return OpenAIProvider(client=client)
    if _OPENAI_PROVIDER_TAKES_OPENAI_CLIENT:
        return OpenAIProvider(openai_client=client)
    # Legacy fallback: no client injection supported.
    kwargs = {"api_key": api_key or "sk-empty"}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAIProvider(**kwargs)


def get_ai_config():
    """Return the [AI.AGENT] config section."""
    return Config.AI_AGENT


def _build_model(
    provider: str,
    model_name: str,
    base_url: str,
    api_key: str,
    timeout: float = 60.0,
):
    """Build a pydantic-ai Model instance for the given provider.

    Args:
        provider: provider id (openai_compatible / openai / anthropic).
        model_name: model name passed to the provider.
        base_url: endpoint base URL (ignored for hosted providers).
        api_key: API key (may be empty for local endpoints).
        timeout: HTTP request timeout in seconds. The OpenAI SDK
            defaults to 600s, which lets a hung LLM endpoint pin an
            API worker for ten minutes - long enough to exhaust the
            worker pool and stall the whole AI API. A finite timeout
            bounds the damage and surfaces RUN_ERROR to the frontend.
    """
    if provider == "openai_compatible":
        return OpenAIModel(
            model_name,
            provider=_build_openai_provider(base_url, api_key, timeout),
        )
    if provider == "openai":
        return OpenAIModel(
            model_name,
            provider=_build_openai_provider(None, api_key, timeout),
        )
    if provider == "anthropic":
        if _ANTHROPIC_MODEL_TAKES_CLIENT:
            from anthropic import AsyncAnthropic

            return AnthropicModel(
                model_name,
                anthropic_client=AsyncAnthropic(
                    api_key=api_key,
                    timeout=timeout,
                ),
            )
        if _ANTHROPIC_MODEL_TAKES_TIMEOUT:
            return AnthropicModel(
                model_name,
                api_key=api_key,
                timeout=timeout,
            )
        return AnthropicModel(model_name, api_key=api_key)
    raise ValueError(f"unsupported provider: {provider}")


@lru_cache(maxsize=1)
def build_text_agent() -> Agent:
    """Build the text-only Agent (tool calling + RAG)."""
    from wy_qcos.ai.tools.mcp_tools import register_mcp_tools

    cfg = get_ai_config()
    model = _build_model(
        cfg.LLM_PROVIDER.lower(),
        cfg.LLM_MODEL,
        cfg.LLM_BASE_URL,
        cfg.LLM_API_KEY,
        cfg.LLM_TIMEOUT,
    )
    kwargs = {"instrument": True} if _AGENT_SUPPORTS_INSTRUMENT else {}
    agent = Agent(
        model,
        system_prompt=build_system_prompt(),
        **kwargs,
    )
    register_mcp_tools(agent)
    return agent


@lru_cache(maxsize=1)
def build_vision_agent() -> Agent:
    """Build the vision Agent for image understanding.

    Falls back to the text model's provider config when VISION_*
    settings are absent, so single-provider deployments work out of
    the box.
    """
    cfg = get_ai_config()
    provider = (cfg.VISION_PROVIDER or cfg.LLM_PROVIDER).lower()
    model_name = cfg.VISION_MODEL or cfg.LLM_MODEL
    base_url = cfg.VISION_BASE_URL or cfg.LLM_BASE_URL
    api_key = cfg.VISION_API_KEY or cfg.LLM_API_KEY
    timeout = cfg.LLM_TIMEOUT
    model = _build_model(provider, model_name, base_url, api_key, timeout)
    kwargs = {"instrument": True} if _AGENT_SUPPORTS_INSTRUMENT else {}
    return Agent(
        model,
        system_prompt=build_vision_system_prompt(),
        **kwargs,
    )
