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

"""JWT authentication middleware for reverse-proxy endpoints.

Follows the global ``AUTH_MODE``:

* ``no``                — pass-through, no token check
* ``virtual_instance``  — pass-through (no JWT in virtual-instance mode)
* ``jwt``               — require ``Authorization: Bearer <token>``
                          and validate via
                          :func:`decode_jwt_token`

The error response matches the MCP middleware format so clients see
a consistent shape across the QCOS REST surface.
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


class ProxyJwtMiddleware:
    """Pure-ASGI JWT middleware for reverse-proxy sub-apps.

    Validates the ``Authorization: Bearer <token>`` header using
    :func:`decode_jwt_token`. When :data:`Config.DEFAULT.AUTH_MODE` is
    not ``"jwt"``, the middleware is a pass-through.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize middleware.

        Args:
            app: The inner ASGI application to wrap.
        """
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self._check_jwt(scope):
            await self._send_unauthorized(send)
            return

        await self.app(scope, receive, send)

    @staticmethod
    def _check_jwt(scope: Scope) -> bool:
        """Return True if the request is allowed through.

        See :class:`ProxyJwtMiddleware` docstring for the mode table.
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
            logger.warning("Proxy access denied: missing Authorization header")
            return False

        parts = auth_header.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.warning("Proxy access denied: invalid Authorization scheme")
            return False

        token = parts[1].strip()
        payload = decode_jwt_token(token)
        if not payload:
            logger.warning("Proxy access denied: invalid or expired JWT token")
            return False
        return True

    @staticmethod
    async def _send_unauthorized(send: Send) -> None:
        """Send HTTP 401 with a JSON error body (MCP-style shape)."""
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
