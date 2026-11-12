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

"""Unit tests for atomic AI session branch truncation."""

import json

import pytest

from wy_qcos.ai.session_store import (
    RedisSessionStore,
    SessionMessageConflictError,
    SessionNotFoundError,
)


class FakePipeline:
    """Small in-memory implementation of the Redis pipeline API."""

    def __init__(self, session_raw, messages):
        self.session_raw = session_raw
        self.messages = list(messages)
        self.expiries = {}
        self.operations = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    def pipeline(self):
        return self

    async def watch(self, *keys):
        return None

    async def get(self, key):
        return self.session_raw

    async def lrange(self, key, start, end):
        return list(self.messages)

    def multi(self):
        self.operations = []

    def delete(self, key):
        self.operations.append(("delete", key))

    def rpush(self, key, *values):
        self.operations.append(("rpush", key, values))

    def expire(self, key, ttl):
        self.operations.append(("expire", key, ttl))

    def set(self, key, value, ex=None):
        self.operations.append(("set", key, value, ex))

    async def execute(self):
        for operation in self.operations:
            name = operation[0]
            if name == "delete":
                self.messages = []
            elif name == "rpush":
                self.messages = list(operation[2])
            elif name == "expire":
                self.expiries[operation[1]] = operation[2]
            elif name == "set":
                self.session_raw = operation[2]
                self.expiries[operation[1]] = operation[3]


def make_store(messages, include_session=True):
    """Build a store backed by an in-memory pipeline."""
    store = RedisSessionStore("user-1", "session-1")
    session_raw = None
    if include_session:
        session_raw = json.dumps({
            "session_id": "session-1",
            "created_at": 1.0,
            "title": "test",
            "message_count": len(messages),
        })
    store._client = FakePipeline(session_raw, messages)
    return store


@pytest.mark.asyncio
async def test_truncate_from_user_message_keeps_prefix():
    """The selected user message and all successors are removed."""
    messages = [
        {"role": "user", "content": "U1", "created_at": 1.0},
        {"role": "assistant", "content": "A1", "created_at": 2.0},
        {"role": "user", "content": "U2", "created_at": 3.0},
        {"role": "assistant", "content": "A2", "created_at": 4.0},
    ]
    store = make_store([json.dumps(message) for message in messages])

    retained = await store.truncate_from(2, "U2")

    assert [message["content"] for message in retained] == ["U1", "A1"]
    assert [
        json.loads(message)["content"] for message in store._client.messages
    ] == [
        "U1",
        "A1",
    ]
    session = json.loads(store._client.session_raw)
    assert session["message_count"] == 2
    assert store._client.expiries


@pytest.mark.asyncio
async def test_truncate_from_zero_deletes_message_list():
    """Editing the first question leaves an empty message list."""
    messages = [json.dumps({"role": "user", "content": "U1"})]
    store = make_store(messages)

    retained = await store.truncate_from(0, "U1")

    assert retained == []
    assert store._client.messages == []
    assert json.loads(store._client.session_raw)["message_count"] == 0


@pytest.mark.asyncio
async def test_content_conflict_does_not_modify_history():
    """A stale browser cannot truncate a changed conversation."""
    messages = [json.dumps({"role": "user", "content": "new"})]
    store = make_store(messages)

    with pytest.raises(SessionMessageConflictError):
        await store.truncate_from(0, "old")

    assert store._client.messages == messages


@pytest.mark.asyncio
async def test_assistant_message_cannot_be_edited():
    """Only user messages are valid truncation points."""
    messages = [json.dumps({"role": "assistant", "content": "A1"})]
    store = make_store(messages)

    with pytest.raises(ValueError, match="Only user messages"):
        await store.truncate_from(0, "A1")

    assert store._client.messages == messages


@pytest.mark.asyncio
async def test_missing_session_raises_not_found():
    """A missing session has a distinct error for REST mapping."""
    store = make_store([], include_session=False)

    with pytest.raises(SessionNotFoundError):
        await store.truncate_from(0, "U1")
