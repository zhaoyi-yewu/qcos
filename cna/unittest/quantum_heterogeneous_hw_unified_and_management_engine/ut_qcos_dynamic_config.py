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
import threading
from qcos.log.qcos_log import QCOSLogger
from qcos.config.qcos_config_manager import qcos_configer
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    qcos_dynamic_config import \
    DynamicConfig, on_config_change


class TestDynamicConfig(unittest.TestCase):
    '''
    测试 DynamicConfig 类的单元测试类
    '''

    def setUp(self):
        '''
        初始化测试环境
        '''
        # 创建日志记录器的模拟对象
        self.mock_logger = MagicMock(spec=QCOSLogger)
        # 创建配置管理器的模拟对象
        self.mock_configer = MagicMock()
        # 设置真实的配置文件路径
        self.mock_configer\
            .get_config_file_absolute_path.return_value \
            = '/qcos/config/qcos_config.conf'
        # 创建回调函数的模拟对象
        self.mock_callback = MagicMock()

        # 使用 patch 替换 qcos_logger 和 qcos_configer
        patcher_logger = patch(
            'qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
            'qcos_dynamic_config.qcos_logger',
            self.mock_logger)
        patcher_configer = patch(
            'qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
            'qcos_dynamic_config.qcos_configer',
            self.mock_configer)

        # 启动 patch 替换
        self.mock_logger_patcher = patcher_logger.start()
        self.mock_configer_patcher = patcher_configer.start()

        # 添加清理方法，确保测试结束后停止 patch
        self.addCleanup(patcher_logger.stop)
        self.addCleanup(patcher_configer.stop)

    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'qcos_dynamic_config.configparser.ConfigParser')
    def test_load_config(self, mock_config_parser):
        '''
        测试加载配置文件的方法
        '''
        # 实例化被测试的类
        dynamic_config = DynamicConfig(callback=self.mock_callback)
        # 调用 load_config 方法
        config = dynamic_config.load_config()

        # 断言 configparser.ConfigParser 被正确调用
        mock_config_parser.assert_called_once()
        # 断言 read 方法被调用，并使用了正确的文件路径和编码
        mock_config_parser.return_value.read.assert_called_with(
            '/qcos/config/qcos_config.conf', encoding='utf-8')

    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'qcos_dynamic_config.configparser.ConfigParser')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'qcos_dynamic_config.os.path.getmtime')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'qcos_dynamic_config.threading.Event')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'qcos_dynamic_config.threading.Thread')
    def test_watch_config_changes(
            self,
            mock_thread_class,
            mock_event,
            mock_getmtime,
            mock_config_parser):
        '''
        测试监视配置文件变化的方法
        '''
        # 设置初始的修改时间和更新后的修改时间
        # 第一次获取mtime为100，第二次为200，模拟文件被修改
        mock_getmtime.side_effect = [100, 200]

        # 设置 Event 实例的 is_set 方法
        is_set_side_effect = iter([False, True])  # 第一次调用返回 False，第二次调用返回 True
        mock_event_instance = mock_event.return_value
        mock_event_instance.is_set.side_effect = lambda: next(
            is_set_side_effect, True)

        # 设置 configparser.ConfigParser 的模拟行为
        mock_config_parser_instance = mock_config_parser.return_value
        mock_config_parser_instance.read.return_value = None

        # 定义当 Thread.start() 被调用时执行目标函数
        def start_thread():
            target = mock_thread_class.call_args[1]['target']
            target()

        # 创建一个 Mock Thread 对象
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread
        mock_thread.start.side_effect = start_thread

        # 使用 patch 替换 time.sleep，以避免实际的等待
        with patch('qcos.'
                   'quantum_heterogeneous_hw_unified_and_management_engine.'
                   'qcos_dynamic_config.time.sleep', return_value=None):
            # 实例化被测试的类
            dynamic_config = DynamicConfig(callback=self.mock_callback)
            # 调用 join 方法，确保线程已经执行完毕
            dynamic_config.watch_thread.join()

        # 断言 os.path.getmtime 被调用两次
        self.assertEqual(mock_getmtime.call_count, 2)
        mock_getmtime.assert_any_call('/qcos/config/qcos_config.conf')

        # 断言配置文件被重新加载
        mock_config_parser_instance.read.assert_called_with(
            '/qcos/config/qcos_config.conf', encoding='utf-8')

        # 断言回调函数被调用一次
        self.mock_callback.assert_called_once()

        # 断言日志记录器的 debug 方法被调用
        self.mock_logger.debug.assert_called_with('配置文件已更新，配置已重新加载！')

    def test_stop_watch(self):
        '''
        测试停止配置文件监控线程的方法
        '''
        # 实例化被测试的类
        dynamic_config = DynamicConfig(callback=self.mock_callback)

        # 使用 mock 替换 stop_event 和 watch_thread
        dynamic_config.stop_event = MagicMock()
        dynamic_config.watch_thread = MagicMock()

        # 调用 stop_watch 方法
        dynamic_config.stop_watch()

        # 断言 stop_event.set 被调用一次
        dynamic_config.stop_event.set.assert_called_once()
        # 断言 watch_thread.join 被调用一次
        dynamic_config.watch_thread.join.assert_called_once()

    def test_on_config_change(self):
        '''
        测试配置文件变化时的回调函数
        '''
        # 调用回调函数
        on_config_change()
        # 断言日志记录器的 debug 方法被调用
        self.mock_logger.debug.assert_called_with('配置文件已更新，配置已重新加载！')


if __name__ == '__main__':
    unittest.main()
