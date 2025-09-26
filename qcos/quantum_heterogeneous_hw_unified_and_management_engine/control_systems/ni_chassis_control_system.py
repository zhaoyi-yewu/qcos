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


class NIChassisControlSystem(BaseQuantumControlSystem):
    """NI机箱控制系统"""

    def __init__(self, address: str):
        """
        初始化NI机箱控制系统
        参数:
        address (str): 设备地址
        """
        super().__init__(address)
        # 机箱配置
        self.chassis_config = None

    def configure_chassis(self, config: str):
        """
        配置NI机箱
        参数:
        config (str): 机箱配置参数
        """
        self.chassis_config = config

    def verify_chassis(self) -> bool:
        """
        验证NI机箱状态
        返回:
        bool: 验证是否成功
        """
        return self.connected and (random.random() > 0.05)

    def run_chassis_sequence(self):
        """
        运行NI机箱序列
        """
        # TODO():后续可以完善
        time.sleep(0.5)
        pass
