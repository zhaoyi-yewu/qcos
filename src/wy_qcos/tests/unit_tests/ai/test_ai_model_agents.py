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

"""Unit tests for per-model Agent construction and orchestration.

These tests require the optional AI dependencies (pydantic-ai); they
are skipped automatically in environments without them.
"""

import pytest

pytest.importorskip("pydantic_ai")
pytest.importorskip("pydantic_ai_harness")

from pydantic_ai import BinaryContent
from pydantic_ai.messages import UserPromptPart

from wy_qcos.ai.agent import AiAgent
from wy_qcos.ai.llm.client import (
    build_text_agent,
    build_vision_agent,
    reset_agent_caches,
)
from wy_qcos.ai.session_store import SessionInfo
from wy_qcos.common.config import (
    AIAgentSection,
    Config,
    UnknownAIModelError,
)


@pytest.fixture(autouse=True)
def _multi_model_config():
    """Install a two-model configuration and restore global state."""
    section = AIAgentSection(
        MODELS=[
            {
                "ID": "a",
                "MODEL": "m-a",
                "BASE_URL": "http://a/v1",
                "API_KEY": "ka",
                "VISION_ENABLED": True,
            },
            {
                "ID": "b",
                "MODEL": "m-b",
                "BASE_URL": "http://b/v1",
                "API_KEY": "kb",
                "TIMEOUT": 5.0,
            },
        ]
    )
    previous_section = Config.AI_AGENT
    previous_ai_enabled = Config.AI.ENABLED
    # initialize() first so the fixture can patch the backing model.
    Config.initialize()
    previous_model = Config._model.AI_AGENT if Config._model else None
    # Avoid RagRetriever construction inside AiAgent.__init__.
    Config.AI.ENABLED = False
    Config.AI_AGENT = section
    if Config._model is not None:
        Config._model.AI_AGENT = section
    reset_agent_caches()
    yield section
    reset_agent_caches()
    Config.AI_AGENT = previous_section
    Config.AI.ENABLED = previous_ai_enabled
    if Config._model is not None and previous_model is not None:
        Config._model.AI_AGENT = previous_model


class TestAgentFactoryCache:
    def test_same_id_reuses_agent(self):
        assert build_text_agent("a") is build_text_agent("a")

    def test_default_and_explicit_default_share_cache(self):
        assert build_text_agent() is build_text_agent("a")

    def test_different_ids_are_isolated(self):
        agent_a = build_text_agent("a")
        agent_b = build_text_agent("b")
        assert agent_a is not agent_b

    def test_reset_caches(self):
        first = build_text_agent("a")
        reset_agent_caches()
        assert build_text_agent("a") is not first

    def test_unknown_id_rejected_before_build(self):
        with pytest.raises(UnknownAIModelError):
            build_text_agent("nope")

    def test_vision_disabled_model_rejected(self):
        with pytest.raises(ValueError, match="vision|image"):
            build_vision_agent("b")

    def test_vision_agent_cached_per_model(self):
        assert build_vision_agent("a") is build_vision_agent()


class TestAgentModelResolution:
    def test_explicit_invalid_id_fails_fast(self):
        with pytest.raises(UnknownAIModelError):
            AiAgent(user_id="u", model_id="nope")

    @pytest.mark.asyncio
    async def test_explicit_id_wins_over_session(self):
        agent = AiAgent(user_id="u", model_id="b")
        agent.session_store.get_session_info = self._info_with_model("a")
        assert await agent._resolve_session_model() == "b"

    @pytest.mark.asyncio
    async def test_session_model_restored(self):
        agent = AiAgent(user_id="u")
        agent.session_store.get_session_info = self._info_with_model("b")
        assert await agent._resolve_session_model() == "b"

    @pytest.mark.asyncio
    async def test_deleted_session_model_falls_back_to_default(self):
        agent = AiAgent(user_id="u")
        agent.session_store.get_session_info = self._info_with_model("gone")
        assert await agent._resolve_session_model() == "a"

    @pytest.mark.asyncio
    async def test_new_session_uses_default(self):
        agent = AiAgent(user_id="u")

        async def no_session():
            return None

        agent.session_store.get_session_info = no_session
        assert await agent._resolve_session_model() == "a"

    @pytest.mark.asyncio
    async def test_legacy_session_without_model_uses_default(self):
        agent = AiAgent(user_id="u")
        agent.session_store.get_session_info = self._info_with_model(None)
        assert await agent._resolve_session_model() == "a"

    @staticmethod
    def _info_with_model(model_id):
        async def get_info():
            return SessionInfo(
                session_id="s",
                created_at=1.0,
                title="t",
                message_count=0,
                model_id=model_id,
            )

        return get_info


class TestMessageHistory:
    def test_image_attachment_nested_in_user_prompt(self):
        """Image content must not be a top-level ModelRequest part."""
        messages = AiAgent._build_message_history([
            {
                "role": "user",
                "content": "Describe this image",
                "attachments": [
                    {
                        "data": "/9j/",
                        "media_type": "image/jpeg",
                    }
                ],
            }
        ])

        assert len(messages) == 1
        assert len(messages[0].parts) == 1
        prompt = messages[0].parts[0]
        assert isinstance(prompt, UserPromptPart)
        assert isinstance(prompt.content, list)
        assert prompt.content[0] == "Describe this image"
        assert isinstance(prompt.content[1], BinaryContent)
        assert prompt.content[1].data == b"\xff\xd8\xff"
        assert prompt.content[1].media_type == "image/jpeg"

    def test_plain_text_prompt_remains_a_string(self):
        """Text-only history keeps the original provider payload shape."""
        messages = AiAgent._build_message_history([
            {"role": "user", "content": "Hello"}
        ])

        prompt = messages[0].parts[0]
        assert isinstance(prompt, UserPromptPart)
        assert prompt.content == "Hello"
