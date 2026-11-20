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
import re
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
from wy_qcos.common.config import Config, UnknownAIModelError

logger = logging.getLogger(__name__)


def _describe_llm_error(exc: Exception, model: str | None = None) -> str:
    """Return a readable detail for an LLM provider failure.

    pydantic-ai wraps provider HTTP errors in ``ModelHTTPError`` whose
    ``body`` carries the vendor payload (typically an OpenAI-style
    ``{"error": {"message": ...}}``). Surfacing the vendor message
    keeps quota / auth / rate-limit failures readable in the chat
    bubble instead of dumping the raw exception repr.

    Gateway (nginx / LB) failures return an HTML error page instead of
    JSON; that raw HTML must never be dumped into the chat bubble - it
    is converted into an actionable message naming the model, the HTTP
    status and the next step (retry / switch model).
    """
    body = getattr(exc, "body", None)
    status_code = getattr(exc, "status_code", None)
    model_name = model or getattr(exc, "model_name", None) or "当前模型"
    if isinstance(body, str) and "<html" in body.lower():
        status_part = f"HTTP {status_code}" if status_code else "上游错误"
        title_match = re.search(
            r"<title>(.*?)</title>", body, re.IGNORECASE | re.DOTALL
        )
        if title_match:
            status_part += f" {title_match.group(1).strip()}"
        return (
            f"上游模型网关错误（{status_part}，模型 {model_name}）。"
            "模型后端可能未启动、已崩溃或网关无法连接后端，"
            "请稍后重试，或在模型菜单切换到其他可用模型。"
        )
    if isinstance(body, str):
        # Some providers hand the raw JSON text over; parse it so the
        # vendor message can still be extracted.
        try:
            body = json.loads(body)
        except ValueError:
            body = {"message": body}
    vendor_message = ""
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            vendor_message = str(error.get("message") or "").strip()
        elif isinstance(error, str):
            vendor_message = error.strip()
        if not vendor_message:
            vendor_message = str(body.get("message") or "").strip()
    if vendor_message:
        # Bound the detail so a pathological vendor payload cannot
        # flood the chat bubble.
        vendor_message = vendor_message[:500]
        prefix = f"HTTP {status_code}: " if status_code else ""
        return f"{prefix}{vendor_message}"
    return str(exc).strip() or type(exc).__name__


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


def _tool_event_to_sse(event) -> dict | None:
    """Convert a tool call/result event into an SSE event dict.

    Shared by the ModelRequestNode and CallToolsNode branches so the
    tool-event mapping is defined exactly once for both text and
    vision turns. Returns ``None`` for non-tool events.
    """
    if isinstance(event, FunctionToolCallEvent):
        return {
            "type": "tool_call",
            "tool": _tool_call_field(event, "tool_name", ""),
            "args": _tool_call_field(event, "args", {}),
            "tool_call_id": _tool_call_field(event, "tool_call_id", ""),
        }
    if isinstance(event, FunctionToolResultEvent):
        return {
            "type": "tool_result",
            "tool": _tool_call_field(event, "tool_name", ""),
            "tool_call_id": _tool_call_field(event, "tool_call_id", ""),
            "result": _tool_result_content(event),
        }
    return None


def _iter_chunk_events(delta: str):
    """Yield chunk SSE events for a text delta.

    Large deltas are split into ~2 character pieces for a smoother
    typewriter effect on the frontend. Shared by the run_stream
    fallback and the graph-driven branch.
    """
    if len(delta) > 2:
        for i in range(0, len(delta), 2):
            yield {"type": "chunk", "delta": delta[i : i + 2]}
    else:
        yield {"type": "chunk", "delta": delta}


