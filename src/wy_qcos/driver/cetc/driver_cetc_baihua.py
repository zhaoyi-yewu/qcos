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

from wy_qcos.driver.cetc.driver_cetc_base import DriverCetcBase


class DriverCetcBaihua(DriverCetcBase):
    """国基量子 百花 超导驱动.

    Driver for the baihua backend (computer_type=60) on the
    TianGong quantum platform.
    """

    def __init__(self):
        super().__init__()
        self.computer_type = 60  # baihua backend
        self.alias_name = "国基量子 百花 超导驱动"
        self.description = "国基量子 百花 超导驱动"
