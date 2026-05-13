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

from __future__ import annotations


class Operation:
    """面向 pulse scheduler 的轻量门描述符.

    与 cmss 内部的重型 ``GateOperation`` 不同，此类仅持有
    pulse scheduler（lowering.py / sequence.py）所需的最小接口：
    ``name``、``params``、``duration``。

    其中 ``name`` 表示门名称，如 ``"rx"``、``"sx"``、``"measure"``；
    ``params`` 保存门参数列表，例如旋转角 ``[math.pi / 2]``，无参数时为
    ``[]``；``duration`` 表示门脉冲时长，单位为 dt，虚拟门如 ``rz``
    的时长为 ``0``。
    """

    __slots__ = ("name", "params", "duration")

    def __init__(
        self,
        name: str,
        params: list | None = None,
        duration: int = 0,
    ):
        self.name = name
        self.params = list(params) if params is not None else []
        self.duration = duration

    def __repr__(self) -> str:
        pstr = (
            f"({', '.join(str(p) for p in self.params)})"
            if self.params
            else ""
        )
        return f"{self.name}{pstr}"
