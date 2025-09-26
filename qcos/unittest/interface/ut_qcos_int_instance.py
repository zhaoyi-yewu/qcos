#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-06
# ------------------------


import unittest
from unittest.mock import Mock, patch, MagicMock
from qcos.config.qcos_config_manager import qcos_configer
from qcos.interface.qcos_int_instance import \
    QCOSInstance, OpenqasmInstance, IsingInstance  # 确保你的类的路径正确
from qcos.log.qcos_log import QCOSLogger
from qcos.interface.qcos_openqasm_int import openqasm_manager


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TestQCOSInstance(unittest.TestCase):
    '''
    测试 QCOSInstance 类及其方法。
    '''

    def setUp(self):
        '''
        在每个测试用例执行前进行初始化，设置测试环境。
        '''

        # 设置基础URL
        self.base_url = qcos_configer.get_dqcos_url()

        # 设置设备ID
        self.device_id = 'device123'

        # 创建一个模拟工厂对象
        self.factory = Mock()
        qcos_logger.debug('测试环境设置完成')

    def test_init(self):
        '''
        测试 __init__ 方法，确保能正确初始化实例变量。
        '''
        # 创建QCOSInstance实例
        instance = QCOSInstance(self.base_url, self.device_id, self.factory)

        # 断言基础URL是否正确设置
        self.assertEqual(instance.base_url, self.base_url)

        # 断言设备ID是否正确设置
        self.assertEqual(instance.device_id, self.device_id)

        # 断言工厂对象是否正确设置
        self.assertEqual(instance.factory, self.factory)
        qcos_logger.debug('初始化测试完成')

    # 确保这里的路径与实际模块路径匹配
    @patch('qcos.interface.qcos_dqcosapi_handler_strategy.QCOSRequestStrategy')
    def test_send_request_dqcos_success(self, mock_strategy):
        '''
        测试 send_request 方法在成功情况下的执行。
        :param mock_strategy: 模拟的请求策略
        '''

        # 设置策略类型
        strategy_type = 'strategy_type'

        # 设置传递给请求的数据
        data = {'key': 'value'}

        # 设置预期的结果
        expected_result = 'success'

        # 获取模拟策略实例
        mock_strategy_instance = mock_strategy.return_value

        # 设置模拟策略执行的返回值
        mock_strategy_instance.execute.return_value = expected_result

        # 创建QCOSInstance实例
        instance = QCOSInstance(self.base_url, self.device_id, self.factory)
        instance.base_url = qcos_configer.get_dqcos_url()

        # 设置工厂返回模拟策略实例
        self.factory.get_strategy.return_value = mock_strategy_instance

        # 调用send_request方法并获取结果
        result = instance.send_request(strategy_type, data)

        # 断言结果是否与预期相符
        self.assertEqual(result, expected_result)

        # 断言工厂是否被正确调用
        self.factory.get_strategy.assert_called_once_with(strategy_type)

        # 断言模拟策略实例是否被正确执行
        mock_strategy_instance.execute.assert_called_once_with(
            f'{self.base_url}/workload-broker/{self.device_id}', data
        )

        qcos_logger.debug(f'请求发送成功测试完成。结果: {result}')

    @patch('qcos.interface.qcos_int_instance.qcos_logger')  # 确保日志对象的路径正确
    def test_send_request_dqcos_exception(self, mock_logger):
        '''
        测试 send_request 方法在发生异常时的执行。
        :param mock_logger: 模拟的日志对象
        '''

        # 设置策略类型
        strategy_type = 'strategy_type'

        # 设置传递给请求的数据
        data = {'key': 'value'}

        # 设置异常信息
        exception_message = 'Exception occurred'

        # 设置工厂在获取策略时抛出异常
        self.factory.get_strategy.side_effect = Exception(exception_message)

        # 创建QCOSInstance实例
        instance = QCOSInstance(self.base_url, self.device_id, self.factory)

        # 调用send_request方法并获取结果
        result = instance.send_request(strategy_type, data)

        # 断言结果是否为None
        self.assertIsNone(result)

        # 断言日志对象是否记录了错误信息
        mock_logger.error.assert_called_once_with(
            f'发送服务请求失败: {exception_message}'
        )

        qcos_logger.debug(f'请求发送异常测试完成。日志记录: {mock_logger.error.call_args}')


