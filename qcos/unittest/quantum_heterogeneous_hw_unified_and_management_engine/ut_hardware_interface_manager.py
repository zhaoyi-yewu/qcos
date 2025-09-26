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
from typing import Any, Dict, List


# 在导入会加载 DLL 的模块之前，先模拟 ctypes.cdll.LoadLibrary 和 qcos_configer.get_awg_lib_path
with patch('ctypes.cdll.LoadLibrary') as mock_load_library, \
        patch('qcos.config.qcos_config_manager.'
              'qcos_configer.get_awg_lib_path',
              return_value='dummy_path'), \
        patch('qcos.config.qcos_config_manager.'
              'qcos_configer.get_awg_serial_number',
              return_value='dummy_serial'), \
        patch('qcos.config.qcos_config_manager.'
              'qcos_configer.get_awg_product',
              return_value='dummy_product'), \
        patch('qcos.config.qcos_config_manager.'
              'qcos_configer.get_awg_sampling_rate',
              return_value=1000), \
        patch('qcos.config.qcos_config_manager.'
              'qcos_configer.get_awg_channel',
              return_value=1), \
        patch('qcos.config.qcos_config_manager.'
              'qcos_configer.get_awg_trigger_mode',
              return_value=1):

    # 创建一个MagicMock对象作为模拟的DLL
    mock_dll = MagicMock()
    # 设置LoadLibrary返回模拟的DLL对象
    mock_load_library.return_value = mock_dll

    from qcos.\
        quantum_heterogeneous_hw_unified_and_management_engine.\
        hardware_interface_manager import \
        HardwareInterfaceManager
    from qcos.\
        quantum_heterogeneous_hw_unified_and_management_engine.\
        observer.hardware_observer import \
        HardwareObserver

    class TestHardwareInterfaceManager(unittest.TestCase):
        '''
        测试 HardwareInterfaceManager 类的单元测试类
        '''

        def setUp(self):
            '''
            初始化测试环境
            '''
            # 使用patch装饰器模拟hardware_interface_manager中的qcos_logger
            patcher_logger = patch(
                'qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
                'hardware_interface_manager.qcos_logger',
                new=MagicMock())
            # 启动patcher并获取模拟的qcos_logger对象
            self.mock_logger = patcher_logger.start()
            # 添加清理工作，确保patcher在测试结束后停止
            self.addCleanup(patcher_logger.stop)

            # 创建HardwareInterfaceManager的实例
            self.manager = HardwareInterfaceManager(config_path='dummy_path')

            # 手动设置硬件接口的模拟对象
            self.mock_awg_interface = MagicMock()
            self.mock_superconducting_interface = MagicMock()
            self.manager.interfaces = {
                'awg': self.mock_awg_interface,
                'superconducting': self.mock_superconducting_interface
            }

        @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
               'hardware_interface_manager.'
               'HardwareInterfaceManager._notify_observers')
        def test_connect_hardware_success(self, mock_notify_observers):
            '''
            测试连接硬件成功的情况
            '''
            # 设置接口的connect方法不抛出异常
            self.mock_awg_interface.connect.return_value = None
            # 设置接口的get_status方法返回特定状态
            self.mock_awg_interface.get_status.return_value = {
                'status': 'Connected'}

            # 调用connect_hardware方法连接'awg'硬件
            self.manager.connect_hardware('awg')

            # 断言接口的connect方法被调用一次
            self.mock_awg_interface.connect.assert_called_once()
            # 断言日志记录了连接成功的信息
            self.mock_logger.debug.assert_called_with('Connected to awg')

            # 断言_notify_observers方法被调用一次，并传入正确的参数
            mock_notify_observers.assert_called_once_with(
                'awg', {'status': 'Connected'})

        @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
               'hardware_interface_manager.'
               'HardwareInterfaceManager._notify_observers')
        def test_connect_hardware_failure(self, mock_notify_observers):
            '''
            测试连接硬件失败的情况
            '''
            # 设置接口的connect方法抛出异常
            self.mock_awg_interface.connect.side_effect = Exception(
                'Connection Error')

            # 调用connect_hardware方法连接'awg'硬件
            self.manager.connect_hardware('awg')

            # 断言接口的connect方法被调用一次
            self.mock_awg_interface.connect.assert_called_once()
            # 断言日志记录了错误信息
            self.mock_logger.error.assert_called_with(
                'Failed to connect to awg: Connection Error')
            # 断言_notify_observers方法没有被调用
            mock_notify_observers.assert_not_called()

        @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
               'hardware_interface_manager.'
               'HardwareInterfaceManager._notify_observers')
        def test_disconnect_hardware_success(self, mock_notify_observers):
            '''
            测试断开硬件连接成功的情况
            '''
            # 设置接口的disconnect方法不抛出异常
            self.mock_awg_interface.disconnect.return_value = None
            # 设置接口的get_status方法返回特定状态
            self.mock_awg_interface.get_status.return_value = {
                'status': 'Disconnected'}

            # 调用disconnect_hardware方法断开'awg'硬件
            self.manager.disconnect_hardware('awg')

            # 断言接口的disconnect方法被调用一次
            self.mock_awg_interface.disconnect.assert_called_once()
            # 断言日志记录了断开连接的信息
            self.mock_logger.debug.assert_called_with('Disconnected from awg')
            # 断言_notify_observers方法被调用一次，并传入正确的参数
            mock_notify_observers.assert_called_once_with(
                'awg', {'status': 'Disconnected'})

        @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
               'hardware_interface_manager.'
               'HardwareInterfaceManager._notify_observers')
        def test_disconnect_hardware_failure(self, mock_notify_observers):
            '''
            测试断开硬件连接失败的情况
            '''
            # 设置接口的disconnect方法抛出异常
            self.mock_awg_interface.disconnect.side_effect = Exception(
                'Disconnection Error')

            # 调用disconnect_hardware方法断开'awg'硬件
            self.manager.disconnect_hardware('awg')

            # 断言接口的disconnect方法被调用一次
            self.mock_awg_interface.disconnect.assert_called_once()
            # 断言日志记录了错误信息
            self.mock_logger.error.assert_called_with(
                'Failed to disconnect from awg: Disconnection Error')
            # 断言_notify_observers方法没有被调用
            mock_notify_observers.assert_not_called()

        def test_get_hardware_status_success(self):
            '''
            测试获取硬件状态成功的情况
            '''
            # 设置接口的get_status方法返回特定状态
            self.mock_awg_interface.get_status.return_value = {
                'status': 'Connected'}

            # 调用get_hardware_status方法获取'awg'硬件的状态
            status = self.manager.get_hardware_status('awg')

            # 断言接口的get_status方法被调用一次
            self.mock_awg_interface.get_status.assert_called_once()
            # 断言返回的状态与预期一致
            self.assertEqual(status, {'status': 'Connected'})

        def test_get_hardware_status_failure(self):
            '''
            测试获取硬件状态失败的情况
            '''
            # 设置接口的get_status方法抛出异常
            self.mock_awg_interface.get_status.side_effect = Exception(
                'Status Error')

            # 调用get_hardware_status方法获取'awg'硬件的状态
            status = self.manager.get_hardware_status('awg')

            # 断言接口的get_status方法被调用一次
            self.mock_awg_interface.get_status.assert_called_once()
            # 断言返回的状态为空字典
            self.assertEqual(status, {})
            # 断言日志记录了错误信息
            self.mock_logger.error.assert_called_with(
                'Failed to get status for awg: Status Error')

        def test_execute_operation_success(self):
            '''
            测试在硬件上成功执行操作的情况
            '''
            # 创建QuantumOperation的模拟对象
            mock_operation = MagicMock()
            # 设置execute方法返回特定结果
            mock_operation.execute.return_value = 'Operation Result'

            # 调用execute_operation方法在'awg'硬件上执行操作
            result = self.manager.execute_operation('awg', mock_operation)

            # 断言操作的execute方法被调用一次，并传入接口实例
            mock_operation.execute.assert_called_once_with(
                self.mock_awg_interface)
            # 断言返回的结果与预期一致
            self.assertEqual(result, 'Operation Result')

        def test_execute_operation_hardware_not_found(self):
            '''
            测试在硬件未找到时执行操作的情况
            '''
            # 创建QuantumOperation的模拟对象
            mock_operation = MagicMock()

            # 调用execute_operation方法在不存在的硬件上执行操作，并断言抛出ValueError
            with self.assertRaises(ValueError):
                self.manager.execute_operation(
                    'nonexistent_hw', mock_operation)

            # 断言操作的execute方法未被调用
            mock_operation.execute.assert_not_called()
            # 断言日志记录了硬件未找到的错误信息
            self.mock_logger.error.assert_called_with(
                'Hardware not found: nonexistent_hw')

        def test_execute_operation_failure(self):
            '''
            测试在执行操作时操作失败的情况
            '''
            # 创建QuantumOperation的模拟对象
            mock_operation = MagicMock()
            # 设置execute方法抛出异常
            mock_operation.execute.side_effect = Exception('Execution Error')

            # 调用execute_operation方法在'awg'硬件上执行操作，并断言抛出异常
            with self.assertRaises(Exception):
                self.manager.execute_operation('awg', mock_operation)

            # 断言操作的execute方法被调用一次
            mock_operation.execute.assert_called_once_with(
                self.mock_awg_interface)
            # 断言日志记录了执行操作的错误信息
            self.mock_logger.error.assert_called_with(
                'Failed to execute operation on awg: Execution Error')

        def test_calibrate_hardware_success(self):
            '''
            测试校准硬件成功的情况
            '''
            # 设置接口的calibrate方法不抛出异常
            self.mock_awg_interface.calibrate.return_value = None

            # 调用calibrate_hardware方法校准'awg'硬件
            self.manager.calibrate_hardware('awg')

            # 断言接口的calibrate方法被调用一次
            self.mock_awg_interface.calibrate.assert_called_once()

            # 断言日志记录了校准成功的信息
            self.mock_logger.debug.assert_called_with('Calibrated awg')

        def test_calibrate_hardware_failure(self):
            '''
            测试校准硬件失败的情况
            '''
            # 设置接口的calibrate方法抛出异常
            self.mock_awg_interface.calibrate.side_effect = Exception(
                'Calibration Error')

            # 调用calibrate_hardware方法校准'awg'硬件
            self.manager.calibrate_hardware('awg')

            # 断言接口的calibrate方法被调用一次
            self.mock_awg_interface.calibrate.assert_called_once()
            # 断言日志记录了校准失败的错误信息
            self.mock_logger.error.assert_called_with(
                'Failed to calibrate awg: Calibration Error')

        def test_add_observer(self):
            '''
            测试添加观察者的方法
            '''
            # 创建HardwareObserver的模拟对象
            mock_observer = MagicMock(spec=HardwareObserver)
            # 调用add_observer方法添加观察者
            self.manager.add_observer(mock_observer)
            # 断言观察者被添加到观察者列表中
            self.assertIn(mock_observer, self.manager.observers)

        def test_remove_observer(self):
            '''
            测试移除观察者的方法
            '''
            # 创建HardwareObserver的模拟对象
            mock_observer = MagicMock(spec=HardwareObserver)
            # 添加观察者到观察者列表中
            self.manager.add_observer(mock_observer)
            # 确认观察者在列表中
            self.assertIn(mock_observer, self.manager.observers)
            # 调用remove_observer方法移除观察者
            self.manager.remove_observer(mock_observer)
            # 断言观察者被移除
            self.assertNotIn(mock_observer, self.manager.observers)

        def test_notify_observers(self):
            '''
            测试通知所有观察者的方法
            '''
            # 创建两个HardwareObserver的模拟对象
            mock_observer1 = MagicMock(spec=HardwareObserver)
            mock_observer2 = MagicMock(spec=HardwareObserver)

            # 添加观察者到观察者列表中
            self.manager.add_observer(mock_observer1)
            self.manager.add_observer(mock_observer2)

            # 设置接口的get_status方法返回特定状态
            self.mock_awg_interface.get_status.return_value = {
                'status': 'Connected'}

            # 调用connect_hardware方法连接'awg'硬件
            self.manager.connect_hardware('awg')

            # 断言_notify_observers方法被调用两次，分别传入不同的观察者
            mock_observer1.update.assert_called_once_with(
                'awg', {'status': 'Connected'})
            mock_observer2.update.assert_called_once_with(
                'awg', {'status': 'Connected'})

    if __name__ == '__main__':
        unittest.main()
