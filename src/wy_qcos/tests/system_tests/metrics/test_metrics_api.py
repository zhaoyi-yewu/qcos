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
import pytest

from wy_qcos.common.constant import HttpCode
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
class TestMetricsAPI:
    @classmethod
    def setup_class(cls):
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]

    @classmethod
    def teardown_class(cls):
        pass

    @pytest.mark.smoke
    def test_get_system_health(self):
        status_code, reason, text, response = (
            self.admin_client.get_system_health()
        )
        assert status_code == HttpCode.SUCCESS_OK

        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0

        results = result["result"]
        assert isinstance(results, dict)
        assert "system_healthy" in results
        assert isinstance(results["system_healthy"], bool)

        assert "heartbeat_timestamp" in results
        assert results["heartbeat_timestamp"] is None or isinstance(
            results["heartbeat_timestamp"], (int, float)
        )

        assert "component_status" in results
        component_status = results["component_status"]
        assert isinstance(component_status, dict)
        for component in ["fastapi", "redis", "prefect", "worker"]:
            assert component in component_status
            assert component_status[component] in ("online", "offline")

    @pytest.mark.smoke
    def test_get_api_stats(self):
        status_code, reason, text, response = self.admin_client.get_api_stats()
        assert status_code == HttpCode.SUCCESS_OK

        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0

        results = result["result"]
        assert isinstance(results, dict)
        assert "total_requests" in results
        assert "last_hour_requests" in results
        assert "last_day_requests" in results

        assert isinstance(results["total_requests"], int)
        assert results["total_requests"] >= 0

        assert isinstance(results["last_hour_requests"], int)
        assert results["last_hour_requests"] >= 0

        assert isinstance(results["last_day_requests"], int)
        assert results["last_day_requests"] >= 0

        assert results["total_requests"] >= results["last_hour_requests"]
        assert results["total_requests"] >= results["last_day_requests"]

    @pytest.mark.smoke
    def test_get_job_stats(self):
        status_code, reason, text, response = self.admin_client.get_job_stats()
        assert status_code == HttpCode.SUCCESS_OK

        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0

        results = result["result"]
        assert isinstance(results, dict)

        expected_fields = [
            "total",
            "completed",
            "failed",
            "running",
            "queued",
            "cancelling",
            "cancelled",
            "deleted",
            "unknown",
        ]
        for field in expected_fields:
            assert field in results
            assert isinstance(results[field], int)
            assert results[field] >= 0

        status_counts = sum(results[field] for field in expected_fields[1:])
        assert results["total"] == status_counts
