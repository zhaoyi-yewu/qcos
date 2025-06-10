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


import unittest
from unittest.mock import patch
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    control_systems.camera_control_system import \
    CameraControlSystem


class TestCameraControlSystem(unittest.TestCase):
    '''
    测试 CameraControlSystem 类的单元测试类
    '''

    def setUp(self):
        '''
        设置测试环境，初始化一个 CameraControlSystem 实例
        '''
        # 实例化 CameraControlSystem
        self.camera_system = CameraControlSystem(address='camera')

    def test_configure_camera(self):
        '''
        测试 configure_camera 函数，配置相机
        '''
        # 配置字符串数据
        config = 'Camera configuration data'
        # 调用 configure_camera 方法
        self.camera_system.configure_camera(config)
        # 验证配置数据是否正确
        self.assertEqual(self.camera_system.camera_config, config)

    def test_verify_camera_connection(self):
        '''
        测试 verify_camera_connection 函数
        '''
        # 调用 verify_camera_connection 方法
        result = self.camera_system.verify_camera_connection(0)
        # 验证返回结果是否符合预期
        self.assertFalse(result)

    @patch('time.sleep', return_value=None)
    def test_run_camera_sequence(self, mock_sleep):
        '''
        测试 run_camera_sequence 函数，模拟相机硬件触发序列的运行
        '''
        # 调用 run_camera_sequence 方法
        self.camera_system.run_camera_sequence()
        # 验证模拟延迟时间的sleep函数是否被调用
        mock_sleep.assert_called_once_with(0.5)


# 执行单元测试
if __name__ == '__main__':
    unittest.main()
