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
    control_systems.fpga_control_system import \
    FPGAControlSystem


class TestFPGAControlSystem(unittest.TestCase):
    '''测试FPGAControlSystem类的单元测试类'''

    def setUp(self):
        '''设置测试环境，初始化一个FPGAControlSystem实例'''
        # 实例化FPGAControlSystem，设定地址为'192.168.0.10'
        self.fpga_system = FPGAControlSystem(address='192.168.0.10')

    def test_configure_fpga(self):
        '''测试configure_fpga函数，配置FPGA参数'''
        # 配置字符串数据
        config = 'FPGA configuration data'
        # 调用configure_fpga方法配置
        self.fpga_system.configure_fpga(config)
        # 验证配置数据是否正确
        self.assertEqual(self.fpga_system.fpga_config, config)

    @patch('random.random', return_value=0.06)
    def test_verify_fpga_success(self, mock_random):
        '''测试verify_fpga函数，在高概率下验证成功'''
        # 设置设备连接状态为True
        self.fpga_system.connected = True
        # 调用verify_fpga方法，期望返回True
        result = self.fpga_system.verify_fpga()
        # 验证返回结果是否符合预期
        self.assertTrue(result)

    @patch('time.sleep', return_value=None)
    def test_run_fpga_sequence(self, mock_sleep):
        '''测试run_fpga_sequence函数，模拟FPGA序列的运行'''
        # 调用run_fpga_sequence方法
        self.fpga_system.run_fpga_sequence()
        # 验证sleep函数是否被调用，模拟延迟时间
        mock_sleep.assert_called_once_with(0.5)

    @patch('time.sleep', return_value=None)
    def test_execute_success(self, mock_sleep):
        '''测试execute函数，模拟FPGA设备上操作的运行'''
        # 参数operation
        operation = {
            'type': 'FPGA',
        }
        # 返回值
        excepted_return = {
            'type': 'FPGA',
            'result': 'success!'
        }
        # 设置设备连接状态为True
        self.fpga_system.connected = True
        # 调用execute方法
        result = self.fpga_system.execute(operation)
        # 验证sleep函数是否被调用，模拟延迟时间
        mock_sleep.assert_called_once_with(0.1)
        # 验证返回结果是否符合预期
        self.assertEqual(result, excepted_return)

    def test_execute_failed(self):
        '''测试execute函数，模拟FPGA未连接情况'''
        # 参数operation
        operation = {
            'type': 'FPGA',
        }
        # 验证连接时抛出ConnectionError异常
        with self.assertRaises(ConnectionError):
            result = self.fpga_system.execute(operation)


# 执行单元测试
if __name__ == '__main__':
    unittest.main()
