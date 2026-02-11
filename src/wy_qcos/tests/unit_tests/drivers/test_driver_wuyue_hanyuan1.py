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

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.drivers.cascoldatom.driver_wuyue_hanyuan1 import (
    DriverWuyueHanyuan1,
)


driver_wuyue_hanyuan1 = DriverWuyueHanyuan1()


@pytest.mark.driver
class TestDriverWuyuehanyuan1:
    def test_init(self):
        assert driver_wuyue_hanyuan1.submit_path == "task/WuYue/submit"
        assert driver_wuyue_hanyuan1.query_task_path == "task/WuYue/query"
        assert driver_wuyue_hanyuan1.version == "0.0.1"
        assert (
            driver_wuyue_hanyuan1.alias_name
            == "WY-中科酷原-汉原1 中性原子驱动"
        )
        assert (
            driver_wuyue_hanyuan1.description
            == "WY-中科酷原-汉原1 中性原子驱动"
        )
        assert driver_wuyue_hanyuan1.enable_transpiler is False
        assert (
            driver_wuyue_hanyuan1.tech_type == Constant.TECH_TYPE_NEUTRAL_ATOM
        )
        assert driver_wuyue_hanyuan1.supported_code_types == [
            Constant.CODE_TYPE_QASM2
        ]
        assert driver_wuyue_hanyuan1.max_qubits == 100
        assert driver_wuyue_hanyuan1.supported_basis_gates == [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
