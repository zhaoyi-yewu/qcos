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

import logging

from wy_qcos.api.posiq.routes_rest.jwt_utils import (
    ASGIApp,
    Receive,
    Scope,
    Send,
    check_jwt,
    send_unauthorized,
)

logger = logging.getLogger(__name__)


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

        if not check_jwt(scope, log_prefix="Proxy access"):
            await send_unauthorized(send)
            return

        await self.app(scope, receive, send)
