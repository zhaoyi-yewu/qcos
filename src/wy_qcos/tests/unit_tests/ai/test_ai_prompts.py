#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of MulanPSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Unit tests for configurable AI system prompts."""

import pytest

from wy_qcos.ai.llm.prompts import (
    build_system_prompt,
    build_vision_system_prompt,
)
from wy_qcos.common.config import AIAgentSection, Config


def test_prompts_forbid_fabricated_job_data():
    """Prompts must force real MCP data for jobs/devices."""
    text = build_system_prompt()
    vision = build_vision_system_prompt()
    # Text agent: real submit -> status -> result tool chain.
    assert "qcos_submit_job" in text
    assert "qcos_get_job_result" in text
    assert "禁止捏造" in text or "严禁" in text
    # Vision agent has the same MCP tools and must run the real chain.
    assert "qcos_submit_job" in vision
    assert "qcos_get_job_status" in vision
    assert "qcos_get_job_result" in vision
    assert "严禁" in vision


def test_model_identity_injected_into_prompts():
    """Resolved model identity is appended for self-introduction."""
    text = build_system_prompt(
        override=None, display_name="GLM-5.3", upstream_model="moma/glm-5.3"
    )
    assert "GLM-5.3" in text
    assert "moma/glm-5.3" in text
    assert "当前模型身份" in text
    vision = build_vision_system_prompt(
        override=None, display_name="Kimi-K3", upstream_model="moma/kimi-k3"
    )
    assert "Kimi-K3" in vision
    assert "moma/kimi-k3" in vision
    # No identity provided: prompts stay unchanged (legacy behaviour).
    assert "当前模型身份" not in build_system_prompt()


@pytest.fixture(autouse=True)
def restore_prompt_config():
    """Restore global prompt settings after each test."""
    Config.initialize()
    text_prompt = Config.AI_AGENT.SYSTEM_PROMPT
    vision_prompt = Config.AI_AGENT.VISION_SYSTEM_PROMPT
    yield
    Config.AI_AGENT.SYSTEM_PROMPT = text_prompt
    Config.AI_AGENT.VISION_SYSTEM_PROMPT = vision_prompt


def test_prompt_fields_default_to_empty():
    """Empty values preserve compatibility with existing deployments."""
    section = AIAgentSection()
    assert section.SYSTEM_PROMPT == ""
    assert section.VISION_SYSTEM_PROMPT == ""


def test_empty_prompts_use_builtin_defaults():
    """Built-in templates are used when no override is configured."""
    Config.AI_AGENT.SYSTEM_PROMPT = ""
    Config.AI_AGENT.VISION_SYSTEM_PROMPT = ""
    assert "AI 智能体" in build_system_prompt()
    assert "图像分析" in build_vision_system_prompt()


def test_default_prompt_requires_mermaid_for_diagrams():
    """Diagram guidance mandates Mermaid and forbids PlantUML fences."""
    Config.AI_AGENT.SYSTEM_PROMPT = ""
    prompt = build_system_prompt()
    assert "```mermaid" in prompt
    assert "禁止输出 PlantUML" in prompt


def test_model_settings_are_opt_in_by_default():
    """Strict model gateways receive no optional sampling parameters."""
    assert AIAgentSection().LLM_MODEL_SETTINGS_ENABLED is False


def test_custom_prompts_override_builtin_defaults():
    """Configured multiline strings are returned unchanged."""
    Config.AI_AGENT.SYSTEM_PROMPT = "第一行\n第二行"
    Config.AI_AGENT.VISION_SYSTEM_PROMPT = "视觉提示词"
    assert build_system_prompt() == "第一行\n第二行"
    assert build_vision_system_prompt() == "视觉提示词"
