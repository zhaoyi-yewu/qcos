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
import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("global_configs")
@pytest.mark.scheduler
class TestFlavor:
    """Test Flavor CRUD and auto scheduling."""

    test_flavor_name = "st-test-flavor"

    @classmethod
    def setup_class(cls):
        """Initialize test environment."""
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        # Clean up existing test flavor
        cls._cleanup_flavor(cls)

    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        cls._cleanup_flavor(cls)

    def _cleanup_flavor(self):
        """Clean up test flavor by name."""
        status_code, reason, text, result = self.admin_client.get_flavors()
        if status_code == 200:
            try:
                resp = json.loads(text)
                flavors = resp.get("result", [])
                for flavor in flavors:
                    if flavor.get("name") == self.test_flavor_name:
                        flavor_id = flavor["id"]
                        self.admin_client.delete_flavor(flavor_id)
                        logger.info(f"Cleaned up test flavor: {flavor_id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup flavor: {e}")

    @pytest.mark.smoke
    def test_create_flavor(self):
        """Test creating a flavor."""
        specs = {
            "min_qubits": 1,
            "tech_type": "none",
        }
        status_code, reason, text, result = self.admin_client.create_flavor(
            name=self.test_flavor_name,
            specs=specs,
            description="ST test flavor",
            is_public=True,
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to create flavor: {err_msg}"
        resp = json.loads(text)
        flavor = resp["result"]
        assert flavor["name"] == self.test_flavor_name
        assert flavor["specs"] == specs
        assert flavor["is_public"] is True

    @pytest.mark.smoke
    def test_get_flavors(self):
        """Test getting flavor list."""
        # First ensure a flavor exists
        self._ensure_flavor_exists()

        status_code, reason, text, result = self.admin_client.get_flavors()
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get flavors: {err_msg}"
        resp = json.loads(text)
        flavors = resp["result"]
        assert isinstance(flavors, list)
        assert len(flavors) > 0

    @pytest.mark.smoke
    def test_get_flavor(self):
        """Test getting a single flavor by ID."""
        flavor_id = self._ensure_flavor_exists()

        status_code, reason, text, result = self.admin_client.get_flavor(
            flavor_id
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get flavor: {err_msg}"
        resp = json.loads(text)
        flavor = resp["result"]
        assert flavor["id"] == flavor_id
        assert flavor["name"] == self.test_flavor_name

    def test_delete_flavor(self):
        """Test deleting a flavor."""
        flavor_id = self._ensure_flavor_exists()

        status_code, reason, text, result = self.admin_client.delete_flavor(
            flavor_id
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to delete flavor: {err_msg}"

    @pytest.mark.smoke
    def test_auto_schedule_with_extra_specs(self):
        """Test auto scheduling with extra_specs (no backend specified).

        This test submits a job without specifying backend,
        providing only extra_specs to trigger auto scheduling.
        The dummy device should be selected.
        """
        job_id = str(Library.create_uuid(prefix=[0xF0]))
        job_name = "test_auto_schedule_extra_specs"
        source_code = SAMPLES["simple-qasm.qasm"]

        status_code, reason, text, result = self.admin_client.submit_job(
            [source_code],
            code_type=Constant.CODE_TYPE_QASM,
            job_id=job_id,
            job_name=job_name,
            job_type=Constant.JOB_TYPE_SAMPLING,
            job_priority=Constant.DEFAULT_JOB_PRIORITY,
            description="ST: auto schedule with extra_specs",
            shots=Constant.DEFAULT_SHOTS,
            backend=None,
            transpiler=Constant.TRANSPILER_CMSS,
            extra_specs={"max_qubits": 100},
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, (
            f"Auto schedule job failed: {err_msg}. Response: {text}"
        )
        resp = json.loads(text)
        result_data = resp["result"]
        assert result_data["job_id"] == job_id
        # backend should be auto-selected
        assert result_data["backend"] is not None
        assert result_data["backend"] != ""
        logger.info(f"Auto scheduled to backend: {result_data['backend']}")

        # Wait for job to complete
        job_info = {
            "job_id": job_id,
            "job_name": job_name,
            "timeout": self.timeout,
            "interval": self.interval,
        }
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(f"Auto scheduled job failed: {err_msg}")
        # Cleanup
        StLibrary.delete_job(self.admin_client, job_id)
        assert success is True

    @pytest.mark.smoke
    def test_auto_schedule_no_params_error(self):
        """Test submitting without backend and without flavor_id/extra_specs.

        Should return an error.
        """
        job_id = str(Library.create_uuid(prefix=[0xF0]))
        source_code = SAMPLES["simple-qasm.qasm"]

        status_code, reason, text, result = self.admin_client.submit_job(
            [source_code],
            code_type=Constant.CODE_TYPE_QASM,
            job_id=job_id,
            job_name="test_auto_schedule_no_params",
            job_type=Constant.JOB_TYPE_SAMPLING,
            job_priority=Constant.DEFAULT_JOB_PRIORITY,
            shots=Constant.DEFAULT_SHOTS,
            backend=None,
            transpiler=Constant.TRANSPILER_CMSS,
        )
        # Should return an error
        assert status_code == 200
        resp = json.loads(text)
        assert "error" in resp
        assert resp["error"] is not None

    def _ensure_flavor_exists(self):
        """Ensure test flavor exists, create if not.

        Returns:
            flavor ID string
        """
        # Check if flavor exists
        status_code, reason, text, result = self.admin_client.get_flavors()
        if status_code == 200:
            try:
                resp = json.loads(text)
                flavors = resp.get("result", [])
                for flavor in flavors:
                    if flavor.get("name") == self.test_flavor_name:
                        return flavor["id"]
            except Exception as e:
                logger.warning(f"Failed to find existing flavor: {e}")

        # Create flavor
        specs = {"min_qubits": 1, "tech_type": "none"}
        status_code, reason, text, result = self.admin_client.create_flavor(
            name=self.test_flavor_name,
            specs=specs,
            description="ST test flavor",
            is_public=True,
        )
        resp = json.loads(text)
        return resp["result"]["id"]
