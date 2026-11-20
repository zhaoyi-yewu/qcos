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

"""REST routes for QCOS AI Agent.

Provides SSE streaming chat, session history management, and
per-user isolation via JWT auth.
"""

import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from wy_qcos.ai.session_store import (
    RedisSessionStore,
    SessionMessageConflictError,
    SessionNotFoundError,
)
from wy_qcos.api.posiq.routes_jsonrpc.dependencies.authentication import (
    get_current_user_from_token,
    get_user_manager,
)
from wy_qcos.common.config import Config, UnknownAIModelError
from wy_qcos.common.constant import Constant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ai", tags=["ai"])


# ===== Request / Response schemas =====


class Attachment(BaseModel):
    """An image attachment in a chat message."""

    kind: str = Field(default="image")
    media_type: str
    data: str  # base64 encoded


class ChatRequest(BaseModel):
    """POST /v1/ai/chat request body."""

    session_id: str | None = None
    message: str
    enable_rag: bool = True
    attachments: list[Attachment] | None = None
    # Optional configured model ID. ``None`` lets the server restore
    # the session's latest model or fall back to the default entry.
    # Arbitrary provider/URL/key values are NOT accepted - only IDs
    # from GET /v1/ai/models (strict whitelist).
    model_id: str | None = None


class SessionCreateRequest(BaseModel):
    """POST /v1/ai/sessions request body."""

    title: str = "新的会话"


class SessionMessagesTruncateRequest(BaseModel):
    """Request to remove an edited user message and its successors."""

    from_index: int = Field(ge=0)
    expected_content: str


class SessionInfoResponse(BaseModel):
    """Session metadata response."""

    session_id: str
    created_at: float
    title: str
    message_count: int
    model_id: str | None = None


class MessageResponse(BaseModel):
    """A single message in a session."""

    role: str
    content: str
    created_at: float
    attachments: list[dict] | None = None
    # Configured model ID selected for this turn (nullable for
    # messages persisted before multi-model support).
    model_id: str | None = None
    # Actual upstream model name that produced this answer.
    model: str | None = None


# ===== Auth dependency =====


async def get_current_user(request: Request) -> dict:
    """Extract and validate the current user from the JWT Bearer token.

    Returns a dict with at least ``user_id`` (or ``sub``).
    Raises 401 when authentication fails.
    """
    if Config.DEFAULT.AUTH_MODE != Constant.AUTH_MODE_JWT:
        # Non-JWT modes: pass-through with a synthetic user
        return {"user_id": "anonymous", "sub": "anonymous"}

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )
    token = auth_header[7:]
    # ``get_user_manager`` is a sync FastAPI dependency that reads
    # the UserManager off ``request.state``; it is NOT async and it
    # requires the Request object. Calling it with no arguments and
    # ``await``-ing the result was a type error.
    user_manager = get_user_manager(request)
    user = get_current_user_from_token(token, user_manager)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"user_id": str(user.id), "sub": user.name}


# ===== Helper functions =====


def _sse_event(event_type: str, data: dict) -> str:
    """Build an AG-UI SSE event string."""
    payload = {"type": event_type, **data}
    return f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"


