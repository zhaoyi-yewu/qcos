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
    control_systems.awg_control_system import \
    AWGControlSystem


class TestAWGControlSystem(unittest.TestCase):
    '''测试AWGControlSystem类的单元测试类'''

    def setUp(self):
        '''设置测试环境，初始化一个AWGControlSystem实例'''
        # 实例化AWGControlSystem，设定地址为'192.168.0.10'
        self.awg_system = AWGControlSystem(address='192.168.0.10')

    def test_load_waveform(self):
        '''测试load_waveform函数，加载波形数据'''
        # 假设的波形数据
        waveform = [1, 2, 3, 4]
        # 调用load_waveform方法加载波形
        self.awg_system.load_waveform(waveform)
        # 验证加载的数据是否正确
        self.assertEqual(self.awg_system.waveform_data, waveform)

    @patch('random.random', return_value=0.06)
    def test_verify_awg_connected_success(self, mock_random):
        '''测试verify_awg函数，模拟连接状态和验证成功率'''
        # 设置设备连接状态为True
        self.awg_system.connected = True
        # 验证AWG状态，期望返回True（因为随机值大于0.05）
        result = self.awg_system.verify_awg()
        # 验证返回结果是否符合预期
        self.assertTrue(result)

    @patch('random.random', return_value=0.04)
    def test_verify_awg_connected_failure(self, mock_random):
        '''测试verify_awg函数，在较低随机值下模拟连接失败'''
        # 设置设备连接状态为True
        self.awg_system.connected = True
        # 验证AWG状态，期望返回False（因为随机值小于0.05）
        result = self.awg_system.verify_awg()
        # 验证返回结果是否符合预期
        self.assertFalse(result)

    def test_verify_awg_not_connected(self):
        '''测试verify_awg函数，在设备未连接时模拟失败情况'''
        # 设置设备连接状态为False
        self.awg_system.connected = False
        # 调用verify_awg方法，期望返回False
        result = self.awg_system.verify_awg()
        # 验证返回结果是否符合预期
        self.assertFalse(result)

    @patch('time.sleep', return_value=None)
    def test_run_awg_sequence(self, mock_sleep):
        '''测试run_awg_sequence函数，模拟AWG序列的运行'''
        # 调用run_awg_sequence方法
        self.awg_system.run_awg_sequence()
        # 验证sleep函数是否被调用，模拟延迟时间
        mock_sleep.assert_called_once_with(0.5)


if __name__ == '__main__':
    unittest.main()
