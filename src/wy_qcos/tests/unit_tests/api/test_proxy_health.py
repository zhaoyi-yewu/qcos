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

"""Unit tests for the get_proxy_health JSON-RPC method."""

import dataclasses
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from wy_qcos.api.posiq.routes_jsonrpc.proxy import _probe_one, get_proxy_health
from wy_qcos.api.posiq.routes_rest.proxy_registry import (
    PROXY_TARGETS,
    ProxyTarget,
)


def _make_request(client):
    """Build a minimal FastAPI Request stub exposing app.state.http_client."""
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(http_client=client))
    )


class TestProbeOne:
    """Unit tests for the _probe_one helper."""

    @pytest.mark.asyncio
    async def test_healthy_returns_true_with_latency(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/-/healthy"
            return httpx.Response(200, text="OK")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            healthy, latency, detail = await _probe_one(
                client, "http://prom:9090", "/-/healthy"
            )
            assert healthy is True
            assert latency is not None and latency >= 0
            assert detail == ""
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_5xx_is_offline_with_status_detail(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="not ready")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            healthy, latency, detail = await _probe_one(
                client, "http://prom:9090", "/-/healthy"
            )
            assert healthy is False
            assert latency is not None
            assert "503" in detail
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_timeout_returns_offline(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("read timed out")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            healthy, latency, detail = await _probe_one(
                client, "http://prom:9090", "/-/healthy"
            )
            assert healthy is False
            assert latency is None
            assert "timeout" in detail.lower()
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_connect_error_returns_offline(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            healthy, latency, detail = await _probe_one(
                client, "http://prom:9090", "/-/healthy"
            )
            assert healthy is False
            assert latency is None
            assert "connect error" in detail.lower()
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_trailing_slash_on_base_url_normalized(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            return httpx.Response(200)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            await _probe_one(client, "http://prom:9090/", "/-/healthy")
            assert captured["url"] == "http://prom:9090/-/healthy"
        finally:
            await client.aclose()


class TestGetProxyHealth:
    """End-to-end tests for the get_proxy_health RPC method."""

    @pytest.mark.asyncio
    async def test_all_healthy(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="OK")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            request = _make_request(client)
            response = await get_proxy_health(request=request, body=None)
            assert len(response.targets) == len(PROXY_TARGETS)
            for item in response.targets:
                assert item.enabled is True
                assert item.healthy is True
                assert item.status == "online"
                assert item.latency_ms is not None
                assert item.detail == ""
                assert item.path.endswith(item.name)
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_one_offline_one_online(self):
        def handler(request: httpx.Request) -> httpx.Response:
            # alertmanager health probe fails, prometheus succeeds
            if "9093" in str(request.url):
                raise httpx.ConnectError("connection refused")
            return httpx.Response(200, text="OK")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            request = _make_request(client)
            response = await get_proxy_health(request=request, body=None)
            by_name = {t.name: t for t in response.targets}
            assert by_name["prometheus"].healthy is True
            assert by_name["alertmanager"].healthy is False
            assert by_name["alertmanager"].status == "offline"
            assert "connect error" in by_name["alertmanager"].detail
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_disabled_when_base_url_empty(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            request = _make_request(client)
            # Disable alertmanager by replacing its registry entry with
            # one whose config_getter returns "". ProxyTarget is frozen,
            # so we patch the PROXY_TARGETS list itself.
            replaced = [
                PROXY_TARGETS[0],
                ProxyTarget(
                    path_segment="alertmanager",
                    config_getter=lambda: "",
                    health_path="/-/healthy",
                ),
            ]
            with patch(
                "wy_qcos.api.posiq.routes_jsonrpc.proxy.PROXY_TARGETS",
                replaced,
            ):
                response = await get_proxy_health(request=request, body=None)
            by_name = {t.name: t for t in response.targets}
            assert by_name["prometheus"].status == "online"
            assert by_name["alertmanager"].status == "disabled"
            assert by_name["alertmanager"].enabled is False
            assert by_name["alertmanager"].healthy is False
            assert "not configured" in by_name["alertmanager"].detail
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_config_getter_raises_marks_disabled(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            request = _make_request(client)

            def _boom():
                raise RuntimeError("no config")

            replaced = [
                ProxyTarget(
                    path_segment="prometheus",
                    config_getter=_boom,
                    health_path="/-/healthy",
                ),
                PROXY_TARGETS[1],
            ]
            with patch(
                "wy_qcos.api.posiq.routes_jsonrpc.proxy.PROXY_TARGETS",
                replaced,
            ):
                response = await get_proxy_health(request=request, body=None)
            by_name = {t.name: t for t in response.targets}
            assert by_name["prometheus"].status == "disabled"
            assert "config error" in by_name["prometheus"].detail
        finally:
            await client.aclose()

    @pytest.mark.asyncio
    async def test_falls_back_to_own_client_when_state_missing(self):
        """When app.state.http_client is None, the RPC builds a temp client."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        # Force httpx.AsyncClient to route through our MockTransport so
        # no real network is used even when the fallback path runs.
        original_init = httpx.AsyncClient.__init__

        def patched_init(self, *args, **kwargs):
            kwargs.setdefault("transport", httpx.MockTransport(handler))
            original_init(self, *args, **kwargs)

        request = _make_request(client=None)
        with patch.object(httpx.AsyncClient, "__init__", patched_init):
            response = await get_proxy_health(request=request, body=None)
        assert all(t.healthy for t in response.targets)


class TestProxyTargetDataclass:
    """Sanity checks on the ProxyTarget dataclass."""

    def test_frozen(self):
        t = PROXY_TARGETS[0]
        with pytest.raises(dataclasses.FrozenInstanceError):
            t.path_segment = "mutated"

    def test_fields(self):
        t = ProxyTarget(
            path_segment="x",
            config_getter=lambda: "http://x",
            health_path="/h",
        )
        assert t.path_segment == "x"
        assert t.config_getter() == "http://x"
        assert t.health_path == "/h"
