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
from schema import Optional

from wy_qcos.common.constant import Constant
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_base import DriverBase


class DriverGateBase(DriverBase):
    """门级驱动基类.

    Gate Base driver
    """

    def __init__(self):
        super().__init__()
        # gate drivers support qasm code types by default
        self.supported_code_types = [
            Constant.CODE_TYPE_QASM,
            Constant.CODE_TYPE_QASM2,
            Constant.CODE_TYPE_QASM3,
        ]
        # default data type in run()
        self.default_data_type = DriverBase.DATA_TYPE_GATE_SEQUENCE
        # enable circuit aggregation for gate drivers
        self.enable_circuit_aggregation = False
        # gate drivers fetch results synchronously by default
        self.results_fetch_mode = Constant.RESULTS_FETCH_MODE_SYNC
        # supported basis gates, subclasses should override this
        self.supported_basis_gates = []
        # transpiler_option schema for specific driver
        self.transpiler_options_schema = {
            "optimization_level": (
                Optional(
                    "optimization_level",
                    default=Constant.DEFAULT_OPTIMIZATION_LEVEL,
                ),
                int,
            ),
            "enable_na_move": (
                Optional("enable_na_move", default=False),
                bool,
            ),
            "na_mapping_type": (Optional("na_mapping_type"), str),
            "enable_mapping": (
                Optional("enable_mapping", default=False),
                bool,
            ),
            "sc_mapping_options": (
                Optional("sc_mapping_options", default=False),
                dict,
            ),
            "enable_wirecut": (
                Optional("enable_wirecut", default=False),
                bool,
            ),
        }

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
