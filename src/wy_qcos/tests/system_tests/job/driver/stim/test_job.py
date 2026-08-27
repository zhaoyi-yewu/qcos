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
@pytest.mark.driver
class TestJob:
    """Test Job for Stim QEC driver."""

    test_job_names = [
        "test_stim_submit_job",
        "test_stim_submit_job_profiling",
        "test_stim_submit_job_with_distance",
        "test_stim_submit_job_with_phy_bit_num",
        "test_stim_submit_job_with_logical_bit_num",
        "test_stim_submit_job_unsupported_bit_num",
        "test_stim_submit_job_unsupported_gate",
        "test_stim_submit_job_unsupported_qec_code",
        "test_stim_submit_job_enable_mapping",
        "test_stim_submit_job_two_qubits_gate",
        "test_stim_submit_job_with_x_error",
        "test_stim_submit_job_with_y_error",
        "test_stim_submit_job_with_z_error",
        "test_stim_submit_job_with_random_error",
        "test_stim_submit_job_with_custom_noise_prob",
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
    def assert_qec_results(job_results):
        """Assert QEC results structure.

        The Stim driver produces single-qubit logical measurement results
        as a count dict, e.g. {"0": N, "1": M} where N + M = shots.
        """
        assert "result" in job_results
        assert "results" in job_results["result"]
        assert isinstance(job_results["result"]["results"], list)
        assert len(job_results["result"]["results"]) == 1
        results_0 = job_results["result"]["results"][0]
        r_0 = results_0["results"].get("0", 0)
        r_1 = results_0["results"].get("1", 0)
        assert r_0 + r_1 == Constant.DEFAULT_SHOTS
        assert results_0["num_qubits"] == 1

    @pytest.mark.smoke
    def test_stim_submit_job(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            self.assert_qec_results(job_results)
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    def test_stim_submit_job_profiling(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job_profiling",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job_profiling",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": [
                Constant.PROFILING_TYPE_CODE,
                Constant.PROFILING_TYPE_SCHEDULING,
                Constant.PROFILING_TYPE_DRIVER_PARSE,
                Constant.PROFILING_TYPE_DRIVER_TRANSPILE,
                Constant.PROFILING_TYPE_DRIVER_RUN,
            ],
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
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
            self.assert_qec_results(job_results)
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

    def test_stim_submit_job_with_distance(self):
        """Test QEC job with custom distance parameter."""
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job_with_distance",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job_with_distance",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
                "distance": 3,
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            self.assert_qec_results(job_results)
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    def test_stim_submit_job_with_phy_bit_num(self):
        """Test QEC job with custom physical bit number."""
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job_with_phy_bit_num",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job_phy_bit_num",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
                "phy_bit_num": 9,
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            self.assert_qec_results(job_results)
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    def test_stim_submit_job_with_logical_bit_num(self):
        """Test QEC job with custom logical bit number."""
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job_with_logical_bit_num",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job_logical_bit_num",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
                "logical_bit_num": 1,
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            self.assert_qec_results(job_results)
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    @pytest.mark.smoke
    def test_stim_submit_job_unsupported_bit_num(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job",
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
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
                "Shor does not support 2 bits qec"
                in job_results["result"]["results"][0]["error"]["message"]
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    @pytest.mark.smoke
    def test_stim_submit_job_unsupported_gate(self):
        test_qasm = """
            OPENQASM 2.0;
            include "qelib1.inc";

            qreg q[1];
            creg c[1];
            rx(1) q[0];

            measure q -> c;
        """
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job",
            "source_code_list": [test_qasm],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
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
                "Cannot decompose gate(s) ['rx']"
                in job_results["result"]["results"][0]["error"]["message"]
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    @pytest.mark.smoke
    def test_stim_submit_job_unsupported_qec_code(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "surface",
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
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
                "Unknown quantum error correction code: 'surface'."
                in job_results["result"]["results"][0]["error"]["message"]
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    @pytest.mark.smoke
    def test_stim_submit_job_enable_mapping(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "surface",
            },
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
                "Missing qpu configs"
                in job_results["result"]["results"][0]["error"]["message"]
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    @pytest.mark.smoke
    def test_stim_submit_job_two_qubits_gate(self):
        test_qasm = """
            OPENQASM 2.0;
            include "qelib1.inc";

            qreg q[2];
            creg c[2];
            cx q[0], q[1];

            measure q[0] -> c[0];
            measure q[1] -> c[1];
        """
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job",
            "source_code_list": [test_qasm],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
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
                "Shor does not support 2 bits qec"
                in job_results["result"]["results"][0]["error"]["message"]
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    def test_stim_submit_job_with_x_error(self):
        """Test QEC job with x_error injection."""
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job_with_x_error",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job_with_x_error",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
                "error_inject": {"error_type": "x_error", "noise_prob": 0.05},
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            self.assert_qec_results(job_results)
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    def test_stim_submit_job_with_y_error(self):
        """Test QEC job with y_error injection."""
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job_with_y_error",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job_with_y_error",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
                "error_inject": {"error_type": "y_error", "noise_prob": 0.02},
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            self.assert_qec_results(job_results)
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    def test_stim_submit_job_with_z_error(self):
        """Test QEC job with z_error injection."""
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job_with_z_error",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job_with_z_error",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
                "error_inject": {"error_type": "z_error", "noise_prob": 0.03},
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            self.assert_qec_results(job_results)
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    def test_stim_submit_job_with_random_error(self):
        """Test QEC job with random_error injection."""
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job_with_random_error",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "test_stim_submit_job_with_random_error",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
                "error_inject": {
                    "error_type": "depolarize",
                    "noise_prob": 0.01,
                },
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            self.assert_qec_results(job_results)
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True

    def test_stim_submit_job_with_custom_noise_prob(self):
        """Test QEC job with custom noise_prob parameter."""
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_stim_submit_job_with_custom_noise_prob",
            "source_code_list": [SAMPLES["simple-qasm-1-bit.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM2,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_stim_submit_job_custom_noise",
            "backend": "stim",
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "qec_options": {
                "qec_code": "shor",
                "error_inject": {"error_type": "x_error", "noise_prob": 0.1},
            },
            "transpiler_options": {
                "enable_mapping": False,
            },
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            self.assert_qec_results(job_results)
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        StLibrary.delete_job(self.admin_client, job_info["job_id"])
        assert success is True
