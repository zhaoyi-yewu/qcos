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

from loguru import logger

from wy_qcos.common.constant import Constant, HttpCode, HttpMethod
from wy_qcos.common.library import Library
from wy_qcos.drivers.cascoldatom.driver_wuyue_hanyuan1 import (
    DriverWuyueHanyuan1,
)


class DriverWuyueHanyuan1Sim(DriverWuyueHanyuan1):
    """五岳中科酷原-汉原1 中性原子驱动, 汉原后端为模拟器.

    Wuyue Cascoldatom Hanyuan1 driver
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "WY-中科酷原-汉原1 中性原子驱动-Sim"
        self.description = "WY-中科酷原-汉原1 中性原子驱动-Sim"
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
        self.supported_code_types = [Constant.CODE_TYPE_QASM2]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.max_qubits = 25
        self.enable_device_monitor = False

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
                result = None
                if data[0]["outData"] is not None:
                    result = data[0]["outData"]

                if task_status == self.task_status_failed:
                    success = True
                    realtime_status = {
                        "task_status": data[0]["taskStatus"],
                        "result": result,
                    }
                    err_msgs.append(f"Task failed: {task_status}")
                elif task_status == self.task_status_completed:
                    success = True
                    realtime_status = {
                        "task_status": data[0]["taskStatus"],
                        "result": result,
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
