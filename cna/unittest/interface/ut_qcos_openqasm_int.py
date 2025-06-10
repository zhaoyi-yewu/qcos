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
from unittest.mock import patch, mock_open
import os
import queue
from qcos.interface.qcos_openqasm_int import OpenQASMManager
from qcos.log.qcos_log import QCOSLogger


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TestOpenQASMManager(unittest.TestCase):
    '''
    测试OpenQASMManager类
    '''

    def setUp(self):
        '''
        测试初始化：创建OpenQASMManager实例
        '''

        # 创建一个OpenQASMManager实例
        self.manager = OpenQASMManager()
        qcos_logger.debug('测试初始化：创建OpenQASMManager实例')

    def test_get_openqasm_tasks_empty_queue(self):
        '''
        测试当队列为空时get_openqasm_tasks函数是否返回None

        返回:
            None
        '''

        # 测试当队列为空时get_openqasm_tasks函数是否返回None
        result = self.manager.get_openqasm_tasks()
        qcos_logger.debug(f'测试get_openqasm_tasks（空队列）：返回值 = {result}')

        self.assertIsNone(result)
        qcos_logger.debug('测试get_openqasm_tasks（空队列）：验证通过')

    def test_get_openqasm_tasks_non_empty_queue(self):
        '''
        测试当队列非空时get_openqasm_tasks函数是否返回正确的任务结构体

        返回:
            None
        '''

        # 设置一个任务结构体放入队列
        test_struct = {
            'openqasm_sequence': 'test',
            'qcos_qubits_num': 1,
            'qcos_shots_num': 10}
        self.manager.task_queue.put(test_struct)
        qcos_logger.debug(
            f'测试get_openqasm_tasks（非空队列）：放入任务结构体 = {test_struct}')

        # 测试当队列非空时get_openqasm_tasks函数是否返回正确的任务结构体
        result = self.manager.get_openqasm_tasks()
        qcos_logger.debug(f'测试get_openqasm_tasks（非空队列）：返回值 = {result}')

        self.assertEqual(result, test_struct)
        qcos_logger.debug('测试get_openqasm_tasks（非空队列）：验证通过')

    @patch('os.listdir', return_value=['test.qasm'])
    @patch('builtins.open', new_callable=mock_open,
           read_data='qcos_qubits_nums=2\nqcos_shots_num=100\nqasm_code')
    def test_load_openqasm_file(self, mock_file, mock_listdir):
        '''
        模拟os.listdir和open函数，测试load_openqasm_file函数

        参数:
            mock_file: 模拟的文件对象
            mock_listdir: 模拟的列表对象
        返回:
            None
        '''

        expected_struct = {
            'openqasm_sequence': 'qasm_code',
            'qcos_qubits_num': 2,
            'qcos_shots_num': 100,
            'qcos_task_name': 'test.qasm',
            'qcos_task_priority': self.manager.task_priority_config,
            'qcos_task_type': self.manager.task_type_config
        }

        self.manager.load_openqasm_file()

        # 测试读取结果是否与预期一致
        self.assertEqual(self.manager.task_queue.qsize(), 1)

        # 测试队列中的任务结构体是否正确
        queue_result = self.manager.task_queue.get()
        qcos_logger.debug(f'测试load_openqasm_file：队列中的任务结构体 = {queue_result}')

        self.assertEqual(queue_result, expected_struct)
        qcos_logger.debug('测试load_openqasm_file：队列任务结构体验证通过')

    @patch('os.listdir')
    @patch('qcos.log.qcos_log.QCOSLogger.debug')
    def test_load_openqasm_file_none(self, mock_debug, mock_listdir):
        '''
        测试load_openqasm_file函数没有openqasm文件的情况

        返回:
            None
        '''

        # 设置mock_listdir返回一个空列表，模拟目录中没有文件的情况
        mock_listdir.return_value = []
        # 设置路径属性
        self.manager.original_openqasm_path = '/path/to/openqasm'

        # 调用方法
        self.manager.load_openqasm_file()

        # 验证original_openqasm_path路径是否被遍历
        mock_listdir.assert_called_once_with(
            self.manager.original_openqasm_path)
        # 验证日志是否被记录
        mock_debug.assert_called_once_with('当前暂无更多任务被添加')


if __name__ == '__main__':
    unittest.main()
