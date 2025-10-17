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
import time

import qcos.api.posiq.routes_jsonrpc.errors as jsonrpc_errors
from qcos.common.constant import Constant, HttpCode
from qcos.common.library import Library


class StLibrary:
    """ST Library"""

    @staticmethod
    def submit_job(client, job_info, timeout=30, interval=5):
        job_id = job_info["job_id"]
        job_name = job_info["job_name"]
        source_code_list = job_info["source_code_list"]
        code_type = job_info["code_type"]
        circuit_aggregation = job_info["circuit_aggregation"]
        job_type = job_info["job_type"]
        job_priority = job_info["job_priority"]
        description = job_info["description"]
        shots = job_info["shots"]
        backend = job_info["backend"]
        driver_options = job_info["driver_options"]
        transpiler = job_info["transpiler"]
        transpiler_options = job_info["transpiler_options"]
        profiling = job_info["profiling"]
        callbacks = job_info["callbacks"]
        dry_run = job_info["dry_run"]
        status_code, reason, text, response = client.submit_job(
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
            dry_run=dry_run,
        )
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
            StLibrary.get_job_status,
            timeout,
            interval,
            client,
            job_id,
        )
        # wait for additional time for job to finish resource cleanup
        time.sleep(5)

        # check results
        job_result = StLibrary.get_job_results(client, job_id)

        return job_result

    @staticmethod
    def get_job_results(client, job_id):
        status_code, reason, text, response = client.get_job_results(job_id)
        assert status_code == HttpCode.SUCCESS_OK
        job_result = json.loads(text)
        job_error = job_result.get("error", {})
        error_code = job_error.get("code", 0)
        assert error_code == 0
        return job_result

    @staticmethod
    def get_job_status(client, job_id):
        _status_code, _reason, _text, _response = client.get_job_status(job_id)
        job_result = json.loads(_text)
        job_status = job_result["result"]["job_status"]
        if job_status in [
            Constant.JOB_STATUS_COMPLETED,
            Constant.JOB_STATUS_FAILED,
            Constant.JOB_STATUS_CANCELLED,
        ]:
            return True
        return False

    @staticmethod
    def delete_job(client, job_id):
        status_code, reason, text, response = client.delete_jobs([job_id])
        assert status_code == HttpCode.SUCCESS_OK

        # check if job deleted
        status_code, reason, text, response = client.get_job_results(job_id)
        assert status_code == HttpCode.SUCCESS_OK
        job_result = json.loads(text)
        job_error = job_result.get("error", {})
        error_code = job_error.get("code", 0)
        assert error_code == jsonrpc_errors.NotFoundError.CODE

    @staticmethod
    def get_devices(client):
        status_code, reason, text, response = client.get_devices()
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0
        devices = result["result"]
        return devices

    @staticmethod
    def get_device(client, device_name):
        status_code, reason, text, response = client.get_device(device_name)
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0
        device = result["result"]
        return device

    @staticmethod
    def get_drivers(client):
        status_code, reason, text, response = client.get_drivers()
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0
        drivers = result["result"]
        return drivers

    @staticmethod
    def get_driver(client, driver_name):
        status_code, reason, text, response = client.get_driver(driver_name)
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0
        driver = result["result"]
        return driver

    @staticmethod
    def get_transpilers(client):
        status_code, reason, text, response = client.get_transpilers()
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0
        transpilers = result["result"]
        return transpilers

    @staticmethod
    def get_transpiler(client, transpiler_name):
        status_code, reason, text, response = client.get_transpiler(
            transpiler_name
        )
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0
        transpiler = result["result"]
        return transpiler
