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
import ipaddress
import socket
from http import HTTPStatus
from unittest.mock import (
    Mock,
    call,
    patch,
)

import pytest

from wy_qcos.metrics import metrics_collector
from wy_qcos.metrics.metrics_server import (
    MetricsServer,
    PrometheusHandler,
)


class TestPrometheusHandler:
    """Test prometheus Handler."""

    def _create_handler(self):
        """Create handler.

        Returns:
            Mock PrometheusHandler
        """
        handler = PrometheusHandler.__new__(PrometheusHandler)
        handler.path = None
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler.client_address = ("127.0.0.1", 12345)
        handler.address_string = Mock(return_value="127.0.0.1")
        return handler

    @pytest.mark.smoke
    def test_do_get_metrics(self):
        """Test normal get metrics data."""
        handler = self._create_handler()
        handler.path = "/metrics"
        mock_data = b"# HELP metric\nmetric 1"
        with patch.object(
            metrics_collector, "get_metrics", return_value=mock_data
        ):
            handler.do_GET()

        handler.send_response.assert_called_once_with(HTTPStatus.OK)
        handler.send_header.assert_has_calls([
            call("Content-Type", "text/plain; charset=utf-8"),
            call("Content-Length", str(len(mock_data))),
        ])
        handler.end_headers.assert_called_once()
        handler.wfile.write.assert_called_once_with(mock_data)

    @pytest.mark.smoke
    def test_do_get_not_found(self):
        """Test url path is invalid."""
        handler = self._create_handler()
        handler.path = "/invalid"
        handler.do_GET()
        handler.send_response.assert_called_once_with(HTTPStatus.NOT_FOUND)
        handler.end_headers.assert_called_once()
        handler.wfile.write.assert_not_called()

    @pytest.mark.smoke
    def test_do_get_connection_reset_error(self):
        """Test connect reseet error."""
        handler = self._create_handler()
        handler.path = "/metrics"
        handler.send_response = Mock(side_effect=ConnectionResetError("reset"))
        with patch("wy_qcos.metrics.metrics_server.logger") as mock_logger:
            handler.do_GET()
            mock_logger.debug.assert_called_once()
            assert "Connection error" in mock_logger.debug.call_args[0][0]

    def test_do_get_other_exception(self):
        """Test get raises expection."""
        handler = self._create_handler()
        handler.path = "/metrics"
        handler.send_response = Mock(side_effect=ValueError("unexpected"))
        with patch("wy_qcos.metrics.metrics_server.logger") as mock_logger:
            with pytest.raises(ValueError):
                handler.do_GET()
            mock_logger.error.assert_called_once()

    @pytest.mark.smoke
    def test_log_message(self):
        handler = self._create_handler()
        with patch("wy_qcos.metrics.metrics_server.logger") as mock_logger:
            handler.log_message("GET %s", "/metrics")
            mock_logger.debug.assert_called_once_with(
                "Metrics HTTP request: %s - %s",
                "127.0.0.1",
                "GET /metrics",
            )


class TestMetricsServer:
    """Test Metric Server."""

    @pytest.mark.smoke
    def test_init_ipv4_specific(self):
        server = MetricsServer(ip="192.168.1.1", port=8080)
        assert server.ip == "192.168.1.1"
        assert server.port == 8080
        assert server.allow_dual_stack is False
        assert isinstance(server.ip_obj, ipaddress.IPv4Address)

    @pytest.mark.smoke
    def test_init_ipv6_specific(self):
        server = MetricsServer(ip="::1", port=9090)
        assert server.ip == "::1"
        assert server.allow_dual_stack is False
        assert isinstance(server.ip_obj, ipaddress.IPv6Address)

    @pytest.mark.smoke
    def test_init_empty_ip_means_dual_stack_ipv6(self):
        server = MetricsServer(ip="", port=9090)
        assert server.ip == "::"
        assert server.allow_dual_stack is True
        assert isinstance(server.ip_obj, ipaddress.IPv6Address)

    @pytest.mark.smoke
    def test_init_none_ip_means_dual_stack_ipv6(self):
        server = MetricsServer(ip=None, port=9090)
        assert server.ip == "::"
        assert server.allow_dual_stack is True
        assert isinstance(server.ip_obj, ipaddress.IPv6Address)

    @pytest.mark.smoke
    def test_init_invalid_ip(self):
        with pytest.raises(ValueError, match="Invalid IP address format"):
            MetricsServer(ip="invalid.ip")

    @pytest.mark.slow
    def test_create_server_ipv4(self):
        server = MetricsServer(ip="127.0.0.1", port=0)
        server._create_server()
        assert server._server is not None
        assert server._server.server_address[0] == "127.0.0.1"
        assert server._server.server_port != 0
        server._server.server_close()

    @pytest.mark.slow
    def test_create_server_ipv6_dual_stack(self):
        try:
            server = MetricsServer(ip="", port=0)
            server._create_server()
            assert server._server is not None
            sock_opt = server._server.socket.getsockopt(
                socket.IPPROTO_IPV6, socket.IPV6_V6ONLY
            )
            assert sock_opt == 0
            server._server.server_close()
        except OSError as e:
            if "Cannot assign requested address" in str(
                e
            ) or "Address family not supported" in str(e):
                pytest.skip("IPv6 not supported on this system")
            else:
                raise

    @pytest.mark.slow
    def test_create_server_ipv6_no_dual_stack(self):
        try:
            server = MetricsServer(ip="::1", port=0)
            server._create_server()
            assert server._server is not None
            sock_opt = server._server.socket.getsockopt(
                socket.IPPROTO_IPV6, socket.IPV6_V6ONLY
            )
            assert sock_opt == 1
            server._server.server_close()
        except OSError as e:
            if "Cannot assign requested address" in str(
                e
            ) or "Address family not supported" in str(e):
                pytest.skip("IPv6 not supported on this system")
            else:
                raise

    @patch("socket.socket.bind")
    def test_create_server_oserror(self, mock_bind):
        mock_bind.side_effect = OSError("bind failed")
        server = MetricsServer(ip="127.0.0.1", port=8080)
        with pytest.raises(OSError, match="bind failed"):
            server._create_server()

    @pytest.mark.asyncio
    async def test_run_normal(self):
        server = MetricsServer(ip="127.0.0.1", port=0)
        task = asyncio.create_task(server.run())
        # enable server
        await asyncio.sleep(0.1)
        await server.stop()
        await task

    @pytest.mark.asyncio
    async def test_run_create_server_fails(self):
        server = MetricsServer(ip="127.0.0.1", port=8080)
        with patch.object(
            server, "_create_server", side_effect=OSError("creation failed")
        ):
            with pytest.raises(OSError):
                await server.run()

    @pytest.mark.slow
    def test_stop(self):
        server = MetricsServer(ip="127.0.0.1", port=0)
        server._shutdown_event = asyncio.Event()
        asyncio.run(server.stop())
        assert server._shutdown_event.is_set()
        assert server._shutdown_event.is_set()
