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
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("global_configs")
class TestAggregate:
    test_job_names = [
        "test_weave_internal_aggregate",
        "test_weave_external_aggregate_parent",
        "test_weave_external_aggregate_sub",
    ]

    @classmethod
    def setup_class(cls):
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)

    @classmethod
    def teardown_class(cls):
        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)

    @staticmethod
    def assert_qutip_results(circuit_result, num_qubits, expected_results):
        assert circuit_result["num_qubits"] == num_qubits
        assert circuit_result["results"] == expected_results
        assert all(
            len(bitstring) == num_qubits
            for bitstring in circuit_result["results"].keys()
        )

    @pytest.mark.smoke
    def test_submit_job_internal_aggregate(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_weave_internal_aggregate",
            "source_code_list": [
                SAMPLES["simple-qasm-1-bit.qasm"],
            ],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_weave_internal_aggregate",
            "backend": "qutip_sim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": Constant.AGGREGATION_TYPE_INTERNAL,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        try:
            StLibrary.submit_job(self.admin_client, job_info)
            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                self.admin_client, job_info, self.timeout, self.interval
            )
            if success:
                result = job_results["result"]
                assert result["job_status"] == Constant.JOB_STATUS_COMPLETED
                assert len(result["results"]) == 1
                self.assert_qutip_results(
                    result["results"][0],
                    1,
                    {"0": Constant.DEFAULT_SHOTS},
                )
            else:
                logger.warning(
                    f"Job failed. err_msg: {err_msg}, "
                    f"job_results: {job_results}"
                )
            assert success is True
        finally:
            StLibrary.cleanup_test_jobs(
                self.admin_client, ["test_weave_internal_aggregate"]
            )

    @pytest.mark.smoke
    def test_submit_job_external_aggregate(self):
        parent_job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_weave_external_aggregate_parent",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_weave_external_aggregate_parent",
            "backend": "qutip_sim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": Constant.AGGREGATION_TYPE_EXTERNAL,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        sub_job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_weave_external_aggregate_sub",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_weave_external_aggregate_sub",
            "backend": "qutip_sim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": Constant.AGGREGATION_TYPE_EXTERNAL,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }

        StLibrary.submit_job(self.admin_client, parent_job_info)
        StLibrary.submit_job(self.admin_client, sub_job_info)

        parent_success, parent_err_msg, parent_results = (
            StLibrary.wait_and_get_job_result(
                self.admin_client,
                parent_job_info,
                self.timeout,
                self.interval,
            )
        )
        sub_success, sub_err_msg, sub_results = (
            StLibrary.wait_and_get_job_result(
                self.admin_client,
                sub_job_info,
                self.timeout,
                self.interval,
            )
        )

        try:
            if parent_success and sub_success:
                parent_result = parent_results["result"]
                sub_result = sub_results["result"]
                assert parent_result["job_status"] == (
                    Constant.JOB_STATUS_COMPLETED
                )
                assert sub_result["job_status"] == (
                    Constant.JOB_STATUS_COMPLETED
                )
                assert len(parent_result["results"]) == 1
                assert len(sub_result["results"]) == 1

                parent_circuit_result = parent_result["results"][0]
                sub_circuit_result = sub_result["results"][0]
                self.assert_qutip_results(
                    parent_circuit_result,
                    1,
                    {"0": Constant.DEFAULT_SHOTS},
                )
                self.assert_qutip_results(
                    sub_circuit_result,
                    2,
                    {"00": Constant.DEFAULT_SHOTS},
                )
            else:
                logger.warning(
                    "External aggregate job failed. "
                    f"parent_err_msg: {parent_err_msg}, "
                    f"parent_results: {parent_results}, "
                    f"sub_err_msg: {sub_err_msg}, sub_results: {sub_results}"
                )
            assert parent_success is True
            assert sub_success is True
        finally:
            StLibrary.cleanup_test_jobs(
                self.admin_client,
                [
                    "test_weave_external_aggregate_parent",
                    "test_weave_external_aggregate_sub",
                ],
            )
