#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-10
# ------------------------


import abc
from typing import Any


class QuantumOperation(abc.ABC):
    """
    量子操作抽象基类
    """

    @abc.abstractmethod
    def execute(self, interface: 'QuantumHardwareInterface') -> Any:
        """
        执行量子操作

        参数:
        interface (QuantumHardwareInterface): 硬件接口

        返回:
        Any: 操作结果
        """
        pass
