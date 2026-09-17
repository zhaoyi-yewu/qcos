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

from wy_qcos.driver.quafu.driver_quafu_base import (
    DriverQuafuBase,
)


class DriverQuafuBaihua(DriverQuafuBase):
    """北京量子院 夸父-Baihua 超导驱动.

    Baihua driver
    https://quafu-sqc.baqis.ac.cn/
    """

    def __init__(self):
        super().__init__()
        self.alias_name = "北京量子院-夸父-Baihua 超导驱动"
        self.description = "北京量子院-夸父-Baihua 超导驱动"
        self.max_qubits = 156
