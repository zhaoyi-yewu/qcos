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
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.quantum_hardware_interface import \
    QuantumHardwareInterface
import abc
from typing import Dict, Any, List


class TestQuantumHardwareInterface(unittest.TestCase):
    '''
    测试QuantumHardwareInterface抽象基类，确保其无法被实例化，并且子类必须实现所有抽象方法
    '''

    def test_cannot_instantiate(self):
        '''
        测试QuantumHardwareInterface无法被实例化
        '''
        # 尝试实例化抽象基类，应该抛出TypeError
        with self.assertRaises(TypeError):
            QuantumHardwareInterface()

    def test_subclass_must_implement_all_methods(self):
        '''
        测试子类必须实现所有抽象方法
        '''
        class IncompleteSubclass(QuantumHardwareInterface):
            '''
            定义一个未实现所有抽象方法的子类
            '''

            def initialize(self):
                pass

        # 尝试实例化不完整的子类，应该抛出TypeError
        with self.assertRaises(TypeError):
            IncompleteSubclass()

        class CompleteSubclass(QuantumHardwareInterface):
            '''
            定义一个完整实现所有抽象方法的子类
            '''

            def initialize(self):
                pass

            def connect(self):
                pass

            def disconnect(self):
                pass

            def execute_operation(self, gate: str, qubits: list):
                pass

            def get_status(self) -> Dict[str, Any]:
                pass

            def calibrate(self):
                pass

            def send_data(self, data: Any):
                pass

            def receive_data(self) -> Any:
                pass

        # 实例化完整的子类，应该成功
        try:
            instance = CompleteSubclass()
        except TypeError:
            self.fail('CompleteSubclass 实现了所有抽象方法，应该可以被实例化')


# 运行测试
if __name__ == '__main__':
    unittest.main()
