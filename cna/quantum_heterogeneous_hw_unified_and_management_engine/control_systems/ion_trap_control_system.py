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
import random
import time


class IonTrapControlSystem(BaseQuantumControlSystem):
    """离子阱控制系统"""

    def __init__(self, address: str):
        """
        初始化离子阱控制系统

        参数:
        address (str): 设备地址
        """
        # 调用父类的构造函数
        super().__init__(address)
        # 离子阱频率
        self.trap_frequency = 0

    def set_trap_frequency(self, frequency: float):
        """
        设置离子阱频率

        参数:
        frequency (float): 频率值
        """
        # 设置离子阱频率
        self.trap_frequency = frequency

    def verify_ions(self, ion_count: int) -> bool:
        """
        验证离子验证过程

        参数:
        ion_count (int): 离子数量

        返回:
        bool: 验证是否成功
        """
        # 模拟验证过程，90%成功率
        return self.connected and (random.random() > 0.1)

    def run_ion_cooling_sequence(self):
        """
        运行离子冷却序列
        """
        # TODO():后续可以完善
        # 模拟冷却过程的延迟
        time.sleep(1)
