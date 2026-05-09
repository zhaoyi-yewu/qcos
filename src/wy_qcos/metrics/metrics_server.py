#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You can obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import asyncio
import ipaddress
import logging
import socket
import time
from http import HTTPStatus
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)

from wy_qcos.common.config import Config
from wy_qcos.metrics import metrics_collector

logger = logging.getLogger(__name__)


class PrometheusHandler(BaseHTTPRequestHandler):
    """HTTP Handler for Prometheus Metrics Server."""

    DEFAULT_SERVER_METRICS_PATH = "/metrics"
    HEADER_CONTENT_TYPE = "Content-Type"
    HEADER_CONTENT_LENGTH = "Content-Length"
    CONTENT_TYPE_TEXT_UTF8 = "text/plain; charset=utf-8"

    def do_GET(self):
        """Handle GET requests."""
        try:
            if self.path == self.DEFAULT_SERVER_METRICS_PATH:
                # returns a byte string representing the metrics in text format
                data = metrics_collector.get_metrics()
                self.send_response(HTTPStatus.OK)
                self.send_header(
                    self.HEADER_CONTENT_TYPE, self.CONTENT_TYPE_TEXT_UTF8
                )
                self.send_header(self.HEADER_CONTENT_LENGTH, str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                # if the path is not /metrics, return a 404 error
                self.send_response(HTTPStatus.NOT_FOUND)
                self.end_headers()
        except (
            ConnectionResetError,
            ConnectionAbortedError,
            BrokenPipeError,
        ) as e:
            logger.debug(
                f"Connection error for client {self.client_address}: {e}"
            )
            pass
        except Exception as e:
            logger.error(
                f"Unexpected error handling request from \
                {self.client_address}: {e}"
            )
            raise

    def log_message(self, format, *args):
        """Log messages for the http server.

        Args:
            format: {str} -- log message format
            *args: {tuple} -- log message arguments

        """
        logger.debug(
            "Metrics HTTP request: %s - %s",
            self.address_string(),
            format % args,
        )
        pass


class MetricsServer:
    """Prometheus Metrics Server."""

    def __init__(
        self,
        ip=Config.METRICS_SERVER_LISTEN_IP,
        port=Config.METRICS_SERVER_LISTEN_PORT,
    ):
        """Initialize metrics server.

        Args:
            ip:
                Listen IP address.
                - None or "" for IPv4 and IPv6 all interfaces (dual-stack)
                -"0.0.0.0" for IPv4 all interfaces
                - "::" for IPv6 all interfaces
                - Specific IP for single interface
            port:
                Listen port, default from Config
        """
        self.port = port
        self.ip = ip if ip else "::"
        self.allow_dual_stack = False if ip else True
        self._server = None
        self._shutdown_event = None
        self._server_task = None
        self.max_retries = 5
        self.retry_delay = 2
        try:
            self.ip_obj = ipaddress.ip_address(self.ip)
        except ValueError:
            raise ValueError(
                f"Invalid IP address format: '{self.ip}' \
                Expected IPv4 or IPv6."
            )

    def _create_server(self):
        """Create HTTP server with IPv4/IPv6 support.

        Implements retry logic for handling TIME_WAIT socket state.
        """
        is_ipv6 = isinstance(self.ip_obj, ipaddress.IPv6Address)

        class SpecificHTTPServer(HTTPServer):
            address_family = socket.AF_INET6 if is_ipv6 else socket.AF_INET

        for attempt in range(self.max_retries):
            try:
                self._server = SpecificHTTPServer(
                    (self.ip, self.port),
                    PrometheusHandler,
                    bind_and_activate=False,
                )
                # Enable SO_REUSEADDR to allow the socket to be bound
                # immediately after restart. This prevents "Address
                # already in use" errors when the service restarts quickly
                self._server.socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
                )

                if self.allow_dual_stack:
                    self._server.socket.setsockopt(
                        socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, False
                    )
                    logger.info("IPv6 Dual-Stack enabled")

                self._server.server_bind()
                self._server.server_activate()
                logger.info(
                    f"Metrics server socket successfully bound to "
                    f"{self.ip}:{self.port}"
                )
                return

            except OSError as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Failed to bind metrics server "
                        f"(attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {self.retry_delay} seconds..."
                    )
                    time.sleep(self.retry_delay)
                else:
                    logger.error(
                        f"Failed to create metrics server after "
                        f"{self.max_retries} attempts: {e}"
                    )
                    raise

    async def start(self):
        """Start the metrics server."""
        logger.info("Starting Prometheus metrics server")
        logger.info(f"Listening on {self.ip}:{self.port}/metrics")

        self._shutdown_event = asyncio.Event()

        try:
            self._create_server()

            loop = asyncio.get_event_loop()
            self._server_task = loop.run_in_executor(
                None, self._server.serve_forever
            )

            await self._shutdown_event.wait()

            if self._server:
                self._server.shutdown()
                await self._server_task
                logger.info("Prometheus metrics server stopped")

        except OSError as e:
            logger.error(
                f"Error running metrics server on {self.ip}:{self.port}: {e}. "
                f"The port may still be in TIME_WAIT state from a previous "
                f"connection. Please wait a moment and try again."
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error running metrics server: {e}")
            raise

    async def stop(self):
        """Stop the metrics server gracefully."""
        if self._shutdown_event:
            self._shutdown_event.set()
            logger.info("Shutdown signal sent")
