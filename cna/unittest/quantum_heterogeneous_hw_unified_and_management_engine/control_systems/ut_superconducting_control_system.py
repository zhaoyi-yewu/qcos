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
    control_systems.superconducting_control_system import \
    SuperconductingControlSystem


class TestSuperconductingControlSystem(unittest.TestCase):
    '''测试SuperconductingControlSystem类的单元测试类'''

    def setUp(self):
        '''设置测试环境，初始化一个SuperconductingControlSystem实例'''
        # 实例化SuperconductingControlSystem，设定地址为'192.168.0.10'
        self.superconducting_system = SuperconductingControlSystem(
            address='192.168.0.10')

    def test_set_working_point(self):
        '''测试set_working_point函数，设置工作点'''
        # 设置工作点值
        point = 5.0
        # 调用set_working_point方法设置工作点
        self.superconducting_system.set_working_point(point)
        # 验证工作点值是否正确
        self.assertEqual(self.superconducting_system.working_point, point)

    @patch('random.random', return_value=0.15)
    def test_verify_qubits_success(self, mock_random):
        '''测试verify_qubits函数，在高概率下验证成功'''
        # 设置设备连接状态为True
        self.superconducting_system.connected = True
        # 调用verify_qubits方法，期望返回True
        result = self.superconducting_system.verify_qubits(qubit_count=5)
        # 验证返回结果是否符合预期
        self.assertTrue(result)

    @patch('time.sleep', return_value=None)
    def test_run_calibration_sequence(self, mock_sleep):
        '''测试run_calibration_sequence函数，模拟校准序列的运行'''
        # 调用run_calibration_sequence方法
        self.superconducting_system.run_calibration_sequence()
        # 验证sleep函数是否被调用，模拟延迟时间
        mock_sleep.assert_called_once_with(1)


# 执行单元测试
if __name__ == '__main__':
    unittest.main()
