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
import os
import configparser
from unittest.mock import patch, MagicMock
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.ni_chassis_interface import \
    NIChassisInterface, NIAOInterface, np, NIDOInterface, NIDIInterface
from qcos.config.qcos_config_manager import qcos_configer
from qcos.log.qcos_log import QCOSLogger

# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TestNIChassisInterface(unittest.TestCase):
    '''
    测试NI机箱接口类，包含硬件连接、断开、执行操作及校准等单元测试
    '''

    @classmethod
    def setUpClass(cls):
        '''
        初始化测试用的配置信息
        '''
        # 配置初始化：机箱配置和地址
        cls.config = {
            'chassis_config': 'default_chassis',
            'address': 'mock_ni_address'}

    @patch('nidaqmx.Task')
    def setUp(self, mock_nidaqmx_task):
        '''
        初始化测试接口，模拟NIChassisControlSystem，避免实际资源消耗
        '''
        # 使用patch装饰器模拟NIChassisControlSystem类
        patcher = patch(
            'qcos.'
            'quantum_heterogeneous_hw_unified_and_management_engine.'
            'hardware_interfaces.'
            'ni_chassis_interface.NIChassisControlSystem',
            autospec=True)
        self.addCleanup(patcher.stop)
        self.mock_ni_chassis_control_system = patcher.start()

        # 创建Mock控制系统实例
        self.mock_control_system =\
            self.mock_ni_chassis_control_system.return_value
        # 设置verify_chassis方法返回True，模拟成功连接
        self.mock_control_system.verify_chassis.return_value = True
        # 设置execute方法返回一个Mock结果
        self.mock_control_system.execute.return_value = 'MockNIChassisResult'
        # 设置其他需要的方法
        self.mock_control_system.configure_chassis = MagicMock()
        self.mock_control_system.run_chassis_sequence = MagicMock()
        self.mock_control_system.send_data = MagicMock()
        self.mock_control_system.receive_data = MagicMock(
            return_value={'ni_key': 'ni_value'})
        self.mock_control_system.close = MagicMock()

        # 初始化待测试的NI机箱接口
        self.interface = NIChassisInterface()

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_initialize(self, mock_logger):
        '''
        测试初始化函数是否正确加载配置和记录
        '''
        # 调用初始化函数
        self.interface.initialize()
        # 检查初始化的机箱配置
        # self.assertEqual(self.interface.chassis_config, 'default_chassis')
        mock_logger.assert_called_once_with('Initialized NI chassis interface')

    def test_connect_success(self):
        '''
        测试连接成功流程，验证机箱配置后连接
        '''
        # 调用connect方法
        self.interface.connect()
        # 检查连接状态是否更新为Connected
        self.assertEqual(self.interface.status, 'Connected')
        # 检查configure_chassis是否被调用一次
        # self.mock_control_system.
        # configure_chassis.assert_called_once_with('default_chassis')
        # 检查verify_chassis是否被调用一次
        self.mock_control_system.verify_chassis.assert_called_once()

    @patch('nidaqmx.Task')
    def test_connect_failure(self, mock_nidaqmx_task):
        '''
        测试连接失败流程，机箱验证失败触发异常
        '''
        # 将verify_chassis设置为False，模拟连接失败
        self.mock_control_system.verify_chassis.return_value = False
        # 创建一个新的接口实例
        new_interface = NIChassisInterface()
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
        测试执行操作，验证硬件连接状态及操作调用
        '''
        # 先连接硬件
        self.interface.connect()
        # 设置已连接状态
        self.interface.status = 'Connected'
        # 测试的操作参数
        test_operation = {'action': 'ni_test_action'}
        # 调用执行操作方法
        result = self.interface.execute_operation(test_operation)
        # 验证操作是否被正确调用
        self.mock_control_system.execute.assert_called_once_with(
            test_operation)
        # 检查返回结果是否正确
        self.assertEqual(result, 'MockNIChassisResult')

    def test_get_status(self):
        '''
        测试获取硬件状态，确保返回正确的状态字典
        '''
        # 先连接硬件
        self.interface.connect()
        # 更新测试状态和参数
        self.interface.status = 'Connected'
        self.interface.chassis_config = 'updated_chassis'
        # 调用获取状态方法
        status = self.interface.get_status()
        # 检查返回的状态信息
        self.assertEqual(status, {
            'status': 'Connected',
            'chassis_config': 'updated_chassis'
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
        self.mock_control_system.run_chassis_sequence.assert_called_once()

    def test_send_and_receive_data(self):
        '''
        测试数据传输，确认发送与接收操作
        '''
        # 先连接硬件
        self.interface.connect()
        # 设置测试数据
        test_data = {'ni_key': 'ni_value'}
        # 发送数据
        self.interface.send_data(test_data)
        # 验证发送是否被调用一次
        self.mock_control_system.send_data.assert_called_once_with(test_data)
        # 调用接收数据方法
        received_data = self.interface.receive_data()
        # 验证接收方法是否被调用一次
        self.mock_control_system.receive_data.assert_called_once()
        # 验证接收的数据是否正确
        self.assertEqual(received_data, {'ni_key': 'ni_value'})


class TestNIAOInterface(unittest.TestCase):
    '''
    测试 NIAOInterface 类
    '''

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('nidaqmx.Task')
    def setUp(self, mock_nidaqmx_task, mock_logger):
        '''
        测试前的准备工作
        '''
        config = configparser.ConfigParser()
        config.read(
            os.path.join(
                qcos_configer.get_config_path(),
                'qcos_config.conf'),
            encoding='utf-8')
        self.task = mock_nidaqmx_task.return_value
        self.ni_ao = NIAOInterface()

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_connect_success(self, mock_logger):
        '''
        测试 connect 方法成功场景
        '''
        # 模拟添加ao通道方法
        self.task.ao_channels.add_ao_voltage_chan.return_value = 'None'
        # 调用 connect 方法
        self.ni_ao.connect()
        # 验证 connect 方法成功连接 NIAO
        self.assertEqual(self.ni_ao.status, 'Connected')
        mock_logger.assert_called_once_with(
            'Successfully connected to NIAO')

    @patch('qcos.log.qcos_log.QCOSLogger.error')
    def test_connect_failure(self, mock_logger):
        '''
        测试 connect 方法失败场景
        '''
        # 模拟添加ao通道方法
        self.task.ao_channels.add_ao_voltage_chan.side_effect = Exception(
            'Test error')
        # 验证 connect 方法连接 NIAO 失败
        self.assertRaisesRegex(
            ConnectionError,
            'Failed to connected NIAO: Test error',
            self.ni_ao.connect)
        self.assertEqual(self.ni_ao.status, 'Disconnected')
        mock_logger.assert_called_once_with(
            'Failed to connected NIAO')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_disconnect(self, mock_logger):
        '''
        测试 disconnect 方法
        '''
        self.ni_ao.status = 'Connected'
        # 模拟 close 方法
        self.task.close = MagicMock()
        # 调用 disconnect 方法
        self.ni_ao.disconnect()
        # 验证 disconnect 方法被成功调用
        self.assertEqual(self.ni_ao.status, 'Disconnected')
        mock_logger.assert_called_once_with(
            'Disconnected from NIAO')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_execute_operation(self, mock_logger):
        '''
        测试 execute_operation 方法
        '''
        self.ni_ao.status = 'Connected'
        # 模拟 start 方法
        self.task.close = MagicMock()
        # 调用 execute_operation 方法
        self.ni_ao.execute_operation()
        # 验证 execute_operation 方法被成功调用
        mock_logger.assert_called_once_with(
            'Start outputting AO signals')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_stop_operation(self, mock_logger):
        '''
        测试 stop_operation 方法
        '''
        self.ni_ao.status = 'Connected'
        # 模拟方法中的函数
        self.task.wait_until_done = MagicMock()
        self.task.stop = MagicMock()
        # 调用 stop_operation 方法
        self.ni_ao.stop_operation()
        # 验证 stop_operation 方法被成功调用
        mock_logger.assert_called_once_with(
            'Stop outputting AO signals')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_send_data(self, mock_logger):
        '''
        测试 send_data 方法
        '''
        self.ni_ao.status = 'Connected'
        # 模拟方法中的函数返回
        self.ni_ao.get_all_ao = MagicMock(return_value=[[MagicMock()]])
        self.task.timing.cfg_samp_clk_timing = MagicMock()
        self.task.write = MagicMock()
        # 调用 send_data 方法
        self.ni_ao.send_data()
        # 验证 send_data 方法被成功调用
        mock_logger.assert_called_once_with(
            'Data sent to NIAO successfully')

    def test_receive_data(self):
        '''
        测试 receive_data 方法
        '''
        # 验证 receive_data 是否正确抛出异常
        self.assertRaisesRegex(
            RuntimeError,
            'There are no input channels in this'
            ' task to which data can be read.',
            self.ni_ao.receive_data)

    @patch('numpy.linspace')
    @patch('numpy.round')
    def test_ao_package_generator(self, mock_round, mock_linspace):
        '''
        测试 ao_package_generator 方法
        '''
        # 设置模拟值
        self.ni_ao.rate = 5e6
        mock_round.return_value = 0
        mock_linspace.return_value = np.pi / 2
        # 调用 ao_package_generator 方法
        signal = self.ni_ao.ao_package_generator(1)
        # 验证 ao_package_generator 方法被成功调用
        self.assertEqual(signal, 1.0)

    @patch('numpy.linspace')
    def test_ao_package_from_signal(self, mock_linspace):
        '''
        测试 ao_package_from_signal 方法
        '''
        # 设置模拟值
        mock_linspace.return_value = np.array([1])
        signal = [(0, 4), (0, 1)]
        # 调用 ao_package_from_signal 方法
        result = self.ni_ao.ao_package_from_signal(signal)
        # 验证 ao_package_from_signal 方法输出正确
        self.assertEqual(result, np.array([1]))

    def test_get_all_ao(self):
        '''
        测试 get_all_ao 方法
        '''
        # 模拟 ao_package_from_signal 方法的返回值
        self.ni_ao.ao_package_from_signal = MagicMock(
            return_value=np.array([1]))
        # 调用 get_all_ao 方法
        result = self.ni_ao.get_all_ao()
        # 验证 get_all_ao 方法输出结果
        self.assertIsNotNone(result)


class TestNIDOInterface(unittest.TestCase):
    '''
    测试 NIDOInterface 类
    '''

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('nidaqmx.Task')
    def setUp(self, mock_nidaqmx_task, mock_logger):
        '''
        测试前的准备工作
        '''
        config = configparser.ConfigParser()
        config.read(
            os.path.join(
                qcos_configer.get_config_path(),
                'qcos_config.conf'),
            encoding='utf-8')
        self.task = mock_nidaqmx_task.return_value
        self.ni_do = NIDOInterface()

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_connect(self, mock_logger):
        '''
        测试 connect 方法
        '''
        # 模拟添加do通道方法
        self.task.do_channels.add_do_chan.return_value = 'None'
        # 调用 connect 方法
        self.ni_do.connect()
        # 验证 connect 方法成功连接 NIDO
        self.assertEqual(self.ni_do.status, 'Connected')
        mock_logger.assert_called_once_with(
            'Successfully connected to NIDO')

    @patch('qcos.log.qcos_log.QCOSLogger.error')
    def test_connect_failure(self, mock_logger):
        '''
        测试 connect 方法失败场景
        '''
        # 模拟添加do通道方法
        self.task.do_channels.add_do_chan.side_effect = Exception(
            'Test error')
        # 验证 connect 方法连接 NIDO 失败
        self.assertRaisesRegex(
            ConnectionError,
            'Failed to connected NIDO: Test error',
            self.ni_do.connect)
        self.assertEqual(self.ni_do.status, 'Disconnected')
        mock_logger.assert_called_once_with(
            'Failed to connected NIDO')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_disconnect(self, mock_logger):
        '''
        测试 disconnect 方法
        '''
        self.ni_do.status = 'Connected'
        # 模拟 close 方法
        self.task.close = MagicMock()
        # 调用 disconnect 方法
        self.ni_do.disconnect()
        # 验证 disconnect 方法被成功调用
        self.assertEqual(
            self.ni_do.status,'Disconnected')
        mock_logger.assert_called_once_with(
            'Disconnected from NIDO')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_execute_operation(self, mock_logger):
        '''
        测试 execute_operation 方法
        '''
        self.ni_do.status = 'Connected'
        # 模拟 start 方法
        self.task.start = MagicMock()
        # 调用 execute_operation 方法
        self.ni_do.execute_operation()
        # 验证 execute_operation 方法被成功调用
        mock_logger.assert_called_once_with(
            'Start outputting DO signals')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_stop_operation(self, mock_logger):
        '''
        测试 stop_operation 方法
        '''
        self.ni_do.status = 'Connected'
        # 模拟方法中的函数
        self.task.wait_until_done = MagicMock()
        self.task.stop = MagicMock()
        # 调用 stop_operation 方法
        self.ni_do.stop_operation()
        # 验证 stop_operation 方法被成功调用
        mock_logger.assert_called_once_with(
            'Stop outputting DO signals')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_send_data(self, mock_logger):
        '''
        测试 send_data 方法
        '''
        self.ni_do.status = 'Connected'
        # 模拟方法中的函数返回
        self.ni_do.get_all_do = MagicMock(return_value=[[MagicMock()]])
        self.task.timing.cfg_samp_clk_timing = MagicMock()
        self.task.write = MagicMock()
        # 调用 send_data 方法
        self.ni_do.send_data()
        # 验证 send_data 方法被成功调用
        mock_logger.assert_called_once_with(
            'Data sent to NIDO successfully')

    def test_receive_data(self):
        '''
        测试 receive_data 方法
        '''
        # 验证 receive_data 是否正确抛出异常
        self.assertRaisesRegex(
            RuntimeError,
            'There are no input channels '
            'in this task to which data can be read.',
            self.ni_do.receive_data)

    def test_ttl_package_generator(self):
        '''
        测试 ttl_package_generator 方法
        '''
        # 模拟输入值
        data = [('00001000', 10)]
        # 调用 ttl_package_generator 方法
        result = self.ni_do.ttl_package_generator(data)
        # 验证 ttl_package_generator 方法输出结果
        self.assertEqual(type(result), np.ndarray)

    @patch('numpy.linspace')
    def test_ttl_package_from_signal(self, mock_linspace):
        '''
        测试 ttl_package_from_signal 方法
        '''
        # 设置模拟值
        mock_linspace.return_value = np.array([1])
        signal = [(0, 0), (50, 1)]
        # 调用 ttl_package_from_signal 方法
        result = self.ni_do.ttl_package_from_signal(signal)
        # 验证 ttl_package_from_signal 方法输出正确
        self.assertEqual(type(result), np.ndarray)

    def test_get_all_do(self):
        '''
        测试 get_all_do 方法
        '''
        # 模拟 ttl_package_from_signal 方法的返回值
        self.ni_do.ttl_package_from_signal = MagicMock(
            return_value=np.array([1]))
        self.ni_do.rate = 0
        # 调用 get_all_do 方法
        result = self.ni_do.get_all_do()
        # 验证 get_all_do 方法输出结果
        self.assertIsNotNone(result)


class TestNIDIInterface(unittest.TestCase):
    '''
    测试 NIDIInterface 类
    '''

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('nidaqmx.Task')
    def setUp(self, mock_nidaqmx_task, mock_logger):
        '''
        测试前的准备工作
        '''
        config = configparser.ConfigParser()
        config.read(
            os.path.join(
                qcos_configer.get_config_path(),
                'qcos_config.conf'),
            encoding='utf-8')
        self.task = mock_nidaqmx_task.return_value
        self.ni_di = NIDIInterface()

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_connect(self, mock_logger):
        '''
        测试 connect 方法
        '''
        # 模拟添加di通道方法
        self.task.di_channels.add_di_chan.return_value = 'None'
        # 调用 connect 方法
        self.ni_di.connect()
        # 验证 connect 方法成功连接 NIDI
        self.assertEqual(self.ni_di.status, 'Connected')
        mock_logger.assert_called_once_with(
            'Successfully connected to NIDI')

    @patch('qcos.log.qcos_log.QCOSLogger.error')
    def test_connect_failure(self, mock_logger):
        '''
        测试 connect 方法失败场景
        '''
        # 模拟添加di通道方法
        self.task.di_channels.add_di_chan.side_effect = Exception(
            'Test error')
        # 验证 connect 方法连接 NIDI 失败
        self.assertRaisesRegex(
            ConnectionError,
            'Failed to connected NIDI: Test error',
            self.ni_di.connect)
        self.assertEqual(self.ni_di.status, 'Disconnected')
        mock_logger.assert_called_once_with(
            'Failed to connected NIDI')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_disconnect(self, mock_logger):
        '''
        测试 disconnect 方法
        '''
        self.ni_di.status = 'Connected'
        # 模拟 close 方法
        self.task.close = MagicMock()
        # 调用 disconnect 方法
        self.ni_di.disconnect()
        # 验证 disconnect 方法被成功调用
        self.assertEqual(self.ni_di.status, 'Disconnected')
        mock_logger.assert_called_once_with('Disconnected from NIDI')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_execute_operation(self, mock_logger):
        '''
        测试 execute_operation 方法
        '''
        # 验证 execute_operation 是否正确抛出异常
        self.assertRaisesRegex(
            RuntimeError,
            'There is no operation to execute.',
            self.ni_di.execute_operation)

    def test_send_data(self):
        '''
        测试 send_data 方法
        '''
        # 验证 send_data 是否正确抛出异常
        self.assertRaisesRegex(
            RuntimeError,
            'There are no output channels'
            ' in this task to which data can be written.',
            self.ni_di.send_data)

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_receive_data(self, mock_logger):
        '''
        测试 receive_data 方法
        '''
        self.ni_di.status = 'Connected'
        # 模拟方法中的函数返回
        self.task.read = MagicMock()
        # 调用 receive_data 方法
        self.ni_di.receive_data()
        # 验证 receive_data 方法被成功调用
        mock_logger.assert_called_once_with('Data received successfully')


# 运行测试
if __name__ == '__main__':
    unittest.main()
