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

"""Shared JWT helpers for pure-ASGI middleware.

Both :class:`ProxyJwtMiddleware` (reverse-proxy sub-apps) and
``McpAsgiMiddleware`` (MCP endpoint in ``fastapi_server.py``) need the
same logic: validate the ``Authorization: Bearer <token>`` header via
:func:`decode_jwt_token` and, on failure, send a 401 response with a
JSON-RPC shaped error body. The helpers live here so the two
middlewares stay consistent and future changes only happen in one
place.
"""

import json
import logging
from collections.abc import Awaitable, Callable

from wy_qcos.api.posiq.routes_jsonrpc.dependencies.authentication import (
    decode_jwt_token,
)
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant

logger = logging.getLogger(__name__)

Scope = dict
Message = dict
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


def check_jwt(scope: Scope, log_prefix: str = "Access") -> bool:
    """Return True if the request is allowed through.

    Follows the global ``AUTH_MODE``:

    * ``no``                — pass-through, no token check
    * ``virtual_instance``  — pass-through (no JWT in virtual-instance
                              mode)
    * ``jwt``               — require ``Authorization: Bearer <token>``
                              and validate via :func:`decode_jwt_token`

    Args:
        scope: ASGI connection scope.
        log_prefix: Prefix for the warning log lines so callers can
            distinguish which middleware rejected the request.

    Returns:
        True when access is allowed (``AUTH_MODE`` is not ``"jwt"``, or
        a valid Bearer token is present), False when the request must
        be rejected with 401.
    """
    if Config.DEFAULT.AUTH_MODE != Constant.AUTH_MODE_JWT:
        return True

    headers = scope.get("headers", [])
    auth_header: str | None = None
    for key, value in headers:
        if key.lower() == b"authorization":
            auth_header = value.decode("latin-1")
            break

    if not auth_header:
        logger.warning(f"{log_prefix} denied: missing Authorization header")
        return False

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"{log_prefix} denied: invalid Authorization scheme")
        return False

    token = parts[1].strip()
    payload = decode_jwt_token(token)
    if not payload:
        logger.warning(f"{log_prefix} denied: invalid or expired JWT token")
        return False
    return True


async def send_unauthorized(send: Send) -> None:
    """Send HTTP 401 with a JSON-RPC shaped error body.

    Args:
        send: ASGI send callable.
    """
    body = json.dumps({
        "jsonrpc": "2.0",
        "error": {
            "code": -32001,
            "message": "Unauthorized: valid JWT token required",
        },
        "id": None,
    }).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": 401,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("latin-1")),
        ],
    })
    await send({"type": "http.response.body", "body": body})
