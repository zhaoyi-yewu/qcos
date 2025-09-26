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
from typing import Dict, Any, List
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.neutral_atom_processor_interface import \
    NeutralAtomProcessorInterface  # 假设此为真实模块路径


class TestNeutralAtomProcessorInterface(unittest.TestCase):
    '''
    测试中性原子量子处理器接口类，包含硬件连接、断开、执行量子操作及校准等单元测试
    '''

    @classmethod
    def setUpClass(cls):
        '''
        初始化测试用的配置信息
        '''
        # 配置初始化：晶格配置、原子数量和地址
        cls.config = {
            'lattice_configuration': 'default_lattice',
            'atom_count': 20,
            'address': 'mock_atom_address'}

    def setUp(self):
        '''
        初始化测试接口，模拟NeutralAtomControlSystem，避免实际资源消耗
        '''
        # 使用patch装饰器模拟NeutralAtomControlSystem类
        patcher = patch(
            'qcos.'
            'quantum_heterogeneous_hw_unified_and_management_engine.'
            'hardware_interfaces.neutral_atom_processor_interface.'
            'NeutralAtomControlSystem',
            autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_neutral_atom_control_system = patcher.start()

        # 创建Mock控制系统实例
        self.mock_control_system \
            = self.mock_neutral_atom_control_system.return_value
        # 设置verify_atoms方法返回True，模拟成功连接
        self.mock_control_system.verify_atoms.return_value = True
        # 设置execute方法返回一个Mock结果
        self.mock_control_system.execute.return_value = 'MockNeutralAtomResult'
        # 设置其他需要的方法
        self.mock_control_system.configure_lattice = MagicMock()
        self.mock_control_system.run_atom_trapping_sequence = MagicMock()
        self.mock_control_system.send_data = MagicMock()
        self.mock_control_system.receive_data = MagicMock(
            return_value={'atom_key': 'atom_value'})
        self.mock_control_system.close = MagicMock()

        # 初始化待测试的中性原子量子处理器接口
        self.interface = NeutralAtomProcessorInterface(config=self.config)

    def test_initialize(self):
        '''
        测试初始化函数是否正确加载配置和记录
        '''
        # 检查初始化的晶格配置和原子数量
        self.assertEqual(
            self.interface.lattice_configuration,
            'default_lattice')
        self.assertEqual(self.interface.atom_count, 20)

    def test_connect_success(self):
        '''
        测试连接成功流程，验证原子数量后连接
        '''
        # 调用connect方法
        self.interface.connect()
        # 检查连接状态是否更新为Connected
        self.assertEqual(self.interface.status, 'Connected')
        # 检查configure_lattice是否被调用一次
        self.mock_control_system.configure_lattice.assert_called_once_with(
            'default_lattice')
        # 检查verify_atoms是否被调用一次
        self.mock_control_system.verify_atoms.assert_called_once_with(20)

    def test_connect_failure(self):
        '''
        测试连接失败流程，原子验证失败触发异常
        '''
        # 将verify_atoms设置为False，模拟连接失败
        self.mock_control_system.verify_atoms.return_value = False
        # 创建一个新的接口实例
        new_interface = NeutralAtomProcessorInterface(config=self.config)
        # 验证连接时抛出ConnectionError异常
        with self.assertRaises(ConnectionError):
            new_interface.connect()

    def test_disconnect(self):
        '''
        测试断开连接，确保连接关闭并更新状态
        '''
        # 先连接硬件
        self.interface.connect()
        # 调用断开连接方法
        self.interface.disconnect()
        # 检查断开后状态是否更新为Disconnected
        self.assertEqual(self.interface.status, 'Disconnected')
        # 检查连接对象是否被设置为None
        self.assertIsNone(self.interface.connection)
        # 检查close方法是否被调用一次
        self.mock_control_system.close.assert_called_once()

    def test_execute_operation(self):
        '''
        测试执行量子操作，验证硬件连接状态及操作调用
        '''
        # 先连接硬件
        self.interface.connect()
        # 设置已连接状态
        self.interface.status = 'Connected'
        # 测试的量子门类型和目标量子比特
        test_gate = 'X'
        test_qubits = [3, 4]
        # 调用执行操作方法
        result = self.interface.execute_operation(test_gate, test_qubits)
        # 验证操作是否被正确调用
        self.mock_control_system.execute.assert_called_once_with({
            'type': 'quantum_gate',
            'gate': test_gate,
            'qubits': test_qubits
        })
        # 检查返回结果是否正确
        self.assertEqual(result, 'MockNeutralAtomResult')

    def test_get_status(self):
        '''
        测试获取硬件状态，确保返回正确的状态字典
        '''
        # 先连接硬件
        self.interface.connect()
        # 更新测试状态和参数
        self.interface.status = 'Connected'
        self.interface.lattice_configuration = 'updated_lattice'
        self.interface.atom_count = 30
        # 调用获取状态方法
        status = self.interface.get_status()
        # 检查返回的状态信息
        self.assertEqual(status, {
            'status': 'Connected',
            'atom_count': 30,
            'lattice_configuration': 'updated_lattice'
        })

    def test_calibrate(self):
        '''
        测试校准流程，确认校准操作被调用
        '''
        # 先连接硬件
        self.interface.connect()
        # 调用校准方法
        self.interface.calibrate()
        # 验证校准方法是否被调用一次
        self.mock_control_system.run_atom_trapping_sequence.assert_called_once()

    def test_send_and_receive_data(self):
        '''
        测试数据传输，确认发送与接收操作
        '''
        # 先连接硬件
        self.interface.connect()
        # 设置测试数据
        test_data = {'atom_key': 'atom_value'}
        # 发送数据
        self.interface.send_data(test_data)
        # 验证发送是否被调用一次
        self.mock_control_system.send_data.assert_called_once_with(test_data)
        # 调用接收数据方法
        received_data = self.interface.receive_data()
        # 验证接收方法是否被调用一次
        self.mock_control_system.receive_data.assert_called_once()
        # 验证接收的数据是否正确
        self.assertEqual(received_data, {'atom_key': 'atom_value'})


# 运行测试
if __name__ == '__main__':
    unittest.main()
