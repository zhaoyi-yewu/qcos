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

import json
from loguru import logger

from wy_qcos.common.constant import Constant, HttpMethod, HttpCode
from wy_qcos.common.library import Library
from wy_qcos.drivers.spinq.spinq_nmr.driver_spinq_nmr import DriverSpinQNmr


class DriverSpinQGemini(DriverSpinQNmr):
    """量旋科技 双子座 核磁驱动.

    SpinQ gemini NMR driver
    https://cloud.spinq.cn
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "量旋科技 双子座 核磁量子计算机驱动"
        self.description = "量旋科技 双子座 核磁量子计算机驱动"
        self.tech_type = Constant.TECH_TYPE_NMR
        self.max_qubits = 2
        self.platform_name = "gemini_vp"
        self.enable_device_mgr = True
        self.enable_device_monitor = True

    def fetch_running_info(self):
        """Fetch running info.

        Returns:
            remote device running info
        """
        device_running_info = {"status": "online"}
        if self._nmr_conn_str is None:
            self.fetch_configs()
        url = f"{self._nmr_conn_str}/fetch_running_info"
        success, err_msg, result = self.send_request_and_process_response(
            None, url, "fetch_running_info"
        )
        if (
            success
            and result is not None
            and isinstance(result, dict)
            and len(result) != 0
        ):
            device_running_info = result.copy()
        return device_running_info

    def send_request_and_process_response(self, data, url, func_name):
        """send_request_and_process_response.G89.

        Args:
            data: http data
            url: http url
            func_name: func_name
        """
        logger.debug(f"url: {url}, data: {data}")
        status_code, reason, text, r = Library.call_http_api(
            url,
            HttpMethod.POST,
            json=data,
            headers=self.auth_headers,
            func_name=func_name,
        )
        success = True
        err_msg = []
        logger.debug(f"code: {status_code}, text: {text}")
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            result = response.get("result", None)
            if result is None:
                success = False
            logger.debug(f"result: {result}")
            return success, "\n".join(err_msg), result
        else:
            err_msg.append(reason)
        return False, err_msg, None

    def calibrate_device(self, data):
        """Calibrate device.

        Args:
            data: calibration data
        """
        logger.info("Start to calibrate")
        if self._nmr_conn_str is None:
            self.fetch_configs()
        url = f"{self._nmr_conn_str}/calibrate"
        return self.send_request_and_process_response(
            data, url, "calibrate_device"
        )

    def set_device_options(self, data):
        """Set Device options.

        Args:
            data: Device options data
        """
        logger.info("Start to set_device_options")
        if self._nmr_conn_str is None:
            self.fetch_configs()
        url = f"{self._nmr_conn_str}/set_device_options"
        return self.send_request_and_process_response(
            data, url, "set_device_options"
        )

    def get_device_options(self, data):
        """Get Device options.

        Args:
            data: data
        """
        logger.info("Start to get_device_options")
        if self._nmr_conn_str is None:
            self.fetch_configs()
        url = f"{self._nmr_conn_str}/get_device_options"
        return self.send_request_and_process_response(
            data, url, "get_device_options"
        )
