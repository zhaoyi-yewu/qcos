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

import logging

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("global_configs")
class TestWirecut:
    test_job_names = ["test_weave_wirecut"]

    @classmethod
    def setup_class(cls):
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        cls.wirecut_qasm = Library.read_file(
            f"{cls.samples_dir}/qasm/2.0/wirecut/3_8.qasm"
        )
        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)

    @classmethod
    def teardown_class(cls):
        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)

    @pytest.mark.smoke
    def test_submit_job_wirecut(self):
        """Wirecut batch should fail when only part of it can be mapped."""
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_weave_wirecut",
            "source_code_list": [self.wirecut_qasm],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_weave_wirecut",
            "backend": Constant.DEVICE_DUMMY,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": {
                "enable_wirecut": True,
                "max_qubits": 2,
            },
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": {
                "enable_mapping": True,
                "enable_na_move": True,
            },
            "profiling": None,
            "callbacks": None,
            "dry_run": True,
        }
        try:
            StLibrary.submit_job(self.admin_client, job_info)
            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                self.admin_client, job_info, self.timeout, self.interval
            )
            if success:
                result = job_results["result"]
                assert result["job_status"] == Constant.JOB_STATUS_FAILED
                assert len(result["results"]) == 1
                circuit_result = result["results"][0]
                assert (
                    "Wirecut batch result count does not match subcircuits"
                    in circuit_result["error"]["message"]
                )
            else:
                logger.warning(
                    f"Job failed. err_msg: {err_msg}, "
                    f"job_results: {job_results}"
                )
            assert success is True
        finally:
            StLibrary.cleanup_test_jobs(
                self.admin_client, ["test_weave_wirecut"]
            )