def _to_agui_event(event: dict, message_id: str) -> str | None:
    """Convert internal event format to AG-UI standard SSE format.

    The internal "done" event intentionally maps to ``None`` here: the
    surrounding generator emits ``TEXT_MESSAGE_END`` and ``RUN_FINISHED``
    itself so the protocol-level framing stays in one place. Mapping
    ``done`` to a duplicate ``RUN_FINISHED`` was the root cause of the
    frontend receiving the completion signal twice (once before
    ``TEXT_MESSAGE_END``), which left the chat UI stuck in its
    streaming-skeleton state.
    """
    event_type = event.get("type")

    if event_type == "chunk":
        return _sse_event(
            "TEXT_MESSAGE_CONTENT",
            {
                "messageId": message_id,
                "delta": event.get("delta", ""),
            },
        )
    elif event_type == "thinking":
        # Chain-of-thought (reasoning) delta. We reuse a custom event
        # type rather than TEXT_MESSAGE_CONTENT so the frontend can
        # route it to a separate, collapsible "thinking" bubble.
        return _sse_event(
            "THINKING_CONTENT",
            {
                "messageId": message_id,
                "delta": event.get("delta", ""),
            },
        )
    elif event_type == "tool_call":
        return _sse_event(
            "TOOL_CALL_START",
            {
                "toolCallId": event.get("tool_call_id", str(uuid.uuid4())),
                "toolCallName": event.get("tool", ""),
                "parentMessageId": message_id,
            },
        )
    elif event_type == "tool_result":
        return _sse_event(
            "TOOL_CALL_RESULT",
            {
                "toolCallId": event.get("tool_call_id", ""),
                "content": json.dumps(event.get("result", "")),
            },
        )
    elif event_type == "done":
        # Skip: handled by the caller to guarantee ordering
        # (TEXT_MESSAGE_END must precede RUN_FINISHED).
        return None
    elif event_type == "error":
        return _sse_event("RUN_ERROR", {"error": event.get("error", "")})
    return None


def _generate_agui_text_start(message_id: str) -> str:
    """Generate AG-UI TEXT_MESSAGE_START event."""
    return _sse_event(
        "TEXT_MESSAGE_START",
        {
            "messageId": message_id,
            "role": "assistant",
        },
    )


def _generate_agui_text_end(message_id: str) -> str:
    """Generate AG-UI TEXT_MESSAGE_END event."""
    return _sse_event("TEXT_MESSAGE_END", {"messageId": message_id})


def _generate_agui_run_started(session_id: str) -> str:
    """Generate AG-UI RUN_STARTED event with the real session id.

    The frontend must key sessions off ``sessionId`` (not the
    per-message ``messageId``) so multi-model session restore works.
    """
    return _sse_event("RUN_STARTED", {"sessionId": session_id})


def _build_ai_agent(user_id: str, request: ChatRequest):
    """Construct an AiAgent, mapping unknown model IDs to HTTP 400.

    Validation happens BEFORE the StreamingResponse is returned so an
    invalid explicit ``model_id`` fails fast instead of surfacing
    mid-stream.
    """
    try:
        from wy_qcos.ai.agent import AiAgent
    except ImportError as exc:
        logger.error(f"AI agent dependencies missing: {exc}")
        raise HTTPException(
            status_code=503,
            detail="AI agent dependencies not installed",
        ) from exc
    try:
        return AiAgent(
            user_id=user_id,
            session_id=request.session_id,
            model_id=request.model_id,
        )
    except UnknownAIModelError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _check_vision_attachments(agent, request: ChatRequest):
    """Reject image attachments for vision-less models before streaming.

    Resolves the effective model exactly as the orchestrator will
    (explicit ID -> session-saved ID -> default) so the request fails
    with HTTP 400 instead of a mid-stream error event.
    """
    if not request.attachments:
        return
    model_id = await agent._resolve_session_model()
    if Config.AI_AGENT.resolve_vision(model_id) is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"AI model '{model_id}' does not support image attachments"
            ),
        )


# ===== Routes =====


@router.get("/models")
async def list_models(
    user: Annotated[dict, Depends(get_current_user)],
):
    """List configured AI models (non-sensitive fields only).

    The response never includes provider URLs, API keys, prompts or
    any other connection detail, and no Agent is instantiated.
    """
    if not Config.is_ai_agent_enabled():
        raise HTTPException(status_code=503, detail="AI agent is disabled")
    user_id = user.get("user_id") or user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")
    return {
        "default_model_id": Config.AI_AGENT.default_model_id,
        "models": Config.AI_AGENT.public_models(),
    }


