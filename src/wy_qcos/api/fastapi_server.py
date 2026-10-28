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

import logging
import socket
import time

import fastapi_jsonrpc as jsonrpc
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi_jsonrpc import InvalidParams
from pydantic import ValidationError
from uvicorn.main import Server as UvicornServer

from wy_qcos.api.fastapi_coroutine import app_lifespan
from wy_qcos.api.mcp.mcp_server import mcp as mcp_server, _MCP_VERSION
from wy_qcos.api.mcp.mcp_server import get_mcp_http_app
from wy_qcos.api.posiq.routes_jsonrpc.routes import all_api, BASE_ENDPOINT
from wy_qcos.api.posiq.routes_jsonrpc.dependencies.authentication import (
    decode_jwt_token,
)
from wy_qcos.api.posiq.routes_rest.proxy_auth import ProxyJwtMiddleware
from wy_qcos.api.posiq.routes_rest.proxy_registry import PROXY_TARGETS
from wy_qcos.api.posiq.routes_rest.reverse_proxy import (
    create_reverse_proxy_app,
)
from wy_qcos.api.posiq.routes_rest.terminal_files import (
    router as terminal_files_router,
)
from wy_qcos.api.posiq.routes_rest.terminal_ws import (
    router as terminal_ws_router,
)
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.metrics.metrics_middleware import MetricsMiddleware

logger = logging.getLogger(__name__)

# MCP endpoint path under /v1/ai/mcp like other QCOS API endpoints.
# Placed under the /v1/ai/ namespace to distinguish AI assistant
# integration endpoints from regular JSON-RPC API endpoints.
MCP_ENDPOINT = f"{BASE_ENDPOINT}/ai/mcp"

# Max retries and interval (seconds) when the listen port is still in
# TIME_WAIT after a rapid restart.
_BIND_MAX_RETRIES = 5
_BIND_RETRY_INTERVAL = 1.0

app = jsonrpc.API(lifespan=app_lifespan)


def patched_invalid_params_from_validation_error(
    exc: ValidationError | RequestValidationError,
) -> InvalidParams:
    """Patched invalid_params_from_validation_error for fastapi_jsonrpc.

    Args:
        exc (Exception): exception

    Returns:
      jsonrpc.InvalidParams, jsonrpc
    """
    errors = []
    details = []
    for err in exc.errors():
        err.pop("url", None)
        if "loc" in err:
            if err["loc"][:1] == ("body",):
                err["loc"] = err["loc"][1:]
            else:
                err["loc"] = (f"<{err['loc'][0]}>",) + err["loc"][1:]
        errors.append(err)
        loc_list = [str(item) for item in err.get("loc", [])]
        details.append(
            f"{err.get('msg', '')}. Actual value: "
            f"{'.'.join(loc_list)}={err.get('input', '')}, "
            f"Except type: {err.get('type', '')}"
        )
    return InvalidParams(
        data={"details": "; ".join(details), "errors": errors}
    )


jsonrpc.invalid_params_from_validation_error = (
    patched_invalid_params_from_validation_error
)


# CORS: allow any origin. ``allow_origins=["*"]`` is incompatible with
# ``allow_credentials=True`` per the CORS spec — Starlette's
# CORSMiddleware will refuse credentialed requests (including WebSocket
# handshakes, which always carry the ``Origin`` header and trigger
# cookie-based auth) with HTTP 403 when both are set. Using
# ``allow_origin_regex=".*"`` makes the middleware echo the request's
# ``Origin`` header back instead of the literal "*", which is what the
# browser expects for credentialed / WebSocket flows.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Metrics Middleware to collect metrics
app.add_middleware(MetricsMiddleware)
# bind entrypoint
for api_entrypoint in all_api:
    app.bind_entrypoint(api_entrypoint)

