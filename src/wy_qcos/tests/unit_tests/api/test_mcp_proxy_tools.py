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
#     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
#     MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Unit tests for the reverse-proxy MCP tools registered on mcp_server.

These tools proxy HTTP requests to upstream observability services
(Prometheus / Alertmanager / VictoriaLogs) mounted under
``/v1/proxy/<name>`` on the same FastAPI process. Tests mock the
underlying ``httpx.AsyncClient.get`` and ``_jsonrpc_call`` to verify
parameter plumbing, response shaping, and error propagation.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from wy_qcos.api.mcp.mcp_server import (
    _proxy_get,
    qcos_proxy_get_health,
    qcos_proxy_list_alerts,
    qcos_proxy_list_metric_names,
    qcos_proxy_list_silences,
    qcos_proxy_log_tail,
    qcos_proxy_query_logs,
    qcos_proxy_query_metrics,
    qcos_proxy_query_metrics_range,
)


def _make_response(
    status_code: int = 200,
    json_body: dict | None = None,
    text_body: str = "",
    content_type: str = "application/json",
) -> MagicMock:
    """Build a mock httpx.Response-like object."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.headers = {"content-type": content_type}
    resp.text = text_body if text_body else json.dumps(json_body or {})
    resp.json = MagicMock(return_value=json_body or {})
    return resp


class TestProxyGet:
    """Direct tests for the low-level ``_proxy_get`` helper."""

    @pytest.mark.asyncio
    async def test_get_json_success(self):
        mock_resp = _make_response(json_body={"status": "success"})
        with patch(
            "wy_qcos.api.mcp.mcp_server.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            result = await _proxy_get(
                "prometheus", "/api/v1/query", {"query": "up"}
            )
        assert result == {"status": "success"}
        call_args = mock_client.get.call_args
        assert "/v1/proxy/prometheus/api/v1/query" in call_args.args[0]
        assert call_args.kwargs["params"] == {"query": "up"}

    @pytest.mark.asyncio
    async def test_get_text_passthrough_when_not_json(self):
        mock_resp = _make_response(
            json_body={},
            text_body="metric_a 1\nmetric_b 0\n",
            content_type="text/plain; charset=utf-8",
        )
        with patch(
            "wy_qcos.api.mcp.mcp_server.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            result = await _proxy_get("victorialogs", "/select/logsql/query")
        assert result == "metric_a 1\nmetric_b 0\n"

    @pytest.mark.asyncio
    async def test_get_4xx_raises_runtime_error(self):
        mock_resp = _make_response(status_code=404, text_body="not found")
        with patch(
            "wy_qcos.api.mcp.mcp_server.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            with pytest.raises(RuntimeError, match="HTTP 404"):
                await _proxy_get("prometheus", "/api/v1/query")

    @pytest.mark.asyncio
    async def test_get_network_error_raises_runtime_error(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(
                side_effect=httpx.ConnectError("connection refused")
            )
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            with pytest.raises(
                RuntimeError, match="Failed to reach proxy upstream"
            ):
                await _proxy_get("prometheus", "/api/v1/query")


class TestProxyHealth:
    """Tests for qcos_proxy_get_health."""

    @pytest.mark.asyncio
    async def test_returns_targets_json(self):
        fake = {
            "targets": [
                {
                    "name": "prometheus",
                    "status": "online",
                    "enabled": True,
                    "healthy": True,
                    "latency_ms": 1,
                    "base_url": "http://127.0.0.1:9090",
                    "path": "/v1/proxy/prometheus",
                    "detail": "",
                }
            ]
        }
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
            return_value=fake,
        ) as mock_call:
            result = await qcos_proxy_get_health()
        data = json.loads(result)
        assert data == fake
        mock_call.assert_awaited_once_with(
            "/v1/metrics", "get_proxy_health", None
        )


class TestProxyMetrics:
    """Tests for Prometheus-related proxy tools."""

    @pytest.mark.asyncio
    async def test_query_metrics_basic(self):
        fake = {"status": "success", "data": {"resultType": "vector"}}
        with patch(
            "wy_qcos.api.mcp.mcp_server._proxy_get",
            new_callable=AsyncMock,
            return_value=fake,
        ) as mock_get:
            result = await qcos_proxy_query_metrics(query="up")
        data = json.loads(result)
        assert data == fake
        mock_get.assert_awaited_once_with(
            "prometheus", "/api/v1/query", {"query": "up"}
        )

    @pytest.mark.asyncio
    async def test_query_metrics_with_optional_params(self):
        fake = {"status": "success"}
        with patch(
            "wy_qcos.api.mcp.mcp_server._proxy_get",
            new_callable=AsyncMock,
            return_value=fake,
        ) as mock_get:
            await qcos_proxy_query_metrics(
                query="up", time="2026-01-01T00:00:00Z", timeout="30s"
            )
        mock_get.assert_awaited_once_with(
            "prometheus",
            "/api/v1/query",
            {"query": "up", "time": "2026-01-01T00:00:00Z", "timeout": "30s"},
        )

    @pytest.mark.asyncio
    async def test_query_metrics_range(self):
        fake = {"status": "success", "data": {"resultType": "matrix"}}
        with patch(
            "wy_qcos.api.mcp.mcp_server._proxy_get",
            new_callable=AsyncMock,
            return_value=fake,
        ) as mock_get:
            result = await qcos_proxy_query_metrics_range(
                query="rate(x[5m])",
                start="2026-01-01T00:00:00Z",
                end="2026-01-01T01:00:00Z",
                step="1m",
            )
        data = json.loads(result)
        assert data == fake
        mock_get.assert_awaited_once_with(
            "prometheus",
            "/api/v1/query_range",
            {
                "query": "rate(x[5m])",
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-01-01T01:00:00Z",
                "step": "1m",
            },
            timeout=60.0,
        )

    @pytest.mark.asyncio
    async def test_list_metric_names(self):
        fake = {"status": "success", "data": ["up", "http_requests_total"]}
        with patch(
            "wy_qcos.api.mcp.mcp_server._proxy_get",
            new_callable=AsyncMock,
            return_value=fake,
        ) as mock_get:
            result = await qcos_proxy_list_metric_names()
        data = json.loads(result)
        assert data == fake
        mock_get.assert_awaited_once_with(
            "prometheus", "/api/v1/label/__name__/values"
        )


class TestProxyAlerts:
    """Tests for Alertmanager-related proxy tools."""

    @pytest.mark.asyncio
    async def test_list_alerts_no_filter(self):
        fake = [{"labels": {"alertname": "HighCpu"}}]
        with patch(
            "wy_qcos.api.mcp.mcp_server._proxy_get",
            new_callable=AsyncMock,
            return_value=fake,
        ) as mock_get:
            result = await qcos_proxy_list_alerts()
        data = json.loads(result)
        assert data == fake
        mock_get.assert_awaited_once_with("alertmanager", "/api/v2/alerts", {})

    @pytest.mark.asyncio
    async def test_list_alerts_with_filters(self) -> None:
        fake: list = []
        with patch(
            "wy_qcos.api.mcp.mcp_server._proxy_get",
            new_callable=AsyncMock,
            return_value=fake,
        ) as mock_get:
            await qcos_proxy_list_alerts(
                status="firing", silenced=False, inhibited=False
            )
        mock_get.assert_awaited_once_with(
            "alertmanager",
            "/api/v2/alerts",
            {
                "filter": 'status="firing"',
                "silenced": "false",
                "inhibited": "false",
            },
        )

    @pytest.mark.asyncio
    async def test_list_silences(self):
        fake = [{"id": "abc", "matchers": []}]
        with patch(
            "wy_qcos.api.mcp.mcp_server._proxy_get",
            new_callable=AsyncMock,
            return_value=fake,
        ) as mock_get:
            result = await qcos_proxy_list_silences()
        data = json.loads(result)
        assert data == fake
        mock_get.assert_awaited_once_with("alertmanager", "/api/v2/silences")


class TestProxyLogs:
    """Tests for VictoriaLogs-related proxy tools."""

    @pytest.mark.asyncio
    async def test_query_logs_returns_json_when_dict(self):
        fake = [{"_msg": "hello", "_time": "2026-01-01T00:00:00Z"}]
        with patch(
            "wy_qcos.api.mcp.mcp_server._proxy_get",
            new_callable=AsyncMock,
            return_value=fake,
        ) as mock_get:
            result = await qcos_proxy_query_logs(query="_time:1h", limit=50)
        data = json.loads(result)
        assert data == fake
        mock_get.assert_awaited_once_with(
            "victorialogs",
            "/select/logsql/query",
            {"query": "_time:1h", "limit": 50},
            timeout=60.0,
        )

    @pytest.mark.asyncio
    async def test_query_logs_passthrough_when_string(self):
        ndjson = '{"_msg":"a"}\n{"_msg":"b"}\n'
        with patch(
            "wy_qcos.api.mcp.mcp_server._proxy_get",
            new_callable=AsyncMock,
            return_value=ndjson,
        ):
            result = await qcos_proxy_query_logs(query="error")
        assert result == ndjson

    @pytest.mark.asyncio
    async def test_log_tail_caps_lines(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._proxy_get",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_get:
            await qcos_proxy_log_tail(lines=99999)
        # 99999 should be clamped to 1000
        call_kwargs = mock_get.await_args
        assert call_kwargs.args[2]["limit"] == 1000

    @pytest.mark.asyncio
    async def test_log_tail_minimum_one(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._proxy_get",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_get:
            await qcos_proxy_log_tail(lines=0)
        call_kwargs = mock_get.await_args
        assert call_kwargs.args[2]["limit"] == 1

    @pytest.mark.asyncio
    async def test_log_tail_default_100(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._proxy_get",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_get:
            await qcos_proxy_log_tail()
        call_kwargs = mock_get.await_args
        assert call_kwargs.args[2]["limit"] == 100
