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


# 在导入接口类之前，先patch IonTrapControlSystem
with patch('qcos.'
           'quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.'
           'ion_trap_processor_interface.IonTrapControlSystem', 
           autospec=True) as MockIonTrapControlSystem:
    from qcos.\
        quantum_heterogeneous_hw_unified_and_management_engine.\
        hardware_interfaces.ion_trap_processor_interface import \
        IonTrapProcessorInterface


class TestIonTrapProcessorInterface(unittest.TestCase):
    '''
    测试离子阱量子处理器接口，包含硬件连接、断开、执行量子操作及校准等单元测试
    '''

    @classmethod
    def setUpClass(cls):
        '''
        初始化测试用的配置信息
        '''
        # 配置初始化：频率和离子数量
        cls.config = {
            'trap_frequency': 1.0,
            'ion_count': 10,
            'address': 'mock_address'}

    def setUp(self):
        '''
        初始化测试接口，模拟IonTrapControlSystem，避免实际资源消耗
        '''
        # 获取当前patch的MockIonTrapControlSystem
        self.mock_control_system_class = patch(
            'qcos.'
            'quantum_heterogeneous_hw_unified_and_management_engine.'
            'hardware_interfaces.ion_trap_processor_interface.'
            'IonTrapControlSystem',
            autospec=True).start()
        self.addCleanup(patch.stopall)

        # 设置 Mock 控制系统实例
        self.mock_control_system = self.mock_control_system_class.return_value
        # 设置verify_ions返回True
        self.mock_control_system.verify_ions.return_value = True
        # 设置execute方法返回一个Mock结果
        self.mock_control_system.execute.return_value = 'MockResult'
        # 设置其他需要的方法
        self.mock_control_system.run_ion_cooling_sequence = MagicMock()
        self.mock_control_system.send_data = MagicMock()
        self.mock_control_system.receive_data = MagicMock(
            return_value={'key': 'value'})
        self.mock_control_system.close = MagicMock()

        # 初始化接口
        self.interface = IonTrapProcessorInterface(config=self.config)
        # 调用 connect
        self.interface.connect()

    def tearDown(self):
        '''
        清理patch
        '''
        patch.stopall()

    def test_initialize(self):
        '''
        测试初始化函数是否正确加载配置和记录
        '''
        # 检查初始化的频率和离子数量
        self.assertEqual(self.interface.trap_frequency, 1.0)
        self.assertEqual(self.interface.ion_count, 10)

    def test_connect_success(self):
        '''
        测试连接成功流程，验证离子数量后连接
        '''
        # 确保 verify_ions 返回True
        self.mock_control_system.verify_ions.return_value = True
        # 调用 connect
        self.interface.connect()
        # 检查状态
        self.assertEqual(self.interface.status, 'Connected')
        # 检查verify_ions被调用
        self.mock_control_system.verify_ions.assert_called_with(10)

    def test_connect_failure(self):
        '''
        测试连接失败流程，离子验证失败触发异常
        '''
        # 将 verify_ions 设置为 False，模拟连接失败
        self.mock_control_system.verify_ions.return_value = False
        # 创建一个新的接口实例
        new_interface = IonTrapProcessorInterface(config=self.config)
        # 测试连接失败
        with self.assertRaises(ConnectionError):
            new_interface.connect()

    def test_disconnect(self):
        '''
        测试断开连接，确保连接关闭并更新状态
        '''
        # 调用 disconnect
        self.interface.disconnect()
        # 检查状态
        self.assertEqual(self.interface.status, 'Disconnected')
        # 检查connection是否为None
        self.assertIsNone(self.interface.connection)
        # 检查close方法是否被调用
        self.mock_control_system.close.assert_called_once()

    def test_execute_operation(self):
        '''
        测试执行量子操作，验证硬件连接状态及操作调用
        '''
        # 测试的操作和目标量子比特
        test_gate = 'H'
        test_qubits = [1, 2]
        # 调用操作方法
        result = self.interface.execute_operation(test_gate, test_qubits)
        # 验证操作是否被正确调用
        self.mock_control_system.execute.assert_called_once_with({
            'type': 'quantum_gate',
            'gate': test_gate,
            'qubits': test_qubits
        })
        # 检查返回结果是否正确
        self.assertEqual(result, 'MockResult')

    def test_get_status(self):
        '''
        测试获取硬件状态，确保返回正确的状态字典
        '''
        # 更新测试状态和参数
        self.interface.status = 'Connected'
        self.interface.trap_frequency = 2.0
        self.interface.ion_count = 20
        # 调用获取状态方法
        status = self.interface.get_status()
        # 检查返回的状态信息
        self.assertEqual(status, {
            'status': 'Connected',
            'trap_frequency': 2.0,
            'ion_count': 20
        })

    def test_calibrate(self):
        '''
        测试校准流程，确认校准操作被调用
        '''
        # 调用校准方法
        self.interface.calibrate()
        # 验证校准方法是否被调用
        self.mock_control_system.run_ion_cooling_sequence.assert_called_once()

    def test_send_and_receive_data(self):
        '''
        测试数据传输，确认发送与接收操作
        '''
        # 设置测试数据
        test_data = {'key': 'value'}
        # 发送数据
        self.interface.send_data(test_data)
        # 验证发送是否被调用
        self.mock_control_system.send_data.assert_called_once_with(test_data)
        # 调用接收数据
        received_data = self.interface.receive_data()
        # 验证接收方法是否被调用
        self.mock_control_system.receive_data.assert_called_once()
        # 验证接收的数据
        self.assertEqual(received_data, {'key': 'value'})


if __name__ == '__main__':
    unittest.main()
