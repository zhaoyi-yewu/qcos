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
from unittest.mock import Mock
from typing import Any, List
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    operations.quantum_operation import QuantumOperation
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    operations.quantum_gate_operation import QuantumGateOperation


class MockQuantumHardwareInterface(object):
    '''
    模拟QuantumHardwareInterface类，用于测试QuantumGateOperation
    '''

    def execute_operation(self, gate: str, qubits: List[int]) -> Any:
        '''
        模拟execute_operation方法

        参数:
        gate (str): 量子门类型
        qubits (List[int]): 作用的量子比特

        返回:
        Any: 模拟的操作结果
        '''
        return 'MockOperationResult'

# QuantumGateOperation的单元测试类


class TestQuantumGateOperation(unittest.TestCase):
    '''
    测试QuantumGateOperation类，确保量子门操作正确执行
    '''

    def setUp(self):
        '''
        初始化测试环境，创建QuantumGateOperation实例和Mock接口
        '''
        # 量子门类型
        self.gate = 'H'
        # 作用的量子比特
        self.qubits = [0, 1]
        # 创建QuantumGateOperation实例
        self.quantum_gate_op = QuantumGateOperation(self.gate, self.qubits)
        # 创建MockQuantumHardwareInterface实例
        self.mock_interface = MockQuantumHardwareInterface()

    def test_initialization(self):
        '''
        测试QuantumGateOperation的初始化是否正确
        '''
        # 检查量子门类型是否正确初始化
        self.assertEqual(self.quantum_gate_op.gate, self.gate)
        # 检查量子比特列表是否正确初始化
        self.assertEqual(self.quantum_gate_op.qubits, self.qubits)

    def test_execute_operation(self):
        '''
        测试QuantumGateOperation的execute方法是否正确调用接口
        '''
        # 执行量子门操作
        result = self.quantum_gate_op.execute(self.mock_interface)
        # 检查execute_operation方法是否被正确调用
        self.assertEqual(result, 'MockOperationResult')

    def test_execute_with_single_qubit(self):
        '''
        测试QuantumGateOperation的execute方法处理单个量子比特
        '''
        # 创建单个量子比特的QuantumGateOperation实例
        single_qubit_op = QuantumGateOperation(self.gate, 2)
        # 执行量子门操作
        result = single_qubit_op.execute(self.mock_interface)
        # 检查量子比特列表是否被正确转换为列表
        self.assertEqual(single_qubit_op.qubits, [2])
        # 检查执行结果是否正确
        self.assertEqual(result, 'MockOperationResult')


# 运行所有单元测试
if __name__ == '__main__':
    unittest.main()
