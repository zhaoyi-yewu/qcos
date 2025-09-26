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
    control_systems.ion_trap_control_system import \
    IonTrapControlSystem


class TestIonTrapControlSystem(unittest.TestCase):
    '''测试IonTrapControlSystem类的单元测试类'''

    def setUp(self):
        '''设置测试环境，初始化一个IonTrapControlSystem实例'''
        # 实例化IonTrapControlSystem，设定地址为'192.168.0.10'
        self.ion_trap_system = IonTrapControlSystem(address='192.168.0.10')

    def test_set_trap_frequency(self):
        '''测试set_trap_frequency函数，设置离子阱频率'''
        # 设置频率值
        frequency = 50.0
        # 调用set_trap_frequency方法设置频率
        self.ion_trap_system.set_trap_frequency(frequency)
        # 验证频率值是否正确
        self.assertEqual(self.ion_trap_system.trap_frequency, frequency)

    @patch('random.random', return_value=0.15)
    def test_verify_ions_success(self, mock_random):
        '''测试verify_ions函数，在高概率下验证成功'''
        # 设置设备连接状态为True
        self.ion_trap_system.connected = True
        # 调用verify_ions方法，期望返回True
        result = self.ion_trap_system.verify_ions(ion_count=10)
        # 验证返回结果是否符合预期
        self.assertTrue(result)

    @patch('time.sleep', return_value=None)
    def test_run_ion_cooling_sequence(self, mock_sleep):
        '''测试run_ion_cooling_sequence函数，模拟离子冷却序列的运行'''
        # 调用run_ion_cooling_sequence方法
        self.ion_trap_system.run_ion_cooling_sequence()
        # 验证sleep函数是否被调用，模拟延迟时间
        mock_sleep.assert_called_once_with(1)


# 执行单元测试
if __name__ == '__main__':
    unittest.main()
