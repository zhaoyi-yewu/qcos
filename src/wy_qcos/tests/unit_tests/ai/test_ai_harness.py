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

"""Unit tests for the pydantic-ai-harness integration."""

import sys
import types

import pytest

# The harness tests need the optional AI dependencies; skip the whole
# module in minimal environments instead of failing collection.
pytest.importorskip("pydantic_ai")
pytest.importorskip("pydantic_ai_harness")

from pydantic_ai import ToolDefinition
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.models.test import TestModel
from pydantic_ai_harness import ToolOutputLimits

from wy_qcos.ai.llm import client
from wy_qcos.common.config import AIAgentSection


@pytest.fixture(autouse=True)
def clear_agent_caches():
    """Keep cached agents from leaking between tests."""
    client.reset_agent_caches()
    yield
    client.reset_agent_caches()


def _has_capability(agent, capability_type) -> bool:
    """Find a capability in the agent's composed capability tree."""
    pending = [agent.root_capability]
    while pending:
        capability = pending.pop()
        if isinstance(capability, capability_type):
            return True
        pending.extend(getattr(capability, "capabilities", ()))
    return False


def test_text_and_vision_agents_mount_harness(monkeypatch):
    """Both agents mount MCP tools with bounded tool output.

    The vision agent needs the same real tool chain as the text
    agent so image turns can submit jobs for real.
    """
    cfg = AIAgentSection(
        MODELS=[
            {
                "ID": "main",
                "MODEL": "text-model",
                "BASE_URL": "http://localhost/v1",
                "API_KEY": "",
                "VISION_ENABLED": True,
            }
        ]
    )
    registered_agents = []
    mcp_tools = types.ModuleType("wy_qcos.ai.tools.mcp_tools")
    mcp_tools.register_mcp_tools = registered_agents.append
    monkeypatch.setitem(sys.modules, mcp_tools.__name__, mcp_tools)
    monkeypatch.setattr(client, "get_ai_config", lambda: cfg)
    monkeypatch.setattr(client, "_build_model", lambda *args: TestModel())
    monkeypatch.setattr(
        client, "build_system_prompt", lambda *args, **kwargs: "text"
    )
    monkeypatch.setattr(
        client, "build_vision_system_prompt", lambda *args, **kwargs: "vision"
    )

    text_agent = client.build_text_agent()
    vision_agent = client.build_vision_agent()

    assert _has_capability(text_agent, ToolOutputLimits)
    assert _has_capability(vision_agent, ToolOutputLimits)
    assert registered_agents == [text_agent, vision_agent]


@pytest.mark.asyncio
async def test_tool_output_limits_preserve_small_and_truncate_large():
    """Existing small results pass through and large results are bounded."""
    capability = client._build_harness_capabilities()[0]
    call = ToolCallPart(tool_name="qcos_list_devices")
    tool_def = ToolDefinition(name="qcos_list_devices")

    small_result = await capability.after_tool_execute(
        None,
        call=call,
        tool_def=tool_def,
        args={},
        result="small result",
    )
    large_result = await capability.after_tool_execute(
        None,
        call=call,
        tool_def=tool_def,
        args={},
        result="x" * (client._TOOL_OUTPUT_MAX_CHARS + 100),
    )

    assert small_result == "small result"
    assert len(large_result) <= client._TOOL_OUTPUT_MAX_CHARS
    assert large_result != "x" * (client._TOOL_OUTPUT_MAX_CHARS + 100)
    assert capability.get_toolset() is None
