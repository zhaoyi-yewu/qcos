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
from wy_qcos.driver.spinq.driver_spinq_base import (
    DriverSpinqBase,
)


class DriverSpinqSqc25(DriverSpinqBase):
    """量旋科技 SQC-25 云平台超导驱动.

    Driver for the SQC-25 platform on SpinQ Cloud.
    """

    def __init__(self):
        super().__init__()
        self._platform = "sqc_25_vp"
        self.max_qubits = 25
        self.alias_name = "量旋科技 SQC-25 云平台超导驱动"
        self.description = "量旋科技 SQC-25 云平台超导驱动"
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_I,
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_Y,
            Constant.SINGLE_QUBIT_GATE_Z,
            Constant.TWO_QUBIT_GATE_CX,
            Constant.SINGLE_QUBIT_GATE_RX,
        ]
        self.tech_type = Constant.TECH_TYPE_SUPERCONDUCTING
