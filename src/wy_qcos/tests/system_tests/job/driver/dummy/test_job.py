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

import pytest
import time

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES


@pytest.mark.usefixtures("global_configs")
class TestJob:
    @classmethod
    def setup_class(cls):
        cls.client = GLOBAL_CONFIGS["client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]

    @classmethod
    def teardown_class(cls):
        pass

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
        StLibrary.submit_job(self.client, job_info)
        job_results = StLibrary.wait_and_get_job_result(
            self.client, job_info, self.timeout, self.interval
        )
        StLibrary.delete_job(self.client, job_info["job_id"])
        assert (
            job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

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
        StLibrary.submit_job(self.client, job_info)
        job_results = StLibrary.wait_and_get_job_result(
            self.client, job_info, self.timeout, self.interval
        )
        StLibrary.delete_job(self.client, job_info["job_id"])
        assert (
            job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

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
        StLibrary.submit_job(self.client, job_info)
        job_results = StLibrary.wait_and_get_job_result(
            self.client, job_info, self.timeout, self.interval
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
            profiling_results[Constant.PROFILING_TYPE_DRIVER_TRANSPILE], float
        )
        assert isinstance(
            profiling_results[Constant.PROFILING_TYPE_DRIVER_RUN], float
        )
        StLibrary.delete_job(self.client, job_info["job_id"])
        assert (
            job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

    def test_submit_job_wirecut(self):
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
        StLibrary.submit_job(self.client, job_info)
        job_results = StLibrary.wait_and_get_job_result(
            self.client, job_info, self.timeout, self.interval
        )
        StLibrary.delete_job(self.client, job_info["job_id"])
        assert (
            job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

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
        StLibrary.submit_job(self.client, first_job_info)

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
        StLibrary.submit_job(self.client, second_job_info)

        result, err_msg, _ = StLibrary.get_job_status(
            self.client, first_job_info["job_id"]
        )
        assert result is False
        assert "QUEUED" in err_msg
        result, err_msg, _ = StLibrary.get_job_status(
            self.client, second_job_info["job_id"]
        )
        assert result is False
        assert "QUEUED" in err_msg

        time.sleep(20)
        result, err_msg, _ = StLibrary.get_job_status(
            self.client, first_job_info["job_id"]
        )
        assert result is False
        assert "RUNNING" in err_msg
        result, err_msg, _ = StLibrary.get_job_status(
            self.client, second_job_info["job_id"]
        )
        assert result is False
        assert "QUEUED" in err_msg

        time.sleep(5)
        first_job_results = StLibrary.wait_and_get_job_result(
            self.client, first_job_info, self.timeout, self.interval
        )
        StLibrary.delete_job(self.client, first_job_info["job_id"])
        assert (
            first_job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

        second_job_results = StLibrary.wait_and_get_job_result(
            self.client, second_job_info, self.timeout, self.interval
        )
        StLibrary.delete_job(self.client, second_job_info["job_id"])
        assert (
            second_job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

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
        StLibrary.submit_job(self.client, first_job_info)

        second_job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "submit_two_diff_priority_jobs_2",
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
        StLibrary.submit_job(self.client, second_job_info)

        result, err_msg, _ = StLibrary.get_job_status(
            self.client, first_job_info["job_id"]
        )
        assert result is False
        assert "QUEUED" in err_msg
        result, err_msg, _ = StLibrary.get_job_status(
            self.client, second_job_info["job_id"]
        )
        assert result is False
        assert "QUEUED" in err_msg

        time.sleep(3)
        result, err_msg, _ = StLibrary.get_job_status(
            self.client, first_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg

        result, err_msg, _ = StLibrary.get_job_status(
            self.client, second_job_info["job_id"]
        )
        assert result is True

        time.sleep(5)
        first_job_results = StLibrary.wait_and_get_job_result(
            self.client, first_job_info, self.timeout, self.interval
        )
        StLibrary.delete_job(self.client, first_job_info["job_id"])
        assert (
            first_job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

        second_job_results = StLibrary.wait_and_get_job_result(
            self.client, second_job_info, self.timeout, self.interval
        )
        StLibrary.delete_job(self.client, second_job_info["job_id"])
        assert (
            second_job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

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
            "driver_options": {"sleep": 30},
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        StLibrary.submit_job(self.client, first_job_info)

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
            "driver_options": {"sleep": 30},
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        StLibrary.submit_job(self.client, second_job_info)

        result, err_msg, _ = StLibrary.get_job_status(
            self.client, first_job_info["job_id"]
        )
        if result is False:
            assert "QUEUED" in err_msg
        result, err_msg, _ = StLibrary.get_job_status(
            self.client, second_job_info["job_id"]
        )
        if result is False:
            assert "QUEUED" in err_msg

        time.sleep(1)
        result, err_msg, _ = StLibrary.get_job_status(
            self.client, first_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg
        result, err_msg, _ = StLibrary.get_job_status(
            self.client, second_job_info["job_id"]
        )
        if result is False:
            assert "RUNNING" in err_msg or "QUEUED" in err_msg

        time.sleep(10)
        first_job_results = StLibrary.wait_and_get_job_result(
            self.client, first_job_info, self.timeout, self.interval
        )
        StLibrary.delete_job(self.client, first_job_info["job_id"])
        assert (
            first_job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

        second_job_results = StLibrary.wait_and_get_job_result(
            self.client, second_job_info, self.timeout, self.interval
        )
        StLibrary.delete_job(self.client, second_job_info["job_id"])
        assert (
            second_job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )
