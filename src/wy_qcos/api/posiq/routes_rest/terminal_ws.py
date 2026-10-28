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

"""WebSocket endpoint for the QCOS web terminal.

Protocol summary (see ``plans/terminal.md`` §4):

1. Client opens ``WS /v1/terminal/ws?cols=80&rows=24``.
2. Within 3 seconds the client must send ``{"type":"auth", "token":
   "<JWT>"}`` as the first frame. The server validates the JWT and
   looks up the user.
3. On success the server spawns a bwrap-sandboxed shell, replies with
   ``{"type":"auth_ok", ...}`` and starts bidirectional forwarding.
4. Client sends ``input`` / ``resize`` / ``ping`` / ``close`` frames;
   the server sends ``output`` / ``exit`` / ``error`` / ``pong``.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi import status as http_status

from wy_qcos.api.posiq.routes_jsonrpc.dependencies.authentication import (
    get_current_user_from_token,
)
from wy_qcos.api.schemas import user as user_schemas
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.terminal import (
    TerminalAuditor,
    TerminalConfig,
    TerminalSessionLimitError,
    TerminalSessionManager,
)
from wy_qcos.user.user_manager import UserManager

logger = logging.getLogger(__name__)

router = APIRouter()

#: How long (seconds) to wait for the initial ``auth`` frame before
#: closing the connection.
AUTH_TIMEOUT_SECONDS = 3.0


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _build_terminal_config() -> TerminalConfig:
    return TerminalConfig.from_config(Config.TERMINAL)


def _authenticate_token(
    token: str | None, user_manager: UserManager
) -> user_schemas.User | None:
    """Authenticate the WebSocket auth frame.

    Follows the global ``Config.DEFAULT.AUTH_MODE``:

    - ``no``: no JWT required. Returns the anonymous user immediately
      regardless of the ``token`` field (which may be empty).
    - ``virtual_instance``: not supported for the terminal endpoint
      (no per-user shell concept); falls through to JWT path.
    - ``jwt``: validate the ``token`` field as a JWT and load the user.

    Returns ``None`` when authentication fails (JWT mode + bad token).
    """
    auth_mode = Config.DEFAULT.AUTH_MODE
    if auth_mode == Constant.AUTH_MODE_NO:
        logger.info("terminal ws: AUTH_MODE=no, using anonymous user")
        return user_schemas.User(
            id=uuid.UUID(Constant.ANONYMOUS_USER_ID),
            user_name=Constant.ANONYMOUS_USERNAME,
            hashed_password="",  # placeholder; never used in this path
            password_expiry_days=None,
        )
    if not token:
        logger.warning("terminal ws: auth failed - empty token")
        return None
    user = get_current_user_from_token(token, user_manager)
    if user is None:
        # Log only metadata about the token, never the token itself.
        # A valid JWT is "header.payload.signature" — exactly 2 dots.
        dots = token.count(".") if isinstance(token, str) else -1
        prefix = (
            (token[:8] + "...")
            if isinstance(token, str) and len(token) > 8
            else "<short>"
        )
        logger.warning(
            "terminal ws: auth failed - token_len=%d dots=%d prefix=%r",
            len(token) if isinstance(token, str) else -1,
            dots,
            prefix,
        )
    return user


async def _send_json_safe(ws: WebSocket, payload: dict) -> None:
    try:
        await ws.send_json(payload)
    except Exception as exc:
        # Client likely went away; log at debug to avoid log spam.
        logger.debug("terminal ws: send_json failed: %s", exc)


async def _close_ws_safe(
    ws: WebSocket, code: int = 1000, reason: str = ""
) -> None:
    """Close the WebSocket, tolerating an already-closed connection.

    Starlette raises ``RuntimeError('Cannot call "send" once a close message
    has been sent.')`` if either peer has already sent a close frame. This
    happens for example when the client connects and immediately disconnects
    without completing the auth handshake.
    """
    try:
        await ws.close(code=code, reason=reason)
    except RuntimeError as exc:
        logger.debug("terminal ws: close skipped (already closed): %s", exc)
    except Exception as exc:
        logger.debug("terminal ws: close failed: %s", exc)


# ----------------------------------------------------------------------
# WebSocket route
# ----------------------------------------------------------------------


@router.websocket("/v1/terminal/ws")
async def terminal_ws(
    ws: WebSocket,
    cols: int = Query(80, ge=20, le=500),
    rows: int = Query(24, ge=5, le=200),
) -> None:
    """WebSocket endpoint driving one interactive pty session."""
    # DEBUG: log every handshake attempt so we can confirm the route
    # is reachable when diagnosing "NS_ERROR_WEBSOCKET_CONNECTION_REFUSED"
    # reports from the browser. Sensitive headers (credentials) are
    # redacted so tokens never land on disk in plaintext.
    client_host = ws.client.host if ws.client else "<unknown>"
    sensitive_headers = {"authorization", "cookie", "proxy-authorization"}
    safe_headers = {
        k: ("***" if k.lower() in sensitive_headers else v)
        for k, v in ws.headers.items()
    }
    logger.debug(
        f"terminal ws handshake: client={client_host} "
        f"cols={cols} rows={rows} headers={safe_headers}"
    )
    await ws.accept()
    logger.info(f"terminal ws accepted: client={client_host}")

    cfg = _build_terminal_config()
    session = None
    recorder = None
    user: user_schemas.User | None = None
    manager = TerminalSessionManager.instance()
    auditor = TerminalAuditor(cfg)

    # ---- 1. Auth (first frame, 3s timeout) -------------------------
    try:
        auth_msg = await asyncio.wait_for(
            ws.receive_json(), timeout=AUTH_TIMEOUT_SECONDS
        )
    except (asyncio.TimeoutError, WebSocketDisconnect):
        await _send_json_safe(
            ws,
            {"type": "auth_fail", "reason": "auth timeout"},
        )
        await _close_ws_safe(ws, code=4401)
        return
    except Exception as exc:
        logger.warning("terminal ws: malformed auth frame: %s", exc)
        await _send_json_safe(ws, {"type": "auth_fail", "reason": "bad frame"})
        await _close_ws_safe(ws, code=4401)
        return

    if not isinstance(auth_msg, dict) or auth_msg.get("type") != "auth":
        await _send_json_safe(
            ws, {"type": "auth_fail", "reason": "expected auth frame"}
        )
        await _close_ws_safe(ws, code=4401)
        return

    # ``ws.app.state._user_manager`` is set in the main lifespan. We cannot
    # construct a ``Request`` here because Starlette asserts
    # ``scope["type"] == "http"``; for WebSocket scopes it is "websocket".
    # ``get_user_manager`` only reads ``request.app.state._user_manager``,
    # so pass the ``WebSocket`` itself — ``ws.app`` works the same way.
    user_manager: UserManager = ws.app.state._user_manager
    user = _authenticate_token(auth_msg.get("token"), user_manager)
    if user is None:
        await _send_json_safe(
            ws,
            {"type": "auth_fail", "reason": "invalid or expired token"},
        )
        await _close_ws_safe(ws, code=4403)
        return

    # ---- 2. Create session ------------------------------------------
    try:
        session = await manager.create(
            user_id=str(user.id),
            user_name=user.user_name,
            cols=cols,
            rows=rows,
        )
    except TerminalSessionLimitError as exc:
        await _send_json_safe(ws, {"type": "error", "message": str(exc)})
        await _close_ws_safe(ws, code=4429)  # Too Many Requests (app-level)
        return
    except Exception as exc:
        logger.exception("terminal ws: failed to spawn session")
        await _send_json_safe(
            ws,
            {"type": "error", "message": f"failed to start: {exc}"},
        )
        await _close_ws_safe(ws, code=1011)
        return

    # ---- 3. Audit + auth_ok -----------------------------------------
    client_ip = None
    user_agent = None
    try:
        if ws.client is not None:
            client_ip = ws.client.host
        user_agent = ws.headers.get("user-agent")
    except Exception as exc:
        logger.debug("terminal ws: failed to read client info: %s", exc)
    recorder = auditor.session_started(
        session_id=session.session_id,
        user_id=str(user.id),
        user_name=user.user_name,
        shell=session.shell,
        client_ip=client_ip,
        user_agent=user_agent,
        cols=cols,
        rows=rows,
    )

    await _send_json_safe(
        ws,
        {
            "type": "auth_ok",
            "session_id": session.session_id,
            "user": user.user_name,
            "shell": session.shell,
        },
    )

    # ---- 4. Bidirectional forwarding --------------------------------
    async def client_to_pty() -> None:
        """WS -> pty."""
        while True:
            msg = await ws.receive_json()
            if not isinstance(msg, dict):
                continue
            mtype = msg.get("type")
            if mtype == "input":
                data = msg.get("data")
                if isinstance(data, str) and data:
                    session.write(data)
            elif mtype == "resize":
                try:
                    c = int(msg.get("cols", cols))
                    r = int(msg.get("rows", rows))
                except (TypeError, ValueError):
                    continue
                session.resize(c, r)
            elif mtype == "ping":
                await _send_json_safe(ws, {"type": "pong"})
            elif mtype == "close":
                # Client asked to shut down; break out and let the
                # outer ``finally`` clean up the session.
                return
            # Unknown types are ignored on purpose.

    async def pty_to_client() -> None:
        """Pty -> WS (via read_loop + add_reader)."""

        async def _on_output(data: str) -> None:
            if recorder is not None:
                try:
                    recorder.record_output(data)
                except Exception:
                    logger.debug("transcript record failed")
            await _send_json_safe(ws, {"type": "output", "data": data})

        async def _on_exit(code: int | None) -> None:
            await _send_json_safe(ws, {"type": "exit", "code": code})

        await session.read_loop(_on_output, _on_exit)

    exit_code: int | None = None
    try:
        # Run both halves concurrently; when either finishes (client
        # closed or pty exited) cancel the other and clean up.
        client_task = asyncio.create_task(client_to_pty())
        pty_task = asyncio.create_task(pty_to_client())
        done, pending = await asyncio.wait(
            {client_task, pty_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
        for t in done:
            try:
                t.result()
            except (WebSocketDisconnect, asyncio.CancelledError):
                pass
            except Exception:
                logger.exception("terminal ws forwarding task failed")
        # Give the pty task a brief moment to flush the exit frame.
        try:
            await asyncio.wait_for(asyncio.shield(pty_task), timeout=1.0)
        except (asyncio.TimeoutError, asyncio.CancelledError) as exc:
            logger.debug("terminal ws: pty flush wait ended: %s", exc)
        except Exception as exc:
            logger.debug("terminal ws: pty flush error: %s", exc)
    finally:
        exit_code = session.exit_code
        auditor.session_ended(
            session_id=session.session_id,
            user_id=str(user.id),
            user_name=user.user_name,
            exit_code=exit_code,
            bytes_in=session.bytes_in,
            bytes_out=session.bytes_out,
            duration_seconds=session.last_active_at - session.created_at,
            recorder=recorder,
        )
        try:
            await manager.terminate(session.session_id)
        except Exception:
            logger.exception(
                "terminal ws: failed to terminate session %s",
                session.session_id,
            )
        try:
            await _close_ws_safe(ws, code=http_status.WS_1000_NORMAL_CLOSURE)
        except Exception as exc:
            logger.debug("terminal ws: close failed: %s", exc)