class AiAgent:
    """Orchestrates a single AI chat session."""

    def __init__(
        self,
        user_id: str,
        session_id: str | None = None,
        model_id: str | None = None,
    ):
        self.user_id = user_id
        self.session_store = RedisSessionStore(user_id, session_id)
        self.session_id = self.session_store.session_id
        self.rag = RagRetriever() if Config.is_ai_agent_enabled() else None

        # Model selection priority: explicit request ID -> model saved
        # on the session (if still configured) -> first configured
        # entry. An explicitly requested unknown ID fails fast here,
        # before any streaming starts; session-saved IDs are resolved
        # lazily in chat_stream because Redis access is async.
        self._requested_model_id = model_id
        if model_id is not None:
            Config.AI_AGENT.resolve_model(model_id)
        self.model_id: str | None = model_id
        # Actual upstream model name used for the current turn
        # (text MODEL or vision VISION_MODEL-or-MODEL).
        self._upstream_model: str | None = None

        # Build agents lazily to avoid import-time side effects
        self._text_agent = None
        self._vision_agent = None

    async def _resolve_session_model(self) -> str:
        """Resolve the effective model ID for this turn.

        Explicit request IDs win; otherwise the session-saved model is
        reused when it still exists in the configuration (a deleted
        model safely falls back to the default and is repaired on the
        next append); new sessions use the first configured entry.
        """
        if self._requested_model_id is not None:
            return self._requested_model_id
        try:
            info = await self.session_store.get_session_info()
        except Exception:
            logger.debug("Failed to read session model", exc_info=True)
            info = None
        if info and info.model_id:
            try:
                Config.AI_AGENT.resolve_model(info.model_id)
                return info.model_id
            except UnknownAIModelError:
                logger.info(
                    "Session model %s is no longer configured; "
                    "falling back to the default model",
                    info.model_id,
                )
        return Config.AI_AGENT.default_model().ID

    @property
    def text_agent(self):
        if self._text_agent is None:
            self._text_agent = build_text_agent(self.model_id)
        return self._text_agent

    @property
    def vision_agent(self):
        if self._vision_agent is None:
            # The vision agent DOES get MCP tools (same set as the
            # text agent) so "analyse this image then submit it" can
            # run the real tool chain instead of fabricating results.
            self._vision_agent = build_vision_agent(self.model_id)
        return self._vision_agent

    @staticmethod
    def _build_message_history(
        history: list[dict], include_images: bool = True
    ) -> list[ModelMessage]:
        """Convert Redis-stored messages into pydantic-ai message_history.

        The session store persists plain ``{role, content, created_at,
        [attachments]}`` dicts. Pydantic-ai expects a list of
        ``ModelRequest`` (user prompts) and ``ModelResponse`` (assistant
        replies) objects wrapping typed parts. We rebuild the simplest
        possible message per turn: a ``UserPromptPart`` for user
        messages and a ``TextPart`` for assistant messages.

        ``include_images`` reflects the CURRENT model's vision
        capability: when the user switches to a model without image
        support, historical attachments must NOT be inlined as
        ``BinaryContent`` - the provider would reject the whole
        request (e.g. HTTP 400 "model does not support image input").
        In that case the text context is kept and attachments are
        replaced with a small placeholder note.

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
                content_parts: list = []
                if content:
                    content_parts.append(content)
                if attachments and not include_images:
                    content_parts.append(
                        f"[历史消息附加了 {len(attachments)} 张图片，"
                        "当前模型不支持图片输入，已省略图片内容]"
                    )
                else:
                    for att in attachments:
                        try:
                            image_bytes = base64.b64decode(att.get("data", ""))
                        except Exception as e:
                            # Skip malformed attachments rather than
                            # crash the whole history rebuild.
                            logger.debug(
                                "Skipping malformed attachment in history: %s",
                                e,
                            )
                            continue
                        content_parts.append(
                            BinaryContent(
                                data=image_bytes,
                                media_type=att.get("media_type", "image/png"),
                            )
                        )
                if not content_parts:
                    # Skip empty user turns - pydantic-ai rejects empty
                    # part lists.
                    continue
                # BinaryContent is user content, not a ModelRequest part.
                # Keep plain text prompts as strings for compatibility.
                prompt_content = (
                    content_parts[0]
                    if len(content_parts) == 1
                    and isinstance(content_parts[0], str)
                    else content_parts
                )
                messages.append(
                    ModelRequest(
                        parts=[UserPromptPart(content=prompt_content)]
                    )
                )
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
        # Resolve the effective model first: explicit invalid IDs and
        # vision-incompatible attachments must fail before streaming.
        self.model_id = await self._resolve_session_model()
        resolved_model = Config.AI_AGENT.resolve_model(self.model_id)
        self._upstream_model = resolved_model.model
        attachments = self._validate_attachments(attachments)
        has_images = bool(attachments)
        if has_images:
            vision = Config.AI_AGENT.resolve_vision(self.model_id)
            if vision is None:
                raise ValueError(
                    f"AI model '{self.model_id}' does not support "
                    "image attachments"
                )
            # Record the actual upstream vision model for this turn.
            self._upstream_model = vision.model
        # Populated from the agent_run's ``usage()`` once the run ends
        # successfully. ``None`` means the backend did not report
        # token statistics (e.g. local providers without a usage API).
        token_usage: dict | None = None
        t_start = time.monotonic()
        logger.info(
            "AI chat_stream start: user=%s session=%s model=%s images=%s",
            self.user_id,
            self.session_id,
            self.model_id,
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
        # ``message_history`` so the LLM sees prior turns. Historical
        # image attachments are only inlined when the CURRENT model
        # supports vision - otherwise the provider would reject the
        # request with "model does not support image input".
        vision_capable = (
            Config.AI_AGENT.resolve_vision(self.model_id) is not None
        )
        message_history = self._build_message_history(
            history, include_images=vision_capable
        )

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

        # 4. Route to text or vision agent. BOTH turn types share the
        # same Agent.iter() graph below, so an image turn can also run
        # the real submit/status/result tool chain after transcribing
        # the picture - the model no longer has to fabricate a job id
        # and counts because it has real tools available.
        final_response_parts: list[str] = []
        has_thinking = False
        try:
            prompt: str | list[str | BinaryContent]
            if has_images:
                prompt = [user_message]
                for att in attachments:
                    image_bytes = base64.b64decode(att["data"])
                    prompt.append(
                        BinaryContent(
                            data=image_bytes,
                            media_type=att["media_type"],
                        )
                    )
                active_agent = self.vision_agent
            else:
                prompt = user_message
                active_agent = self.text_agent
            t_run_stream = time.monotonic()
            logger.info(
                "AI chat_stream agent ready at +%.3fs (vision=%s)",
                time.monotonic() - t_start,
                has_images,
            )

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
                async with active_agent.run_stream(
                    prompt,
                    deps=deps,
                    message_history=message_history,
                ) as result:
                    async for chunk in result.stream_text(delta=True):
                        final_response_parts.append(chunk)
                        for chunk_event in _iter_chunk_events(chunk):
                            yield chunk_event
            else:
                first_node_logged = False
                async with active_agent.iter(
                    prompt,
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
                                    thinking_delta = _extract_thinking_delta(
                                        event
                                    )
                                    text_delta = _extract_text_delta(event)
                                    if thinking_delta:
                                        has_thinking = True
                                        yield {
                                            "type": "thinking",
                                            "delta": thinking_delta,
                                        }
                                    elif text_delta:
                                        final_response_parts.append(text_delta)
                                        for chunk_event in _iter_chunk_events(
                                            text_delta
                                        ):
                                            yield chunk_event
                                    else:
                                        tool_event = _tool_event_to_sse(event)
                                        if tool_event:
                                            yield tool_event
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
                                    tool_event = _tool_event_to_sse(event)
                                    if tool_event:
                                        yield tool_event
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
        except Exception as exc:
            logger.exception("AI agent stream failed")
            error_detail = _describe_llm_error(exc, self._upstream_model)
            failure_message = f"抱歉，AI 智能体思考失败：{error_detail}"
            partial_response = "".join(final_response_parts)
            response_delta = (
                f"\n\n{failure_message}"
                if partial_response
                else failure_message
            )
            failed_response = f"{partial_response}{response_delta}"
            # Send the visible answer before persistence so provider errors
            # (for example HTTP 429) are not hidden by a slow session store.
            yield {"type": "chunk", "delta": response_delta}
            try:
                await self.session_store.append(
                    "user",
                    user_message,
                    attachments=attachments,
                    model_id=self.model_id,
                )
                await self.session_store.append(
                    "assistant",
                    failed_response,
                    model_id=self.model_id,
                    model=self._upstream_model,
                )
            except Exception:
                logger.exception("Failed to persist AI agent failure")
            yield {"type": "error", "error": error_detail}
            return

        # 5. Persist messages
        final_response = "".join(final_response_parts)
        if not final_response.strip():
            if has_thinking:
                final_response = (
                    "抱歉，AI 智能体在思考阶段未生成最终回复，可能是输出 "
                    "Token 已耗尽。请增大模型 Token 限额或缩短输入后重试。"
                )
            else:
                final_response = (
                    "抱歉，AI 智能体未生成回复，请检查模型配置或稍后重试。"
                )
            yield {"type": "chunk", "delta": final_response}
        await self.session_store.append(
            "user",
            user_message,
            attachments=attachments,
            model_id=self.model_id,
        )
        await self.session_store.append(
            "assistant",
            final_response,
            model_id=self.model_id,
            model=self._upstream_model,
        )

        done_event: dict = {
            "type": "done",
            "message_id": self.session_id,
            "model_id": self.model_id,
            "model": self._upstream_model,
        }
        if token_usage:
            done_event["usage"] = token_usage
        yield done_event