class TestOpenqasmInstance(unittest.TestCase):
    '''
    测试 OpenqasmInstance 类及其方法。
    '''

    def setUp(self):
        '''
        在每个测试用例执行前进行初始化，设置测试环境。
        '''

        # 设置基础path
        self.base_path = openqasm_manager.original_openqasm_path

        # 创建一个模拟工厂对象
        self.factory = Mock()
        qcos_logger.debug('测试环境设置完成')

    def test_init(self):
        '''
        测试 __init__ 方法，确保能正确初始化实例变量。
        '''
        # 创建OpenqasmInstance实例
        instance = OpenqasmInstance(self.base_path, self.factory)

        # 断言基础path是否正确设置
        self.assertEqual(instance.base_path, self.base_path)

        # 断言工厂对象是否正确设置
        self.assertEqual(instance.factory, self.factory)
        qcos_logger.debug('初始化测试完成')

    # 确保这里的路径与实际模块路径匹配
    @patch('qcos.interface.qcos_xternalapi_handler_strategy.OpenqasmStrategy')
    def test_send_request_xternal_success(self, mock_strategy):
        '''
        测试 send_request 方法在成功情况下的执行。
        :param mock_strategy: 模拟的策略
        '''

        # 设置策略类型
        strategy_type = 'strategy_type'

        # 设置传递给请求的数据
        openqasm_struct = {'key': 'value'}

        # 设置预期的结果
        expected_result = 'success'

        # 获取模拟策略实例
        mock_strategy_instance = mock_strategy.return_value

        # 设置模拟策略执行的返回值
        mock_strategy_instance.execute.return_value = expected_result

        # 创建OpenqasmInstance实例
        instance = OpenqasmInstance(self.base_path, self.factory)

        # 设置工厂返回模拟策略实例
        self.factory.get_strategy.return_value = mock_strategy_instance

        # 调用send_request方法并获取结果
        result = instance.send_request(strategy_type, openqasm_struct)

        # 断言结果是否与预期相符
        self.assertEqual(result, expected_result)

        # 断言工厂是否被正确调用
        self.factory.get_strategy.assert_called_once_with(strategy_type)

        # 断言模拟策略实例是否被正确执行
        mock_strategy_instance.execute.assert_called_once_with(openqasm_struct)

        qcos_logger.debug(f'请求发送成功测试完成。结果: {result}')

    @patch('qcos.interface.qcos_int_instance.qcos_logger')  # 确保日志对象的路径正确
    def test_send_request_xternal_exception(self, mock_logger):
        '''
        测试 send_request 方法在发生异常时的执行。
        :param mock_logger: 模拟的日志对象
        '''

        # 设置策略类型
        strategy_type = 'strategy_type'

        # 设置传递给请求的数据
        openqasm_struct = {'key': 'value'}

        # 设置异常信息
        exception_message = 'Exception occurred'

        # 设置工厂在获取策略时抛出异常
        self.factory.get_strategy.side_effect = Exception(exception_message)

        # 创建OpenqasmInstance实例
        instance = OpenqasmInstance(self.base_path, self.factory)

        # 调用send_request方法并获取结果
        result = instance.send_request(strategy_type, openqasm_struct)

        # 断言结果是否为None
        self.assertIsNone(result)

        # 断言日志对象是否记录了错误信息
        mock_logger.error.assert_called_once_with(
            f'发送xternal请求失败: {exception_message}'
        )

        qcos_logger.debug(
            f'send_request异常测试完成。日志记录: {
                mock_logger.error.call_args}')


class TestIsingInstance(unittest.TestCase):
    '''
    测试 IsingInstance 类及其方法。
    '''

    def setUp(self):
        '''
        在每个测试用例执行前进行初始化，设置测试环境。
        '''

        # 设置基础URL
        self.base_url = 'http://127.0.0.1:8088'
        # 创建一个模拟工厂对象
        self.factory = Mock()

        qcos_logger.debug('测试环境设置完成')

    def test_init(self):
        '''
        测试 __init__ 方法，确保能正确初始化实例变量。
        '''

        # 创建IsingInstance实例
        instance = IsingInstance(self.base_url, self.factory)

        # 断言基础URL是否正确设置
        self.assertEqual(instance.base_url, self.base_url)
        # 断言工厂对象是否正确设置
        self.assertEqual(instance.factory, self.factory)
        qcos_logger.debug('初始化测试完成')

    @patch('qcos.interface.qcos_isingapi_handler_strategy.IsingRequestStrategy')
    def test_send_request_ising_success(self, mock_strategy):
        '''
        测试 send_request 方法在成功情况下的执行。
        :param mock_strategy: 模拟的策略
        '''

        # 设置策略类型
        strategy_type = 'strategy_type'
        ising_task_type = 'ising_task_type'
        # 设置传递给请求的数据
        data = {'key': 'value'}
        # 设置预期的结果
        expected_result = 'success'

        # 获取模拟策略实例
        mock_strategy_instance = mock_strategy.return_value
        # 设置模拟策略执行的返回值
        mock_strategy_instance.execute.return_value = expected_result
        # 创建IsingInstance实例
        instance = IsingInstance(self.base_url, self.factory)
        # 设置工厂返回模拟策略实例
        self.factory.get_strategy.return_value = mock_strategy_instance

        # 调用send_request方法并获取结果
        result = instance.send_request(strategy_type, ising_task_type, data)

        # 断言结果是否与预期相符
        self.assertEqual(result, expected_result)
        # 断言工厂是否被正确调用
        self.factory.get_strategy.assert_called_once_with(strategy_type)
        # 断言模拟策略实例是否被正确执行
        mock_strategy_instance.execute.assert_called_once_with(
            ising_task_type, self.base_url, data)

        qcos_logger.debug(f'请求发送成功测试完成。结果: {result}')

    @patch('qcos.interface.qcos_int_instance.qcos_logger')
    def test_send_request_ising_exception(self, mock_logger):
        '''
        测试 send_request 方法在发生异常时的执行。
        :param mock_logger: 模拟的日志对象
        '''

        # 设置策略类型
        strategy_type = 'strategy_type'
        # 设置请求类型
        ising_task_type = 'ising_task_type'
        # 设置传递给请求的数据
        data = {'key': 'value'}

        # 设置异常信息
        exception_message = 'Exception occurred'

        # 设置工厂在获取策略时抛出异常
        self.factory.get_strategy.side_effect = Exception(exception_message)

        # 调用send_request方法并获取结果
        instance = IsingInstance(self.base_url, self.factory)
        result = instance.send_request(strategy_type, ising_task_type, data)

        # 断言结果是否为None
        self.assertIsNone(result)

        # 断言日志对象是否记录了错误信息
        mock_logger.error.assert_called_once_with(
            f'发送服务请求失败: {exception_message}'
        )

        qcos_logger.debug(f'请求发送异常测试完成。日志记录: {mock_logger.error.call_args}')


if __name__ == '__main__':
    unittest.main()
