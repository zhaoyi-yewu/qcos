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

import copy
from schema import Optional

from wy_qcos.common.constant import Constant
from wy_qcos.drivers.driver_wuyue_base import DriverWuyueBase


class DriverWuyueHanyuan1(DriverWuyueBase):
    """五岳中科酷原-汉原1 中性原子驱动.

    Wuyue Cascoldatom Hanyuan1 driver
    """

    # url path
    submit_path = "task/WuYue/submit"
    query_task_path = "task/WuYue/query"

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "WY-中科酷原-汉原1 中性原子驱动"
        self.description = "WY-中科酷原-汉原1 中性原子驱动"
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
        self.supported_code_types = [Constant.CODE_TYPE_QASM2]
        self.supported_transpilers = [Constant.TRANSPILER_CMSS]
        self.max_qubits = 100
        self.hanyuan1_device_info_schema = {
            Optional("horizontalRelaxationTime"): int,
            Optional("uniformityDephasingTime"): int,
            Optional("nonUniformityDephasingTime"): int,
            Optional("verticalRelaxationTime"): int,
            Optional("tweezersNum"): int,
            Optional("vaccum"): float,
            Optional("rydbergExcitation"): float,
            Optional("transportFidelity"): float,
            Optional("elementAtom"): str,
            Optional("time"): str,
        }

    def update_device_info_schema(self) -> dict:
        """Update device info schema.

        Returns:
            updated schema
        """
        device_info_schema = copy.deepcopy(self.default_device_info_schema)
        device_info_schema.update(self.hanyuan1_device_info_schema)
        return device_info_schema
