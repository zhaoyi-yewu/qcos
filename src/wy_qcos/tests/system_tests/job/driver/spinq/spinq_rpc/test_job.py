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

import multiprocessing
import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES
from .spinq_rpc_api_server import main


@pytest.mark.usefixtures("global_configs")
class TestJob:
    @classmethod
    def setup_class(cls):
        cls.client = GLOBAL_CONFIGS["client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        print("Start SpinQ server")
        cls.rpc_process = multiprocessing.Process(target=main, daemon=True)
        cls.rpc_process.start()

    @classmethod
    def teardown_class(cls):
        print("Stop SpinQ server")
        cls.rpc_process.terminate()

    def test_submit_job(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_spinq_submit_job",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_spinq_submit_job",
            "backend": "spinq_rpc",
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
            "job_name": "test_spinq_submit_job",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_spinq_submit_job",
            "backend": "spinq_rpc",
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

    def test_submit_job_with_multiple_source_code(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_spinq_submit_job",
            "source_code_list": [
                SAMPLES["simple-qasm.qasm"],
                SAMPLES["simple-qasm.qasm"],
            ],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_spinq_submit_job",
            "backend": "spinq_rpc",
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
