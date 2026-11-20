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

"""Unit tests for per-model session metadata in the AI session store."""

import json

import pytest

from wy_qcos.ai.session_store import RedisSessionStore


class FakePipeline:
    """In-memory pipeline covering append/create/clear operations."""

    def __init__(self, client):
        self.client = client
        self.operations = []

    def rpush(self, key, *values):
        self.operations.append(("rpush", key, values))

    def expire(self, key, ttl):
        self.operations.append(("expire", key, ttl))

    def set(self, key, value, ex=None):
        self.operations.append(("set", key, value, ex))

    def sadd(self, key, *values):
        self.operations.append(("sadd", key, values))

    def ltrim(self, key, start, end):
        self.operations.append(("ltrim", key, start, end))

    def delete(self, key):
        self.operations.append(("delete", key))

    async def execute(self):
        for operation in self.operations:
            name = operation[0]
            if name == "rpush":
                self.client.messages.extend(operation[2])
            elif name == "set":
                self.client.session_raw = operation[2]
            elif name == "delete":
                self.client.messages = []


class FakeRedis:
    """Minimal async Redis stand-in for model metadata tests."""

    def __init__(self, session_raw=None):
        self.session_raw = session_raw
        self.messages = []

    def pipeline(self):
        return FakePipeline(self)

    async def get(self, key):
        return self.session_raw

    async def lrange(self, key, start, end):
        return list(self.messages)


def make_store(session_data=None):
    store = RedisSessionStore("user-1", "session-1")
    raw = json.dumps(session_data) if session_data is not None else None
    store._client = FakeRedis(raw)
    return store


def _session_dict(**overrides):
    data = {
        "session_id": "session-1",
        "created_at": 1.0,
        "title": "test",
        "message_count": 0,
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_append_records_model_metadata():
    store = make_store(_session_dict(model_id="a"))
    await store.append("user", "hello", model_id="b")
    await store.append("assistant", "answer", model_id="b", model="m-b")

    user_msg = json.loads(store._client.messages[0])
    assistant_msg = json.loads(store._client.messages[1])
    assert user_msg["model_id"] == "b"
    assert "model" not in user_msg
    assert assistant_msg["model_id"] == "b"
    assert assistant_msg["model"] == "m-b"
    # The session tracks the latest selected model.
    session = json.loads(store._client.session_raw)
    assert session["model_id"] == "b"


@pytest.mark.asyncio
async def test_append_without_model_keeps_legacy_shape():
    store = make_store(_session_dict())
    await store.append("user", "hello")
    message = json.loads(store._client.messages[0])
    assert "model_id" not in message
    assert "model" not in message
    session = json.loads(store._client.session_raw)
    assert "model_id" not in session


@pytest.mark.asyncio
async def test_append_creates_session_with_model():
    store = make_store(session_data=None)
    await store.append("user", "hello", model_id="a")
    session = json.loads(store._client.session_raw)
    assert session["model_id"] == "a"


@pytest.mark.asyncio
async def test_legacy_session_without_model_id():
    store = make_store(_session_dict())
    info = await store.get_session_info()
    assert info.model_id is None


@pytest.mark.asyncio
async def test_clear_messages_preserves_model_id():
    store = make_store(_session_dict(model_id="b", message_count=2))
    await store.clear_messages()
    session = json.loads(store._client.session_raw)
    assert session["model_id"] == "b"
    assert session["message_count"] == 0
