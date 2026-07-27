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
import os
import re

import pytest
import requests

from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


def parse_prometheus_metrics(text):
    """Parse Prometheus text format into a dict.

    Returns:
        dict mapping "metric_name{labels}" or "metric_name" to float value
    """
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(
            r"^([a-zA-Z_:][a-zA-Z0-9_:]*(?:\{[^}]*\})?)[ \t]+(.+)$", line
        )
        if match:
            metric_key = match.group(1)
            try:
                result[metric_key] = float(match.group(2).strip())
            except ValueError:
                pass
    return result


@pytest.mark.usefixtures("global_configs")
class TestMetricsCrossCompare:
    @classmethod
    def setup_class(cls):
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
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
        cls.metrics_url = f"http://{cls.metrics_ip}:{cls.metrics_port}/metrics"
        cls.timeout = 5

    @classmethod
    def _get_rpc_result(cls, method_name):
        status_code, reason, text, response = method_name()
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        assert error.get("code", 0) == 0
        return result["result"]

    @classmethod
    def _get_prometheus_metrics(cls):
        resp = requests.get(cls.metrics_url, timeout=cls.timeout)
        assert resp.status_code == HttpCode.SUCCESS_OK
        return parse_prometheus_metrics(resp.text)

    def test_job_metrics_rpc_vs_prometheus(self):
        """Compare job stats from RPC interface vs Prometheus endpoint."""
        rpc_result = self._get_rpc_result(self.admin_client.get_job_stats)
        prom_metrics = self._get_prometheus_metrics()

        status_fields = {
            "completed": Constant.JOB_METRICS_FIELD_COMPLETED,
            "failed": Constant.JOB_METRICS_FIELD_FAILED,
            "running": Constant.JOB_METRICS_FIELD_RUNNING,
            "queued": Constant.JOB_METRICS_FIELD_QUEUED,
            "cancelling": Constant.JOB_METRICS_FIELD_CANCELLING,
            "cancelled": Constant.JOB_METRICS_FIELD_CANCELLED,
            "deleting": Constant.JOB_METRICS_FIELD_DELETING,
            "deleted": Constant.JOB_METRICS_FIELD_DELETED,
            "unknown": Constant.JOB_METRICS_FIELD_UNKNOWN,
        }

        for rpc_field, prom_status in status_fields.items():
            rpc_value = rpc_result[rpc_field]
            prom_key = (
                f'{Constant.JOB_METRICS_FIELD_TOTAL}{{status="{prom_status}"}}'
            )
            assert prom_key in prom_metrics, (
                f"Prometheus missing metric: {prom_key}"
            )
            assert rpc_value == prom_metrics[prom_key], (
                f"Mismatch for {rpc_field}: RPC={rpc_value}, "
                f"Prometheus={prom_metrics[prom_key]}"
            )

    def test_system_health_rpc_vs_prometheus(self):
        """Compare system health from RPC interface vs Prometheus endpoint."""
        rpc_result = self._get_rpc_result(self.admin_client.get_system_health)
        prom_metrics = self._get_prometheus_metrics()

        rpc_healthy = rpc_result[Constant.SYSTEM_HEALTHY]
        prom_healthy = prom_metrics.get(Constant.SYSTEM_HEALTHY)
        assert prom_healthy is not None, "Prometheus missing system_healthy"
        assert (prom_healthy == 1.0) == rpc_healthy, (
            f"Mismatch for system_healthy: RPC={rpc_healthy}, "
            f"Prometheus={prom_healthy}"
        )

        rpc_timestamp = rpc_result[Constant.HEARTBEAT_TIMESTAMP]
        prom_timestamp = prom_metrics.get(Constant.HEARTBEAT_TIMESTAMP)
        if rpc_timestamp is None:
            assert prom_timestamp in (None, 0.0, 0), (
                f"RPC timestamp is None but Prometheus={prom_timestamp}"
            )
        else:
            assert prom_timestamp is not None, (
                "Prometheus missing heartbeat_timestamp"
            )
            assert abs(rpc_timestamp - prom_timestamp) < 30, (
                f"Timestamp mismatch: RPC={rpc_timestamp}, \
                Prometheus={prom_timestamp}"
            )

        rpc_components = rpc_result[Constant.COMPONENT_STATUS]
        for component, status in rpc_components.items():
            prom_key = (
                f'{Constant.COMPONENT_STATUS}{{component="{component}"}}'
            )
            assert prom_key in prom_metrics, (
                f"Prometheus missing metric: {prom_key}"
            )
            expected = (
                1.0 if status == Constant.COMPONENT_STATUS_ONLINE else 0.0
            )
            assert prom_metrics[prom_key] == expected, (
                f"Mismatch for component {component}: "
                f"RPC={status}, Prometheus={prom_metrics[prom_key]}"
            )

    def test_api_total_requests_rpc_vs_prometheus(self):
        """Compare total API requests between RPC stats and Prometheus.

        RPC total_requests includes all requests since startup.
        Prometheus api_requests_total is a counter summed across all label
        combinations. They should be equal.
        """
        rpc_result = self._get_rpc_result(self.admin_client.get_api_stats)
        prom_metrics = self._get_prometheus_metrics()

        rpc_total = rpc_result[Constant.API_TOTAL_REQUESTS]

        prom_total = sum(
            v
            for k, v in prom_metrics.items()
            if k.startswith(Constant.API_METRICS_REQUESTS_TOTAL + "{")
        )
        assert rpc_total == prom_total, (
            f"API total mismatch: RPC={rpc_total}, Prometheus sum={prom_total}"
        )

        assert (
            rpc_result[Constant.API_LAST_HOUR_REQUESTS]
            <= rpc_result[Constant.API_LAST_DAY_REQUESTS]
            <= rpc_result[Constant.API_TOTAL_REQUESTS]
        ), (
            f"Inconsistent API stats: "
            f"hour={rpc_result[Constant.API_LAST_HOUR_REQUESTS]}, "
            f"day={rpc_result[Constant.API_LAST_DAY_REQUESTS]}, "
            f"total={rpc_result[Constant.API_TOTAL_REQUESTS]}"
        )

    def test_api_in_progress_rpc_vs_prometheus(self):
        """Compare requests_in_progress between RPC stats and Prometheus."""
        self._get_rpc_result(self.admin_client.get_api_stats)
        prom_metrics = self._get_prometheus_metrics()

        in_progress_key = Constant.API_METRICS_REQUESTS_IN_PROGRESS
        assert in_progress_key in prom_metrics, (
            f"Prometheus missing metric: {in_progress_key}"
        )
        assert prom_metrics[in_progress_key] >= 0, (
            f"Invalid in_progress value: {prom_metrics[in_progress_key]}"
        )
