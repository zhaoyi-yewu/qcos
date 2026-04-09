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

import json
import logging
import re
import time
from collections.abc import Callable

from fastapi import (
    Request,
    Response,
)
from starlette.middleware.base import BaseHTTPMiddleware

from wy_qcos.common.constant import HttpCode
from wy_qcos.metrics import metrics_collector

logger = logging.getLogger(__name__)

ID_PATTERN = re.compile(r"/\d+")
UUID_PATTERN = re.compile(
    r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
HEX_ID_PATTERN = re.compile(r"/[0-9a-f]{24}")


class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for collecting API access metrics."""

    # Excluded paths for which metrics are not collected
    EXCLUDED_PATHS = {"/metrics", "/health", "/favicon.ico"}

    # Modules for which metrics are collected
    MODULES = {"device", "driver", "job", "system", "transpiler"}

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process each request and collect metrics.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response object
        """
        # Skip metrics collection for /metrics endpoint itself
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Increment in-progress counter
        metrics_collector.record_api_requests_in_progress(is_increment=True)
        normalized_path = self._normalize_endpoint(request.url.path)

        # Read body to parse JSON-RPC method
        body = await request.body()
        module = self._extract_module(normalized_path)
        rpc_method = self._extract_rpc_method(body)

        # Restore request body for downstream middleware
        self._restore_request_body(request, body)

        # --- Calculate duration ---
        start_time = time.time()
        response = None
        status_code = HttpCode.INTERNAL_SERVER_ERROR

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            logger.debug(f"Request processing error: {str(e)}", exc_info=True)
            raise e
        finally:
            duration = time.time() - start_time

            #  Record metrics
            data = metrics_collector.api_metrics.APIMetricsData(
                module=module,
                method=rpc_method,
                endpoint=self._normalize_endpoint(request.url.path),
                status_code=status_code,
                duration=duration,
            )
            metrics_collector.record_api_request(data=data)

            # Decrement in-progress counter
            metrics_collector.record_api_requests_in_progress(
                is_increment=False
            )

    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path by removing dynamic parameters.

        Args:
            path:{str} -- Endpoint path to normalize.

        Returns:
           {str} -- Normalized endpoint path.

        Example:
            Input: /api/v1/jobs/<job_id>
            Output: /api/v1/jobs/
        """
        # Remove query parameters
        if "?" in path:
            path = path.split("?")[0]

        # Replace common dynamic parameters with placeholders
        path = ID_PATTERN.sub("/{id}", path)
        path = UUID_PATTERN.sub("/{uuid}", path)
        path = HEX_ID_PATTERN.sub("/{hex_id}", path)

        return path

    def _extract_module(self, path: str) -> str:
        """From path get module name.

        /v1/driver -> driver
        /v1/device -> device.
        """
        parts = [p for p in path.strip("/").split("/") if p]
        for part in reversed(parts):
            if part in self.MODULES:
                return part

        return parts[-1] if parts else "root"

    def _extract_rpc_method(self, body: bytes) -> str:
        """Extract RPC method from request body (assumes JSON format)."""
        try:
            json_body = json.loads(body)
            raw_method = json_body.get("method", "unknown")

            # Check method name
            if re.match(r"^[a-zA-Z0-9_.]+$", raw_method):
                return raw_method
            return "invalid_method"
        except (json.JSONDecodeError, ValueError, TypeError):
            return "parse_error"

    def _restore_request_body(self, request: Request, body: bytes):
        """Restore request body for downstream middleware."""

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive
