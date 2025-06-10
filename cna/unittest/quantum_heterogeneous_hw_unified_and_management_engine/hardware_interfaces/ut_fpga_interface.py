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
    hardware_interfaces.fpga_interface import FPGAInterface
import numpy as np


class TestFPGAInterface(unittest.TestCase):
    '''
    测试FPGA接口类，包含硬件连接、断开、执行操作及校准等单元测试
    '''
    #
    # @classmethod
    # def setUpClass(cls):
    #     '''
    #     初始化测试用的配置信息
    #     '''
    #     # 配置初始化：FPGA配置和地址
    #     cls.config = {'fpga_config':
    #     'default_config', 'address': 'mock_fpga_address'}

    def setUp(self):
        '''
        初始化测试接口，模拟FPGAControlSystem，避免实际资源消耗
        '''
        self.name = 'test_fpga'
        # 通信串口
        self.port = 'COM5'
        # 时钟周期
        self.clock_period = 1E-3
        # 返回数据字节数
        self.bytes_returned = 12
        self.test_time = 0.5
        self.connection = None
        self.status = 'Disconnected'

        # 使用patch装饰器模拟FPGAControlSystem类
        patcher = patch(
            'qcos.'
            'quantum_heterogeneous_hw_unified_and_management_engine.'
            'hardware_interfaces.'
            'fpga_interface.FPGAControlSystem', autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_fpga_control_system = patcher.start()

        # 创建Mock控制系统实例
        self.mock_control_system = self.mock_fpga_control_system.return_value
        # 设置verify_fpga方法返回True，模拟成功连接
        self.mock_control_system.verify_fpga.return_value = True
        # 设置execute方法返回一个Mock结果
        self.mock_control_system.execute.return_value = 'MockFPGAResult'
        # 设置其他需要的方法
        self.mock_control_system.configure_fpga = MagicMock()
        self.mock_control_system.run_fpga_sequence = MagicMock()
        self.mock_control_system.send_data = MagicMock()
        self.mock_control_system.receive_data = MagicMock(
            return_value={'fpga_key': 'fpga_value'})
        self.mock_control_system.close = MagicMock()
        #
        # # 初始化待测试的FPGA接口
        # self.interface = FPGAInterface(config=self.config)
        # 创建FPGAInterface实例
        self.fpga = FPGAInterface(self.name)

    def test_init(self):
        '''
        测试 __init__ 方法，确保能正确初始化实例变量
        '''

        # 断言name是否正确设置
        self.assertEqual(self.fpga.name, self.name)

        # 断言设备port是否正确设置
        self.assertEqual(self.fpga.port, self.port)

        # 断言clock_period是否正确设置
        self.assertEqual(self.fpga.clock_period, self.clock_period)

        # 断言bytes_returned是否正确设置
        self.assertEqual(self.fpga.bytes_returned, self.bytes_returned)

        # 断言bytes_returned是否正确设置
        self.assertEqual(self.fpga.test_time, self.test_time)

        # 断言connection是否正确设置
        self.assertIsNone(self.fpga.connection)

        # 断言status是否正确设置
        self.assertEqual(self.fpga.status, self.status)

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_initialize(self, mock_logger_info):
        '''
        测试初始化函数是否正确记录
        '''
        # 设置模拟对象的返回值
        mock_logger_info.return_value = 'Initialized FPGA interface'

        # 初始化设备
        self.fpga.initialize()

        # 检查QCOSLogger.info是否被调用一次
        mock_logger_info.assert_called_once_with(mock_logger_info.return_value)

    def test_connect_success(self):
        '''
        测试连接成功流程，验证FPGA配置后连接
        '''
        # 调用connect方法
        self.fpga.connect()
        # 检查连接状态是否更新为Connected
        self.assertEqual(self.fpga.status, 'Connected')
        # 检查connect是否被调用一次
        self.mock_control_system.connect.assert_called_once()
        # 检查verify_fpga是否被调用一次
        self.mock_control_system.verify_fpga.assert_called_once()

    def test_connect_failure(self):
        '''
        测试连接失败流程，FPGA验证失败触发异常
        '''
        # 将verify_fpga设置为False，模拟连接失败
        self.mock_control_system.verify_fpga.return_value = False
        # 创建一个新的接口实例
        new_interface = FPGAInterface(name='test_fpga_1')
        # 验证未连接时抛出ConnectionError异常
        with self.assertRaises(ConnectionError):
            new_interface.connect()

    def test_disconnect(self):
        '''
        测试断开连接，确保连接关闭并更新状态
        '''
        # 先连接硬件
        self.fpga.connect()
        # 调用断开连接方法
        self.fpga.disconnect()
        # 检查断开后状态是否更新为Disconnected
        self.assertEqual(self.fpga.status, 'Disconnected')
        # 检查连接对象是否被设置为None
        self.assertIsNone(self.fpga.connection)
        # 检查close方法是否被调用一次
        self.mock_control_system.disconnect.assert_called_once()

    def test_execute_operation(self):
        '''
        测试执行操作，验证硬件连接状态及操作调用
        '''
        # 先连接硬件
        self.fpga.connect()
        # 测试的操作参数
        test_operation = {'action': 'test_action'}
        # 调用执行操作方法
        result = self.fpga.execute_operation(test_operation)
        # 验证操作是否被正确调用
        self.mock_control_system.execute.assert_called_once_with(
            test_operation)
        # 检查返回结果是否正确
        self.assertEqual(result, 'MockFPGAResult')

    def test_execute_operation_failed(self):
        '''
        测试执行操作，验证硬件未连接情况
        '''
        # 先连接硬件
        self.fpga.connect()
        # 测试的操作参数
        test_operation = {'action': 'test_action'}
        # 调用断开连接方法
        self.fpga.disconnect()
        # 检查断开后状态是否更新为Disconnected
        self.assertEqual(self.fpga.status, 'Disconnected')
        # 验证未连接时抛出ConnectionError异常
        with self.assertRaises(ConnectionError):
            self.fpga.execute_operation(test_operation)

    def test_get_status(self):
        '''
        测试获取硬件状态，确保返回正确的状态字典
        '''
        # 先连接硬件
        self.fpga.connect()
        # 更新测试状态和参数
        self.fpga.status = 'Connected'
        # 调用获取状态方法
        status = self.fpga.get_status()
        # 检查返回的状态信息
        self.assertEqual(status, {
            'status': 'Connected',
        })

    def test_calibrate(self):
        '''
        测试校准流程，确认校准操作被调用
        '''
        # 先连接硬件
        self.fpga.connect()
        # 调用校准方法
        self.fpga.calibrate()
        # 验证校准方法是否被调用一次
        self.mock_control_system.run_fpga_sequence.assert_called_once()

    def test_calibrate_failed(self):
        '''
        测试校准流程，设备未连接情况，status ！= ”connected“
        '''
        # 先连接硬件
        self.fpga.connect()
        # 设置status为disconnected
        self.fpga.status = 'disconnected'
        # 验证未连接时抛出ConnectionError异常
        with self.assertRaises(ConnectionError):
            self.fpga.calibrate()

    def test_send_and_receive_data(self):
        '''
        测试数据传输，确认发送与接收操作
        '''
        # 先连接硬件
        self.fpga.connect()
        # 设置测试数据
        test_data = {'fpga_key': 'fpga_value'}
        # 发送数据
        self.fpga.send_data(test_data)
        # 验证发送是否被调用一次
        self.mock_control_system.send_data.assert_called_once_with(test_data)
        # 调用接收数据方法
        received_data = self.fpga.receive_data()
        # 验证接收方法是否被调用一次
        self.mock_control_system.receive_data.assert_called_once()
        # 验证接收的数据是否正确
        self.assertEqual(received_data, {'fpga_key': 'fpga_value'})

    @patch('qcos.'
           'config.qcos_config_manager.QcosConfigManager.'
           'get_fpga_ext_trig')
    @patch('qcos.'
           'quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.'
           'fpga_interface.FPGAInterface.pre_binary')
    @patch('qcos.'
           'quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.'
           'fpga_interface.FPGAInterface.packets_generator')
    def test_send_data_preprocess(
            self,
            mock_packets_generator,
            mock_pre_binary,
            mock_get_fpga_ext_trig):
        '''
        测试send_data_preprocess 函数是否正确处理数据和返回预期的输出
        '''
        # 设置测试数据
        test_data = {'fpga_key': 'fpga_value'}
        # 设置模拟对象的返回值
        mock_get_fpga_ext_trig.return_value = 1
        mock_pre_binary.return_value = [1, 0]
        mock_packets_generator.return_value = '0101'

        # 预处理数据
        packets = self.fpga.send_data_preprocess(test_data, repeat=100)

        # 检查 get_fpga_ext_trig 方法是否被正确调用
        mock_get_fpga_ext_trig.assert_called_once_with()
        # 检查 pre_binary 方法是否被正确调用
        mock_pre_binary.assert_called_once_with(test_data, self.clock_period)
        # 检查 packets_generator 方法是否被正确调用
        mock_packets_generator.assert_called_once_with([1, 0], 1, 100)
        # 检查返回的数据包是否正确
        expected_packets = [
            mock_packets_generator.return_value, int(
                100 * self.fpga.bytes_returned)]
        self.assertEqual(packets, expected_packets)

    def test_receive_data_postprocess(self):
        '''
        测试receive_data_postprocess 函数是否正确处理数据和返回预期的输出
        '''
        # 设置测试数据
        test_data = None
        repeat = 2
        ion_number = 3
        channel = list(range(ion_number))
        active_channel = channel
        kwargs = {
            'repeat': repeat,
            'ion_number': ion_number,
            'channel': channel,
            'active_channel': active_channel
        }

        # 后处理数据
        result = self.fpga.receive_data_postprocess(test_data, **kwargs)

        # 检查返回的数据结果是否符合预期
        self.assertEqual(result.shape, (ion_number * repeat,
                                        ))

    @patch('qcos.'
           'quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.'
           'fpga_interface.FPGAInterface.send_data_preprocess')
    @patch('qcos.'
           'quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.'
           'fpga_interface.FPGAInterface.send_data')
    @patch('qcos.'
           'quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.'
           'fpga_interface.FPGAInterface.receive_data')
    @patch('qcos.'
           'quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.'
           'fpga_interface.FPGAInterface.receive_data_postprocess')
    def test_process_and_transmit(
            self,
            mock_receive_data_postprocess,
            mock_receive_data,
            mock_send_data,
            mock_send_data_preprocess):
        '''
        测试process_and_transmit 函数是否正确处理和收发数据
        '''
        # 设置测试数据
        test_data = {'fpga_key': 'fpga_value'}

        # 设置模拟对象的返回值
        mock_receive_data_postprocess.return_value = ['100', 10]
        mock_receive_data.return_value = {'data': 1}
        mock_send_data.return_value = None
        mock_send_data_preprocess.return_value = ['100', 10]

        # 设置实例属性以通过 hasattr 检查
        self.fpga.preprocess = True
        self.fpga.postprocess = True

        # 处理并收发数据
        result = self.fpga.process_and_transmit(test_data)

        # 检查 send_data_preprocess 方法是否被正确调用
        mock_send_data_preprocess.assert_called_once_with(test_data)
        # 检查 send_data 方法是否被正确调用
        mock_send_data.assert_called_once_with(
            mock_send_data_preprocess.return_value)
        # 检查 receive_data 方法是否被正确调用
        mock_receive_data.assert_called_once_with()
        # 检查 receive_data_postprocess 方法是否被正确调用
        mock_receive_data_postprocess.assert_called_once_with(
            mock_receive_data.return_value)
        # 检查返回的数据包是否正确
        self.assertEqual(result, mock_receive_data_postprocess.return_value)

    @patch('qcos.'
           'quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.'
           'fpga_interface.FPGAInterface.timestamp_generator')
    def test_timestamp(self, mock_timestamp_generator):
        '''
        测试timestamp 函数是否正确处理时间数据
        '''
        # 设置模拟对象的返回值
        mock_timestamp_generator.return_value = '0110'
        # 设置测试数据
        duration = 10

        # 处理duration数据
        result = self.fpga.timestamp(duration, self.clock_period)

        # 检查 timestamp_generator 方法是否被正确调用
        mock_timestamp_generator.assert_called_once_with(
            int(duration / self.clock_period - 1))
        # # 检查返回的数据包是否正确
        self.assertEqual(result, mock_timestamp_generator.return_value)

    def test_timestamp_generator(self):
        '''
        测试timestamp_generator 函数是否正确执行
        '''
        # 设置测试数据
        n = 10

        # 处理duration数据
        result = self.fpga.timestamp_generator(n)

        # 检查返回的数据包是否正确
        self.assertTrue(result)
        self.assertEqual(len(result), 40)

    def test_chapter_padding(self):
        '''
        测试chapter_padding 函数是否正确执行
        '''
        # 设置测试数据
        chapter = '10001100000000001001'
        # 设置预期返回
        expected_value = '10001100000000001000000000 01'

        # 处理duration数据
        result = self.fpga.chapter_padding(chapter)

        # 检查返回的数据包是否正确
        self.assertEqual(result, expected_value)

    @patch('qcos.'
           'quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.'
           'fpga_interface.FPGAInterface.chapter_padding')
    @patch('qcos.'
           'quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.'
           'fpga_interface.FPGAInterface.timestamp')
    def test_timestamp(self, mock_timestamp, mock_chapter_padding):
        '''
        测试timestamp 函数是否正确处理时间数据
        '''
        # 设置模拟对象的返回值
        mock_timestamp.return_value = '0110'
        mock_chapter_padding.return_value = '01000000'

        # 设置测试数据
        pulses = [(1, 2)]
        # 设置预期返回
        expected_value = [['01000000', '0110']]

        # 处理duration数据
        result = self.fpga.pre_binary(pulses, self.clock_period)

        # 检查 chapter_padding 方法是否被正确调用
        mock_chapter_padding.assert_called_once_with(pulses[0][0])
        # 检查 timestamp_generator 方法是否被正确调用
        mock_timestamp.assert_called_once_with(
            pulses[0][1], self.clock_period)

        # 检查返回的数据包是否正确
        self.assertEqual(result, expected_value)

    @patch('qcos.'
           'quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.'
           'fpga_interface.FPGAInterface.timestamp_generator')
    def test_packets_generator(self, mock_timestamp_generator):
        '''
        测试packets_generator 函数是否正确处理时间数据
        '''
        # 设置模拟对象的返回值
        mock_timestamp_generator.return_value = '01'

        # 设置测试数据
        pulses = [['0110', '1101'],
                  ['1001', '1011']]
        ext_trig = 1
        repeat = 10
        # 设置预期返回
        expected_value = [['01000000', '0110']]

        # 处理duration数据
        result = self.fpga.packets_generator(
            pulses, ext_trig, repeat)

        # 检查 timestamp_generator 方法是否被正确调用
        mock_timestamp_generator.assert_any_call(7)

        # 检查返回的数据包是否正确
        self.assertTrue(result)
        self.assertEqual(len(result), 187)


# 运行测试
if __name__ == '__main__':
    unittest.main()
