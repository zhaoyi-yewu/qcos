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

import os

import pytest
import requests

from wy_qcos.common.constant import Constant, HttpCode


@pytest.mark.usefixtures("global_configs")
class TestMetricsServer:
    metrics_url: str
    timeout: int

    @classmethod
    def setup_class(cls):
        cls.metrics_port = os.environ.get(
            "METRICS_SERVER_LISTEN_PORT",
            str(Constant.DEFAULT_METRICS_SERVER_LISTEN_PORT),
        )
        cls.metrics_ip = (
            os.environ.get(
                "METRICS_SERVER_LISTEN_IP",
                str(Constant.DEFAULT_METRICS_SERVER_LISTEN_IP),
            )
            or "127.0.0.1"
        )
        cls.metrics_url = f"http://{cls.metrics_ip}:{cls.metrics_port}"
        cls.timeout = 5

    @classmethod
    def teardown_class(cls):
        pass

    @classmethod
    def _get_metrics(cls) -> requests.Response:
        return requests.get(
            f"{cls.metrics_url}/metrics",
            timeout=cls.timeout,
        )

    def test_metrics_endpoint_exists(self):
        """Test Prometheus metrics endpoint returns successfully."""
        resp = self._get_metrics()
        assert resp.status_code == HttpCode.SUCCESS_OK

        content_type = resp.headers.get("Content-Type", "")
        assert "text/plain" in content_type

        body = resp.text
        assert body

    def test_metrics_contains_job_metrics(self):
        """Test metrics output contains job metrics."""
        resp = self._get_metrics()
        assert resp.status_code == HttpCode.SUCCESS_OK
        body = resp.text
        assert "status" in body

    def test_metrics_contains_health_metrics(self):
        """Test metrics output contains system health metrics."""
        resp = self._get_metrics()
        assert resp.status_code == HttpCode.SUCCESS_OK
        body = resp.text
        assert "system_health" in body

    def test_metrics_contains_api_metrics(self):
        """Test metrics output contains API metrics."""
        resp = self._get_metrics()
        assert resp.status_code == HttpCode.SUCCESS_OK
        body = resp.text
        assert "api_requests_total" in body

    def test_non_metrics_path_returns_NOT_FOUND_ERROR(self):
        """Test non /metrics path returns HttpCode.NOT_FOUND_ERROR."""
        resp = requests.get(
            f"{self.metrics_url}/",
            timeout=self.timeout,
        )
        assert resp.status_code == HttpCode.NOT_FOUND_ERROR

    def test_random_path_returns_NOT_FOUND_ERROR(self):
        """Test random path returns HttpCode.NOT_FOUND_ERROR."""
        resp = requests.get(
            f"{self.metrics_url}/random",
            timeout=self.timeout,
        )
        assert resp.status_code == HttpCode.NOT_FOUND_ERROR
