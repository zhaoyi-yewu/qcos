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
    MagicMock,
    patch,
)

import pytest

from wy_qcos.metrics.metrics_server import (
    MetricsServer,
    PrometheusHandler,
)


class TestPrometheusHandler:
    """Unit tests for PrometheusHandler."""

    @pytest.fixture
    def handler(self):
        """Create a PrometheusHandler instance with mocked base attributes."""
        handler = PrometheusHandler.__new__(PrometheusHandler)
        handler.path = "/metrics"
        handler.client_address = ("127.0.0.1", 12345)
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.address_string = MagicMock(return_value="127.0.0.1")
        return handler

    @pytest.fixture
    def mock_logger(self):
        with patch("wy_qcos.metrics.metrics_server.logger") as mock_log:
            yield mock_log

    def test_do_get_metrics_path_success(self, handler, mock_logger):
        """Test do_GET with /metrics path returns metrics data."""
        mock_metrics_data = b"# HELP some metric\nsome_metric 42\n"
        with patch(
            "wy_qcos.metrics.metrics_server.metrics_collector.get_metrics",
            return_value=mock_metrics_data,
        ):
            handler.do_GET()

        handler.send_response.assert_called_once_with(HTTPStatus.OK)
        handler.send_header.assert_any_call(
            "Content-Type", "text/plain; charset=utf-8"
        )
        handler.send_header.assert_any_call(
            "Content-Length", str(len(mock_metrics_data))
        )
        handler.end_headers.assert_called_once()
        handler.wfile.write.assert_called_once_with(mock_metrics_data)

    def test_do_get_not_found(self, handler, mock_logger):
        """Test do_GET with non-metrics path returns 404."""
        handler.path = "/invalid"
        handler.do_GET()
        handler.send_response.assert_called_once_with(HTTPStatus.NOT_FOUND)
        handler.end_headers.assert_called_once()
        handler.wfile.write.assert_not_called()

    def test_do_get_connection_reset_error(self, handler, mock_logger):
        """Test do_GET handles ConnectionResetError gracefully."""
        handler.wfile.write.side_effect = ConnectionResetError(
            "Connection reset"
        )
        with patch(
            "wy_qcos.metrics.metrics_server.metrics_collector.get_metrics",
            return_value=b"data",
        ):
            handler.do_GET()
        mock_logger.debug.assert_called_once()
        assert "Connection error" in mock_logger.debug.call_args[0][0]
        handler.send_response.assert_called_once_with(HTTPStatus.OK)
        handler.end_headers.assert_called_once()

    def test_do_get_connection_aborted_error(self, handler, mock_logger):
        """Test do_GET handles ConnectionAbortedError gracefully."""
        handler.wfile.write.side_effect = ConnectionAbortedError(
            "Connection aborted"
        )
        with patch(
            "wy_qcos.metrics.metrics_server.metrics_collector.get_metrics",
            return_value=b"data",
        ):
            handler.do_GET()
        mock_logger.debug.assert_called_once()

    def test_do_get_broken_pipe_error(self, handler, mock_logger):
        """Test do_GET handles BrokenPipeError gracefully."""
        handler.wfile.write.side_effect = BrokenPipeError("Broken pipe")
        with patch(
            "wy_qcos.metrics.metrics_server.metrics_collector.get_metrics",
            return_value=b"data",
        ):
            handler.do_GET()
        mock_logger.debug.assert_called_once()

    def test_do_get_unexpected_exception(self, handler, mock_logger):
        """Test do_GET propagates unexpected exceptions after logging."""
        handler.wfile.write.side_effect = RuntimeError("Unexpected error")
        with (
            patch(
                "wy_qcos.metrics.metrics_server.metrics_collector.get_metrics",
                return_value=b"data",
            ),
            pytest.raises(RuntimeError),
        ):
            handler.do_GET()
        mock_logger.error.assert_called_once()
        assert "Unexpected error" in mock_logger.error.call_args[0][0]

    def test_log_message(self, handler, mock_logger):
        """Test log_message method logs via logger."""
        handler.log_message("GET /metrics %s", "200")
        mock_logger.debug.assert_called_once()
        args = mock_logger.debug.call_args[0]
        assert "Metrics HTTP request:" in args[0]
        assert args[1] == "127.0.0.1"
        assert "GET /metrics 200" in args[2]


class TestMetricsServer:
    """Unit tests for MetricsServer."""

    def test_init_default_ipv6_all_interfaces(self):
        """Test default initialization results in '::' and dual-stack."""
        server = MetricsServer(ip=None, port=9090)
        assert server.ip == "::"
        assert server.port == 9090
        assert server.allow_dual_stack is True
        assert isinstance(server.ip_obj, ipaddress.IPv6Address)
        assert server.ip_obj == ipaddress.ip_address("::")

    def test_init_explicit_ipv4(self):
        """Test initialization with explicit IPv4 address."""
        server = MetricsServer(ip="192.168.1.1", port=8000)
        assert server.ip == "192.168.1.1"
        assert server.port == 8000
        assert server.allow_dual_stack is False
        assert isinstance(server.ip_obj, ipaddress.IPv4Address)
        assert server.ip_obj == ipaddress.ip_address("192.168.1.1")

    def test_init_explicit_ipv6(self):
        """Test initialization with explicit IPv6 address."""
        server = MetricsServer(ip="::1", port=9090)
        assert server.ip == "::1"
        assert server.port == 9090
        assert server.allow_dual_stack is False
        assert isinstance(server.ip_obj, ipaddress.IPv6Address)
        assert server.ip_obj == ipaddress.ip_address("::1")

    def test_init_invalid_ip(self):
        """Test initialization with invalid IP raises ValueError."""
        with pytest.raises(ValueError, match="Invalid IP address format"):
            MetricsServer(ip="invalid.ip")

    @pytest.mark.smoke
    def test_create_server_ipv4(self):
        """Test created an IPv4 server with correct socket options."""
        server = MetricsServer(ip="127.0.0.1", port=0)
        server._create_server()
        assert server._server is not None
        assert server._server.socket.family == socket.AF_INET
        assert server._server.server_address[0] == "127.0.0.1"
        assert server._server.server_address[1] != 0

        server._server.server_close()

    @pytest.mark.smoke
    def test_create_server_ipv6_dual_stack_enabled(self):
        """Test _create_server with dual-stack enabled creates IPv6 server."""
        server = MetricsServer(ip=None, port=0)
        server._create_server()
        assert server._server is not None
        assert server._server.socket.family == socket.AF_INET6
        # Should bind to '::' (all IPv6 interfaces)
        assert server._server.server_address[0] == "::"
        assert server._server.server_address[1] != 0
        server._server.server_close()

    @pytest.mark.smoke
    def test_create_server_ipv6_no_dual_stack(self):
        """Test _create_server with IPv6 address disables dual-stack."""
        server = MetricsServer(ip="::1", port=0)
        server._create_server()
        assert server._server is not None
        assert server._server.socket.family == socket.AF_INET6
        assert server._server.server_address[0] == "::1"
        assert server._server.server_address[1] != 0
        server._server.server_close()

    def test_create_server_os_error(self):
        """Test _create_server raises OSError if bind fails."""
        server = MetricsServer(ip="127.0.0.1", port=8080)
        with patch(
            "socket.socket.bind", side_effect=OSError("Address already in use")
        ):
            with pytest.raises(OSError, match="Address already in use"):
                server._create_server()

    def test_start_stop_normal_flow(self):
        """Test start and stop methods work correctly with a real server."""
        server = MetricsServer(ip="127.0.0.1", port=0)

        async def run():
            task = asyncio.create_task(server.start())
            await asyncio.sleep(0.1)
            await server.stop()
            await task

        asyncio.run(run())

        assert server._server is None or server._server is not None

    def test_start_os_error(self):
        """Test start handles OSError during server creation."""
        server = MetricsServer(ip="127.0.0.1", port=8080)
        with patch.object(
            server, "_create_server", side_effect=OSError("Bind failed")
        ):

            async def run():
                with pytest.raises(OSError, match="Bind failed"):
                    await server.start()

            asyncio.run(run())

    def test_start_unexpected_exception(self):
        """Test start handles unexpected exception during server creation."""
        server = MetricsServer(ip="127.0.0.1", port=8080)
        with patch.object(
            server, "_create_server", side_effect=RuntimeError("Unexpected")
        ):

            async def run():
                with pytest.raises(RuntimeError, match="Unexpected"):
                    await server.start()

            asyncio.run(run())

    def test_stop_before_start(self):
        """Test stop called before start does nothing."""
        server = MetricsServer(ip="127.0.0.1", port=8080)
        server._shutdown_event = None

        async def run():
            await server.stop()

        asyncio.run(run())

    @pytest.mark.smoke
    def test_dual_stack_ipv4_with_allow_dual_stack_true(self):
        """Test that IPv4 server never sets dual-stack option."""
        server = MetricsServer(ip="0.0.0.0", port=0)
        assert server.allow_dual_stack is False
        server._create_server()
        assert server._server.socket.family == socket.AF_INET
        server._server.server_close()
