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

import asyncio
import json
from unittest.mock import (
    AsyncMock,
    MagicMock,
    call,
    patch,
)

import pytest
from fastapi import Response

from wy_qcos.common.constant import HttpCode
from wy_qcos.metrics import metrics_collector
from wy_qcos.metrics.metrics_middleware import MetricsMiddleware


def create_mock_request(path: str, body: bytes = b"", method: str = "POST"):
    request = MagicMock()
    request.url.path = path
    request.method = method
    request._receive = None
    request.body = AsyncMock(return_value=body)
    return request


@pytest.mark.asyncio
class TestMetricsMiddleware:
    async def test_dispatch_excluded_path(self):
        middleware = MetricsMiddleware(app=MagicMock())
        request = create_mock_request("/metrics")
        call_next = AsyncMock(return_value=Response(status_code=200))

        with patch.object(middleware, "_normalize_endpoint") as mock_normalize:
            response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        call_next.assert_awaited_once_with(request)
        mock_normalize.assert_not_called()

    async def test_dispatch_success(self):
        middleware = MetricsMiddleware(app=MagicMock())
        path = "/v1/driver/123"
        body = json.dumps({"method": "getDriver"}).encode()
        request = create_mock_request(path, body)
        call_next = AsyncMock(return_value=Response(status_code=200))

        # only mock need methods
        with patch.object(
            metrics_collector, "record_api_requests_in_progress"
        ) as mock_record_in_progress:
            with patch.object(
                metrics_collector, "record_api_request"
            ) as mock_record_request:
                with patch.object(
                    middleware,
                    "_normalize_endpoint",
                    return_value="/v1/driver/{id}",
                ):
                    with patch.object(
                        middleware, "_extract_module", return_value="driver"
                    ):
                        with patch.object(
                            middleware,
                            "_extract_rpc_method",
                            return_value="getDriver",
                        ):
                            response = await middleware.dispatch(
                                request, call_next
                            )

        assert response.status_code == 200
        call_next.assert_awaited_once()

        expected_calls = [call(is_increment=True), call(is_increment=False)]
        mock_record_in_progress.assert_has_calls(expected_calls)
        mock_record_request.assert_called_once()

        _, kwargs = mock_record_request.call_args
        data = kwargs["data"]
        assert data.module == "driver"
        assert data.method == "getDriver"
        assert data.endpoint == "/v1/driver/{id}"
        assert data.status_code == 200
        assert data.duration > 0

    async def test_dispatch_exception(self):
        middleware = MetricsMiddleware(app=MagicMock())
        path = "/v1/device"
        body = b"{}"
        request = create_mock_request(path, body)
        call_next = AsyncMock(side_effect=ValueError("test error"))

        with patch.object(
            metrics_collector, "record_api_requests_in_progress"
        ) as mock_record_in_progress:
            with patch.object(
                metrics_collector, "record_api_request"
            ) as mock_record_request:
                with patch.object(
                    middleware,
                    "_normalize_endpoint",
                    return_value="/v1/device",
                ):
                    with patch.object(
                        middleware, "_extract_module", return_value="device"
                    ):
                        with patch.object(
                            middleware,
                            "_extract_rpc_method",
                            return_value="unknown",
                        ):
                            with pytest.raises(ValueError):
                                await middleware.dispatch(request, call_next)

        expected_calls = [call(is_increment=True), call(is_increment=False)]
        mock_record_in_progress.assert_has_calls(expected_calls)
        mock_record_request.assert_called_once()
        _, kwargs = mock_record_request.call_args
        data = kwargs["data"]
        assert data.status_code == HttpCode.INTERNAL_SERVER_ERROR

    def test_normalize_endpoint(self):
        middleware = MetricsMiddleware(app=MagicMock())
        assert middleware._normalize_endpoint("/v1/driver") == "/v1/driver"
        assert (
            middleware._normalize_endpoint("/v1/driver/123")
            == "/v1/driver/{id}"
        )
        assert (
            middleware._normalize_endpoint("/v1/driver/123/status")
            == "/v1/driver/{id}/status"
        )
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = middleware._normalize_endpoint(f"/v1/device/{uuid}")
        assert result.startswith("/v1/device/{id}")
        hex_id = "507f1f77bcf86cd799439011"
        result = middleware._normalize_endpoint(f"/v1/job/{hex_id}")
        assert result.startswith("/v1/job/{id}")
        path = "/v1/driver/123/device/456"
        assert (
            middleware._normalize_endpoint(path)
            == "/v1/driver/{id}/device/{id}"
        )
        assert (
            middleware._normalize_endpoint("/v1/driver?name=test")
            == "/v1/driver"
        )
        assert middleware._normalize_endpoint("") == ""

    def test_extract_module(self):
        middleware = MetricsMiddleware(app=MagicMock())
        assert middleware._extract_module("/v1/driver") == "driver"
        assert middleware._extract_module("/v1/driver/123") == "driver"
        assert middleware._extract_module("/v2/device/info") == "device"
        assert middleware._extract_module("/v1/unknown/path") == "path"
        assert middleware._extract_module("") == "root"
        assert middleware._extract_module("/") == "root"
        assert middleware._extract_module("/v1/system/status") == "system"

    def test_extract_rpc_method(self):
        middleware = MetricsMiddleware(app=MagicMock())
        body = json.dumps({"method": "createDriver"}).encode()
        assert middleware._extract_rpc_method(body) == "createDriver"
        body = json.dumps({"method": "bad!method"}).encode()
        assert middleware._extract_rpc_method(body) == "invalid_method"
        body = json.dumps({"id": 1}).encode()
        assert middleware._extract_rpc_method(body) == "unknown"
        assert middleware._extract_rpc_method(b"") == "parse_error"
        assert middleware._extract_rpc_method(b"{invalid") == "parse_error"
        assert middleware._extract_rpc_method(b"not json") == "parse_error"

    def test_restore_request_body(self):
        middleware = MetricsMiddleware(app=MagicMock())
        request = MagicMock()
        body = b"test body"
        middleware._restore_request_body(request, body)
        assert callable(request._receive)

        async def test_receive():
            return await request._receive()

        result = asyncio.run(test_receive())
        assert result == {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    @pytest.mark.smoke
    async def test_full_flow_with_mocked_metrics(self):
        middleware = MetricsMiddleware(app=MagicMock())
        path = "/v1/transpiler/123"
        body = json.dumps({"method": "compile"}).encode()
        request = create_mock_request(path, body)
        call_next = AsyncMock(return_value=Response(status_code=201))

        with patch.object(
            metrics_collector, "record_api_requests_in_progress"
        ) as mock_record_in_progress:
            with patch.object(
                metrics_collector, "record_api_request"
            ) as mock_record_request:
                response = await middleware.dispatch(request, call_next)

        assert response.status_code == 201
        expected_calls = [call(is_increment=True), call(is_increment=False)]
        mock_record_in_progress.assert_has_calls(expected_calls)
        mock_record_request.assert_called_once()
        _, kwargs = mock_record_request.call_args
        data = kwargs["data"]
        assert data.module == "transpiler"
        assert data.method == "compile"
        assert data.endpoint == "/v1/transpiler/{id}"
        assert data.status_code == 201
        assert data.duration > 0
