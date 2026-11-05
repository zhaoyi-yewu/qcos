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

"""QCOS AI Agent orchestration.

Combines LLM (text + vision), RAG retrieval, and MCP tool calling
into a single streaming chat pipeline.
"""

import base64
import json
import logging
import time
from collections.abc import AsyncGenerator

from pydantic_ai import BinaryContent
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    UserPromptPart,
)

# Agent-graph node classes used by the ``Agent.iter()`` code path. We
# need to distinguish three node kinds when manually driving the run:
# - ModelRequestNode: an LLM call is happening, stream its events
# - CallToolsNode: pydantic-ai is executing tool calls, surface them
# - End: run finished, stop iterating
# Older pydantic-ai releases place these under ``_agent_graph`` (private)
# or re-export them at the package root; try both so the import is
# version-tolerant.
try:
    from pydantic_ai import CallToolsNode as _CallToolsNode
    from pydantic_ai import End as _End
    from pydantic_ai import ModelRequestNode as _ModelRequestNode
except ImportError:  # pragma: no cover
    try:
        from pydantic_ai._agent_graph import (
            CallToolsNode as _CallToolsNode,
        )
        from pydantic_ai._agent_graph import (
            End as _End,
        )
        from pydantic_ai._agent_graph import (
            ModelRequestNode as _ModelRequestNode,
        )
    except ImportError:
        _CallToolsNode = ()
        _End = ()
        _ModelRequestNode = ()

# Older pydantic-ai releases named the thinking part differently or
# lacked it entirely; tolerate both so the import never fails.
try:
    from pydantic_ai.messages import (
        ThinkingPart as _ThinkingPart,
        ThinkingPartDelta as _ThinkingPartDelta,
    )
except ImportError:  # pragma: no cover
    _ThinkingPart = ()  # isinstance(x, ()) is always False
    _ThinkingPartDelta = ()

from wy_qcos.ai.deps import AiDeps
from wy_qcos.ai.llm.client import build_text_agent, build_vision_agent
from wy_qcos.ai.rag.retriever import RagRetriever, format_chunks_for_prompt
from wy_qcos.ai.session_store import RedisSessionStore
from wy_qcos.common.config import Config

logger = logging.getLogger(__name__)


def _extract_text_delta(event) -> str:
    """Extract the text delta carried by a pydantic-ai stream event.

    Returns an empty string for events that carry no user-visible
    text (tool events, final-result events, thinking parts).
    """
    if isinstance(event, PartStartEvent):
        part = event.part
        if _ThinkingPart and isinstance(part, _ThinkingPart):
            return ""
        if isinstance(part, TextPart):
            return part.content or ""
        return ""
    if isinstance(event, PartDeltaEvent) and isinstance(
        event.delta, TextPartDelta
    ):
        # pydantic-ai >= 0.7 renamed TextPartDelta.delta ->
        # TextPartDelta.content_delta (matching ThinkingPartDelta).
        # Older versions only expose `delta`. Try both.
        return (
            getattr(event.delta, "content_delta", None)
            or getattr(event.delta, "delta", "")
            or ""
        )
    return ""


def _extract_thinking_delta(event) -> str:
    """Extract the chain-of-thought (thinking) delta, if any.

    CoT arrives as PartStartEvent(ThinkingPart) at the start of the
    thinking section, followed by PartDeltaEvent(ThinkingPartDelta)
    for each subsequent token batch. Returns an empty string when
    the event carries no thinking content.
    """
    if not _ThinkingPart:
        return ""
    if isinstance(event, PartStartEvent) and isinstance(
        event.part, _ThinkingPart
    ):
        logger.debug(
            "AI thinking PartStartEvent: %s",
            event.part.content[:50] if event.part.content else "",
        )
        return event.part.content or ""
    if (
        _ThinkingPartDelta
        and isinstance(event, PartDeltaEvent)
        and isinstance(event.delta, _ThinkingPartDelta)
    ):
        # ThinkingPartDelta exposes the new text on `content_delta`
        # (newer pydantic-ai) or `delta` (older); tolerate both.
        delta = (
            getattr(event.delta, "content_delta", None)
            or getattr(event.delta, "delta", "")
            or ""
        )
        logger.debug(
            "AI thinking PartDeltaEvent: %s", delta[:50] if delta else ""
        )
        return delta
    return ""


