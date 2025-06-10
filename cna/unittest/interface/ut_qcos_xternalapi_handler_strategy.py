#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Bowen Zhang at 2024-10
# ------------------------


import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
from qcos.interface.qcos_xternalapi_handler_strategy import (
    OpenqasmStrategy, XternalFetchOpenqasmStrategy, XternalSaveOpenqasmStrategy)
from qcos.log.qcos_log import QCOSLogger
from qcos.interface.qcos_openqasm_int import openqasm_manager
from qcos.interface.qcos_task_manager import qcos_task_id_generator
from qcos.interface.qcos_task_manager import qcos_hybird_task_manager


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TestOpenqasmStrategy(unittest.TestCase):
    '''
    测试OpenqasmStrategy策略类及其子类的单元测试类。
    该类是对xternal openqasm任务处理策略的测试，确保能按照预期处理并保存openqasm任务
    '''

    def test_openqasm_strategy(self):
        '''
        测试基类OpenqasmStrategy策略的执行
        '''

        strategy = OpenqasmStrategy()

        with self.assertRaises(NotImplementedError) as context:
            strategy.execute()

        # 检查异常消息是否正确
        self.assertEqual(
            str(context.exception),
            'Each strategy must implement an execute method')

    def test_xternal_fetch_openqasm_strategy(self):
        '''
        测试xternal openqasm任务处理策略的执行情况
        '''

        # 构建openqasm文件的绝对路径
        original_openqasm_path = openqasm_manager.original_openqasm_path
        original_openqasm_file = original_openqasm_path + '/test.qasm'

        # 编辑测试所有openqasm文件并保存到original_openqasm路径下
        openqasm_sequence = ''
        with open(original_openqasm_file, 'w') as file:
            file.write(f'qcos_shots_num=100\n')
            file.write(f'qcos_qubits_num=3\n')
            file.write(f'test_openqasm_code')
            file.write(openqasm_sequence)

        # 模拟add_task
        mock_add_task = MagicMock()

        strategy = XternalFetchOpenqasmStrategy()
        with patch(
                'qcos.interface.qcos_task_manager.TaskManager.add_task',
                mock_add_task):
            result = strategy.execute()

        # 验证任务是否被添加
        mock_add_task.assert_any_call(
            'test.qasm',
            100,
            3,
            'test_openqasm_code',
            1,
            'PriorityTask'
        )

        # 验证文件是否成功移动
        processing_openqasm_file = (openqasm_manager.processing_openqasm_path
                                    + '/test.qasm')
        self.assertTrue(os.path.exists(processing_openqasm_file))

        # 模拟返回
        tasks = [
            {
                'id': 'test.qasm',
                'openqasm': 'test_openqasm_code'
            }
        ]
        # 验证返回的任务列表
        self.assertEqual(result, tasks)

    def test_xternal_save_openqasm_strategy(self):
        '''
        测试xternal openqasm任务保存策略的执行情况
        '''

        # 测试openqasm结构体
        task_id = qcos_task_id_generator.generate_qcos_task_id('test.qasm')
        test_openqasm_struct = {
            # XternalSaveOpenqasmStrategy中保存openqasm_struct只需要解析task_name
            'id': task_id
        }

        # 编辑测试所用task_info
        qcos_hybird_task_manager.task_info[task_id] = {
            'test_task': 'test_task_info_content'
        }

        # 构建openqasm文件的绝对路径
        processing_openqasm_path = openqasm_manager.processing_openqasm_path
        processing_openqasm_file = processing_openqasm_path + '/test.qasm'
        # 编辑测试所用openqasm文件并保存到original_openqasm路径下
        openqasm_sequence = ''
        with open(processing_openqasm_file, 'w') as file:
            file.write(f'test_openqasm_code')
            file.write(openqasm_sequence)

        strategy = XternalSaveOpenqasmStrategy()

        result = strategy.execute(test_openqasm_struct)
        qcos_logger.debug(f'xternal openqasm任务处理策略：'
                          f'\n\t\t\t\t\t\t\t\t返回路径:{result}')

        # 验证保存文件是否正确创建
        self.assertTrue(os.path.exists(result))

        # 验证task_info中task_id对应的任务信息是否已删除
        self.assertNotIn(task_id, qcos_hybird_task_manager.task_info)

        # 验证processing_openqasm_file是否已删除
        self.assertFalse(os.path.exists(processing_openqasm_file))

        qcos_logger.debug('测试xternal openqasm任务保存策略的执行情况：验证通过！')


if __name__ == '__main__':
    unittest.main()
