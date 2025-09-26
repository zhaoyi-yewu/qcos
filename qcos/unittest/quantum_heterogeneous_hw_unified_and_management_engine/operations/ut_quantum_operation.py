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
    operations.quantum_operation import QuantumOperation
from typing import Any, Dict, List


class MockQuantumHardwareInterface(object):
    """
    模拟QuantumHardwareInterface类，用于测试QuantumOperation
    """

    def execute_operation(self, gate: str, qubits: list) -> Any:
        """
        模拟execute_operation方法

        参数:
        gate (str): 量子门类型
        qubits (list): 作用的量子比特

        返回:
        Any: 模拟的操作结果
        """
        pass


class TestQuantumOperation(unittest.TestCase):
    """
    测试QuantumOperation抽象基类，确保无法直接实例化
    """

    def test_cannot_instantiate_abstract_class(self):
        """
        测试QuantumOperation类不能被实例化
        """
        # 尝试实例化QuantumOperation，应该抛出TypeError
        with self.assertRaises(TypeError):
            QuantumOperation()


if __name__ == '__main__':
    unittest.main()
