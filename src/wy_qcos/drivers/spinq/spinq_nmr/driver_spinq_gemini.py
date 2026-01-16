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
