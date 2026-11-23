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
self-hosted vLLM / Ollama, LiteLLM gateway, ...). Each configured
``[[AI.AGENT.MODELS]]`` entry owns an independent provider connection.

Maintains per-model Agent instances:

- text agents   : text-only conversation, tool calling, RAG
- vision agents : handle messages with image attachments (only for
  models with VISION_ENABLED=true)
"""

import inspect
import logging
import os
from functools import lru_cache
from typing import Any

# Disable pydantic-ai startup banner
os.environ["PYDANTIC_AI_NO_BANNER"] = "1"

from openai import AsyncOpenAI
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.models.anthropic import AnthropicModel

# pydantic-ai >= 0.2 renamed OpenAIModel -> OpenAIChatModel
try:
    from pydantic_ai.models.openai import OpenAIChatModel as OpenAIModel
except ImportError:
    from pydantic_ai.models.openai import OpenAIModel

from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai_harness import ToolOutputLimits
from pydantic_ai_harness.tool_output_limits import Band, Truncate

from wy_qcos.ai.llm.prompts import (
    build_system_prompt,
    build_vision_system_prompt,
)
from wy_qcos.common.config import Config

logger = logging.getLogger(__name__)

# Zero disables tool-output truncation. Set a positive value to enforce
# a character budget when the configured model has a smaller context.
_TOOL_OUTPUT_MAX_CHARS = int(
    os.environ.get("QCOS_AI_TOOL_OUTPUT_MAX_CHARS", "0")
)
_REASONING_LANGUAGE_INSTRUCTIONS = (
    "内部分析、推理以及 thinking/reasoning 内容必须始终使用简体中文，"
    "禁止使用英文思考。最终回答默认使用简体中文；用户明确要求其他语言时，"
    "仅最终回答可以切换语言，思考过程仍须使用简体中文。"
    "代码、标识符、工具参数和报错信息保持原文。"
)

# pydantic-ai added the `instrument` Agent kwarg in a recent release;
# older versions raise TypeError on it. Detect support once at import
# time so deployments pinned to either version work.
_AGENT_SUPPORTS_INSTRUMENT = (
    "instrument" in inspect.signature(Agent.__init__).parameters
)
_AGENT_SUPPORTS_INSTRUCTIONS = (
    "instructions" in inspect.signature(Agent.__init__).parameters
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


def _build_agent_kwargs(cfg) -> dict[str, Any]:
    """Build Agent options from a resolved per-model config."""
    kwargs: dict[str, Any] = (
        {"instrument": True} if _AGENT_SUPPORTS_INSTRUMENT else {}
    )
    if _AGENT_SUPPORTS_INSTRUCTIONS:
        kwargs["instructions"] = _REASONING_LANGUAGE_INSTRUCTIONS
    if _AGENT_SUPPORTS_MODEL_SETTINGS and cfg.model_settings_enabled:
        kwargs["model_settings"] = ModelSettings(
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
    return kwargs


class _QcosToolOutputLimits(ToolOutputLimits):
    """Limit tool output without registering an additional read-back tool."""

    def get_toolset(self) -> None:
        return None


def _build_harness_capabilities() -> list[ToolOutputLimits]:
    """Return the optional tool-output limit without a read-back tool."""
    if _TOOL_OUTPUT_MAX_CHARS <= 0:
        return []
    return [
        _QcosToolOutputLimits(
            bands=[
                Band(
                    over=_TOOL_OUTPUT_MAX_CHARS,
                    action=Truncate(max_chars=_TOOL_OUTPUT_MAX_CHARS),
                )
            ]
        )
    ]


def _assemble_agent(model, system_prompt: str, cfg) -> Agent:
    """Assemble an Agent with the shared MCP toolset and limits.

    Text and vision agents share the exact same tool registration and
    optional tool-output limit so both turn types can run the real
    submit/status/result tool chain; they differ only in the model
    connection and the system prompt.
    """
    from wy_qcos.ai.tools.mcp_tools import register_mcp_tools

    if not _AGENT_SUPPORTS_INSTRUCTIONS:
        system_prompt = (
            f"{system_prompt}\n\n{_REASONING_LANGUAGE_INSTRUCTIONS}"
        )
    agent = Agent(
        model,
        system_prompt=system_prompt,
        capabilities=_build_harness_capabilities(),
        **_build_agent_kwargs(cfg),
    )
    register_mcp_tools(agent)
    return agent


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


def build_text_agent(model_id: str | None = None) -> Agent:
    """Build (or reuse) the text Agent for one configured model.

    ``None`` selects the default model; an explicit default ID hits
    the same cache entry because the cache is keyed by the resolved
    model ID, never by the raw argument.
    """
    resolved = get_ai_config().resolve_model(model_id)
    return _build_text_agent_cached(resolved.id)


@lru_cache(maxsize=32)
def _build_text_agent_cached(model_id: str) -> Agent:
    """Build the text-only Agent (tool calling + RAG) for one model."""
    cfg = get_ai_config().resolve_model(model_id)
    model = _build_model(
        cfg.provider.lower(),
        cfg.model,
        cfg.base_url,
        cfg.api_key,
        cfg.timeout,
    )
    return _assemble_agent(
        model,
        build_system_prompt(cfg.system_prompt, cfg.display_name, cfg.model),
        cfg,
    )


def build_vision_agent(model_id: str | None = None) -> Agent:
    """Build (or reuse) the vision Agent for one configured model.

    Raises ``ValueError`` when the model has VISION_ENABLED=false so
    callers can reject image attachments before streaming starts.
    """
    resolved = get_ai_config().resolve_model(model_id)
    return _build_vision_agent_cached(resolved.id)


@lru_cache(maxsize=32)
def _build_vision_agent_cached(model_id: str) -> Agent:
    """Build the vision Agent for image understanding.

    VISION_* overrides fall back to the model's own connection, so
    single-provider deployments work out of the box.

    MCP tools ARE registered (same set as the text agent): a request
    like "analyse this circuit image, submit it and analyse the
    result" needs the real submit/status/result tool chain after the
    image has been transcribed. Without tools the model could only
    fabricate a job id and counts.
    """
    section = get_ai_config()
    cfg = section.resolve_model(model_id)
    vision = section.resolve_vision(model_id)
    if vision is None:
        raise ValueError(
            f"AI model '{model_id}' does not support image attachments"
        )
    model = _build_model(
        vision.provider.lower(),
        vision.model,
        vision.base_url,
        vision.api_key,
        cfg.timeout,
    )
    return _assemble_agent(
        model,
        build_vision_system_prompt(
            cfg.vision_system_prompt, cfg.display_name, vision.model
        ),
        cfg,
    )


def reset_agent_caches() -> None:
    """Drop all cached Agents (used by tests and config reloads)."""
    _build_text_agent_cached.cache_clear()
    _build_vision_agent_cached.cache_clear()
