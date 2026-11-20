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

"""Unit tests for AI session history management routes."""

from fastapi import HTTPException
import pytest

from wy_qcos.ai.session_store import (
    SessionMessageConflictError,
    SessionNotFoundError,
)
from wy_qcos.api.posiq.routes_rest import ai as ai_routes
from wy_qcos.common.config import AIAgentSection, Config


class FakeSessionStore:
    """Configurable session-store stub for route tests."""

    retained = []
    error = None
    closed = False

    def __init__(self, user_id, session_id):
        self.user_id = user_id
        self.session_id = session_id
        type(self).closed = False

    async def truncate_from(self, from_index, expected_content):
        if type(self).error:
            raise type(self).error
        return type(self).retained

    async def close(self):
        type(self).closed = True


@pytest.fixture(autouse=True)
def reset_fake_store(monkeypatch):
    """Install a fresh stub and reset class-level test state."""
    FakeSessionStore.retained = []
    FakeSessionStore.error = None
    FakeSessionStore.closed = False
    monkeypatch.setattr(ai_routes, "RedisSessionStore", FakeSessionStore)


def make_request(content="old question"):
    """Build a valid truncation request."""
    return ai_routes.SessionMessagesTruncateRequest(
        from_index=0,
        expected_content=content,
    )


@pytest.mark.asyncio
async def test_truncate_returns_retained_messages_and_closes_store():
    """A successful edit returns the authoritative retained prefix."""
    FakeSessionStore.retained = [
        {
            "role": "user",
            "content": "earlier question",
            "created_at": 1.0,
            "attachments": None,
        }
    ]

    result = await ai_routes.truncate_session_messages(
        "session-1",
        make_request(),
        {"user_id": "user-1"},
    )

    assert result["session_id"] == "session-1"
    assert result["message_count"] == 1
    assert result["messages"][0].content == "earlier question"
    assert FakeSessionStore.closed is True


@pytest.mark.asyncio
async def test_truncate_conflict_returns_409_and_closes_store():
    """A stale edit is rejected without being treated as a server error."""
    FakeSessionStore.error = SessionMessageConflictError("session-1")

    with pytest.raises(HTTPException) as exc_info:
        await ai_routes.truncate_session_messages(
            "session-1",
            make_request(),
            {"user_id": "user-1"},
        )

    assert exc_info.value.status_code == 409
    assert FakeSessionStore.closed is True


@pytest.mark.asyncio
async def test_truncate_missing_session_returns_404():
    """A missing session uses the same 404 semantics as session restore."""
    FakeSessionStore.error = SessionNotFoundError("session-1")

    with pytest.raises(HTTPException) as exc_info:
        await ai_routes.truncate_session_messages(
            "session-1",
            make_request(),
            {"user_id": "user-1"},
        )

    assert exc_info.value.status_code == 404
    assert FakeSessionStore.closed is True


@pytest.fixture
def multi_model_config():
    """Install a two-model config and restore global state after."""
    section = AIAgentSection(
        MODELS=[
            {
                "ID": "a",
                "MODEL": "m-a",
                "BASE_URL": "http://a/v1",
                "API_KEY": "sk-secret-a",
                "VISION_ENABLED": True,
            },
            {"ID": "b", "MODEL": "m-b", "API_KEY": "sk-secret-b"},
        ]
    )
    previous_section = Config.AI_AGENT
    # initialize() first so the fixture can patch the backing model;
    # otherwise a lazy initialize() would overwrite the class attribute
    # with a fresh default section on first use.
    Config.initialize()
    previous_model = Config._model.AI_AGENT if Config._model else None
    Config.AI_AGENT = section
    if Config._model is not None:
        Config._model.AI_AGENT = section
    yield section
    Config.AI_AGENT = previous_section
    if Config._model is not None and previous_model is not None:
        Config._model.AI_AGENT = previous_model


@pytest.mark.asyncio
async def test_list_models_exposes_only_public_fields(multi_model_config):
    """The model list never leaks URLs, keys or prompts."""
    result = await ai_routes.list_models({"user_id": "user-1"})

    assert result["default_model_id"] == "a"
    assert result["models"] == [
        {
            "id": "a",
            "display_name": "m-a",
            "model": "m-a",
            "supports_vision": True,
        },
        {
            "id": "b",
            "display_name": "m-b",
            "model": "m-b",
            "supports_vision": False,
        },
    ]
    dumped = str(result)
    assert "sk-secret-a" not in dumped
    assert "sk-secret-b" not in dumped
    assert "http://a/v1" not in dumped


def test_chat_request_model_id_defaults_to_none():
    """Legacy clients send no model_id; the server decides."""
    request = ai_routes.ChatRequest(message="hi")
    assert request.model_id is None
    selected = ai_routes.ChatRequest(message="hi", model_id="b")
    assert selected.model_id == "b"


def test_message_response_carries_model_metadata():
    message = ai_routes.MessageResponse(
        role="assistant",
        content="answer",
        created_at=1.0,
        model_id="b",
        model="m-b",
    )
    assert message.model_id == "b"
    assert message.model == "m-b"
    legacy = ai_routes.MessageResponse(
        role="user", content="q", created_at=1.0
    )
    assert legacy.model_id is None
    assert legacy.model is None


def test_session_info_response_carries_model_id():
    info = ai_routes.SessionInfoResponse(
        session_id="s",
        created_at=1.0,
        title="t",
        message_count=0,
        model_id="b",
    )
    assert info.model_id == "b"
