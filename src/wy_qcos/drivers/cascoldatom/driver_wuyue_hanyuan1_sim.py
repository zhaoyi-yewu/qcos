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
        machine_time_info = final_results.get("machine_time_info", None)
        return success, "\n".join(err_msg), results, machine_time_info
