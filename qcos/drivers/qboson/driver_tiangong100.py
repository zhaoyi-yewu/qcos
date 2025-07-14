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

import csv
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta

from prefect.logging import get_run_logger

from qcos.common.constant import Constant, HttpMethod
from qcos.common.library import Library
from qcos.drivers.driver_base import DriverBase

logger = logging.getLogger(__name__)


class DriverTiangong100(DriverBase):
    """
    玻色量子-天工1000 光量子伊辛机驱动
    Qboson Tiangong1000 driver
    CQ-D-100

    注意:
    * token有效期30天
    * 一般最长任务执行时间是10分钟

    # 用户认证
    curl -i -H "Accept: application/json" -H "Content-Type: application/json" -X POST -d '{"username":"username","pwd":"123"}' http://127.0.0.1:8088/kdev/terminal/login/
    # 获取真机信息
    curl -i -H "Accept: application/json" -H "Content-Type: application/json" -H "Authorization: JWT ${token}" http://127.0.0.1:8088/kdev/terminal/machine/
    # pylint: disable=line-too-long
    """
    # http request headers
    default_headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN"
    }
    auth_headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN",
        "Authorization": None
    }

    # url path
    login_path = "kdev/terminal/login"
    upload_path = "kdev/terminal/upload_file"
    batch_task_path = "/kdev/terminal/batch-task"
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
        self.enable_transpiler = False
        self.max_qubits = 100
        self.supported_code_types = [
            Constant.CODE_TYPE_QUBO
        ]
        self.token = None

    def init_driver(self):
        """
        Init driver
        """
        self.set_status(self.DRIVER_STATUS_ONLINE)

    def validate_driver_configs(self):
        """
        Validate driver configurations

        :return success or fail, error message
        """
        success = True
        err_msg = None

        # check and load driver configs
        driver_config_schema = {
            "base_url": str,
            "username": str,
            "password": str,
            "project_id": int,
            "device_id": int
        }
        _success, err_msgs = Library.validate_schema(
            self.extra_configs, driver_config_schema)
        if not _success:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False
        return success, err_msg

    def close_driver(self):
        """
        Close driver
        """
        # pylint: disable=duplicate-code
        self.set_status(self.DRIVER_STATUS_OFFLINE)

    def run(self, job_id, num_qubits, data, data_type, shots=1):
        """
        Run job

        :param job_id: job ID
        :param num_qubits: number of qubits
        :param data: data
        :param data_type: data type
        :param shots: shots
        """
        # pylint: disable=duplicate-code
        prefect_logger = get_run_logger()
        logger.info(f"job_id: {job_id}, shots: {shots}, "
                    f"num_qubits: {num_qubits}, "
                    f"data_type: {data_type}, data: {data}")
        self.set_status(self.DRIVER_STATUS_BUSY)
        extra_configs = self.get_extra_configs()
        project_id = extra_configs.get("project_id", 1)
        device_id = extra_configs.get("device_id", 1)
        username = extra_configs.get("username", "")
        password = extra_configs.get("password", "")
        self.base_url = extra_configs.get("base_url", "")

        # Load qubo matrix
        qubo_matrix = None
        try:
            qubo_matrix = json.loads(data["source_code"][0])
        except Exception as e:
            raise ValueError(f"Invalid qubo matrix [{job_id}]") from e

        # Validate base_url
        if not Library.is_valid_url(self.base_url, {"http", "https"}):
            raise ValueError(f"Invalid URL [{job_id}]: {self.base_url}")

        # User authentication and get token
        success, err_msg, self.token = self.user_auth(username, password)
        if not success:
            raise ValueError(f"Authorize failed [{job_id}]: {err_msg}")
        self.auth_headers["Authorization"] = f"JWT {self.token}"
        prefect_logger.info(f"token: {self.token}")

        # Check device status
        prefect_logger.info("check_device_status")
        success, err_msg = self.check_device_status(device_id)
        if not success:
            raise ValueError(err_msg)

        prefect_logger.info("upload file")
        # Upload file
        success, err_msg, file_info = self.upload_file(job_id, qubo_matrix)
        if not success:
            raise ValueError(f"Failed to upload file [{job_id}]: {err_msg}")

        # Submit task
        estimated_datetime = datetime.now() + timedelta(minutes=1)
        estimated_datetime_str = estimated_datetime.strftime(
            "%Y-%m-%d %H:%M:%S")
        task_info = {
            "priority": 0,
            "machine_id": device_id,
            "task_name": job_id,
            "user_id": file_info["creator"],
            "file_id": file_info["id"],
            "csv_name": file_info["name"],
            "estimated_datetime": estimated_datetime_str,
            "expected_description": "1",
            "project_id": project_id
        }
        tasks_info = {
            "data": [task_info]
        }
        prefect_logger.info("submit task")
        success, err_msg = self.submit_tasks(tasks_info)
        if not success:
            raise ValueError(f"Failed to submit task [{job_id}]: {err_msg}")

        # Get task id and wait for task_status is completed
        prefect_logger.info("wait")
        success, err_msg, _ = Library.loop_with_timeout(
            self.check_task_status, 3600, 5, job_id,
            expect_task_status=[self.task_status_completed])
        if not success:
            raise ValueError(f"Failed to wait for task [{job_id}]: {err_msg}")

        # Get task id
        prefect_logger.info("wait done")
        success, err_msg, task_info = self.get_task_id(job_id)
        if not success:
            raise ValueError(f"Failed to get task id [{job_id}]: {err_msg}")

        # Get task results
        success, err_msg, results = self.get_task_results(
            task_id=task_info["id"])
        if not success:
            raise ValueError(f"Failed to get task results [{job_id}]: "
                             f"{err_msg}")

        # Save results and set driver status to ONLINE
        self.set_results(job_id, results=results)
        self.set_status(self.DRIVER_STATUS_ONLINE)

    def user_auth(self, username, password):
        """
        User authorization

        :param username: username
        :param password: password
        :return success or fail, error message, token
        """
        success = True
        err_msgs = []
        token = None
        url = f"{self.base_url}/{self.login_path}/"
        data = {
            "username": username,
            "pwd": password
        }
        status_code, reason, text, r = \
            Library.call_http_api(url, HttpMethod.POST, json=data,
                                  headers=self.default_headers,
                                  func_name="user_auth")
        if status_code == 200:
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
        """
        Check device status

        :param device_id: device id
        :return success or fail, error message
        """
        prefect_logger = get_run_logger()
        success = True
        err_msgs = []
        url = f"{self.base_url}/{self.machine_path}/"
        params = {
            "machine_id": device_id
        }
        status_code, reason, text, r = \
            Library.call_http_api(url, HttpMethod.GET, params=params,
                                  headers=self.auth_headers,
                                  func_name="check_device_status")
        if status_code == 200:
            response = json.loads(text)
            err_code = response["code"]
            err_msg = response["msg"]
            if err_code == "0":
                data = response.get("data", None)
                prefect_logger.info(f"device status: {data['status']}")
                if data["status"] != self.device_status_available:
                    success = False
                    err_msgs.append(
                        f"Unexpected device status: {data['status_desc']}")
            else:
                success = False
                err_msgs.append(err_msg)
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs)

    def upload_file(self, job_id, data):
        """
        Upload qubo matrix file

        :param job_id: job ID
        :param data: qubo matrix in dict format
        :return success or fail, error message, file info
        """
        success = True
        err_msgs = []
        file_info = None
        if data is None or len(data) == 0:
            raise ValueError("Invalid qubo matrix value")

        # upload qubo matrix csv file
        temp_dir = tempfile.gettempdir()
        csv_filename = f"job_{job_id}.csv"
        csv_filepath = os.path.join(temp_dir, csv_filename)
        url = f"{self.base_url}/{self.upload_path}/"
        try:
            # write to csv file
            with open(csv_filepath, 'w', newline='',
                      encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                for row in data:
                    writer.writerow(row)

            # open csv file and upload to server
            with open(csv_filepath, 'rb') as csv_file:
                filename = os.path.basename(csv_filepath)
                files = {
                    'name': ('', filename),
                    'url': (filename, csv_file, 'text/csv')
                }
                status_code, reason, text, r = \
                    Library.call_http_api(url, HttpMethod.POST, files=files,
                                          headers=self.auth_headers,
                                          func_name="upload_file")
                if status_code == 200:
                    response = json.loads(text)
                    err_code = response["code"]
                    err_msg = response["msg"]
                    if err_code == "0":
                        file_info = {
                            "creator": response["data"]["creator"],
                            "id": response["data"]["id"],
                            "name": response["data"]["name"]
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
        """
        Submit tasks

        :param tasks_info: tasks info
        :return success or fail, error message
        """
        success = True
        err_msgs = []

        # Submit task
        url = f"{self.base_url}/{self.batch_task_path}/"
        status_code, reason, text, r = \
            Library.call_http_api(url, HttpMethod.POST, json=tasks_info,
                                  headers=self.auth_headers,
                                  func_name="submit_tasks")
        if status_code == 200:
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

    def get_task_id(self, task_name):
        """
        Get task id by task name

        :param task_name: task name
        :return success or fail, error message, task info
        """
        prefect_logger = get_run_logger()
        success = True
        err_msgs = []
        task_info = {}

        # Get task info by task name
        params = {
            "page": 1,
            "size": 10,
            "task_name": task_name
        }
        url = f"{self.base_url}/{self.machine_task_path}/"
        status_code, reason, text, r = \
            Library.call_http_api(url, HttpMethod.GET, params=params,
                                  headers=self.auth_headers,
                                  func_name="get_task_id")
        if status_code == 200:
            response = json.loads(text)
            err_code = response["code"]
            err_msg = response["msg"]
            if err_code == "0":
                response_data = response["data"].get("data", [])
                for _task_info in response_data:
                    task_info["id"] = _task_info.get("id")
                    task_info["status"] = _task_info.get("status")
                    prefect_logger.info(task_info["status"])
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

    def check_task_status(self, job_id, expect_task_status):
        """
        Check task status meets requirements

        :param job_id: job ID
        :param expect_task_status: expect task status list
        :return: True if task status meets requirements, False otherwise
        """
        success, err_msg, task_info = self.get_task_id(job_id)
        if success and task_info.get("status", self.task_status_unknown) in \
                expect_task_status:
            return True
        return False

    def get_task_results(self, task_id):
        """
        Get task results

        :param task_id: task ID
        :return success or fail, error message, task results
        """
        success = True
        err_msgs = []
        results = None

        # Get task results
        url = f"{self.base_url}/{self.task_results_path}/{task_id}/"
        status_code, reason, text, r = \
            Library.call_http_api(url, HttpMethod.GET,
                                  headers=self.auth_headers,
                                  func_name="get_task_results")
        if status_code == 200:
            response = json.loads(text)
            err_code = response["code"]
            err_msg = response["msg"]
            if err_code == "0":
                results = response["data"]["out_data"]
            else:
                success = False
                err_msgs.append(err_msg)
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs), results

    def delete_task(self, task_id):
        """
        Delete task

        :param task_id: task ID
        :return success or fail, error message
        """
        success = True
        err_msgs = []

        # Get task results
        url = f"{self.base_url}/{self.machine_task_path}/{task_id}/"
        status_code, reason, text, r = \
            Library.call_http_api(url, HttpMethod.DELETE,
                                  headers=self.auth_headers,
                                  func_name="delete_task")
        if status_code == 200:
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
