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


class NeutralAtomControlSystem(BaseQuantumControlSystem):
    """中性原子控制系统"""

    def __init__(self, address: str):
        """
        初始化中性原子控制系统
        参数:
        address (str): 设备地址
        """
        # 调用父类的构造函数
        super().__init__(address)
        # 原子阵列配置
        self.lattice_config = None

    def configure_lattice(self, config: str):
        """
        配置原子阵列
        参数:
        config (str): 阵列配置参数
        """
        # 设置阵列配置
        self.lattice_config = config

    def verify_atoms(self, atom_count: int) -> bool:
        """
        验证原子数量
        参数:
        atom_count (int): 原子数量
        返回:
        bool: 验证是否成功
        """
        # 模拟验证过程，90%成功率
        return self.connected and (random.random() > 0.1)

    def run_atom_trapping_sequence(self):
        """
        运行原子捕获序列
        """
        # TODO():后续可以完善
        # 模拟捕获过程的延迟
        time.sleep(1)
