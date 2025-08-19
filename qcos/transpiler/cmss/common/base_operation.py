#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from enum import Enum


class OperationType(Enum):
    """
    操作类型.
    """
    SINGLE_QUBIT_OPERATION = 1
    DOUBLE_QUBIT_OPERATION = 2
    TRIPLE_QUBIT_OPERATION = 3
    MEASURE = 0
    SYNC = -1
    MOVE = -2
    RESET = -3


class BaseOperation:
    """
    中间表示类基类
    """

    def __init__(
            self, name, targets=None, arg_value=None,
            operation_type=OperationType.SINGLE_QUBIT_OPERATION.value
    ) -> None:
        """
        :param name (_type_): 操作名称
        :param targets (_type_, optional): 目标量子比特. Defaults to None.
        :param arg_value (_type_, optional): 参数（旋转门所需）. Defaults to None.
        :param operation_type: 操作类型
        """
        self.name = name
        self.targets = targets
        # pylint: disable=use-list-literal
        self.arg_value = arg_value if arg_value is not None else list()
        if not isinstance(self.arg_value, list):
            self.arg_value = [self.arg_value]
        self.operation_type = operation_type

    def __repr__(self):
        return (f"{type(self).__name__}(targets={self.targets},"
                f"arg_value={self.arg_value})")
