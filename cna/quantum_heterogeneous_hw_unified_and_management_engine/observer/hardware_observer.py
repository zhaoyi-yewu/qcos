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
from typing import Any, Dict


class HardwareObserver(abc.ABC):
    """
    硬件观察者抽象基类
    """

    @abc.abstractmethod
    def update(self, hw_name: str, status: Dict[str, Any]):
        """
        更新硬件状态

        参数:
        hw_name (str): 硬件名称
        status (Dict[str, Any]): 状态信息
        """
        pass
