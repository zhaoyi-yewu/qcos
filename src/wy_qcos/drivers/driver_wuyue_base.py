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

import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from datetime import datetime
import json
import hashlib
import urllib.parse

from loguru import logger

from wy_qcos.common.constant import Constant, HttpCode, HttpMethod
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.driver_base import DriverBase


class DriverWuyueBase(DriverBase):
    """Wuyue驱动基类.

    Wuyue Base driver
    """

    # url path
    submit_path = "submit"
    query_task_path = "query_task"

    # task status
    # 1: submitted, 2: queuing,   3. computing,
    # 4. pending,   5: completed, 6.failed
    task_status_submitted = 1
    task_status_queuing = 2
    task_status_computing = 3
    task_status_pending = 4
    task_status_completed = 5
    task_status_failed = 6

    default_headers = {
        "accept": "application/json, */*",
        "accept-language": "zh-CN",
    }

    def __init__(self):
        super().__init__()
        self.enable_transpiler = False
        self.tech_type = Constant.TECH_TYPE_NONE
        self.default_data_type = DriverBase.DATA_TYPE_QASM2
        self.supported_code_types = [Constant.CODE_TYPE_QASM2]
        self.ip_addr = None
        self.port = None
        self.client_id = None
        self.eng_code = None
        self.password_secret = None
        self.password_pub_key = None
        self.password_pri_key = None

        # task stages and percentages
        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_INIT: 10,
            self.TASK_STAGE_SUBMIT_TASK: 20,
            self.TASK_STAGE_WAIT_TASK: 30,
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
            "ip_address": str,
            "port": int,
            "client_id": str,
            "eng_code": str,
            "password_secret": str,
            "password_pub_key": str,
            "password_pri_key": str,
        }
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema
        )
        if _success:
            self.ip_addr = configs.get("ip_address", None)
            self.port = configs.get("port", None)
            self.client_id = configs.get("client_id", None)
            self.eng_code = configs.get("eng_code", None)
            self.password_secret = configs.get("password_secret", None)
            self.password_pub_key = configs.get("password_pub_key", None)
            self.password_pri_key = configs.get("password_pri_key", None)
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

        # 1. Load code
        logger.info("1. load code")
        self.set_progress_by_task(self.TASK_STAGE_LOADING)
        src_code = data["source_code"]

        # 2. Prepare task data
        logger.info("2. prepare data")
        self.set_progress_by_task(self.TASK_STAGE_PREPARE_DATA)
        task_data = self.prepare_submit_data(
            job_id, src_code, shots, data_index
        )

        # 3. Submit task
        logger.info("3. submit task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        success, err_msg = self.submit_tasks(task_data)
        if not success:
            raise ValueError(f"Failed to submit task: {err_msg}")

        # 4. Wait for task_status is completed or failed
        logger.info("4. wait for task_status=completed")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        task_id = f"{job_id}-{data_index}"
        success, err_msg, results = Library.loop_with_timeout(
            self.check_task_status,
            3600,
            5,
            task_id,
            expect_task_status=[
                self.task_status_completed,
                self.task_status_failed,
            ],
        )
        if not success:
            raise ValueError(f"Failed to wait for task [{job_id}]: {err_msg}")

        if results is None or results != self.task_status_completed:
            raise ValueError(
                f"Failed to wait for task [{job_id}]: {err_msg},"
                f"task status:{results}"
            )

        # 5. Get task final result
        logger.info("5. get task results")
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

    def format_item(self, item):
        """Format list item.

        Args:
            item: list item

        Returns:
            formatted list item
        """
        if isinstance(item, str):
            return f'"{item}"'
        return str(item)

    def prepare_sign(self, data):
        """Prepare sign data.

        Args:
            data: raw data

        Returns:
            signed value
        """
        sorted_params = sorted(data.items())
        sb = []
        for key, value in sorted_params:
            if isinstance(value, list):
                elements = []
                for item in value:
                    if isinstance(item, str):
                        elements.append(f'"{item}"')
                    else:
                        elements.append(str(item))
                str_value = f"[{', '.join(elements)}]"
            else:
                str_value = str(value) if value is not None else ""
            encoded_value = urllib.parse.quote(str_value, safe="")
            sb.append(f"{key}={encoded_value}")

        param_str = "&".join(sb) + self.password_secret
        md5_hash = hashlib.md5(param_str.encode("utf-8"))
        return md5_hash.hexdigest()

    def encrypt_by_public_key(self, raw_data):
        """Encrypt by pub key.

        Args:
            raw_data: raw_data

        Returns:
            encryptted data
        """
        public_key_der = base64.b64decode(self.password_pub_key)
        public_key = serialization.load_der_public_key(
            public_key_der, backend=default_backend()
        )

        plaintext = json.dumps(raw_data, ensure_ascii=False).encode("utf-8")

        key_size_bytes = public_key.key_size // 8
        max_length = key_size_bytes - 11
        encrypted_parts = []

        for i in range(0, len(plaintext), max_length):
            part = plaintext[i : i + max_length]
            encrypted_part = public_key.encrypt(part, padding.PKCS1v15())
            encrypted_parts.append(encrypted_part)

        ciphertext = b"".join(encrypted_parts)
        return base64.b64encode(ciphertext).decode("utf-8")

    def decrypt_by_private_key(self, raw_data):
        """decrypt_by_private_key.

        Args:
            raw_data: raw_data

        Returns:
            decryptted data
        """
        private_key_der = base64.b64decode(self.password_pri_key)
        private_key = serialization.load_der_private_key(
            private_key_der, password=None, backend=default_backend()
        )
        ciphertext = base64.b64decode(raw_data)
        decrypted_parts = []
        max_length = private_key.key_size // 8
        for i in range(0, len(ciphertext), max_length):
            part = ciphertext[i : i + max_length]
            decrypted_part = private_key.decrypt(part, padding.PKCS1v15())
            decrypted_parts.append(decrypted_part)
        plaintext = b"".join(decrypted_parts)
        return json.loads(plaintext.decode("utf-8"))

    def prepare_submit_data(self, job_id, src_code, shots, data_index):
        """Prepare submit data.

        Args:
            job_id: job_id
            src_code: src_code
            shots: shots
            data_index: data_index

        Returns:
            prepared task data
        """
        encrypted_data = None
        create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_id = f"{job_id}-{data_index}"
        name = task_id
        raw_data = {
            "clientId": self.client_id,
            "engCode": self.eng_code,
            "taskId": task_id,
            "name": name,
            "examNum": shots,
            "createTime": create_time,
            "inDataType": 1,
            "inData": src_code,
        }
        raw_data["sign"] = self.prepare_sign(raw_data)
        encrypted_data = self.encrypt_by_public_key(raw_data)
        return encrypted_data

    def submit_tasks(self, task_data):
        """Submit tasks.

        Args:
            task_data: task_data

        Returns:
            success or fail, error message
        """
        if task_data is None or len(task_data) == 0:
            raise ValueError("Invalid data")

        success = True
        err_msgs = []

        url = f"http://{self.ip_addr}:{self.port}/{self.submit_path}"
        logger.info(f"url :{url}")
        headers = self.default_headers
        headers["clientId"] = self.client_id
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.POST,
            data=task_data,
            headers=headers,
            func_name="submit_tasks",
        )
        logger.info(f"status_code :{status_code}")
        if status_code == HttpCode.SUCCESS_OK:
            response = self.decrypt_by_private_key(text)
            err_code = response["code"]
            err_msg = response["msg"]
            if err_code != 1:
                success = False
                err_msgs.append(err_msg)
        else:
            success = False
            err_msgs.append(reason)
        return success, "\n".join(err_msgs)

    def check_task_status(self, task_id, expect_task_status):
        """Check task status meets requirements.

        Args:
            task_id: task id
            expect_task_status: expect task status list

        Returns:
            True if task status meets requirements, False otherwise
        """
        success, err_msg, realtime_result = self.get_task_realtime_result(
            task_id
        )
        task_status = realtime_result.get(
            "task_status", self.task_status_computing
        )
        if success and task_status in expect_task_status:
            return True, err_msg, task_status
        err_msg = (
            "Task status is not in "
            f"{', '.join(map(str, expect_task_status))}, "
            f"and current status: {task_status}"
        )
        return False, err_msg, task_status

    def prepare_query_task_data(self, task_id):
        """prepare_query_task_data.

        Args:
            task_id: task ID

        Returns:
            query task data
        """
        raw_data = {
            "clientId": self.client_id,
            "engCode": self.eng_code,
            "taskIds": [task_id],
            "type": 1,
        }
        raw_data["sign"] = self.prepare_sign(raw_data)
        return self.encrypt_by_public_key(raw_data)

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

        query_data = self.prepare_query_task_data(task_id)
        # Get task status
        url = f"http://{self.ip_addr}:{self.port}/{self.query_task_path}"
        logger.info(f"get task result url: {url}")
        headers = self.default_headers
        headers["clientId"] = self.client_id
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.POST,
            data=query_data,
            headers=headers,
            func_name="get_task_realtime_result",
        )
        realtime_status = None
        if status_code == HttpCode.SUCCESS_OK:
            response = self.decrypt_by_private_key(text)
            err_code = response["code"]
            err_msg = response["msg"]
            logger.info(f"err_code: {err_code}, msg: {err_msg}")
            if err_code == 1:
                data = response["data"]
                if (
                    data is None
                    or data[0] is None
                    or data[0]["taskStatus"] is None
                ):
                    success = False
                    err_msgs.append("invalid data received")
                    return success, "\n".join(err_msgs), None
                task_status = data[0]["taskStatus"]
                logger.info(f"task_status: {task_status}")
                if task_status == self.task_status_failed:
                    success = True
                    realtime_status = {
                        "task_status": data[0]["taskStatus"],
                        "result": data[0]["outData"]["lineResult"],
                    }
                    err_msgs.append(f"Task failed: {task_status}")
                elif task_status == self.task_status_completed:
                    realtime_status = {
                        "task_status": data[0]["taskStatus"],
                        "result": data[0]["outData"]["lineResult"],
                    }
                else:
                    success = False
                    realtime_status = {
                        "task_status": data[0]["taskStatus"],
                    }
                    err_msgs.append(
                        f"Task failed, task status : {task_status}"
                    )
            else:
                realtime_status = {
                    "task_status": self.task_status_failed,
                }
                success = True
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
        results = final_results.get("result", None)
        if isinstance(results, str):
            results_dict = json.loads(results)
            results = {
                key: value for key, value in results_dict.items() if value != 0
            }
        return success, "\n".join(err_msg), results
