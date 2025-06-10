#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Longfei Tian at 2025-01
# ------------------------


import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import logging
from logging import FileHandler
from qcos.log.qcos_log import QCOSLogger, FileRotatingHandler


class TestFileRotatingHandler(unittest.TestCase):
    '''
    FileRotatingHandler 类的单元测试
    '''

    @patch('os.fspath')
    @patch('os.path.abspath')
    @patch('logging.FileHandler')
    def setUp(self, mock_abspath, mock_fspath, mock_file_hander):
        '''
        测试前的设置
        '''
        self.rotating_handler = FileRotatingHandler(
            'test.log', max_bytes=50 * 1024, backup_count=1)
        self.rotating_handler.baseFilename = 'C:/test/qcos_2024-12-30.log'

    @patch('os.listdir')
    @patch('os.remove')
    @patch('os.path.exists')
    @patch('os.rename')
    def test_manage_log_rollover(
            self,
            mock_rename,
            mock_exists,
            mock_remove,
            mock_listdir):
        '''
        测试 manage_log_rollover 方法实现文件轮转功能
        '''
        # 模拟方法中的属性和方法
        self.rotating_handler.stream = Mock
        self.rotating_handler.stream.close = Mock
        mock_listdir.return_value = ['qcos_2024-12-30-1.log']
        self.rotating_handler._builtin_open = Mock

        # 调用 manage_log_rollover 方法
        self.rotating_handler.manage_log_rollover()

        # 验证 manage_log_rollover 方法被成功调用
        mock_rename.assert_called_once_with(
            'C:/test/qcos_2024-12-30.log',
            'C:/test/qcos_2024-12-30-1.log')
        mock_exists.assert_called()
        mock_remove.assert_called()
        mock_listdir.assert_called_once_with('C:/test')
        self.rotating_handler.rotate(
            'C:/test/qcos_2024-12-30.log',
            'C:/test/qcos_2024-12-30-1.log')

    @patch('os.path.basename')
    @patch('os.path.dirname')
    def test_rename_base_filename(self, mock_dirname, mock_basename):
        '''
        测试 _rename_base_filename 方法修改日志文件名，加上备份序号
        '''
        mock_dirname.return_value = 'C:/test'
        mock_basename.return_value = 'qcos_2024-12-30.log'
        backup_index = 5

        # 调用 _rename_base_filename 方法
        result = self.rotating_handler._rename_base_filename(backup_index)

        # 验证 _rename_base_filename 方法被成功调用
        mock_dirname.assert_called_once_with('C:/test/qcos_2024-12-30.log')
        mock_basename.assert_called_once_with('C:/test/qcos_2024-12-30.log')
        self.assertEqual(result, 'C:/test/qcos_2024-12-30-5.log')

    @patch('os.stat')
    def test_should_rollover(self, mock_stat):
        '''
        测试 should_rollover 方法对日志文件是否需要轮转进行判断
        '''
        self.rotating_handler.formatter = Mock(spec=logging.Formatter)
        mock_stat.return_value = [0] * 7
        record = 'info msg'
        self.rotating_handler.max_bytes = len(f'{format(record)}\n')

        # 调用 should_rollover 方法
        result = self.rotating_handler.should_rollover(record)

        # 验证 should_rollover 方法被成功调用
        mock_stat.assert_called_once_with('C:/test/qcos_2024-12-30.log')
        self.assertTrue(result)

    @patch('logging.FileHandler')
    def test_emit(self, mock_handler):
        '''
        测试 emit 方法发送记录信息到文件
        '''
        record = Mock(spec=logging.LogRecord)
        self.rotating_handler.should_rollover = Mock(return_value=True)
        self.rotating_handler.manage_log_rollover = Mock
        mock_handler.emit = Mock(return_value=record)

        # 调用 emit 方法
        self.rotating_handler.emit(record)

        # 验证 emit 方法被成功调用
        self.rotating_handler.should_rollover.assert_called_once_with(record)
        mock_handler.emit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