# Mount MCP server for AI assistant integration.
# This shares the same HTTP port as the JSON-RPC API (no extra port).
# AI clients connect to: http://<host>:<port>/v1/ai/mcp
try:
    mcp_app = None
    if _MCP_VERSION >= 2:
        # Use the singleton MCP HTTP app (same instance used by lifespan init)
        mcp_app = get_mcp_http_app()
    else:
        for method_name in ("streamable_http_app", "http_app", "sse_app"):
            if hasattr(mcp_server, method_name):
                mcp_app = getattr(mcp_server, method_name)()
                break
    if mcp_app is not None:
        if _MCP_VERSION >= 2:
            # MCP 2.x: use pure ASGI middleware to intercept /v1/ai/mcp
            # and forward to MCP app with path rewritten to /mcp
            _mcp_prefix = MCP_ENDPOINT.rstrip("/")  # "/v1/ai/mcp"

            class McpAsgiMiddleware:
                """Pure ASGI middleware to route /v1/ai/mcp to MCP app.

                Intercepts HTTP requests to MCP_ENDPOINT and forwards
                them to the MCP ASGI app with the path rewritten to
                /mcp (MCP 2.x internal route). Non-matching requests
                pass through to the main app. JWT auth is enforced
                when AUTH_MODE == 'jwt' before forwarding.
                """

                def __init__(self, main_app):
                    self.app = main_app

                async def __call__(self, scope, receive, send):
                    if scope["type"] == "http":
                        path = scope.get("path", "")
                        if path == _mcp_prefix or path.startswith(
                            _mcp_prefix + "/"
                        ):
                            # Reuse existing JWT auth when user management
                            # is enabled (AUTH_MODE == "jwt"). Requests
                            # without a valid Bearer token are rejected
                            # with HTTP 401 before reaching the MCP app.
                            # When AUTH_MODE is "no" or "virtual_instance",
                            # the MCP endpoint is accessible without JWT.
                            if not self._check_jwt(scope):
                                await self._send_unauthorized(send)
                                return
                            # Rewrite: /v1/ai/mcp -> /mcp,
                            # /v1/ai/mcp/ -> /mcp/
                            new_path = "/mcp" + path[len(_mcp_prefix) :]
                            scope["path"] = new_path
                            scope["raw_path"] = new_path.encode()
                            # Rewrite Host to localhost to bypass MCP 2.x
                            # transport_security Host validation
                            headers = scope.get("headers", [])
                            new_headers = [
                                (k, v)
                                for k, v in headers
                                if k.lower() != b"host"
                            ]
                            new_headers.append((b"host", b"localhost"))
                            scope["headers"] = new_headers
                            # Also rewrite ASGI server tuple (host, port)
                            # transport_security may check scope["server"]
                            orig_server = scope.get("server", ("", 0))
                            scope["server"] = ("localhost", orig_server[1])
                            await mcp_app(scope, receive, send)
                            return
                    await self.app(scope, receive, send)

                @staticmethod
                def _check_jwt(scope) -> bool:
                    """Validate JWT token from Authorization header.

                    Returns True when access is allowed (AUTH_MODE is not
                    'jwt', or a valid Bearer token is present), and False
                    when the request must be rejected with 401.
                    """
                    # Only enforce JWT when user management is enabled
                    if Config.DEFAULT.AUTH_MODE != Constant.AUTH_MODE_JWT:
                        return True
                    # Extract Authorization header from ASGI scope
                    headers = scope.get("headers", [])
                    auth_header = None
                    for key, value in headers:
                        if key.lower() == b"authorization":
                            auth_header = value.decode("latin-1")
                            break
                    if not auth_header:
                        logger.warning(
                            "MCP access denied: missing Authorization header"
                        )
                        return False
                    # Expect "Bearer <token>"
                    parts = auth_header.split(" ", 1)
                    if len(parts) != 2 or parts[0].lower() != "bearer":
                        logger.warning(
                            "MCP access denied: invalid Authorization scheme"
                        )
                        return False
                    token = parts[1].strip()
                    payload = decode_jwt_token(token)
                    if not payload:
                        logger.warning(
                            "MCP access denied: invalid or expired JWT token"
                        )
                        return False
                    return True

                @staticmethod
                async def _send_unauthorized(send) -> None:
                    """Send an HTTP 401 JSON error response."""
                    import json

                    body = json.dumps({
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32001,
                            "message": "Unauthorized: "
                            "valid JWT token required",
                        },
                        "id": None,
                    }).encode("utf-8")
                    await send({
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (
                                b"content-length",
                                str(len(body)).encode("latin-1"),
                            ),
                        ],
                    })
                    await send({"type": "http.response.body", "body": body})

            app.add_middleware(McpAsgiMiddleware)
            logger.info(f"MCP server middleware (v2.x) at {MCP_ENDPOINT}")
        else:
            # MCP 1.x: mount at /v1/ai/mcp prefix
            app.mount(MCP_ENDPOINT, mcp_app)
            logger.info(f"MCP server mounted (v1.x) at {MCP_ENDPOINT}")
    else:
        logger.warning("MCP server: no suitable HTTP app method found")
except Exception as e:
    logger.warning(f"Failed to mount MCP server: {e}")

# Mount reverse-proxy endpoints under /v1/proxy/<service> for each
# configured upstream (e.g. Prometheus, Alertmanager). Targets whose
# configured base URL is empty are skipped so an unset field simply
# disables the corresponding endpoint without breaking other routes.
for _target in PROXY_TARGETS:
    try:
        _base_url = _target.config_getter()
    except Exception as e:
        logger.warning(
            f"Reverse proxy '{_target.path_segment}': failed to resolve "
            f"upstream base URL: {e}"
        )
        continue
    if not _base_url:
        logger.info(
            f"Reverse proxy '{_target.path_segment}': "
            f"disabled (empty base URL)"
        )
        continue
    try:
        app.mount(
            f"{BASE_ENDPOINT}/proxy/{_target.path_segment}",
            ProxyJwtMiddleware(
                create_reverse_proxy_app(_target.path_segment, _base_url)
            ),
        )
        logger.info(
            f"Reverse proxy mounted at "
            f"{BASE_ENDPOINT}/proxy/{_target.path_segment} -> {_base_url}"
        )
    except Exception as e:
        logger.warning(
            f"Failed to mount reverse proxy '{_target.path_segment}': {e}"
        )