@router.post("/chat")
async def chat_stream(
    request: ChatRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Submit a user message and stream the AI response via SSE."""
    if not Config.is_ai_agent_enabled():
        raise HTTPException(status_code=503, detail="AI agent is disabled")

    user_id = user.get("user_id") or user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")

    agent = _build_ai_agent(user_id, request)
    await _check_vision_attachments(agent, request)

    async def event_generator():
        try:
            async for event in agent.chat_stream(
                user_message=request.message,
                enable_rag=request.enable_rag,
                attachments=[
                    att.model_dump() for att in (request.attachments or [])
                ],
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.exception("Chat stream error")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/agui")
async def chat_stream_agui(
    request: ChatRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Submit a user message and stream the AI response via AG-UI protocol SSE.

    This endpoint follows the AG-UI protocol standard for agentic UI
    communication, using standardized event types like TEXT_MESSAGE_START,
    TEXT_MESSAGE_CONTENT, TEXT_MESSAGE_END, TOOL_CALL_*, RUN_STARTED,
    RUN_FINISHED, RUN_ERROR.
    """
    t_route_start = time.monotonic()
    logger.info(
        "AI agui request received: user=%s session=%s "
        "msg_len=%d attachments=%d",
        user.get("user_name") or user.get("user_id") or user.get("sub"),
        request.session_id,
        len(request.message or ""),
        len(request.attachments or []),
    )

    if not Config.is_ai_agent_enabled():
        raise HTTPException(status_code=503, detail="AI agent is disabled")

    user_id = user.get("user_id") or user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")

    t_agent_init_start = time.monotonic()
    agent = _build_ai_agent(user_id, request)
    await _check_vision_attachments(agent, request)
    logger.info(
        "AI agui AiAgent init done in %.3fs (session=%s)",
        time.monotonic() - t_agent_init_start,
        agent.session_id,
    )
    message_id = str(uuid.uuid4())

    async def event_generator() -> AsyncGenerator[str, None]:
        t_gen_start = time.monotonic()
        logger.info("AI agui generator started (message_id=%s)", message_id)
        try:
            # Send RUN_STARTED event with the real session id
            yield _generate_agui_run_started(agent.session_id)
            logger.info(
                "AI agui first yield (RUN_STARTED) at +%.3fs",
                time.monotonic() - t_gen_start,
            )

            # Send TEXT_MESSAGE_START event
            yield _generate_agui_text_start(message_id)

            t_chat_start = time.monotonic()
            first_event_logged = False
            event_count = 0
            # Populated when the internal agent stream emits its final
            # ``done`` event; consumed by RUN_FINISHED below. ``None``
            # when the backend has no usage stats for this run.
            token_usage: dict | None = None
            # Model metadata relayed from the internal done event.
            done_model_id: str | None = None
            done_model: str | None = None
            async for event in agent.chat_stream(
                user_message=request.message,
                enable_rag=request.enable_rag,
                attachments=[
                    att.model_dump() for att in (request.attachments or [])
                ],
            ):
                if not first_event_logged:
                    logger.info(
                        "AI agui first chat_stream event received at +%.3fs "
                        "(type=%s)",
                        time.monotonic() - t_chat_start,
                        event.get("type"),
                    )
                    first_event_logged = True
                event_count += 1
                # Capture token usage and model info from the internal
                # ``done`` event so we can forward them in RUN_FINISHED
                # below. The internal event is dropped by _to_agui_event
                # (returns None) - only its payload is relayed.
                if event.get("type") == "done":
                    token_usage = event.get("usage")
                    done_model_id = event.get("model_id")
                    done_model = event.get("model")
                agui_event = _to_agui_event(event, message_id)
                if agui_event:
                    yield agui_event

            logger.info(
                "AI agui chat_stream finished: %d events in %.3fs",
                event_count,
                time.monotonic() - t_chat_start,
            )

            # Send TEXT_MESSAGE_END event first so the client can close
            # the assistant bubble before the run-level completion
            # signal arrives.
            yield _generate_agui_text_end(message_id)

            # Always send RUN_FINISHED last so the client knows the
            # stream has completed successfully. Without this event the
            # UI stays in streaming skeleton state forever. This is the
            # ONLY place RUN_FINISHED is emitted - the per-event mapper
            # above deliberately drops the internal "done" event.
            run_finished_payload: dict = {
                "messageId": message_id,
                # Real session id: the frontend keys sessions off this
                # value instead of the per-message messageId.
                "sessionId": agent.session_id,
                "modelId": done_model_id,
                "model": done_model,
            }
            if token_usage:
                run_finished_payload["usage"] = token_usage
            yield _sse_event("RUN_FINISHED", run_finished_payload)

        except Exception as e:
            logger.exception("Chat stream error")
            yield _sse_event("RUN_ERROR", {"error": str(e)})

    logger.info(
        "AI agui route returning StreamingResponse at +%.3fs",
        time.monotonic() - t_route_start,
    )
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions")
async def list_sessions(
    user: Annotated[dict, Depends(get_current_user)],
):
    """List all AI chat sessions for the current user."""
    user_id = user.get("user_id") or user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user identity")
    store = RedisSessionStore(str(user_id))
    sessions = await store.list_sessions()
    await store.close()
    return [
        SessionInfoResponse(
            session_id=s.session_id,
            created_at=s.created_at,
            title=s.title,
            message_count=s.message_count,
            model_id=s.model_id,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Retrieve all messages for a single session."""
    user_id = user.get("user_id") or user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user identity")
    store = RedisSessionStore(str(user_id), session_id)
    info = await store.get_session_info()
    if not info:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await store.get_messages()
    await store.close()
    return {
        "session": SessionInfoResponse(
            session_id=info.session_id,
            created_at=info.created_at,
            title=info.title,
            message_count=info.message_count,
            model_id=info.model_id,
        ),
        "messages": [
            MessageResponse(
                role=m["role"],
                content=m["content"],
                created_at=m["created_at"],
                attachments=m.get("attachments"),
                model_id=m.get("model_id"),
                model=m.get("model"),
            )
            for m in messages
        ],
    }


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a session and its messages."""
    user_id = user.get("user_id") or user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user identity")
    store = RedisSessionStore(str(user_id), session_id)
    await store.delete_session()
    await store.close()
    return {"status": "deleted", "session_id": session_id}


@router.post("/sessions/{session_id}/messages/truncate")
async def truncate_session_messages(
    session_id: str,
    request: SessionMessagesTruncateRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Remove an edited user message and all subsequent messages."""
    user_id = user.get("user_id") or user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user identity")
    store = RedisSessionStore(str(user_id), session_id)
    try:
        retained = await store.truncate_from(
            request.from_index,
            request.expected_content,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="Session not found"
        ) from exc
    except SessionMessageConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail="Session history changed; reload and retry",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await store.close()
    return {
        "session_id": session_id,
        "message_count": len(retained),
        "messages": [
            MessageResponse(
                role=message["role"],
                content=message["content"],
                created_at=message["created_at"],
                attachments=message.get("attachments"),
                model_id=message.get("model_id"),
                model=message.get("model"),
            )
            for message in retained
        ],
    }


@router.delete("/sessions/{session_id}/messages")
async def clear_session_messages(
    session_id: str,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Clear all messages in a session without deleting the session.

    The session record (id / title / created_at) is preserved so the
    conversation stays in the user's session list; only the message
    history is wiped. Used by the chat toolbar's "clear conversation"
    button.
    """
    user_id = user.get("user_id") or user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user identity")
    store = RedisSessionStore(str(user_id), session_id)
    await store.clear_messages()
    await store.close()
    return {"status": "cleared", "session_id": session_id}


@router.post("/sessions")
async def create_session(
    request: SessionCreateRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Create a new empty session."""
    user_id = user.get("user_id") or user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user identity")
    store = RedisSessionStore(str(user_id))
    # New sessions start on the configured default model.
    session_id = await store.create_session(
        title=request.title,
        model_id=Config.AI_AGENT.default_model_id,
    )
    await store.close()
    return {"session_id": session_id, "title": request.title}
