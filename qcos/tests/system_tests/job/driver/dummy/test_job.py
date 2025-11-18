#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.tests.system_tests.common.library import StLibrary
from qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES


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

    def test_submit_job(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_job",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_job",
            "backend": Constant.DRIVER_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
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

    def test_submit_job_dry_run(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_submit_job",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_job",
            "backend": Constant.DRIVER_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": True,
        }
        job_results = StLibrary.submit_job(
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
            "job_name": "test_submit_job",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_submit_job",
            "backend": Constant.DRIVER_DUMMY,
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
        job_results = StLibrary.submit_job(
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
