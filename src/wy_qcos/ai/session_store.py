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

"""Redis-based session store for QCOS AI Agent.

Stores conversation history per user per session, with TTL-based
expiration and size caps to prevent Redis memory exhaustion.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass

from redis import asyncio as async_redis

from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Metadata for a single AI chat session."""

    session_id: str
    created_at: float
    title: str
    message_count: int


class RedisSessionStore:
    """Manages AI conversation sessions in Redis."""

    def __init__(self, user_id: str, session_id: str | None = None):
        self.user_id = user_id
        self.session_id = session_id or self._new_session_id()
        self._client: async_redis.Redis | None = None

    @staticmethod
    def _new_session_id() -> str:
        return str(uuid.uuid4())

    async def _get_client(self) -> async_redis.Redis:
        if self._client is None:
            self._client = async_redis.Redis.from_url(
                Config.REDIS.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        return self._client

    @property
    def _session_key(self) -> str:
        return (
            f"{Constant.REDIS_CHANNEL_AI_SESSION_PREFIX}/"
            f"{self.user_id}/{self.session_id}"
        )

    @property
    def _messages_key(self) -> str:
        return (
            f"{Constant.REDIS_CHANNEL_AI_MESSAGES_PREFIX}/"
            f"{self.user_id}/{self.session_id}"
        )

    @property
    def _user_sessions_key(self) -> str:
        return (
            f"{Constant.REDIS_CHANNEL_AI_USER_SESSIONS_PREFIX}/{self.user_id}"
        )

    @property
    def _ttl(self) -> int:
        return Config.AI_AGENT.SESSION_TTL_SECONDS

    async def create_session(self, title: str = "新的会话") -> str:
        """Create a new session record."""
        client = await self._get_client()
        now = time.time()
        session_data = {
            "session_id": self.session_id,
            "created_at": now,
            "title": title,
            "message_count": 0,
        }
        pipe = client.pipeline()
        pipe.set(self._session_key, json.dumps(session_data), ex=self._ttl)
        pipe.sadd(self._user_sessions_key, self.session_id)
        pipe.expire(self._user_sessions_key, self._ttl)
        await pipe.execute()
        return self.session_id

    async def append(
        self,
        role: str,
        content: str,
        attachments: list[dict] | None = None,
    ) -> None:
        """Append a message to the session history."""
        client = await self._get_client()
        now = time.time()

        message = {
            "role": role,
            "content": content,
            "created_at": now,
        }
        if attachments:
            message["attachments"] = attachments

        pipe = client.pipeline()
        pipe.rpush(self._messages_key, json.dumps(message))
        pipe.expire(self._messages_key, self._ttl)

        # Update session metadata
        session_raw = await client.get(self._session_key)
        if session_raw:
            session = json.loads(session_raw)
            session["message_count"] = session.get("message_count", 0) + 1
            # Auto-generate title from first user message
            if role == "user" and session.get("message_count") == 1:
                session["title"] = content[:50]
            pipe.set(self._session_key, json.dumps(session), ex=self._ttl)
        else:
            await self.create_session(
                title=(content[:50] if role == "user" else "新的会话")
            )

        # Trim old messages if over cap
        cap = 200
        pipe.ltrim(self._messages_key, -cap, -1)
        await pipe.execute()

    async def get_messages(self) -> list[dict]:
        """Retrieve all messages for the current session."""
        client = await self._get_client()
        raw_messages = await client.lrange(self._messages_key, 0, -1)
        return [json.loads(m) for m in raw_messages]

    async def get_session_info(self) -> SessionInfo | None:
        """Retrieve session metadata."""
        client = await self._get_client()
        raw = await client.get(self._session_key)
        if not raw:
            return None
        data = json.loads(raw)
        return SessionInfo(
            session_id=data["session_id"],
            created_at=data["created_at"],
            title=data.get("title", ""),
            message_count=data.get("message_count", 0),
        )

    async def list_sessions(self) -> list[SessionInfo]:
        """List all sessions for the current user."""
        client = await self._get_client()
        session_ids = await client.smembers(self._user_sessions_key)
        sessions = []
        for sid in session_ids:
            store = RedisSessionStore(self.user_id, sid)
            info = await store.get_session_info()
            if info:
                sessions.append(info)
        # Sort by created_at descending
        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions

    async def delete_session(self) -> None:
        """Delete the current session and its messages."""
        client = await self._get_client()
        pipe = client.pipeline()
        pipe.delete(self._session_key)
        pipe.delete(self._messages_key)
        pipe.srem(self._user_sessions_key, self.session_id)
        await pipe.execute()

    async def clear_messages(self) -> None:
        """Clear all messages in the current session.

        The session record itself (id / title / created_at) is kept so
        the conversation remains in the user's session list; only the
        per-message Redis list is wiped. The session's
        ``message_count`` counter is reset to zero so the next append
        starts fresh.
        """
        client = await self._get_client()
        pipe = client.pipeline()
        pipe.delete(self._messages_key)
        # Reset message_count on the session record so the list view
        # shows "0 messages" until the user sends something new.
        session_raw = await client.get(self._session_key)
        if session_raw:
            session = json.loads(session_raw)
            session["message_count"] = 0
            pipe.set(self._session_key, json.dumps(session), ex=self._ttl)
        await pipe.execute()

    async def get_total_attachment_bytes(self) -> int:
        """Sum the size of all image attachments in this session."""
        messages = await self.get_messages()
        total = 0
        for msg in messages:
            for att in msg.get("attachments", []):
                total += att.get("size_bytes", 0)
        return total

    async def close(self):
        """Close the Redis client."""
        if self._client:
            await self._client.aclose()
            self._client = None
