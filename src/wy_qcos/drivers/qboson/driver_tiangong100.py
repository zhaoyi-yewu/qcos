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
from datetime import datetime, timedelta

from loguru import logger

from wy_qcos.common.constant import HttpCode, HttpMethod
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.driver_qubo_base import DriverQuboBase


class DriverTiangong100(DriverQuboBase):
    """玻色量子-天工100 光量子伊辛机驱动.

    Qboson Tiangong100 driver
    CQ-D-100
    """

    # url path
    login_path = "kdev/terminal/login"
    upload_path = "kdev/terminal/upload_file"
    batch_task_path = "kdev/terminal/batch-task"
    machine_path = "kdev/terminal/machine"
    machine_task_path = "kdev/terminal/machine-task"
    task_results_path = "kdev/terminal/task"

    # auth code
    # 20001: token is expired or invalid
    # 50008: token is used and unavailable
    auth_code_invalid = "20001"
    auth_code_used = "50008"
    invalid_auth_codes = [auth_code_invalid, auth_code_used]

    # device status
    # 0: shutdown, 1: available, 2: debugging 3: malfunctioning,
    # 4: self-testing
    device_status_shutdown = 0
    device_status_available = 1
    device_status_debugging = 2
    device_status_malfunctioning = 3
    device_status_self_testing = 4
    device_status_mapping = {
        device_status_shutdown: {"desc": "shutdown"},
        device_status_available: {"desc": "available"},
        device_status_debugging: {"desc": "debugging"},
        device_status_malfunctioning: {"desc": "malfunctioning"},
        device_status_self_testing: {"desc": "self_testing"},
    }

    # task status
    # -1: unknown, 0: queue, 1: computing, 5. completed, 6. failed
    task_status_unknown = -1
    task_status_queue = 0
    task_status_computing = 1
    task_status_completed = 5
    task_status_failed = 6

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "玻色量子-天工100 光量子伊辛机驱动"
        self.description = "玻色量子-天工100 光量子伊辛机驱动"
        self.max_qubits = 100
        self.base_url = None
        # task stages and percentages
        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_LOADING: 10,
            self.TASK_STAGE_VALIDATING: 15,
            self.TASK_STAGE_USER_AUTHENTICATION: 20,
            self.TASK_STAGE_CHECK_DEVICE_STATUS: 25,
            self.TASK_STAGE_UPLOAD_FILE: 30,
            self.TASK_STAGE_SUBMIT_TASK: 35,
            self.TASK_STAGE_WAIT_TASK: 40,
            self.TASK_STAGE_GET_RESULTS: 95,
            self.TASK_STAGE_COMPLETE: 100,
        }

    def init_driver(self):
        """Init driver.

        注意:
        token有效期30天
        一般最长任务执行时间是10分钟
        用户认证
        curl -i -H "Accept: application/json" \
          -H "Content-Type: application/json" -X POST \
          -d '{"username":"username","pwd":"123"}' \
          http://127.0.0.1:8088/kdev/terminal/login/

        获取真机信息
        curl -i -H "Accept: application/json" \
          -H "Content-Type: application/json" \
          -H "Authorization: JWT ${token}" \
          http://127.0.0.1:8088/kdev/terminal/machine/
        """
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
            "base_url": str,
            "username": str,
            "password": str,
            "project_id": int,
            "device_id": int,
        }
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema
        )
        if not _success:
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
        project_id = extra_configs.get("project_id", 1)
        device_id = extra_configs.get("device_id", 1)
        username = extra_configs.get("username", "")
        password = extra_configs.get("password", "")
        self.base_url = extra_configs.get("base_url", "")
        task_name = f"{job_id}_{data_index}"

        # 1. Load qubo matrix
        logger.info("1. load qubo matrix")
        self.set_progress_by_task(self.TASK_STAGE_LOADING)
        qubo_matrix = data["source_code"]

        # 2. Validate base_url
        logger.info("2. validate base_url")
        self.set_progress_by_task(self.TASK_STAGE_VALIDATING)
        if not Library.is_valid_url(self.base_url, {"http", "https"}):
            raise ValueError(f"Invalid URL [{job_id}]: {self.base_url}")

        # 3. User authentication and get token
        logger.info("3. user authentication")
        self.set_progress_by_task(self.TASK_STAGE_USER_AUTHENTICATION)
        success, err_msg, self.token = Library.loop_with_timeout(
            self.user_auth, 3600, 5, username, password
        )
        if not success:
            raise ValueError(f"Authorize failed [{job_id}]: {err_msg}")
        self.auth_headers["Authorization"] = f"JWT {self.token}"
        logger.info(f"user token: {self.token}")

        # 4. Check device status
        logger.info("4. check_device_status")
        self.set_progress_by_task(self.TASK_STAGE_CHECK_DEVICE_STATUS)
        success, err_msg, _ = Library.loop_with_timeout(
            self.check_device_status, 3600, 5, device_id
        )
        if not success:
            raise ValueError(
                f"Failed to check device status [{task_name}]: {err_msg}"
            )

        # 5. Upload file
        logger.info("5. upload file")
        self.set_progress_by_task(self.TASK_STAGE_UPLOAD_FILE)
        success, err_msg, file_info = Library.loop_with_timeout(
            self.upload_file, 3600, 5, job_id, data_index, qubo_matrix
        )
        if not success:
            raise ValueError(f"Failed to upload file [{job_id}]: {err_msg}")

        # 6. Submit task
        logger.info("6. submit task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        estimated_datetime = datetime.now() + timedelta(minutes=1)
        estimated_datetime_str = estimated_datetime.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        task_info = {
            "priority": 0,
            "machine_id": device_id,
            "task_name": task_name,
            "user_id": file_info["creator"],
            "file_id": file_info["id"],
            "csv_name": file_info["name"],
            "estimated_datetime": estimated_datetime_str,
            "expected_description": "1",
            "project_id": project_id,
        }
        tasks_info = {"data": [task_info]}
        success, err_msg, _ = Library.loop_with_timeout(
            self.submit_tasks, 3600, 5, tasks_info
        )
        if not success:
            raise ValueError(f"Failed to submit task [{task_name}]: {err_msg}")

        # 7. Get task id and wait for task_status is completed
        logger.info("7. wait for task_status=completed")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        success, err_msg, _ = Library.loop_with_timeout(
            self.check_task_status,
            3600,
            5,
            task_name,
            expect_task_status=[self.task_status_completed],
        )
        if not success:
            raise ValueError(
                f"Failed to wait for task [{task_name}]: {err_msg}"
            )

        # 8. Get task id
        logger.info("8. get task results")
        self.set_progress_by_task(self.TASK_STAGE_GET_RESULTS)
        success, err_msg, task_info = self.get_task_id(task_name)
        if not success:
            raise ValueError(f"Failed to get task id [{task_name}]: {err_msg}")

        success, err_msg, results = self.get_task_results(
            task_id=task_info["id"]
        )
        if not success:
            raise ValueError(
                f"Failed to get task results [{job_id}]: {err_msg}"
            )

        # 9. Save results and set driver status to ONLINE
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

    def user_auth(self, username, password):
        """User authorization.

        Args:
            username: username
            password: password

        Returns:
            success or fail, error message, token
        """
        success = True
        err_msgs = []
        token = None
        url = f"{self.base_url}/{self.login_path}/"
        data = {"username": username, "pwd": Library.md5_encrypt(password)}
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
                token = response["data"]["token"]["access"]
            else:
                success = False
                err_msgs.append(err_msg)
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), token

    def check_device_status(self, device_id):
        """Check device status.

        Args:
            device_id: device id

        Returns:
            success or fail, error message
        """
        success = True
        err_msgs = []
        url = f"{self.base_url}/{self.machine_path}/"
        params = {"machine_id": device_id}
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.GET,
            params=params,
            headers=self.auth_headers,
            func_name="check_device_status",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            err_code = response["code"]
            err_msg = response["msg"]
            if err_code == "0":
                data = response.get("data", None)
                data_status = data["status"]
                logger.info(f"device status: {data_status}")
                if data_status != self.device_status_available:
                    success = False
                    device_status_desc = self.device_status_mapping[
                        data_status
                    ]["desc"]
                    err_msgs.append(
                        f"Unexpected device status: {device_status_desc}, "
                        f"controller status: {data['status_desc']}"
                    )
            else:
                success = False
                err_msgs.append(err_msg)
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), None

    def upload_file(self, job_id, data_index, data):
        """Upload qubo matrix file.

        Args:
            job_id: job ID
            data_index: data index
            data: qubo matrix in dict format

        Returns:
            success or fail, error message, file info
        """
        success = True
        err_msgs = []
        file_info = None
        if data is None or len(data) == 0:
            raise ValueError("Invalid qubo matrix value")

        # upload qubo matrix csv file
        temp_dir = tempfile.gettempdir()
        csv_filename = f"job_{job_id}_{data_index}.csv"
        csv_filepath = os.path.join(temp_dir, csv_filename)
        url = f"{self.base_url}/{self.upload_path}/"
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
                    "name": ("", filename),
                    "url": (filename, csv_file, "text/csv"),
                }
                status_code, reason, text, r = Library.call_http_api(
                    url,
                    HttpMethod.POST,
                    files=files,
                    headers=self.auth_headers,
                    func_name="upload_file",
                )
                if status_code == HttpCode.SUCCESS_OK:
                    response = json.loads(text)
                    err_code = response["code"]
                    err_msg = response["msg"]
                    if err_code == "0":
                        file_info = {
                            "creator": response["data"]["creator"],
                            "id": response["data"]["id"],
                            "name": response["data"]["name"],
                        }
                    else:
                        success = False
                        err_msgs.append(err_msg)
                else:
                    success = False
                    err_msgs.append(reason)
        finally:
            # remove csv file
            if os.path.exists(csv_filepath):
                os.remove(csv_filepath)
        return success, "\n".join(err_msgs), file_info

    def submit_tasks(self, tasks_info):
        """Submit tasks.

        Args:
            tasks_info: tasks info

        Returns:
            success or fail, error message
        """
        success = True
        err_msgs = []

        # Submit task
        url = f"{self.base_url}/{self.batch_task_path}/"
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.POST,
            json=tasks_info,
            headers=self.auth_headers,
            func_name="submit_tasks",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            err_code = response["code"]
            err_msg = response["msg"]
            if err_code != "0":
                success = False
                err_msgs.append(err_msg)
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), None

    def get_task_id(self, task_name):
        """Get task id by task name.

        Args:
            task_name: task name

        Returns:
            success or fail, error message, task info
        """
        success = True
        err_msgs = []
        task_info = {}

        # Get task info by task name
        params = {"page": 1, "size": 10, "task_name": task_name}
        url = f"{self.base_url}/{self.machine_task_path}/"
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.GET,
            params=params,
            headers=self.auth_headers,
            func_name="get_task_id",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            err_code = response["code"]
            err_msg = response["msg"]
            if err_code == "0":
                response_data = response["data"].get("data", [])
                for _task_info in response_data:
                    task_info["id"] = _task_info.get("id")
                    task_info["status"] = _task_info.get("status")
                    logger.info(f"task status: {task_info['status']}")
                if not task_info:
                    success = False
                    err_msgs.append(f"Can't find task name: {task_name}")
            else:
                success = False
                err_msgs.append(err_msg)
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), task_info

    def check_task_status(self, task_name, expect_task_status):
        """Check task status meets requirements.

        Args:
            task_name: task name
            expect_task_status: expect task status list

        Returns:
            bool: True if task status meets requirements, False otherwise
            str: error message
            str: task status
        """
        success, err_msg, task_info = self.get_task_id(task_name)
        if success:
            task_status = task_info.get("status", self.task_status_unknown)
            if task_status in expect_task_status:
                return True, None, task_status
            err_msg = (
                "Task status is not in "
                f"{', '.join(map(str, expect_task_status))}, "
                f"and current status: {task_status}"
            )
        return False, err_msg, None

    def get_task_results(self, task_id):
        """Get task results.

        Args:
            task_id: task ID

        Returns:
            success or fail, error message, task results
        """
        success = True
        err_msgs = []
        results = None

        # Get task results
        url = f"{self.base_url}/{self.task_results_path}/{task_id}/"
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.GET,
            headers=self.auth_headers,
            func_name="get_task_results",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            err_code = response["code"]
            err_msg = response["msg"]
            if err_code == "0":
                results = {
                    "out_data": response["data"]["out_data"],
                    "visual_data": response["data"]["visual_data"],
                }
            else:
                success = False
                err_msgs.append(err_msg)
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), results

    def delete_task(self, task_id):
        """Delete task.

        Args:
            task_id: task ID

        Returns:
            success or fail, error message
        """
        success = True
        err_msgs = []

        # Get task results
        url = f"{self.base_url}/{self.machine_task_path}/{task_id}/"
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.DELETE,
            headers=self.auth_headers,
            func_name="delete_task",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            err_code = response["code"]
            err_msg = response["msg"]
            if err_code != "0":
                success = False
                err_msgs.append(err_msg)
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs)
