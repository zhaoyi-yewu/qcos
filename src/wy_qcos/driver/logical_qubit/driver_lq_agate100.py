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

from wy_qcos.driver.logical_qubit.driver_lq_base import (
    DriverLogicalQubitBase,
)


class DriverLqAGate100(DriverLogicalQubitBase):
    """逻辑比特 AGate-100 超导驱动.

    Logical Qubit AGate-100 driver
    https://cloud.logicalqubit.com.
    """

    def __init__(self) -> None:
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "逻辑比特 AGate-100 超导驱动"
        self.description = "逻辑比特 AGate-100 超导驱动"
        self.max_qubits = 101