# NOTE: Terminal routes (WebSocket + file REST) are NOT registered here at
# module import time. Config.initialize() has not run yet when this module is
# first imported by ``wy_qcos.server``, so ``Config.TERMINAL.ENABLED`` would
# still be the Pydantic default (``False``) and the routes would never be
# mounted even when ``qcos.toml`` has ``ENABLED = true``. Instead, call
# :func:`register_terminal_routes` from ``Server.run()`` after
# ``Config.initialize()``.


def register_terminal_routes() -> None:
    """Register terminal WebSocket / file REST routes on the FastAPI app.

    Must be called after ``Config.initialize()`` so that
    ``Config.TERMINAL.ENABLED`` reflects the actual ``qcos.toml`` value
    instead of the Pydantic schema default (``False``).

    The function is idempotent: if the routes are already present it
    logs and returns without re-registering.
    """
    # Avoid double-registration on hot paths that may call this twice.
    existing = {getattr(r, "path", None) for r in app.routes}
    if "/v1/terminal/ws" in existing:
        logger.info("Terminal routes already registered, skipping")
        return

    _terminal_enabled_type = type(Config.TERMINAL.ENABLED).__name__
    logger.info(
        f"Terminal route registration check: TERMINAL.ENABLED="
        f"{Config.TERMINAL.ENABLED} (type={_terminal_enabled_type})"
    )
    if not Config.TERMINAL.ENABLED:
        logger.info("Terminal feature disabled (TERMINAL.ENABLED=false)")
        return

    try:
        app.include_router(terminal_ws_router)
        app.include_router(terminal_files_router)
        ws_paths = [
            str(getattr(r, "path", ""))
            for r in app.routes
            if "terminal" in str(getattr(r, "path", ""))
        ]
        logger.info(
            f"Terminal routes registered at /v1/terminal/ws and "
            f"/v1/terminal/files; current terminal paths: {ws_paths}"
        )
    except Exception:
        # Log full traceback so production deployments can see the real
        # import/registration failure (previously silently swallowed).
        logger.exception("Failed to register terminal routes")


# Monkey Patch uvicorn signal handler to detect the app is shutting down
app.state.exiting = False
app.state.timing = False


# Force include_signal_handlers=True to ensure SIGTERM is handled correctly
class QcosUvicornServer(UvicornServer):
    """QCOS Uvicorn Server."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Monkey-patch ``config.bind_socket`` with a retry-capable
        # closure so that a rapid container restart (where the previous
        # listener's sockets are still in TIME_WAIT) does not kill the
        # server on the first bind attempt. This affects both the
        # single-process path and the multi-worker supervisor path,
        # because uvicorn ultimately calls ``config.bind_socket()`` in
        # either case.
        cfg = self.config
        original_bind_socket = cfg.bind_socket

        def _bind_socket_with_retry():
            """Bind the server socket with retry and SO_REUSEPORT.

            Delegates to uvicorn's original ``bind_socket`` (which
            sets ``SO_REUSEADDR``) but retries on ``OSError`` for a
            few times to tolerate TIME_WAIT sockets left by a
            previous rapid restart.
            """
            last_exc = None
            for attempt in range(1, _BIND_MAX_RETRIES + 1):
                try:
                    sock = original_bind_socket()
                    logger.info(
                        f"Successfully bound to {cfg.host}:"
                        f"{cfg.port} on attempt "
                        f"{attempt}/{_BIND_MAX_RETRIES}"
                    )
                    # Additionally set SO_REUSEPORT so multiple worker
                    # processes can share the same port (Linux >= 3.9).
                    if hasattr(socket, "SO_REUSEPORT"):
                        try:
                            sock.setsockopt(
                                socket.SOL_SOCKET,
                                socket.SO_REUSEPORT,
                                1,
                            )
                        except OSError:
                            pass
                    return sock
                except SystemExit:
                    # uvicorn's original bind_socket calls sys.exit(1)
                    # on OSError; translate that into a retryable
                    # error instead of terminating the process.
                    last_exc = OSError(
                        f"bind_socket raised SystemExit on attempt "
                        f"{attempt}/{_BIND_MAX_RETRIES}"
                    )
                    logger.warning(
                        f"Bind attempt {attempt}/{_BIND_MAX_RETRIES} "
                        f"failed. Retrying in "
                        f"{_BIND_RETRY_INTERVAL}s..."
                    )
                    time.sleep(_BIND_RETRY_INTERVAL)

            logger.error(
                f"Failed to bind after {_BIND_MAX_RETRIES} attempts: "
                f"{last_exc}"
            )
            raise SystemExit(1)

        cfg.bind_socket = _bind_socket_with_retry
        logger.info("QcosUvicornServer initialized")

    def handle_exit(self, sig: int, frame) -> None:
        """Handle exit signal.

        Args:
            sig: signal
            frame: frame
        """
        logger.info(f"QcosUvicornServer received signal {sig}")
        app.state.exiting = True

        try:
            super().handle_exit(sig, frame)
        except Exception as e:
            logger.error(f"Error in QcosUvicornServer.handle_exit: {e}")
            raise
