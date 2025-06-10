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

from .base_quantum_control_system import BaseQuantumControlSystem
from typing import Any
import random
import time


class AWGControlSystem(BaseQuantumControlSystem):
    """任意波形发生器（AWG）控制系统"""

    def __init__(self, address: str):
        """
        初始化AWG控制系统

        参数:
        address (str): 设备地址
        """
        super().__init__(address)
        # 波形数据
        self.waveform_data = None

    def load_waveform(self, waveform: Any):
        """
        加载波形数据

        参数:
        waveform (Any): 波形数据
        """
        self.waveform_data = waveform

    def verify_awg(self) -> bool:
        """
        验证AWG状态

        返回:
        bool: 验证是否成功
        """
        return self.connected and (random.random() > 0.05)

    def run_awg_sequence(self):
        """
        运行AWG序列
        """
        # TODO():后续可以完善
        time.sleep(0.5)
        pass
