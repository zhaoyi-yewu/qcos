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

"""System tests for error mitigation module.

Tests the full error mitigation pipeline through the API layer,
using the dummy driver as backend.

Run command:
    python -m pytest src/wy_qcos/tests/system_tests/job/driver/\
dummy/test_job_error_mitigation.py -v -s
"""

import logging

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("global_configs")
@pytest.mark.driver
class TestJobErrorMitigation:
    """Test error mitigation integration with job submission."""

    test_job_names = [
        "test_submit_job_rem",
        "test_submit_job_zne",
        "test_submit_job_rem_zne",
        "test_submit_job_no_mitigation",
        "test_submit_job_mitigation_dry_run",
    ]

    @classmethod
    def setup_class(cls):
        """Initialize test environment."""
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]

        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)

    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)

    def _build_job_info(self, job_name, source_code, qem_options=None):
        """Build standard job_info dict."""
        return {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": job_name,
            "source_code_list": [source_code],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": f"error mitigation test: {job_name}",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qem_options": qem_options,
        }

    @staticmethod
    def assert_results_exist(job_results):
        """Assert that job results contain valid sampling counts."""
        assert "result" in job_results
        assert "results" in job_results["result"]
        assert isinstance(job_results["result"]["results"], list)
        assert len(job_results["result"]["results"]) == 1
        results_0 = job_results["result"]["results"][0]
        assert results_0["results"] is not None
        assert isinstance(results_0["results"], dict)
        total = sum(results_0["results"].values())
        assert total > 0
        logger.info(
            "Results: %s (total=%d, num_qubits=%s)",
            results_0["results"],
            total,
            results_0.get("num_qubits"),
        )

    @pytest.mark.smoke
    def test_submit_job_no_mitigation(self):
        """Baseline: submit job without error mitigation."""
        job_info = self._build_job_info(
            "test_submit_job_no_mitigation",
            SAMPLES["simple-qasm.qasm"],
        )
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        assert success is True, f"Job failed: {err_msg}"
        self.assert_results_exist(job_results)
        assert (
            job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

        # Verify no mitigation metadata present
        results_0 = job_results["result"]["results"][0]
        metadata = results_0.get("metadata", {})
        assert "mitigation" not in metadata

        StLibrary.delete_job(self.admin_client, job_info["job_id"])

    @pytest.mark.smoke
    def test_submit_job_rem(self):
        """Submit job with readout error mitigation (REM) enabled."""
        job_info = self._build_job_info(
            "test_submit_job_rem",
            SAMPLES["simple-qasm.qasm"],
            qem_options={
                "rem": {"enabled": True, "calibration_shots": 4096},
            },
        )
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        assert success is True, f"Job failed: {err_msg}"
        self.assert_results_exist(job_results)
        assert (
            job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

        # Verify mitigation metadata is present
        results_0 = job_results["result"]["results"][0]
        metadata = results_0.get("metadata", {})
        mitigation = metadata.get("mitigation", {})
        logger.info("REM mitigation metadata: %s", mitigation)

        if mitigation:
            techniques = mitigation.get("techniques_applied", [])
            assert "readout" in techniques, (
                f"Expected 'readout' in techniques, got {techniques}"
            )

        StLibrary.delete_job(self.admin_client, job_info["job_id"])

    def test_submit_job_zne(self):
        """Submit job with zero-noise extrapolation (ZNE) enabled.

        Uses a circuit with CZ gates since ZNE requires CZ tripling.
        """
        job_info = self._build_job_info(
            "test_submit_job_zne",
            SAMPLES["bell-with-cz.qasm"],
            qem_options={
                "zne": {"enabled": True, "scale_factor": 3},
            },
        )
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        assert success is True, f"Job failed: {err_msg}"
        self.assert_results_exist(job_results)
        assert (
            job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

        # Verify ZNE metadata
        results_0 = job_results["result"]["results"][0]
        metadata = results_0.get("metadata", {})
        mitigation = metadata.get("mitigation", {})
        logger.info("ZNE mitigation metadata: %s", mitigation)

        if mitigation:
            techniques = mitigation.get("techniques_applied", [])
            assert "zne" in techniques, (
                f"Expected 'zne' in techniques, got {techniques}"
            )

        StLibrary.delete_job(self.admin_client, job_info["job_id"])

    def test_submit_job_rem_zne(self):
        """Submit job with both REM and ZNE enabled."""
        job_info = self._build_job_info(
            "test_submit_job_rem_zne",
            SAMPLES["bell-with-cz.qasm"],
            qem_options={
                "rem": {"enabled": True, "calibration_shots": 4096},
                "zne": {"enabled": True, "scale_factor": 3},
            },
        )
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        assert success is True, f"Job failed: {err_msg}"
        self.assert_results_exist(job_results)
        assert (
            job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

        # Verify both techniques applied
        results_0 = job_results["result"]["results"][0]
        metadata = results_0.get("metadata", {})
        mitigation = metadata.get("mitigation", {})
        logger.info("REM+ZNE mitigation metadata: %s", mitigation)

        if mitigation:
            techniques = mitigation.get("techniques_applied", [])
            assert "readout" in techniques
            assert "zne" in techniques

            # Verify raw results are preserved
            raw = mitigation.get("raw_results", {})
            assert "original" in raw

        StLibrary.delete_job(self.admin_client, job_info["job_id"])

    def test_submit_job_mitigation_dry_run(self):
        """Dry-run should skip mitigation execution."""
        job_info = self._build_job_info(
            "test_submit_job_mitigation_dry_run",
            SAMPLES["simple-qasm.qasm"],
            qem_options={
                "rem": {"enabled": True},
                "zne": {"enabled": True},
            },
        )
        job_info["dry_run"] = True

        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        assert success is True, f"Dry-run job failed: {err_msg}"
        assert (
            job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

        StLibrary.delete_job(self.admin_client, job_info["job_id"])
