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
    control_systems.neutral_atom_control_system import \
    NeutralAtomControlSystem


class TestNeutralAtomControlSystem(unittest.TestCase):
    '''测试NeutralAtomControlSystem类的单元测试类'''

    def setUp(self):
        '''设置测试环境，初始化一个NeutralAtomControlSystem实例'''
        # 实例化NeutralAtomControlSystem，设定地址为'192.168.0.10'
        self.atom_system = NeutralAtomControlSystem(address='192.168.0.10')

    def test_configure_lattice(self):
        '''测试configure_lattice函数，配置原子阵列'''
        # 配置字符串数据
        config = 'Lattice configuration data'
        # 调用configure_lattice方法配置阵列
        self.atom_system.configure_lattice(config)
        # 验证配置数据是否正确
        self.assertEqual(self.atom_system.lattice_config, config)

    @patch('random.random', return_value=0.15)
    def test_verify_atoms_success(self, mock_random):
        '''测试verify_atoms函数，在高概率下验证成功'''
        # 设置设备连接状态为True
        self.atom_system.connected = True
        # 调用verify_atoms方法，期望返回True
        result = self.atom_system.verify_atoms(atom_count=100)
        # 验证返回结果是否符合预期
        self.assertTrue(result)

    @patch('time.sleep', return_value=None)
    def test_run_atom_trapping_sequence(self, mock_sleep):
        '''测试run_atom_trapping_sequence函数，模拟原子捕获序列的运行'''
        # 调用run_atom_trapping_sequence方法
        self.atom_system.run_atom_trapping_sequence()
        # 验证sleep函数是否被调用，模拟延迟时间
        mock_sleep.assert_called_once_with(1)


# 执行单元测试
if __name__ == '__main__':
    unittest.main()
