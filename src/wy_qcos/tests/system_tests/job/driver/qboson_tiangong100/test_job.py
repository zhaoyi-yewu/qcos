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
import time

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES
from .tiangong_api_server import main


@pytest.mark.usefixtures("global_configs")
class TestJob:
    @classmethod
    def setup_class(cls):
        cls.client = GLOBAL_CONFIGS["client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        cls.tiangong_process = multiprocessing.Process(
            target=main, daemon=True
        )
        cls.tiangong_process.start()

    @classmethod
    def teardown_class(cls):
        print("Stop tiangong server")
        cls.tiangong_process.terminate()

    def test_submit_job(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_tiangong_submit_job",
            "source_code_list": [SAMPLES["simple-qubo.json"]],
            "code_type": Constant.CODE_TYPE_QUBO,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_tiangong_submit_job",
            "backend": "tiangong100",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": None,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        job_results = StLibrary.submit_job(
            self.client, job_info, self.timeout, self.interval
        )
        StLibrary.delete_job(self.client, job_info["job_id"])
        assert (
            job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )

    def test_submit_job_enable_subqubo(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_qboson_submit_job",
            "source_code_list": [SAMPLES["qubo_200X200.json"]],
            "code_type": Constant.CODE_TYPE_QUBO,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_qboson_submit_job",
            "backend": "tiangong100",
            "shots": 100,
            "circuit_aggregation": None,
            "driver_options": {"enable_subqubo": True},
            "transpiler": None,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        job_results = StLibrary.submit_job(
            self.client, job_info, self.timeout, self.interval
        )
        assert job_results["result"]["job_status"] in [
            Constant.JOB_STATUS_QUEUED,
            Constant.JOB_STATUS_RUNNING,
            Constant.JOB_STATUS_COMPLETED,
        ]
        while job_results["result"]["job_status"] in [
            Constant.JOB_STATUS_QUEUED,
            Constant.JOB_STATUS_RUNNING,
        ]:
            job_results = StLibrary.get_job_results(
                self.client, job_info["job_id"]
            )
            time.sleep(self.interval)
        StLibrary.delete_job(self.client, job_info["job_id"])
        assert (
            job_results["result"]["job_status"]
            == Constant.JOB_STATUS_COMPLETED
        )
