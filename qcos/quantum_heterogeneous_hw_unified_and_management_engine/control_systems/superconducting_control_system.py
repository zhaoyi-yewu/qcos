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


class SuperconductingControlSystem(BaseQuantumControlSystem):
    """超导控制系统"""

    def __init__(self, address: str):
        """
        初始化超导控制系统
        参数:
        address (str): 设备地址
        """
        # 调用父类的构造函数
        super().__init__(address)
        # 工作点设置
        self.working_point = 0

    def set_working_point(self, point: float):
        """
        设置工作点
        参数:
        point (float): 工作点值
        """
        # 设置工作点
        self.working_point = point

    def verify_qubits(self, qubit_count: int) -> bool:
        """
        验证量子比特数量
        参数:
        qubit_count (int): 量子比特数量
        返回:
        bool: 验证是否成功
        """
        # 模拟验证过程，90%成功率
        return self.connected and (random.random() > 0.1)

    def run_calibration_sequence(self):
        """
        运行校准序列
        """
        # TODO():后续可以完善
        # 模拟校准过程的延迟
        time.sleep(1)
