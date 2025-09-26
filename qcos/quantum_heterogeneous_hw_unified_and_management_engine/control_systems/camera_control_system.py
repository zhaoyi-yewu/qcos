#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Longfei Tian at 2024-11
# ------------------------


from .base_quantum_control_system import BaseQuantumControlSystem
import random
import time


class CameraControlSystem(BaseQuantumControlSystem):
    """相机控制系统"""

    def __init__(self, address: str):
        """
        初始化相机控制系统
        参数:
        address (str): 设备地址
        """
        super().__init__(address)
        # 相机配置
        self.camera_config = None

    def configure_camera(self, config: str):
        """
        配置相机
        参数:
        config (str): 相机配置参数
        """
        self.camera_config = config

    def verify_camera_connection(self, camera_status) -> bool:
        """
        验证相机是否正常连接
        返回:
        bool: 相机是否正常连接
        """
        if camera_status == 0:
            self.disconnect()
        return self.connected

    def run_camera_sequence(self):
        """
        运行相机序列
        """
        # TODO():后续可以完善
        time.sleep(0.5)
        pass
