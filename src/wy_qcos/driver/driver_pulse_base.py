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

from wy_qcos.common.constant import Constant
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_base import DriverBase


class DriverPulseBase(DriverBase):
    """脉冲驱动基类.

    Pulse Base driver
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.tech_type = Constant.TECH_TYPE_NONE
        self.transpiler = Constant.TRANSPILER_CMSS
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]

    def init_driver(self):
        """Init driver."""
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def close_driver(self):
        """Close driver."""

    def cancel(self, job_id):
        """Cancel running job in driver.

        Driver should clean up any resources of the job

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")

    def fetch_running_info(self):
        """Fetch running info.

        Returns:
            remote device running info
        """
        device_running_info = {"status": Device.DEVICE_STATUS_ONLINE}
        return device_running_info

    def fetch_configs(self):
        """Fetch configs.

        Returns:
            remote transpiler configs
        """
        return
