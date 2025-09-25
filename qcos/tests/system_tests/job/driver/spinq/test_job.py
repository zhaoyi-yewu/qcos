#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
import multiprocessing
import pytest
import time

import qcos.api.posiq.routes_jsonrpc.errors as jsonrpc_errors
from qcos.common.constant import Constant, HttpCode
from qcos.common.library import Library
from qcos.tests.system_tests.common.library import StLibrary
from qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES
from .spinq_rpc_server import main


@pytest.mark.usefixtures("global_configs")
class TestJob:
    @classmethod
    def setup_class(cls):
        cls.client = GLOBAL_CONFIGS["client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        print("Start SpinQ server")
        cls.rpc_process = multiprocessing.Process(
            target=main,
            daemon=True
        )
        cls.rpc_process.start()

    @classmethod
    def teardown_class(cls):
        print("Stop SpinQ server")
        cls.rpc_process.terminate()

    def test_submit_job(self):
        driver_name = "spinq_rpc"
        qasm_content = SAMPLES["simple-qasm.qasm"]
        source_code_list = [qasm_content]
        code_type = Constant.CODE_TYPE_QASM
        job_id = str(Library.create_uuid(prefix=[0xf0]))
        job_name = "test_spinq_submit_job"
        circuit_aggregation = None
        job_type = Constant.JOB_TYPE_SAMPLING
        job_priority = Constant.DEFAULT_JOB_PRIORITY
        description = "description: test_spinq_submit_job"
        shots = Constant.DEFAULT_SHOTS
        backend = driver_name
        driver_options = None
        transpiler = Constant.TRANSPILER_CMSS
        transpiler_options = None
        profiling = None
        callbacks = None
        dry_run = False
        status_code, reason, text, response = self.client.submit_job(
            source_code_list,
            code_type=code_type,
            job_id=job_id,
            circuit_aggregation=circuit_aggregation,
            job_name=job_name,
            job_type=job_type,
            job_priority=job_priority,
            description=description,
            shots=shots,
            backend=backend,
            driver_options=driver_options,
            transpiler=transpiler,
            transpiler_options=transpiler_options,
            profiling=profiling,
            callbacks=callbacks,
            dry_run=dry_run)
        assert status_code == HttpCode.SUCCESS_OK
        json_results = json.loads(text)
        result = json_results["result"]

        # check results from submit_job
        assert result["job_id"] == job_id
        assert result["job_name"] == job_name
        assert result["job_type"] == job_type
        assert result["job_priority"] == job_priority
        assert result["description"] == description
        assert result["shots"] == shots
        assert result["backend"] == backend
        assert result["driver_options"] == driver_options
        assert result["transpiler"] == transpiler
        assert result["transpiler_options"] == transpiler_options
        assert result["profiling"] == profiling
        assert result["callbacks"] == callbacks
        assert result["dry_run"] == dry_run

        # wait for job status to COMPLETED
        success, err_msg, _ = Library.loop_with_timeout(
            StLibrary.get_results,
            self.timeout,
            self.interval,
            self.client,
            job_id)
        # wait for additional time for job to finish resource cleanup
        time.sleep(5)

        # check results
        status_code, reason, text, response = self.client.get_job_results(
            job_id)
        assert status_code == HttpCode.SUCCESS_OK
        job_result = json.loads(text)
        job_error = job_result.get("error", {})
        error_code = job_error.get("code", 0)
        assert error_code == 0
        status_code, reason, text, response = self.client.delete_jobs([job_id])
        assert status_code == HttpCode.SUCCESS_OK

        # check if job deleted
        status_code, reason, text, response = self.client.get_job_results(
            job_id)
        assert status_code == HttpCode.SUCCESS_OK
        job_result = json.loads(text)
        job_error = job_result.get("error", {})
        error_code = job_error.get("code", 0)
        assert error_code == jsonrpc_errors.NotFoundError.CODE
