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

"""Unit tests for routes_rest.reverse_proxy / proxy_auth / proxy_registry."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from wy_qcos.api.posiq.routes_rest.proxy_auth import ProxyJwtMiddleware
from wy_qcos.api.posiq.routes_rest.proxy_registry import PROXY_TARGETS
from wy_qcos.api.posiq.routes_rest.reverse_proxy import (
    _filter_request_headers,
    _filter_response_headers,
    create_reverse_proxy_app,
)
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _make_scope(
    method="GET",
    path="/api/v1/query",
    query_string=b"",
    headers=None,
    app=None,
):
    """Build a minimal ASGI HTTP scope."""
    return {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string,
        "headers": headers or [],
        "app": app,
    }


def _make_receive(body: bytes = b""):
    """Build an ASGI receive callable that returns the body once."""
    sent = {"done": False}

    async def receive():
        if not sent["done"]:
            sent["done"] = True
            return {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }
        return {"type": "http.disconnect"}

    return receive


class _SendRecorder:
    """Capture ASGI send messages for assertion."""

    def __init__(self):
        self.messages = []

    async def __call__(self, message):
        self.messages.append(message)

    @property
    def status(self):
        for m in self.messages:
            if m["type"] == "http.response.start":
                return m["status"]
        return None

    @property
    def response_headers(self):
        for m in self.messages:
            if m["type"] == "http.response.start":
                return m["headers"]
        return []

    @property
    def body(self) -> bytes:
        return b"".join(
            m.get("body", b"")
            for m in self.messages
            if m["type"] == "http.response.body"
        )


def _build_mock_client(handler):
    """Build an httpx.AsyncClient backed by a MockTransport."""
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        timeout=httpx.Timeout(5.0, read=5.0, write=5.0, pool=5.0),
    )


def _fake_app_with_client(client):
    """Return a stub FastAPI-like object exposing state.http_client."""
    return SimpleNamespace(state=SimpleNamespace(http_client=client))


# ----------------------------------------------------------------------
# Header filtering
# ----------------------------------------------------------------------


class TestFilterRequestHeaders:
    """Verify hop-by-hop and Host headers are stripped."""

    def test_strips_hop_by_hop_and_host(self):
        headers = [
            (b"host", b"example.com"),
            (b"connection", b"keep-alive"),
            (b"keep-alive", b"timeout=5"),
            (b"proxy-authorization", b"Basic abc"),
            (b"te", b"trailers"),
            (b"trailer", b"Expires"),
            (b"transfer-encoding", b"chunked"),
            (b"upgrade", b"h2c"),
            (b"authorization", b"Bearer token"),
            (b"content-type", b"application/json"),
            (b"x-custom", b"yes"),
        ]
        out = _filter_request_headers(headers)
        # Hop-by-hop + Host are removed
        assert "host" not in out
        assert "connection" not in out
        assert "keep-alive" not in out
        assert "proxy-authorization" not in out
        assert "te" not in out
        assert "trailer" not in out
        assert "transfer-encoding" not in out
        assert "upgrade" not in out
        # Business headers are kept
        assert out["authorization"] == "Bearer token"
        assert out["content-type"] == "application/json"
        assert out["x-custom"] == "yes"


class TestFilterResponseHeaders:
    """Verify response headers strip hop-by-hop and Content-Length."""

    def test_strips_content_length_and_hop_by_hop(self):
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", b"123"),
            (b"connection", b"close"),
            (b"transfer-encoding", b"chunked"),
        ]
        out = _filter_response_headers(headers)
        names = [n for n, _ in out]
        assert (b"content-type", b"application/json") in out
        assert b"content-length" not in names
        assert b"connection" not in names
        assert b"transfer-encoding" not in names

    def test_strips_content_encoding(self):
        """Content-Encoding must be stripped.

        httpx has already transparently decompressed the body. Forwarding
        the upstream ``Content-Encoding: gzip`` header would cause the
        browser to attempt gunzip on a plain JSON payload, resulting in
        ``NS_ERROR_INVALID_CONTENT_ENCODING`` (Firefox) or an empty
        response (Chrome).
        """
        headers = [
            (b"content-type", b"application/json"),
            (b"content-encoding", b"gzip"),
            (b"content-length", b"297"),
        ]
        out = _filter_response_headers(headers)
        names = [n for n, _ in out]
        assert (b"content-type", b"application/json") in out
        assert b"content-encoding" not in names
        assert b"content-length" not in names


# ----------------------------------------------------------------------
# Reverse proxy behavior
# ----------------------------------------------------------------------


class TestReverseProxyApp:
    """End-to-end tests for create_reverse_proxy_app."""

    @pytest.mark.asyncio
    async def test_get_path_and_query_passthrough(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["url"] = str(request.url)
            captured["path"] = request.url.path
            captured["query"] = request.url.query.decode()
            return httpx.Response(200, json={"status": "success"})

        client = _build_mock_client(handler)
        app = _fake_app_with_client(client)
        proxy = create_reverse_proxy_app("prometheus", "http://prom:9090")

        scope = _make_scope(
            method="GET",
            path="/api/v1/query",
            query_string=b"query=up&time=now",
            app=app,
        )
        recorder = _SendRecorder()
        await proxy(scope, _make_receive(), recorder)
        await client.aclose()

        assert captured["method"] == "GET"
        assert captured["path"] == "/api/v1/query"
        assert captured["query"] == "query=up&time=now"
        assert captured["url"].startswith("http://prom:9090/api/v1/query")
        assert recorder.status == 200
        assert json.loads(recorder.body) == {"status": "success"}

    @pytest.mark.asyncio
    async def test_post_body_passthrough(self):
        payload = b'{"matchers":[]}'

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            assert request.url.path == "/api/v2/silences"
            assert request.content == payload
            return httpx.Response(200, json={"silenceID": "abc"})

        client = _build_mock_client(handler)
        app = _fake_app_with_client(client)
        proxy = create_reverse_proxy_app("alertmanager", "http://alert:9093")

        scope = _make_scope(
            method="POST",
            path="/api/v2/silences",
            headers=[(b"content-type", b"application/json")],
            app=app,
        )
        recorder = _SendRecorder()
        await proxy(scope, _make_receive(payload), recorder)
        await client.aclose()

        assert recorder.status == 200
        assert json.loads(recorder.body) == {"silenceID": "abc"}

    @pytest.mark.asyncio
    async def test_custom_headers_passthrough_host_stripped(self):
        def handler(request: httpx.Request) -> httpx.Response:
            # Business headers should be forwarded
            assert request.headers.get("x-request-id") == "r-1"
            assert request.headers.get("authorization") == "Bearer abc"
            # Host is regenerated by httpx from the target URL
            assert request.headers.get("host") == "prom:9090"
            return httpx.Response(200, text="ok")

        client = _build_mock_client(handler)
        app = _fake_app_with_client(client)
        proxy = create_reverse_proxy_app("prometheus", "http://prom:9090")

        scope = _make_scope(
            headers=[
                (b"host", b"qcos.local:18400"),
                (b"connection", b"keep-alive"),
                (b"x-request-id", b"r-1"),
                (b"authorization", b"Bearer abc"),
            ],
            app=app,
        )
        recorder = _SendRecorder()
        await proxy(scope, _make_receive(), recorder)
        await client.aclose()
        assert recorder.status == 200

    @pytest.mark.asyncio
    async def test_upstream_4xx_status_passthrough(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                400,
                json={"status": "error", "error": "bad query"},
            )

        client = _build_mock_client(handler)
        app = _fake_app_with_client(client)
        proxy = create_reverse_proxy_app("prometheus", "http://prom:9090")

        recorder = _SendRecorder()
        await proxy(_make_scope(app=app), _make_receive(), recorder)
        await client.aclose()

        assert recorder.status == 400
        assert json.loads(recorder.body)["error"] == "bad query"

    @pytest.mark.asyncio
    async def test_upstream_5xx_status_passthrough(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="prometheus unavailable")

        client = _build_mock_client(handler)
        app = _fake_app_with_client(client)
        proxy = create_reverse_proxy_app("prometheus", "http://prom:9090")

        recorder = _SendRecorder()
        await proxy(_make_scope(app=app), _make_receive(), recorder)
        await client.aclose()

        assert recorder.status == 503
        assert recorder.body == b"prometheus unavailable"

    @pytest.mark.asyncio
    async def test_upstream_connect_error_returns_502(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        client = _build_mock_client(handler)
        app = _fake_app_with_client(client)
        proxy = create_reverse_proxy_app("prometheus", "http://prom:9090")

        recorder = _SendRecorder()
        await proxy(_make_scope(app=app), _make_receive(), recorder)
        await client.aclose()

        assert recorder.status == 502
        body = json.loads(recorder.body)
        assert "Bad gateway" in body["detail"]

    @pytest.mark.asyncio
    async def test_upstream_timeout_returns_504(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("read timed out")

        client = _build_mock_client(handler)
        app = _fake_app_with_client(client)
        proxy = create_reverse_proxy_app("prometheus", "http://prom:9090")

        recorder = _SendRecorder()
        await proxy(_make_scope(app=app), _make_receive(), recorder)
        await client.aclose()

        assert recorder.status == 504
        body = json.loads(recorder.body)
        assert "Gateway timeout" in body["detail"]

    @pytest.mark.asyncio
    async def test_trailing_slash_on_base_url(self):
        """Base URL trailing slash is normalized."""
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            return httpx.Response(200, text="ok")

        client = _build_mock_client(handler)
        app = _fake_app_with_client(client)
        proxy = create_reverse_proxy_app("prometheus", "http://prom:9090/")

        recorder = _SendRecorder()
        await proxy(_make_scope(app=app), _make_receive(), recorder)
        await client.aclose()

        # No double slash
        assert captured["url"].startswith("http://prom:9090/api/v1/query")
        assert "//api" not in captured["url"]

    @pytest.mark.asyncio
    async def test_mounted_path_strips_root_path_prefix(self):
        """Regression test for the Starlette app.mount() behavior.

        Starlette's Mount sets scope["root_path"] to the mount prefix
        (e.g. "/v1/proxy/prometheus") while keeping scope["path"] as the
        FULL original path. The proxy must strip the root_path prefix,
        otherwise the upstream URL would become
        "<base>/v1/proxy/prometheus/api/v1/query" and return 404.
        """
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["path"] = request.url.path
            return httpx.Response(200, json={"status": "success"})

        client = _build_mock_client(handler)
        app = _fake_app_with_client(client)
        proxy = create_reverse_proxy_app("prometheus", "http://prom:9090")

        # Simulate what Starlette's Mount produces when the client
        # requests "/v1/proxy/prometheus/api/v1/query":
        #   scope["path"]      = "/v1/proxy/prometheus/api/v1/query"
        #   scope["root_path"] = "/v1/proxy/prometheus"
        scope = _make_scope(
            method="GET",
            path="/v1/proxy/prometheus/api/v1/query",
            query_string=b"query=up",
            app=app,
        )
        scope["root_path"] = "/v1/proxy/prometheus"

        recorder = _SendRecorder()
        await proxy(scope, _make_receive(), recorder)
        await client.aclose()

        # The upstream URL must NOT contain the mount prefix.
        assert captured["path"] == "/api/v1/query"
        assert captured["url"].startswith("http://prom:9090/api/v1/query")
        assert "/v1/proxy/prometheus" not in captured["url"]
        assert recorder.status == 200

    @pytest.mark.asyncio
    async def test_mounted_root_path_only_produces_upstream_root(self):
        """Mount-point root requests must hit the upstream root.

        When the client requests exactly the mount prefix (e.g.
        "/v1/proxy/prometheus"), the stripped path becomes "" and
        must be normalised to "/" so the upstream URL is "<base>/".
        """
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            return httpx.Response(200, text="ok")

        client = _build_mock_client(handler)
        app = _fake_app_with_client(client)
        proxy = create_reverse_proxy_app("prometheus", "http://prom:9090")

        scope = _make_scope(
            method="GET",
            path="/v1/proxy/prometheus",
            app=app,
        )
        scope["root_path"] = "/v1/proxy/prometheus"

        recorder = _SendRecorder()
        await proxy(scope, _make_receive(), recorder)
        await client.aclose()

        assert captured["url"] in ("http://prom:9090/", "http://prom:9090")
        assert recorder.status == 200


# ----------------------------------------------------------------------
# JWT middleware
# ----------------------------------------------------------------------


def _ok_asgi_app():
    async def app(scope, receive, send):
        body = b"ok"
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-length", b"2")],
        })
        await send({"type": "http.response.body", "body": body})

    return app


class TestProxyJwtMiddleware:
    """Verify ProxyJwtMiddleware follows global AUTH_MODE."""

    @pytest.mark.asyncio
    async def test_auth_mode_no_passes_without_token(self):
        with patch.object(Config.DEFAULT, "AUTH_MODE", Constant.AUTH_MODE_NO):
            middleware = ProxyJwtMiddleware(_ok_asgi_app())
            recorder = _SendRecorder()
            await middleware(_make_scope(), _make_receive(), recorder)
            assert recorder.status == 200

    @pytest.mark.asyncio
    async def test_auth_mode_virtual_instance_passes_without_token(self):
        with patch.object(
            Config.DEFAULT, "AUTH_MODE", Constant.AUTH_MODE_VIRTUAL_INSTANCE
        ):
            middleware = ProxyJwtMiddleware(_ok_asgi_app())
            recorder = _SendRecorder()
            await middleware(_make_scope(), _make_receive(), recorder)
            assert recorder.status == 200

    @pytest.mark.asyncio
    async def test_auth_mode_jwt_missing_token_returns_401(self):
        with patch.object(Config.DEFAULT, "AUTH_MODE", Constant.AUTH_MODE_JWT):
            middleware = ProxyJwtMiddleware(_ok_asgi_app())
            recorder = _SendRecorder()
            await middleware(_make_scope(), _make_receive(), recorder)
            assert recorder.status == 401
            body = json.loads(recorder.body)
            assert body["error"]["code"] == -32001

    @pytest.mark.asyncio
    async def test_auth_mode_jwt_invalid_scheme_returns_401(self):
        with patch.object(Config.DEFAULT, "AUTH_MODE", Constant.AUTH_MODE_JWT):
            middleware = ProxyJwtMiddleware(_ok_asgi_app())
            scope = _make_scope(headers=[(b"authorization", b"Basic abc123")])
            recorder = _SendRecorder()
            await middleware(scope, _make_receive(), recorder)
            assert recorder.status == 401

    @pytest.mark.asyncio
    async def test_auth_mode_jwt_invalid_token_returns_401(self):
        with (
            patch.object(Config.DEFAULT, "AUTH_MODE", Constant.AUTH_MODE_JWT),
            patch(
                "wy_qcos.api.posiq.routes_rest.proxy_auth.decode_jwt_token",
                return_value=None,
            ),
        ):
            middleware = ProxyJwtMiddleware(_ok_asgi_app())
            scope = _make_scope(
                headers=[(b"authorization", b"Bearer bad-token")]
            )
            recorder = _SendRecorder()
            await middleware(scope, _make_receive(), recorder)
            assert recorder.status == 401

    @pytest.mark.asyncio
    async def test_auth_mode_jwt_valid_token_passes(self):
        with (
            patch.object(Config.DEFAULT, "AUTH_MODE", Constant.AUTH_MODE_JWT),
            patch(
                "wy_qcos.api.posiq.routes_rest.proxy_auth.decode_jwt_token",
                return_value={"sub": "user1"},
            ),
        ):
            middleware = ProxyJwtMiddleware(_ok_asgi_app())
            scope = _make_scope(
                headers=[(b"authorization", b"Bearer good-token")]
            )
            recorder = _SendRecorder()
            await middleware(scope, _make_receive(), recorder)
            assert recorder.status == 200
            assert recorder.body == b"ok"


# ----------------------------------------------------------------------
# Registry
# ----------------------------------------------------------------------


class TestProxyRegistry:
    """Verify PROXY_TARGETS registry shape."""

    def test_registry_contains_prometheus_and_alertmanager(self):
        names = {t.path_segment for t in PROXY_TARGETS}
        assert "prometheus" in names
        assert "alertmanager" in names

    def test_getter_returns_string(self):
        for t in PROXY_TARGETS:
            value = t.config_getter()
            assert isinstance(value, str), (
                f"{t.path_segment} getter must return str"
            )

    def test_getter_respects_config_override(self):
        with patch.object(
            Config.PROXY, "PROMETHEUS_BASE_URL", "http://prom:19090"
        ):
            for t in PROXY_TARGETS:
                if t.path_segment == "prometheus":
                    assert t.config_getter() == "http://prom:19090"

    def test_health_path_present(self):
        for t in PROXY_TARGETS:
            assert isinstance(t.health_path, str)
            assert t.health_path.startswith("/")
