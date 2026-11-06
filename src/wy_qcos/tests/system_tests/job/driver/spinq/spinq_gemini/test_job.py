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
import multiprocessing

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES
from .spinq_gemini_api_server import main

logger = logging.getLogger(__name__)

SPINQ_GEMINI_SHOTS = 1024
BACKEND = "spinq_gemini"
TRANSPILER_OPTIONS = {"enable_mapping": False}


@pytest.mark.usefixtures("global_configs")
@pytest.mark.driver
class TestJob:
    """Test Job for spinq_gemini driver.

    A mock SpinQ Cloud server (spinq_gemini_api_server.py) is started
    on port 18626 to emulate the Gemini NMR cloud API.
    """

    test_job_names = [
        "test_spinq_gemini_submit_job",
        "test_spinq_gemini_submit_job_dry_run",
        "test_spinq_gemini_submit_job_profiling",
        "test_spinq_gemini_submit_multi_circuit",
    ]

    @classmethod
    def setup_class(cls):
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        cls.api_host = "127.0.0.1"
        cls.api_port = 18626

        cls.spinq_process = multiprocessing.Process(
            target=main,
            daemon=True,
            kwargs={"port": cls.api_port},
        )
        cls.spinq_process.start()

        connected = Library.wait_network_connection(
            cls.api_host,
            port=cls.api_port,
        )
        assert connected, (
            f"Failed to connect to spinq_gemini mock server at "
            f"{cls.api_host}:{cls.api_port}"
        )

        # Generate a test RSA keyfile for SpinQ Cloud auth if absent.
        # The mock server does not verify the signature, so any valid
        # RSA private key is sufficient.
        StLibrary.ensure_spinq_test_keyfile()

        try:
            cls.admin_client.set_device(
                BACKEND,
                enable=True,
                state="online",
            )
        except Exception as e:
            logger.warning(f"Could not set {BACKEND} device online: {e}")

        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)

    @classmethod
    def teardown_class(cls):
        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)
        print("Stop spinq_gemini mock server")
        cls.spinq_process.terminate()

    @staticmethod
    def assert_spinq_gemini_results(job_results):
        """Assert results match expected circuit output.

        The test circuit (simple-qasm.qasm) applies X to q[0] and
        q[1], so the expected measurement is "11" with 100% probability.
        """
        assert "result" in job_results
        assert "results" in job_results["result"]
        assert isinstance(job_results["result"]["results"], list)
        assert len(job_results["result"]["results"]) == 1
        results_0 = job_results["result"]["results"][0]
        counts = results_0.get("results")
        assert counts is not None, (
            f"results is None. error: {job_results.get('error')}, "
            f"metadata: {job_results.get('metadata')}"
        )
        total = sum(counts.values())
        assert total == SPINQ_GEMINI_SHOTS, (
            f"Expected total counts == {SPINQ_GEMINI_SHOTS}, got {total}"
        )
        assert results_0["num_qubits"] == 2

    def _make_job_info(self, job_name, **overrides):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": job_name,
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": f"description: {job_name}",
            "backend": BACKEND,
            "shots": SPINQ_GEMINI_SHOTS,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": TRANSPILER_OPTIONS,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        job_info.update(overrides)
        return job_info

    @pytest.mark.smoke
    def test_spinq_gemini_submit_job(self):
        """Submit a sampling job to spinq_gemini and verify results."""
        job_info = self._make_job_info("test_spinq_gemini_submit_job")
        self.admin_client.set_device(job_info["backend"], state="online")
        StLibrary.submit_job(self.admin_client, job_info)
        self.admin_client.set_device(job_info["backend"], state="auto")
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            self.assert_spinq_gemini_results(job_results)
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

    def test_spinq_gemini_submit_job_dry_run(self):
        """Submit a dry-run job to spinq_gemini and verify completion."""
        job_info = self._make_job_info(
            "test_spinq_gemini_submit_job_dry_run",
            dry_run=True,
        )
        self.admin_client.set_device(job_info["backend"], state="online")
        StLibrary.submit_job(self.admin_client, job_info)
        self.admin_client.set_device(job_info["backend"], state="auto")
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
            StLibrary.delete_job(self.admin_client, job_info["job_id"])
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True

    def test_spinq_gemini_submit_job_profiling(self):
        """Submit a job with profiling and verify profiling metrics."""
        job_info = self._make_job_info(
            "test_spinq_gemini_submit_job_profiling",
            profiling=[
                Constant.PROFILING_TYPE_CODE,
                Constant.PROFILING_TYPE_SCHEDULING,
                Constant.PROFILING_TYPE_DRIVER_PARSE,
                Constant.PROFILING_TYPE_DRIVER_TRANSPILE,
                Constant.PROFILING_TYPE_DRIVER_RUN,
            ],
        )
        self.admin_client.set_device(job_info["backend"], state="online")
        StLibrary.submit_job(self.admin_client, job_info)
        self.admin_client.set_device(job_info["backend"], state="auto")
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
                profiling_results[Constant.PROFILING_TYPE_DRIVER_PARSE],
                float,
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

    def test_spinq_gemini_submit_multi_circuit(self):
        """Submit multiple circuits with circuit aggregation.

        Uses two 1-qubit circuits (1+1=2) to stay within Gemini's
        max_qubits=2 limit.
        """
        job_info = self._make_job_info(
            "test_spinq_gemini_submit_multi_circuit",
            source_code_list=[
                SAMPLES["simple-qasm-1-bit.qasm"],
                SAMPLES["simple-qasm-1-bit.qasm"],
            ],
            circuit_aggregation=Constant.AGGREGATION_TYPE_INTERNAL,
        )
        self.admin_client.set_device(job_info["backend"], state="online")
        StLibrary.submit_job(self.admin_client, job_info)
        self.admin_client.set_device(job_info["backend"], state="auto")
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )
        if success:
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
            StLibrary.delete_job(self.admin_client, job_info["job_id"])
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True
