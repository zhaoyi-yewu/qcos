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

import csv
import json
import os
import tempfile

from loguru import logger

from wy_qcos.common.constant import HttpCode, HttpMethod
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.driver_qubo_base import DriverQuboBase


class DriverTiangongBase(DriverQuboBase):
    """玻色量子-天工光量子伊辛机驱动基类.

    Qboson Tiangong driver Base
    """

    # url path
    auth_path = "sso/access_token"
    task_path = "api/system/business/task"

    # task status
    # 0: checking, 1: computing, 2. completed, 3. failed
    task_status_checking = 0
    task_status_computing = 1
    task_status_completed = 2
    task_status_failed = 3

    def __init__(self):
        super().__init__()
        self.domain_url_task = None
        self.domain_url_auth = None
        self.version = "0.0.1"
        self.alias_name = "玻色量子-天工光量子伊辛机驱动"
        self.description = "玻色量子-天工光量子伊辛机驱动"
        self.max_qubits = 1000
        self.token = None
        # task stages and percentages
        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_LOADING: 10,
            self.TASK_STAGE_VALIDATING: 15,
            self.TASK_STAGE_USER_AUTHENTICATION: 20,
            self.TASK_STAGE_SUBMIT_TASK: 35,
            self.TASK_STAGE_WAIT_TASK: 40,
            self.TASK_STAGE_GET_RESULTS: 95,
            self.TASK_STAGE_COMPLETE: 100,
        }

    def init_driver(self):
        """Init driver."""
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def validate_driver_configs(self, configs):
        """Validate driver configs.

        Args:
            configs: configs dictionary

        Returns:
            success, err_msg
        """
        success = True
        err_msg = None

        # check and load driver configs
        driver_config_schema = {
            "domain_url_auth": str,
            "domain_url_task": str,
            "user_id": str,
            "password_sdk_code": str,
            "machine_name": str,
        }
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema
        )
        if _success:
            self.machine_name = configs.get("machine_name", "CPQC-1000")
        else:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False
        return success, err_msg

    def close_driver(self):
        """Close driver."""

    def fetch_configs(self):
        """Fetch configs.

        Returns:
            remote transpiler configs
        """

    def run(self, job_id, num_qubits, data, data_type, shots=1):
        """Run job.

        Args:
            job_id: job ID
            num_qubits: number of qubits
            data: data
            data_type: data type
            shots: shots (Default value = 1)
        """
        # pylint: disable=duplicate-code
        data_index = data["index"]
        logger.debug(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}"
        )

        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_device_status(Device.DEVICE_STATUS_BUSY)
        extra_configs = self.get_configs()

        # 1. Load qubo matrix
        logger.info("1. load qubo matrix")
        self.set_progress_by_task(self.TASK_STAGE_LOADING)
        qubo_matrix = data["source_code"]

        # 2. Validate url
        logger.info("2. validate url")
        self.set_progress_by_task(self.TASK_STAGE_VALIDATING)
        self.domain_url_auth = extra_configs.get("domain_url_auth", "")
        self.domain_url_task = extra_configs.get("domain_url_task", "")
        if not Library.is_valid_url(self.domain_url_auth, {"http", "https"}):
            raise ValueError(f"Invalid URL [{job_id}]: {self.domain_url_auth}")
        if not Library.is_valid_url(self.domain_url_task, {"http", "https"}):
            raise ValueError(f"Invalid URL [{job_id}]: {self.domain_url_task}")

        # 3. User authentication and get token
        logger.info("3. user authentication")
        self.set_progress_by_task(self.TASK_STAGE_USER_AUTHENTICATION)
        user_id = extra_configs.get("user_id", "")
        password_sdk_code = extra_configs.get("password_sdk_code", "")
        success, err_msg, self.token = Library.loop_with_timeout(
            self.user_auth, 3600, 5, user_id, password_sdk_code
        )
        if not success:
            raise ValueError(f"Authorize failed [{job_id}]: {err_msg}")

        self.auth_headers["Authorization"] = f"JWT {self.token}"

        # 4. Submit task
        logger.info("4. submit task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        success, err_msg, task_id = Library.loop_with_timeout(
            self.submit_tasks, 3600, 5, job_id, data_index, qubo_matrix
        )
        if not success:
            raise ValueError(f"Failed to submit task: {err_msg}")

        # 5. Wait for task_status is completed
        logger.info("5. wait for task_status=completed")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        success, err_msg, _ = Library.loop_with_timeout(
            self.check_task_status,
            3600,
            5,
            task_id,
            expect_task_status=[self.task_status_completed],
        )
        if not success:
            raise ValueError(f"Failed to wait for task [{task_id}]: {err_msg}")

        # 6. Get task final result
        logger.info("6. get task results")
        self.set_progress_by_task(self.TASK_STAGE_GET_RESULTS)
        success, err_msg, results = self.get_task_results(task_id)
        if not success:
            raise ValueError(
                f"Failed to get task results [{job_id}]: {err_msg}"
            )

        # 7. Save results and set driver status to ONLINE
        self.set_results(job_id, data_index, results=results)
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)

    def cancel(self, job_id):
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")

    def user_auth(self, user_id, sdk_code):
        """User authorization.

        Args:
            user_id: user_id
            sdk_code: sdk_code

        Returns:
            success or fail, error message, token
        """
        success = True
        err_msgs = []
        token = None
        url = f"{self.domain_url_auth}/{self.auth_path}/"
        data = {"user_id": user_id, "sdk_code": sdk_code}

        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.POST,
            json=data,
            headers=self.default_headers,
            func_name="user_auth",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            err_code = response["code"]
            err_msg = response["msg"]
            if err_code == "0":
                token = response["data"]["token"]
            else:
                success = False
                err_msgs.append(err_msg)
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), token

    def submit_tasks(self, job_id, data_index, data):
        """Submit tasks.

        Args:
            job_id: job ID
            data_index: data index
            data: qubo matrix in dict format

        Returns:
            success or fail, error message, task id
        """
        if data is None or len(data) == 0:
            raise ValueError("Invalid qubo matrix value")

        success = True
        err_msgs = []
        task_id = None

        temp_dir = tempfile.gettempdir()
        csv_filename = f"job_{job_id}_{data_index}.csv"
        csv_filepath = os.path.join(temp_dir, csv_filename)
        try:
            # write to csv file
            with open(
                csv_filepath, "w", newline="", encoding="utf-8"
            ) as csv_file:
                writer = csv.writer(csv_file)
                for row in data:
                    writer.writerow(row)

            # open csv file and upload to server
            with open(csv_filepath, "rb") as csv_file:
                filename = os.path.basename(csv_filepath)
                files = {
                    "url": (filename, csv_file, "text/csv"),
                }
                task_name = f"{job_id}_{data_index}"
                data = {
                    "task_name": task_name,
                    "name": filename,
                    "is_qubo": True,
                    "machine_name": self.machine_name,
                }
                # Submit task
                url = f"{self.domain_url_task}/{self.task_path}/"
                status_code, reason, text, r = Library.call_http_api(
                    url,
                    HttpMethod.POST,
                    files=files,
                    data=data,
                    headers=self.auth_headers,
                    func_name="submit_tasks",
                )
                if status_code == HttpCode.SUCCESS_OK:
                    response = json.loads(text)
                    err_code = response["code"]
                    err_msg = response["msg"]
                    if err_code == "0":
                        task_id = response["data"]["task_id"]
                    else:
                        success = False
                        err_msgs.append(err_msg)
                else:
                    success = False
                    err_msgs.append(reason)
        except Exception as e:
            success = False
            err_msgs.append(
                f"Unexpected exception happens."
                f"Exception type: {type(e).__name__}"
            )
        finally:
            # remove csv file
            if os.path.exists(csv_filepath):
                os.remove(csv_filepath)
        return success, "\n".join(err_msgs), task_id

    def check_task_status(self, task_id, expect_task_status):
        """Check task status meets requirements.

        Args:
            task_id: task id
            expect_task_status: expect task status list

        Returns:
            bool: True if task status meets requirements, False otherwise
            str: error message
            str: task status
        """
        success, err_msg, realtime_result = self.get_task_realtime_result(
            task_id
        )
        if success:
            task_status = realtime_result.get(
                "task_status", self.task_status_computing
            )
            if task_status in expect_task_status:
                return True, None, task_status
            err_msg = (
                "Task status is not in "
                f"{', '.join(map(str, expect_task_status))}, "
                f"and current status: {task_status}"
            )
        return False, err_msg, None

    def get_task_realtime_result(self, task_id):
        """Get task realtime result.

        Args:
            task_id: task ID

        Returns:
            success or fail, error message, task status
        """
        success = True
        err_msgs = []
        realtime_status = None

        # Get task status
        url = f"{self.domain_url_task}/{self.task_path}/{task_id}/"
        logger.info(f"get task result url: {url}")
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.GET,
            headers=self.auth_headers,
            func_name="get_task_realtime_result",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            err_code = response["code"]
            err_msg = response["msg"]
            if err_code == "0":
                task_status = response["data"]["task_status"]
                if task_status == self.task_status_failed:
                    desc = response["data"]["desc"]
                    success = False
                    err_msgs.append(f"Task failed: {desc}")
                else:
                    realtime_status = {
                        "task_status": response["data"]["task_status"],
                        "qubo_value": response["data"]["qubo_value"],
                        "qubo_solution_data": response["data"][
                            "qubo_solution_data"
                        ],
                        "visual_data": response["data"]["visual_data"],
                    }
            else:
                success = False
                err_msgs.append(err_msg)
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), realtime_status

    def get_task_results(self, task_id):
        """Get task results.

        Args:
            task_id: task id

        Returns:
            success or fail, error message, task results
        """
        # Get task results
        success, err_msg, final_results = self.get_task_realtime_result(
            task_id
        )
        if not success:
            raise ValueError(
                f"Failed to get task results [{task_id}]: {err_msg}"
            )
        out_data = []
        qubo_value = final_results.get("qubo_value", None)
        qubo_solution_data = final_results.get("qubo_solution_data", None)

        qubo_value_len = len(qubo_value)
        qubo_solution_data_len = len(qubo_solution_data)
        if qubo_value_len != qubo_solution_data_len:
            raise ValueError("Invalid result")

        for i in range(qubo_value_len):
            single_result = {}
            single_result["result"] = i + 1
            single_result["quboValue"] = qubo_value[i]
            single_result["solutionVector"] = qubo_solution_data[i]
            out_data.append(single_result)

        visual_data = final_results.get("visual_data", None)
        results = {
            "out_data": out_data,
            "visual_data": visual_data,
        }
        return success, "\n".join(err_msg), results
