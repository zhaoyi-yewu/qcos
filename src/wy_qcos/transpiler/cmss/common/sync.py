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

from wy_qcos.transpiler.cmss.common.base_operation import BaseOperation
from wy_qcos.transpiler.cmss.common.base_operation import OperationType


class Sync(BaseOperation):
    """同步操作，用于在量子电路中同步操作，确保某些操作在特定的时间点同时发生."""

    def __init__(
        self,
        targets=None,
        arg_value=None,
        operation_type=OperationType.SYNC.value,
    ) -> None:
        super().__init__("sync", targets, arg_value, operation_type)
