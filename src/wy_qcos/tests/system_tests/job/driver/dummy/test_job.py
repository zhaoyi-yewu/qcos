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
import time

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("global_configs")
@pytest.mark.driver
class TestJob:
    """Test Job."""

    test_job_names = [
        "test_submit_job",
        "test_submit_job_dry_run",
        "test_submit_job_profiling",
        "test_submit_job_wirecut",
        "test_submit_two_same_priority_jobs_1",
        "test_submit_two_same_priority_jobs_2",
        "test_submit_two_different_priority_jobs_1",
        "test_submit_two_diff_priority_jobs_2",
        "test_submit_two_diff_device_jobs_1",
        "test_submit_two_diff_device_jobs_2",
        "test_submit_job_disabled_device",
        "test_submit_job_offline_device",
    ]

    @classmethod
    def setup_class(cls):
        """Initialize test environment."""
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]

        # Initialize and clean up test resources
        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)

    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)

    @staticmethod
    def assert_default_results(job_results):
        assert "result" in job_results
        assert "results" in job_results["result"]
        assert isinstance(job_results["result"]["results"], list)
        assert len(job_results["result"]["results"]) == 1
        results_0 = job_results["result"]["results"][0]
        r_00 = results_0["results"].get("00", 0)
        r_01 = results_0["results"].get("01", 0)
        r_10 = results_0["results"].get("10", 0)
        r_11 = results_0["results"].get("11", 0)
        assert r_00 + r_01 + r_10 + r_11 == Constant.DEFAULT_SHOTS
        assert results_0["num_qubits"] == 2

    @pytest.mark.smoke
    def test_submit_job(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_job",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_job",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            self.assert_default_results(job_results)
            StLibrary.delete_job(self.admin_client, job_info["job_id"])
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True

    def test_submit_job_dry_run(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_job_dry_run",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_job_dry_run",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": True,
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            self.assert_default_results(job_results)
            StLibrary.delete_job(self.admin_client, job_info["job_id"])
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True

    def test_submit_job_profiling(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_job_profiling",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_job_profiling",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": [
                Constant.PROFILING_TYPE_CODE,
                Constant.PROFILING_TYPE_SCHEDULING,
                Constant.PROFILING_TYPE_DRIVER_PARSE,
                Constant.PROFILING_TYPE_DRIVER_TRANSPILE,
                Constant.PROFILING_TYPE_DRIVER_RUN,
            ],
            "callbacks": None,
            "dry_run": False,
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
            profiling_results = job_results["result"]["results"][0].get(
                "profiling", {}
            )
            assert isinstance(profiling_results, dict)
            assert isinstance(
                profiling_results[Constant.PROFILING_TYPE_CODE], float
            )
            assert isinstance(
                profiling_results[Constant.PROFILING_TYPE_SCHEDULING], float
            )
            assert isinstance(
                profiling_results[Constant.PROFILING_TYPE_DRIVER_PARSE], float
            )
            assert isinstance(
                profiling_results[Constant.PROFILING_TYPE_DRIVER_TRANSPILE],
                float,
            )
            assert isinstance(
                profiling_results[Constant.PROFILING_TYPE_DRIVER_RUN], float
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    def test_submit_job_wirecut(self):
        """Wirecut batch should fail when only part of it can be mapped."""
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_job_wirecut",
            "source_code_list": [SAMPLES["15_35.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_job_wirecut",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": {"enable_wirecut": True, "max_qubits": 6},
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": {"enable_na_move": True},
            "profiling": None,
            "callbacks": None,
            "dry_run": True,
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_FAILED
            )
            assert (
                "Wirecut batch result count does not match subcircuits"
                in job_results["result"]["results"][0]["error"]["message"]
            )
            StLibrary.delete_job(self.admin_client, job_info["job_id"])
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True

    @pytest.mark.slow
    def test_submit_two_same_priority_jobs(self):
        first_job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_two_same_priority_jobs_1",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_two_same_priority_jobs_1",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": {"sleep": 30},
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        StLibrary.submit_job(self.admin_client, first_job_info)

        second_job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_two_same_priority_jobs_2",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_two_same_priority_jobs_2",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        StLibrary.submit_job(self.admin_client, second_job_info)

        result, err_msg, _ = StLibrary.get_job_status(
            self.admin_client, first_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg
        result, err_msg, _ = StLibrary.get_job_status(
            self.admin_client, second_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg

        time.sleep(20)
        result, err_msg, _ = StLibrary.get_job_status(
            self.admin_client, first_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg
        result, err_msg, _ = StLibrary.get_job_status(
            self.admin_client, second_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg

        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, first_job_info, self.timeout, self.interval
        )
        if success:
            StLibrary.delete_job(self.admin_client, first_job_info["job_id"])
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True

        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, second_job_info, self.timeout, self.interval
        )
        if success:
            StLibrary.delete_job(self.admin_client, second_job_info["job_id"])
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True

    @pytest.mark.slow
    def test_submit_two_different_priority_jobs(self):
        first_job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_two_different_priority_jobs_1",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.MAX_JOB_PRIORITY,
            "description": "description: submit_two_different_priority_jobs_1",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        StLibrary.submit_job(self.admin_client, first_job_info)

        second_job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_two_diff_priority_jobs_2",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: submit_two_diff_priority_jobs_2",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        StLibrary.submit_job(self.admin_client, second_job_info)

        result, err_msg, _ = StLibrary.get_job_status(
            self.admin_client, first_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg
        result, err_msg, _ = StLibrary.get_job_status(
            self.admin_client, second_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg

        time.sleep(3)
        result, err_msg, _ = StLibrary.get_job_status(
            self.admin_client, first_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg

        result, err_msg, _ = StLibrary.get_job_status(
            self.admin_client, second_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg

        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, first_job_info, self.timeout, self.interval
        )
        if success:
            self.assert_default_results(job_results)
            StLibrary.delete_job(self.admin_client, first_job_info["job_id"])
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True

        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, second_job_info, self.timeout, self.interval
        )
        if success:
            self.assert_default_results(job_results)
            StLibrary.delete_job(self.admin_client, second_job_info["job_id"])
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True

    @pytest.mark.slow
    def test_submit_two_different_device_jobs(self):
        first_job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_two_diff_device_jobs_1",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_two_diff_device_jobs_1",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": {"sleep": 10},
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        StLibrary.submit_job(self.admin_client, first_job_info)

        second_job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_two_diff_device_jobs_2",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_two_diff_device_jobs_2",
            "backend": "qutip_sim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": {"sleep": 10},
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        StLibrary.submit_job(self.admin_client, second_job_info)

        result, err_msg, _ = StLibrary.get_job_status(
            self.admin_client, first_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg
        result, err_msg, _ = StLibrary.get_job_status(
            self.admin_client, second_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg

        time.sleep(1)
        result, err_msg, _ = StLibrary.get_job_status(
            self.admin_client, first_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg
        result, err_msg, _ = StLibrary.get_job_status(
            self.admin_client, second_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg

        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, first_job_info, self.timeout, self.interval
        )
        if success:
            self.assert_default_results(job_results)
            StLibrary.delete_job(self.admin_client, first_job_info["job_id"])
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True

        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, second_job_info, self.timeout, self.interval
        )
        if success:
            self.assert_default_results(job_results)
            StLibrary.delete_job(self.admin_client, second_job_info["job_id"])
            terminal_statuses = {
                Constant.JOB_STATUS_COMPLETED,
                Constant.JOB_STATUS_FAILED,
            }
            assert job_results["result"]["job_status"] in terminal_statuses
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True

    def _restore_device(self, enable=True, status="online"):
        """Restore device to enabled and online state."""
        self.admin_client.set_device(
            Constant.DEVICE_DUMMY,
            enable=enable,
            status=status,
        )

    @pytest.mark.smoke
    def test_submit_job_disabled_device(self):
        """Submit job to a disabled device (enable=false) should fail."""
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_job_disabled_device",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_job_disabled_device",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        # disable device
        self.admin_client.set_device(Constant.DEVICE_DUMMY, enable=False)
        try:
            status_code, reason, text, response = self.admin_client.submit_job(
                job_info["source_code_list"],
                code_type=job_info["code_type"],
                job_id=job_info["job_id"],
                circuit_aggregation=None,
                job_name=job_info["job_name"],
                job_type=job_info["job_type"],
                job_priority=job_info["job_priority"],
                description=job_info["description"],
                shots=job_info["shots"],
                backend=job_info["backend"],
                driver_options=None,
                transpiler=job_info["transpiler"],
                transpiler_options=None,
                profiling=None,
                callbacks=None,
                dry_run=False,
                qec_options=None,
            )
            # job submission should fail with error
            job_result = json.loads(text)
            assert "error" in job_result
            assert job_result["error"] is not None
        except AssertionError:
            # if submission succeeded, job should fail
            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                self.admin_client,
                job_info,
                self.timeout,
                self.interval,
            )
            assert success is False or (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_FAILED
            )
        finally:
            self._restore_device()

    @pytest.mark.smoke
    def test_submit_job_offline_device(self):
        """Submit job to an offline device (status=offline) should fail."""
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_job_offline_device",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_job_offline_device",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        # set device offline
        self.admin_client.set_device(Constant.DEVICE_DUMMY, status="offline")
        try:
            status_code, reason, text, response = self.admin_client.submit_job(
                job_info["source_code_list"],
                code_type=job_info["code_type"],
                job_id=job_info["job_id"],
                circuit_aggregation=None,
                job_name=job_info["job_name"],
                job_type=job_info["job_type"],
                job_priority=job_info["job_priority"],
                description=job_info["description"],
                shots=job_info["shots"],
                backend=job_info["backend"],
                driver_options=None,
                transpiler=job_info["transpiler"],
                transpiler_options=None,
                profiling=None,
                callbacks=None,
                dry_run=False,
                qec_options=None,
            )
            # job submission should fail with error
            job_result = json.loads(text)
            assert "error" in job_result
            assert job_result["error"] is not None
        except AssertionError:
            # if submission succeeded, job should fail
            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                self.admin_client,
                job_info,
                self.timeout,
                self.interval,
            )
            assert success is False or (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_FAILED
            )
        finally:
            self._restore_device()
