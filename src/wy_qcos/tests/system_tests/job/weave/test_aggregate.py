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
        "test_agg_diff_specs_job1",
        "test_agg_diff_specs_job2",
        "test_agg_exceed_max_jobs",
        "test_agg_external_exceed_max_job_0",
        "test_agg_external_exceed_max_job_1",
        "test_agg_external_exceed_max_job_2",
        "test_agg_external_exceed_max_job_3",
        "test_agg_external_exceed_max_job_4",
        "test_agg_external_exceed_max_job_5",
        "test_agg_external_exceed_max_job_6",
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
    def assert_results(circuit_result, num_qubits, expected_results):
        assert circuit_result["num_qubits"] == num_qubits
        assert all(
            len(bitstring) == num_qubits
            for bitstring in circuit_result["results"].keys()
        )

    @pytest.mark.smoke
    def test_submit_job_internal_aggregate_dummy(self):
        self._test_submit_job_internal_aggregate("dummy")

    def test_submit_job_internal_aggregate_qutip(self):
        self._test_submit_job_internal_aggregate("qutip_sim")

    def _test_submit_job_internal_aggregate(self, device_name):
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
            "backend": device_name,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": Constant.AGGREGATION_TYPE_INTERNAL,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": {"enable_mapping": True},
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        try:
            StLibrary.submit_job(self.admin_client, job_info)
            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                self.admin_client,
                job_info,
                self.timeout,
                self.interval,
            )
            if success:
                result = job_results["result"]
                assert result["job_status"] == (Constant.JOB_STATUS_COMPLETED)
                assert len(result["results"]) == 1
                self.assert_results(
                    result["results"][0],
                    1,
                    {"1": Constant.DEFAULT_SHOTS},
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
    def test_submit_job_external_aggregate_dummy(self):
        self._test_submit_job_external_aggregate("dummy")

    def test_submit_job_external_aggregate_qutip(self):
        self._test_submit_job_external_aggregate("qutip_sim")

    def _test_submit_job_external_aggregate(self, device_name):
        parent_job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_weave_external_aggregate_parent",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": (
                "description: test_weave_external_aggregate_parent"
            ),
            "backend": device_name,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": Constant.AGGREGATION_TYPE_EXTERNAL,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": {"enable_mapping": True},
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
            "backend": device_name,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": Constant.AGGREGATION_TYPE_EXTERNAL,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": {"enable_mapping": True},
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
                self.assert_results(
                    parent_circuit_result,
                    1,
                    {"1": Constant.DEFAULT_SHOTS},
                )
                self.assert_results(
                    sub_circuit_result,
                    2,
                    {"11": Constant.DEFAULT_SHOTS},
                )
            else:
                logger.warning(
                    "External aggregate job failed. "
                    f"parent_err_msg: {parent_err_msg}, "
                    f"parent_results: {parent_results}, "
                    f"sub_err_msg: {sub_err_msg}, "
                    f"sub_results: {sub_results}"
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

    def test_aggregate_different_specs_cannot_aggregate(self):
        """Jobs with different specs (backend) should not aggregate.

        Two external aggregate jobs submitted to different backends
        should run independently without aggregation.
        """
        job1_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_agg_diff_specs_job1",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "diff specs job1 (dummy1)",
            "backend": "dummy1",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": Constant.AGGREGATION_TYPE_EXTERNAL,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": {"enable_mapping": True},
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        job2_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_agg_diff_specs_job2",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "diff specs job2 (dummy)",
            "backend": "dummy2",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": Constant.AGGREGATION_TYPE_EXTERNAL,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": {"enable_mapping": True},
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        try:
            StLibrary.submit_job(self.admin_client, job1_info)
            StLibrary.submit_job(self.admin_client, job2_info)

            success1, err1, results1 = StLibrary.wait_and_get_job_result(
                self.admin_client,
                job1_info,
                self.timeout,
                self.interval,
            )
            success2, err2, results2 = StLibrary.wait_and_get_job_result(
                self.admin_client,
                job2_info,
                self.timeout,
                self.interval,
            )
            # Both jobs should complete independently
            assert success1 is True, f"Job1 failed: {err1}"
            assert success2 is True, f"Job2 failed: {err2}"
            r1 = results1["result"]
            r2 = results2["result"]
            assert r1["job_status"] == Constant.JOB_STATUS_COMPLETED
            assert r2["job_status"] == Constant.JOB_STATUS_COMPLETED
            # Each job should have exactly 1 result (not aggregated)
            assert len(r1["results"]) == 1
            assert len(r2["results"]) == 1
            # circuit_aggregation should not be set
            assert (
                r1["results"][0]["metadata"].get("circuit_aggregation", None)
                is None
            )
            assert (
                r2["results"][0]["metadata"].get("circuit_aggregation", None)
                is None
            )
        finally:
            StLibrary.cleanup_test_jobs(
                self.admin_client,
                [
                    "test_agg_diff_specs_job1",
                    "test_agg_diff_specs_job2",
                ],
            )

    def test_internal_aggregate_exceeds_max_jobs(self):
        """Internal aggregate with > MAX_AGGREGATION_JOBS jobs.

        Submitting an internal aggregate job with more than
        Constant.MAX_AGGREGATION_JOBS source code files should fail
        with a validation error.
        """
        # Create more source codes than MAX_AGGREGATION_JOBS
        num_codes = Constant.MAX_AGGREGATION_JOBS + 1
        source_code_list = [SAMPLES["simple-qasm-1-bit.qasm"]] * num_codes

        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_agg_exceed_max_jobs",
            "source_code_list": source_code_list,
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": (
                f"exceeds max aggregation jobs ({num_codes} > "
                f"{Constant.MAX_AGGREGATION_JOBS})"
            ),
            "backend": "dummy",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": Constant.AGGREGATION_TYPE_INTERNAL,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": {"enable_mapping": True},
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        try:
            status_code, reason, text, result = StLibrary.submit_job(
                self.admin_client, job_info
            )
        except AssertionError as e:
            assert (
                f"length of value should <= {Constant.MAX_AGGREGATION_JOBS}"
                in str(e)
            )
        finally:
            StLibrary.cleanup_test_jobs(
                self.admin_client, ["test_agg_exceed_max_jobs"]
            )

    def test_external_aggregate_exceeds_max_jobs(self):
        """External aggregate with > MAX_AGGREGATION_JOBS jobs.

        Submitting more than MAX_AGGREGATION_JOBS external aggregate
        jobs to the same backend. Only MAX_AGGREGATION_JOBS jobs
        should be aggregated; the excess job runs independently.
        All jobs should complete successfully.
        """
        num_jobs = Constant.MAX_AGGREGATION_JOBS + 2
        job_infos = []
        job_names = []
        circuit_aggregation_count = 0
        for i in range(num_jobs):
            job_name = f"test_agg_external_exceed_max_job_{i}"
            job_names.append(job_name)
            # first job will wait for external aggregation
            driver_options = {"sleep": 10}
            if i > 0:
                driver_options = None
            job_info = {
                "job_id": str(Library.create_uuid(prefix=[0xF0])),
                "job_name": job_name,
                "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
                "code_type": Constant.CODE_TYPE_QASM,
                "job_type": Constant.JOB_TYPE_SAMPLING,
                "job_priority": Constant.DEFAULT_JOB_PRIORITY,
                "description": (f"external aggregate exceed max job {i}"),
                "backend": "dummy",
                "shots": Constant.DEFAULT_SHOTS,
                "circuit_aggregation": (Constant.AGGREGATION_TYPE_EXTERNAL),
                "driver_options": driver_options,
                "transpiler": Constant.TRANSPILER_CMSS,
                "transpiler_options": {"enable_mapping": True},
                "profiling": None,
                "callbacks": None,
                "dry_run": False,
            }
            job_infos.append(job_info)

        try:
            # Submit all jobs
            for i, job_info in enumerate(job_infos):
                StLibrary.submit_job(self.admin_client, job_info)

            # Wait for all jobs to complete
            all_success = True
            for job_info in job_infos:
                success, err_msg, results = StLibrary.wait_and_get_job_result(
                    self.admin_client,
                    job_info,
                    self.timeout,
                    self.interval,
                )
                if not success:
                    logger.warning(
                        f"Job {job_info['job_name']} failed: "
                        f"{err_msg}, results: {results}"
                    )
                    all_success = False
                else:
                    result = results["result"]
                    assert result["job_status"] == (
                        Constant.JOB_STATUS_COMPLETED
                    ), (
                        f"Job {job_info['job_name']} status: "
                        f"{result['job_status']}"
                    )
                    circuit_aggregation = result["results"][0]["metadata"].get(
                        "circuit_aggregation", None
                    )
                    if (
                        circuit_aggregation
                        == Constant.AGGREGATION_TYPE_EXTERNAL
                    ):
                        circuit_aggregation_count += 1

            # All jobs should complete successfully even though
            # only MAX_AGGREGATION_JOBS can be aggregated
            assert all_success is True, (
                "Not all external aggregate jobs completed successfully"
            )
            # check max aggregation counts
            assert circuit_aggregation_count == Constant.MAX_AGGREGATION_JOBS
        finally:
            StLibrary.cleanup_test_jobs(self.admin_client, job_names)
