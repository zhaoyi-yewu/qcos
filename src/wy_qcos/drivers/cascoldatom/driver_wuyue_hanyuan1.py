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
        self.enable_transpiler = False
        self.tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
        self.supported_code_types = [Constant.CODE_TYPE_QASM2]
        self.max_qubits = 100
