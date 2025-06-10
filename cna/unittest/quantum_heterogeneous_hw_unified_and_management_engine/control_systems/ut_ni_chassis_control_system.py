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


import unittest
from unittest.mock import patch, MagicMock
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    control_systems.ni_chassis_control_system import \
    NIChassisControlSystem


class TestNIChassisControlSystem(unittest.TestCase):
    '''测试NIChassisControlSystem类的单元测试类'''

    def setUp(self):
        '''设置测试环境，初始化一个NIChassisControlSystem实例'''
        # 实例化NIChassisControlSystem，设定地址为'192.168.0.10'
        self.chassis_system = NIChassisControlSystem(address='192.168.0.10')

    def test_configure_chassis(self):
        '''测试configure_chassis函数，配置NI机箱'''
        # 配置字符串数据
        config = 'Chassis configuration data'
        # 调用configure_chassis方法配置机箱
        self.chassis_system.configure_chassis(config)
        # 验证配置数据是否正确
        self.assertEqual(self.chassis_system.chassis_config, config)

    @patch('random.random', return_value=0.06)
    def test_verify_chassis_success(self, mock_random):
        '''测试verify_chassis函数，在高概率下验证成功'''
        # 设置设备连接状态为True
        self.chassis_system.connected = True
        # 调用verify_chassis方法，期望返回True
        result = self.chassis_system.verify_chassis()
        # 验证返回结果是否符合预期
        self.assertTrue(result)

    @patch('time.sleep', return_value=None)
    def test_run_chassis_sequence(self, mock_sleep):
        '''测试run_chassis_sequence函数，模拟NI机箱序列的运行'''
        # 调用run_chassis_sequence方法
        self.chassis_system.run_chassis_sequence()
        # 验证sleep函数是否被调用，模拟延迟时间
        mock_sleep.assert_called_once_with(0.5)


# 执行单元测试
if __name__ == '__main__':
    unittest.main()