def _tool_call_field(event, field: str, default=None):
    """Read a field from a FunctionTool(Call|Result)Event.

    Tolerates both the legacy flat layout (event.tool_name /
    event.args / event.tool_call_id) and the new nested layout where
    those live on ``event.part`` (pydantic-ai >= 0.7).
    """
    if hasattr(event, field):
        return getattr(event, field)
    part = getattr(event, "part", None)
    if part is not None and hasattr(part, field):
        return getattr(part, field)
    return default


def _tool_result_content(event: FunctionToolResultEvent) -> str:
    """Return the string content of a tool result event."""
    content = getattr(event, "content", None)
    if content is None:
        # Newer pydantic-ai nests the result under ``result``; older
        # releases exposed ``content`` directly. Try both.
        result = getattr(event, "result", None)
        content = getattr(result, "content", "") if result is not None else ""
    if not isinstance(content, str):
        return json.dumps(content, ensure_ascii=False, default=str)
    return content


class AiAgent:
    """Orchestrates a single AI chat session."""

    def __init__(self, user_id: str, session_id: str | None = None):
        self.user_id = user_id
        self.session_store = RedisSessionStore(user_id, session_id)
        self.session_id = self.session_store.session_id
        self.rag = RagRetriever() if Config.is_ai_agent_enabled() else None

        # Build agents lazily to avoid import-time side effects
        self._text_agent = None
        self._vision_agent = None

    @property
    def text_agent(self):
        if self._text_agent is None:
            self._text_agent = build_text_agent()
        return self._text_agent

    @property
    def vision_agent(self):
        if self._vision_agent is None:
            self._vision_agent = build_vision_agent()
            # Vision agent does NOT get MCP tools: image analysis should
            # not accidentally trigger tool calls.
        return self._vision_agent

    @staticmethod
    def _build_message_history(history: list[dict]) -> list[ModelMessage]:
        """Convert Redis-stored messages into pydantic-ai message_history.

        The session store persists plain ``{role, content, created_at,
        [attachments]}`` dicts. Pydantic-ai expects a list of
        ``ModelRequest`` (user prompts) and ``ModelResponse`` (assistant
        replies) objects wrapping typed parts. We rebuild the simplest
        possible message per turn: a ``UserPromptPart`` for user
        messages and a ``TextPart`` for assistant messages. Image
        attachments are inlined as ``BinaryContent`` on the user side
        so vision turns remain coherent.

        Tool-call messages are intentionally NOT replayed: they are
        re-derivable from the model's tool-use + our persistence layer
        on the next turn, and replaying them risks confusing models
        that don't expect raw tool payloads in user-visible history.
        """
        messages: list[ModelMessage] = []
        for msg in history:
            role = msg.get("role")
            content = msg.get("content") or ""
            attachments = msg.get("attachments") or []
            if role == "user":
                parts: list = []
                if content:
                    parts.append(UserPromptPart(content=content))
                for att in attachments:
                    try:
                        image_bytes = base64.b64decode(att.get("data", ""))
                    except Exception as e:
                        # Skip malformed attachments rather than crash
                        # the whole history rebuild.
                        logger.debug(
                            "Skipping malformed attachment in history: %s",
                            e,
                        )
                        continue
                    parts.append(
                        BinaryContent(
                            data=image_bytes,
                            media_type=att.get("media_type", "image/png"),
                        )
                    )
                if not parts:
                    # Skip empty user turns - pydantic-ai rejects empty
                    # part lists.
                    continue
                messages.append(ModelRequest(parts=parts))
            elif role == "assistant":
                if not content:
                    continue
                messages.append(
                    ModelResponse(parts=[TextPart(content=content)])
                )
            # Other roles (system / tool) are not persisted to the
            # session store, so we silently ignore them.
        return messages

    async def _retrieve_rag_context(self, query: str) -> str:
        """Retrieve relevant documentation chunks via RAG."""
        if not self.rag or not Config.is_ai_agent_enabled():
            return ""
        try:
            from wy_qcos.ai.rag.embedder import embed_single

            embedding = await embed_single(query)
            if not embedding:
                return ""
            chunks = await self.rag.retrieve(embedding)
            return format_chunks_for_prompt(chunks)
        except Exception as e:
            logger.warning(f"RAG retrieval failed, degrading to no-RAG: {e}")
            return ""

    def _validate_attachments(
        self, attachments: list[dict] | None
    ) -> list[dict]:
        """Validate and normalize image attachments."""
        if not attachments:
            return []
        cfg = Config.AI_AGENT
        if len(attachments) > cfg.IMAGE_MAX_COUNT_PER_MESSAGE:
            raise ValueError(
                f"Too many attachments: max {cfg.IMAGE_MAX_COUNT_PER_MESSAGE}"
            )
        validated = []
        for att in attachments:
            if att.get("kind") != "image":
                continue
            data = att.get("data", "")
            # base64 size approximation: 4/3 of raw bytes
            estimated_bytes = len(data) * 3 // 4
            if estimated_bytes > cfg.IMAGE_MAX_BYTES_PER_IMAGE:
                raise ValueError(
                    f"Image too large: max "
                    f"{cfg.IMAGE_MAX_BYTES_PER_IMAGE} bytes"
                )
            media_type = att.get("media_type", "image/png")
            if media_type not in (
                "image/png",
                "image/jpeg",
                "image/webp",
                "image/gif",
            ):
                raise ValueError(f"Unsupported image type: {media_type}")
            validated.append({
                "kind": "image",
                "media_type": media_type,
                "data": data,
                "size_bytes": estimated_bytes,
            })
        return validated

    async def chat_stream(
        self,
        user_message: str,
        enable_rag: bool = True,
        attachments: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream a chat response as SSE events.

        Yields dicts with keys:
            - type: "chunk" | "tool_call" | "tool_result" | "done" | "error"
            - delta: text chunk (for type="chunk")
            - tool / args / result: tool call info
            - message_id: final message ID (for type="done")
            - usage: token usage dict (for type="done"), when available
        """
        attachments = self._validate_attachments(attachments)
        has_images = bool(attachments)
        # Populated from the agent_run's ``usage()`` once the run ends
        # successfully. ``None`` means the backend did not report
        # token statistics (e.g. local providers without a usage API).
        token_usage: dict | None = None
        t_start = time.monotonic()
        logger.info(
            "AI chat_stream start: user=%s session=%s images=%s",
            self.user_id,
            self.session_id,
            len(attachments),
        )

        # 1. Load history
        t_history = time.monotonic()
        history = await self.session_store.get_messages()
        logger.info(
            "AI chat_stream history loaded in %.3fs: %d msgs",
            time.monotonic() - t_history,
            len(history),
        )
        # Convert the raw Redis dicts into pydantic-ai's typed
        # ``message_history`` so the LLM sees prior turns. Without this
        # the model only ever saw the current user_message and behaved
        # as if every turn started a brand-new conversation.
        message_history = self._build_message_history(history)

        # 2. Optional RAG (skip for image messages)
        rag_context = ""
        if enable_rag and not has_images:
            t_rag = time.monotonic()
            rag_context = await self._retrieve_rag_context(user_message)
            logger.info(
                "AI chat_stream RAG retrieved in %.3fs: %d chars",
                time.monotonic() - t_rag,
                len(rag_context),
            )

        # 3. Build deps
        deps = AiDeps(
            user_id=self.user_id,
            session_id=self.session_id,
            rag_context=rag_context,
            history=history,
        )
        logger.debug(
            "AI chat_stream deps ready: rag_context=%d chars",
            len(rag_context),
        )

        # 4. Route to text or vision agent
        final_response_parts: list[str] = []
        try:
            if has_images:
                parts: list = [user_message]
                for att in attachments:
                    image_bytes = base64.b64decode(att["data"])
                    parts.append(
                        BinaryContent(
                            data=image_bytes,
                            media_type=att["media_type"],
                        )
                    )
                async with self.vision_agent.run_stream(
                    parts, deps=deps, message_history=message_history
                ) as result:
                    async for chunk in result.stream_text(delta=True):
                        final_response_parts.append(chunk)
                        # Split large chunks into smaller pieces for a
                        # smoother typewriter effect on the frontend.
                        # If the LLM returns one big blob, we break it
                        # down into ~2 character pieces.
                        if len(chunk) > 2:
                            for i in range(0, len(chunk), 2):
                                small_chunk = chunk[i : i + 2]
                                yield {"type": "chunk", "delta": small_chunk}
                        else:
                            yield {"type": "chunk", "delta": chunk}
            else:
                t_agent_build = time.monotonic()
                text_agent = self.text_agent
                logger.info(
                    "AI chat_stream text_agent built in %.3fs",
                    time.monotonic() - t_agent_build,
                )
                logger.info(
                    "AI chat_stream calling text_agent.iter at +%.3fs",
                    time.monotonic() - t_start,
                )
                t_run_stream = time.monotonic()

                # Drive the agent graph manually via ``Agent.iter()``.
                # Unlike ``run_stream()``, ``iter()`` yields each graph
                # node (ModelRequestNode -> CallToolsNode -> ModelRequest
                # Node-with-tool-results -> ... -> End), so we can keep
                # streaming text after a tool call finishes. This is the
                # only way to surface both the tool-call event AND the
                # final LLM summary in a single SSE stream.
                if not (_ModelRequestNode and _CallToolsNode and _End):
                    # Fallback for very old pydantic-ai: pure text
                    # streaming without tool events.
                    async with text_agent.run_stream(
                        user_message,
                        deps=deps,
                        message_history=message_history,
                    ) as result:
                        async for chunk in result.stream_text(delta=True):
                            final_response_parts.append(chunk)
                            if len(chunk) > 2:
                                for i in range(0, len(chunk), 2):
                                    yield {
                                        "type": "chunk",
                                        "delta": chunk[i : i + 2],
                                    }
                            else:
                                yield {"type": "chunk", "delta": chunk}
                else:
                    first_node_logged = False
                    async with text_agent.iter(
                        user_message,
                        deps=deps,
                        message_history=message_history,
                    ) as agent_run:
                        async for node in agent_run:
                            if not first_node_logged:
                                logger.info(
                                    "AI chat_stream first agent node at "
                                    "+%.3fs: %s",
                                    time.monotonic() - t_run_stream,
                                    type(node).__name__,
                                )
                                first_node_logged = True

                            if isinstance(node, _ModelRequestNode):
                                # An LLM call: stream its events (text
                                # deltas, tool-call requests, thinking).
                                async with node.stream(
                                    agent_run.ctx
                                ) as event_stream:
                                    async for event in event_stream:
                                        thinking_delta = (
                                            _extract_thinking_delta(event)
                                        )
                                        text_delta = _extract_text_delta(event)
                                        if thinking_delta:
                                            yield {
                                                "type": "thinking",
                                                "delta": thinking_delta,
                                            }
                                        elif text_delta:
                                            final_response_parts.append(
                                                text_delta
                                            )
                                            if len(text_delta) > 2:
                                                for i in range(
                                                    0, len(text_delta), 2
                                                ):
                                                    yield {
                                                        "type": "chunk",
                                                        "delta": text_delta[
                                                            i : i + 2
                                                        ],
                                                    }
                                            else:
                                                yield {
                                                    "type": "chunk",
                                                    "delta": text_delta,
                                                }
                                        elif isinstance(
                                            event, FunctionToolCallEvent
                                        ):
                                            yield {
                                                "type": "tool_call",
                                                "tool": _tool_call_field(
                                                    event, "tool_name", ""
                                                ),
                                                "args": _tool_call_field(
                                                    event, "args", {}
                                                ),
                                                "tool_call_id": (
                                                    _tool_call_field(
                                                        event,
                                                        "tool_call_id",
                                                        "",
                                                    )
                                                ),
                                            }
                                        elif isinstance(
                                            event, FunctionToolResultEvent
                                        ):
                                            yield {
                                                "type": "tool_result",
                                                "tool": _tool_call_field(
                                                    event, "tool_name", ""
                                                ),
                                                "tool_call_id": (
                                                    _tool_call_field(
                                                        event,
                                                        "tool_call_id",
                                                        "",
                                                    )
                                                ),
                                                "result": (
                                                    _tool_result_content(event)
                                                ),
                                            }
                            elif isinstance(node, _CallToolsNode):
                                # Tool execution node: pydantic-ai runs
                                # the tools and emits
                                # FunctionToolResultEvent via its stream.
                                # We surface them so the frontend can
                                # render "tool finished" UI.
                                async with node.stream(
                                    agent_run.ctx
                                ) as event_stream:
                                    async for event in event_stream:
                                        if isinstance(
                                            event, FunctionToolCallEvent
                                        ):
                                            yield {
                                                "type": "tool_call",
                                                "tool": _tool_call_field(
                                                    event, "tool_name", ""
                                                ),
                                                "args": _tool_call_field(
                                                    event, "args", {}
                                                ),
                                                "tool_call_id": (
                                                    _tool_call_field(
                                                        event,
                                                        "tool_call_id",
                                                        "",
                                                    )
                                                ),
                                            }
                                        elif isinstance(
                                            event, FunctionToolResultEvent
                                        ):
                                            yield {
                                                "type": "tool_result",
                                                "tool": _tool_call_field(
                                                    event, "tool_name", ""
                                                ),
                                                "tool_call_id": (
                                                    _tool_call_field(
                                                        event,
                                                        "tool_call_id",
                                                        "",
                                                    )
                                                ),
                                                "result": (
                                                    _tool_result_content(event)
                                                ),
                                            }
                            # ``End`` node and others (e.g. UserPromptNode)
                            # need no special handling - the loop just
                            # continues to the next node.
                        # Capture token usage as soon as the agent run
                        # completes. ``usage()`` is only valid after the
                        # run has finished; calling it inside the loop
                        # would return partial counters.
                        try:
                            usage_obj = agent_run.usage()
                            if usage_obj is not None:
                                token_usage = {
                                    "input_tokens": getattr(
                                        usage_obj, "input_tokens", 0
                                    )
                                    or 0,
                                    "output_tokens": getattr(
                                        usage_obj, "output_tokens", 0
                                    )
                                    or 0,
                                    "total_tokens": getattr(
                                        usage_obj, "total_tokens", 0
                                    )
                                    or 0,
                                    # Some providers expose the
                                    # context-window size on the
                                    # response; when absent the
                                    # frontend falls back to a static
                                    # per-model default.
                                    "context_window": getattr(
                                        usage_obj, "context_window", 0
                                    )
                                    or 0,
                                }
                        except Exception:
                            logger.debug(
                                "Failed to read agent_run.usage()",
                                exc_info=True,
                            )
        except Exception:
            logger.exception("AI agent stream failed")
            yield {
                "type": "error",
                "error": (
                    "AI assistant is temporarily unavailable. "
                    "Please try again later."
                ),
            }
            return

        # 5. Persist messages
        final_response = "".join(final_response_parts)
        await self.session_store.append(
            "user", user_message, attachments=attachments
        )
        await self.session_store.append("assistant", final_response)

        done_event: dict = {"type": "done", "message_id": self.session_id}
        if token_usage:
            done_event["usage"] = token_usage
        yield done_event
