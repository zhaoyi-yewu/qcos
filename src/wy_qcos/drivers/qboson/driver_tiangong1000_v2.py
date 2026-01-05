#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from wy_qcos.drivers.qboson.driver_tiangong_base import DriverTiangongBase


class DriverTiangong1000V2(DriverTiangongBase):
    """玻色量子-天工1000光量子伊辛机驱动-V2.

    Qboson Tiangong 1000 driver - V2
    """

    def __init__(self):
        super().__init__()
        self.alias_name = "玻色量子-天工1000光量子伊辛机驱动-V2"
        self.description = "玻色量子-天工1000光量子伊辛机驱动-V2"
        self.max_qubits = 1000
