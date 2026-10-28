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

"""JSON-RPC routes for reverse-proxy upstream health checks.

The :func:`get_proxy_health` method probes every registered entry in
:data:`wy_qcos.api.posiq.routes_rest.proxy_registry.PROXY_TARGETS` and
returns a per-target status snapshot so WebUI can render which
upstream services (Prometheus, Alertmanager, ...) are reachable.
"""

import logging
import time

import httpx
from fastapi import Depends, Request

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import (
    BASE_ENDPOINT,
    metrics_api_v1,
)
from wy_qcos.api.posiq.routes_rest.proxy_registry import PROXY_TARGETS
from wy_qcos.common.constant import Constant

from .dependencies.authentication import auth

logger = logging.getLogger(__name__)
module_name = "PROXY"

# Health-probe timeout (seconds). Kept short on purpose: this RPC is
# polled by WebUI on a timer and must fail fast when an upstream is
# unreachable.
_PROBE_TIMEOUT = httpx.Timeout(connect=2.0, read=3.0, write=2.0, pool=1.0)


async def _probe_one(
    client: httpx.AsyncClient,
    base_url: str,
    health_path: str,
) -> tuple[bool, int | None, str]:
    """Probe a single upstream health endpoint.

    Args:
        client: Shared httpx AsyncClient.
        base_url: Upstream base URL, e.g. ``http://127.0.0.1:9090``.
        health_path: Lightweight probe path, e.g. ``/-/healthy``.

    Returns:
        ``(healthy, latency_ms, detail)`` tuple. ``latency_ms`` is
        ``None`` when the probe failed; ``detail`` carries a short
        human-readable reason when ``healthy`` is False.
    """
    url = f"{base_url.rstrip('/')}{health_path}"
    started = time.monotonic()
    try:
        resp = await client.get(url, timeout=_PROBE_TIMEOUT)
        latency_ms = int((time.monotonic() - started) * 1000)
        # Treat any 2xx as healthy. 3xx/4xx/5xx indicate the upstream
        # is reachable but misbehaving; classify as offline so WebUI
        # can surface the issue.
        if 200 <= resp.status_code < 300:
            return True, latency_ms, ""
        return False, latency_ms, f"upstream returned {resp.status_code}"
    except httpx.TimeoutException as e:
        return False, None, f"timeout: {type(e).__name__}"
    except httpx.TransportError as e:
        return False, None, f"connect error: {e}"
    except Exception as e:  # pragma: no cover - defensive
        return False, None, f"unexpected: {type(e).__name__}: {e}"


@metrics_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
)
async def get_proxy_health(
    request: Request,
    body: schemas.GetProxyHealthRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetProxyHealthResponse:
    """Get health status for all reverse-proxy upstream services.

    Each registered proxy target (see
    :data:`PROXY_TARGETS`) is probed at its configured ``health_path``.
    Targets with an empty ``base_url`` are reported as ``disabled``.

    Args:
        request: FastAPI request (used to access the shared http client
            on ``app.state.http_client``).
        body: Get proxy health request (empty)
        auth_data: Authentication data

    Returns:
        Get proxy health response with per-target status entries.
    """
    func_name = "get_proxy_health"
    logger.info(f"Call {func_name}")

    try:
        client = getattr(request.app.state, "http_client", None)
        own_client: httpx.AsyncClient | None = None
        if client is None:
            own_client = httpx.AsyncClient(follow_redirects=False)
            client = own_client

        try:
            items: list[schemas.ProxyHealthItem] = []
            for target in PROXY_TARGETS:
                try:
                    base_url = target.config_getter()
                except Exception as e:
                    items.append(
                        schemas.ProxyHealthItem(
                            name=target.path_segment,
                            path=(
                                f"{BASE_ENDPOINT}/proxy/{target.path_segment}"
                            ),
                            base_url="",
                            enabled=False,
                            healthy=False,
                            status="disabled",
                            latency_ms=None,
                            detail=f"config error: {e}",
                        )
                    )
                    continue

                mount_path = f"{BASE_ENDPOINT}/proxy/{target.path_segment}"
                if not base_url:
                    items.append(
                        schemas.ProxyHealthItem(
                            name=target.path_segment,
                            path=mount_path,
                            base_url="",
                            enabled=False,
                            healthy=False,
                            status="disabled",
                            latency_ms=None,
                            detail="base_url not configured",
                        )
                    )
                    continue

                healthy, latency_ms, detail = await _probe_one(
                    client, base_url, target.health_path
                )
                items.append(
                    schemas.ProxyHealthItem(
                        name=target.path_segment,
                        path=mount_path,
                        base_url=base_url,
                        enabled=True,
                        healthy=healthy,
                        status="online" if healthy else "offline",
                        latency_ms=latency_ms,
                        detail=detail,
                    )
                )
        finally:
            if own_client is not None:
                await own_client.aclose()

        return schemas.GetProxyHealthResponse(targets=items)
    except Exception as e:
        logger.error(f"Failed to get proxy health: {e}")
        return jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
