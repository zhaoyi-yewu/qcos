#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-09
# ------------------------


import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, mock_open
from qcos.config.qcos_config_manager import qcos_configer
from qcos.interface.qcos_api_manager import (
    IsingTaskStatus, QCOSTaskHandler, DQCOSTaskHandler, XTERNALTaskHandler,
    QCOSTaskHandlerFactory, QCOSTaskManager, ISINGTaskHandler
)
from qcos.interface.qcos_int_instance import qcos_dqcosapi_handler
from qcos.memory.qcos_mem_task_scheduler import TaskStatus
from qcos.log.qcos_log import QCOSLogger

# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TestIsingTaskStatus(unittest.TestCase):
    '''
    测试 IsingTaskStatus 抽象基类
    '''

    def test_enum_values(self):
        # 测试枚举值是否正确
        self.assertEqual(IsingTaskStatus.QUEUING.value, 0)
        self.assertEqual(IsingTaskStatus.COMPUTING.value, 1)
        self.assertEqual(IsingTaskStatus.COMPLETED.value, 5)
        self.assertEqual(IsingTaskStatus.FAILED.value, 6)


class TestQCOSTaskHandler(unittest.TestCase):
    '''
    测试 QCOSTaskHandler 抽象基类
    '''

    def test_abstract_methods(self):
        '''
        测试 QCOSTaskHandler 的抽象方法
        '''
        # 验证无法直接实例化抽象类
        with self.assertRaises(TypeError):
            QCOSTaskHandler()


class TestDQCOSTaskHandler(unittest.IsolatedAsyncioTestCase):
    '''
    测试 DQCOSTaskHandler 类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''
        # 创建一个模拟的 QCOS 实例
        self.mock_qcos_instance = Mock()
        # 确保 send_request 被模拟为异步方法
        self.mock_qcos_instance.send_request = AsyncMock()
        # 创建 DQCOSTaskHandler 实例
        self.handler = DQCOSTaskHandler(self.mock_qcos_instance)

    @patch('qcos.interface.qcos_int_instance.IsingInstance.send_request')
    async def test_fetch_tasks(self, mock_send_request):
        '''
        测试 fetch_tasks 方法
        '''
        # 模拟返回的任务列表
        mock_tasks = ['task1', 'task2']
        # 设置模拟的 send_request 方法返回值
        self.mock_qcos_instance.send_request.side_effect = [mock_tasks, []]
        fetch_tasks_data = {
            'workload':
                {
                    'limit': qcos_configer.get_fetch_task_num(),
                    'strategyName': 'fetch_workload'
                }
        }

        # case1: 调用 fetch_tasks 方法获得任务
        tasks = await self.handler.fetch_tasks()
        # 验证结果
        self.assertEqual(tasks, mock_tasks)
        # 验证 send_request 方法被正确调用
        self.mock_qcos_instance.send_request.assert_called_once_with(
            'dqcos_fetch_workload', fetch_tasks_data)

        # case2: 调用 fetch_tasks 方法未获得任务
        tasks = await self.handler.fetch_tasks()
        # 验证结果
        self.assertEqual(tasks, [])
        # 验证 send_request 方法被正确调用
        self.mock_qcos_instance.send_request.assert_called_with(
            'dqcos_fetch_workload', fetch_tasks_data)

    async def test_confirm_workload(self):
        '''
        测试 confirm_workload 方法
        '''
        # 模拟的返回结果
        confirm_workload_data = {
            'workload':
                {
                    'confirmations': ['task1']
                }
        }

        # 调用 confirm_workload 方法
        await self.handler.confirm_workload(['task1'])

        # 验证 send_request 方法被调用
        self.mock_qcos_instance.send_request.assert_called_once_with(
            'dqcos_confirm_workload', confirm_workload_data)

    async def test_fetch_cancellation(self):
        '''
        测试 fetch_cancellation 方法
        '''
        # 模拟的返回结果
        fetch_cancellation_data = {
            'cancellation': {
                'selection': {
                    'limit': 5,
                    'strategyName': 'string'
                }
            }
        }
        # 调用 fetch_cancellation 方法
        await self.handler.fetch_cancellation()

        # 验证 send_request 方法被调用
        self.mock_qcos_instance.send_request.assert_called_once_with(
            'dqcos_fetch_cancellation', fetch_cancellation_data)

    @patch('qcos.memory.qcos_mem_task_scheduler.QuantumTaskScheduler.'
           'cancel_task')
    @patch('qcos.memory.qcos_mem_task_scheduler.QuantumTaskScheduler.'
           'get_task_status')
    async def test_receive_cancellation_result(
            self, mock_get_task_status, mock_cancel_task):
        '''
        测试 receive_cancellation_result 方法
        '''
        # 模拟的返回结果
        receive_cancellation_result_data = {
            'cancellation': {
                'results': [
                    {
                        'id': 'task1',
                        'isCancelled': True
                    },
                    {
                        'id': 'task2',
                        'isCancelled': False
                    }
                ]
            }
        }
        # 模拟查询任务状态的返回
        mock_get_task_status.side_effect = [
            TaskStatus.PENDING, TaskStatus.COMPLETED]
        mock_cancel_task.return_value = True

        # 调用 receive_cancellation_result 方法
        await self.handler.receive_cancellation_result(['task1', 'task2'])

        # 验证 send_request 方法被调用
        self.mock_qcos_instance.send_request.assert_called_once_with(
            'dqcos_receive_cancellation_result',
            receive_cancellation_result_data)

    @patch('qcos.memory.qcos_mem_task_scheduler.QuantumTaskScheduler.'
           'get_task_result')
    @patch('qcos.memory.qcos_mem_task_scheduler.QuantumTaskScheduler.'
           'get_task_status')
    async def test_send_results(
            self,
            mock_get_task_status,
            mock_get_task_result):
        ''''
        测试 send_results 方法
        '''
        # 模拟的处理结果
        receive_workload_result_data = {
            'workload':
                {
                    'results': [
                        {
                            'id': 'success_task',
                            'result': 'result1'
                        },
                        {
                            'id': 'failed_task',
                            'message': 'Failed'
                        },
                        {
                            'id': 'cancelled_task',
                            'message': 'Failed'
                        }
                    ]
                }
        }
        # 模拟收到的任务列表
        self.handler.openqasm_task_list = [
            'success_task', 'failed_task', 'cancelled_task']
        # 模拟调用的方法
        from qcos.interface.qcos_task_manager import qcos_task_id_generator
        qcos_task_id_generator.reverse_map = {
            'task1': 'success_task',
            'task2': 'failed_task',
            'task3': 'cancelled_task'}
        mock_get_task_status.side_effect = [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.CANCELLED]
        mock_get_task_result.side_effect = ['result1']

        # 抛出 CancelledError 错误
        self.mock_qcos_instance.send_request.\
            side_effect = asyncio.CancelledError

        # 调用 send_results 方法
        await asyncio.wait_for(self.handler.send_results(), timeout=1.0)

        # 验证 send_results 方法被正确调用
        self.mock_qcos_instance.send_request.assert_called_once_with(
            'dqcos_receive_workload_result',
            receive_workload_result_data)
        mock_get_task_status.assert_called()
        mock_get_task_result.assert_called()


class TestISINGTaskHandler(unittest.IsolatedAsyncioTestCase):
    '''
    测试 ISINGTaskHandler 类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''
        # 创建一个模拟的 IsingInstance 实例
        self.mock_ising_instance = Mock()
        # 确保 send_request 被模拟为异步方法
        self.mock_ising_instance.send_request = AsyncMock()
        # 创建 ISINGTaskHandler 实例
        self.handler = ISINGTaskHandler(self.mock_ising_instance)

    async def test_fetch_tasks(self):
        '''
        测试 fetch_tasks 方法
        '''
        # 模拟返回的任务列表
        mock_tasks = [('task_id', 1, 1,
                       'test_task_name',
                       '2025-2-14 23:59:59',
                       'test', 1, 1, 10,
                       {
                           'type': 'ISING',
                           'matrix': [
                               [-1, 1, 1],
                               [-1, 1, 1]]
                       })]
        # 设置模拟的 send_request 方法返回值
        qcos_dqcosapi_handler.send_request = AsyncMock(return_value=mock_tasks)
        upload_response_data = {
            'data': {
                'creator': 'user_id',
                'id': 'file_id',
                'name': 'file_name'
            }
        }
        submit_response_data = {'data': {}}
        machine_task_response_data = {'data': {'data': [{'id': 'test_id'}]}}
        status_code = 200
        self.mock_ising_instance.send_request = AsyncMock(
            side_effect=[
                (status_code,
                 upload_response_data),
                (status_code,
                 submit_response_data),
                (status_code,
                 machine_task_response_data)])
        fetch_tasks_data = {
            'workload':
                {
                    'limit': qcos_configer.get_fetch_task_num(),
                    'strategyName': 'fetch_ising_workload'
                }
        }

        # 调用 fetch_tasks 方法
        await self.handler.fetch_tasks()

        # 验证结果
        self.assertIn('task_id', self.handler.ising_task_dict.keys())
        qcos_dqcosapi_handler.send_request.assert_called_once_with(
            'dqcos_fetch_ising_workload', fetch_tasks_data)
        self.mock_ising_instance.send_request.assert_called()

    @patch('qcos.log.qcos_log.QCOSLogger.error')
    async def test_fetch_tasks_error(self, mock_logger):
        '''
        测试 fetch_tasks 方法错误场景
        '''
        # 模拟返回的任务列表
        mock_tasks = [
            (
                'task_id1', 1, 1,
                'test_task_name',
                '2025-2-14 23:59:59',
                'test', 1, 1, 10,
                {
                    'type': 'ISING',
                    'matrix': [
                        [-1, 1, 1],
                        [-1, 1, 1]
                    ]
                }
            ),
            (
                'task_id2', 1, 1,
                'test_task_name',
                '2025-2-14 23:59:59',
                'test', 1, 1, 10,
                {
                    'type': 'ISING',
                    'matrix': [
                        [-1, 1, 1],
                        [-1, 1, 1]
                    ]
                }
            ),
            (
                'task_id3', 1, 1,
                'test_task_name',
                '2025-2-14 23:59:59',
                'test', 1, 1, 10,
                {
                    'type': 'ISING',
                    'matrix': [
                        [-1, 1, 1],
                        [-1, 1, 1]
                    ]
                }
            )
        ]
        # 设置模拟的 send_request 方法返回值
        qcos_dqcosapi_handler.send_request = AsyncMock(return_value=mock_tasks)
        upload_response_data = {
            'data': {
                'creator': 'user_id',
                'id': 'file_id',
                'name': 'file_name'
            }
        }
        submit_response_data = {'data': {}}
        machine_task_response_data = {'data': {'data': [{'id': 'test_id'}]}}
        correct_status_code = 200
        error_status_code = 404
        self.mock_ising_instance.send_request = AsyncMock(
            side_effect=[
                (error_status_code,
                 upload_response_data),
                (correct_status_code,
                 upload_response_data),
                (error_status_code,
                 submit_response_data),
                (correct_status_code,
                 upload_response_data),
                (correct_status_code,
                 submit_response_data),
                (error_status_code,
                 machine_task_response_data)])
        fetch_tasks_data = {
            'workload':
                {
                    'limit': qcos_configer.get_fetch_task_num(),
                    'strategyName': 'fetch_ising_workload'
                }
        }

        # 调用 fetch_tasks 方法
        await self.handler.fetch_tasks()

        # 验证结果
        self.assertEqual(len(self.handler.ising_task_dict.items()), 0)
        qcos_dqcosapi_handler.send_request.assert_called_once_with(
            'dqcos_fetch_ising_workload', fetch_tasks_data)
        self.mock_ising_instance.send_request.assert_called()
        mock_logger.assert_called_with(
            'Failed to get machine task id on task task_id3, errcode is 404')

    async def test_receive_cancellation_result(self):
        '''
        测试 receive_cancellation_result 方法
        '''
        # 模拟任务取消结果
        receive_cancellation_result_data = {
            'cancellation': {
                'results': [
                    {
                        'id': 'task_id1',
                        'isCancelled': False
                    },
                    {
                        'id': 'task_id2',
                        'isCancelled': True
                    },
                    {
                        'id': 'task_id3',
                        'isCancelled': False
                    }
                ]
            }
        }
        self.handler.ising_task_dict = {
            'task_id1': 'id1',
            'task_id2': 'id2',
            'task_id3': 'id3'}
        qcos_dqcosapi_handler.send_request = AsyncMock()
        # 模拟 send_request 的返回
        correct_status_code = 200
        error_status_code = 404
        check_response_data = {'data': {'status': 0}}

        self.mock_ising_instance.send_request.side_effect = [
            (error_status_code,
             check_response_data),
            (correct_status_code,
             check_response_data),
            (correct_status_code,
             check_response_data),
            (correct_status_code,
             check_response_data),
            (error_status_code,
             check_response_data)]

        task_id_list = ['task_id1', 'task_id2', 'task_id3']
        # 调用 receive_cancellation_result 方法
        await self.handler.receive_cancellation_result(task_id_list)

        # 验证结果
        qcos_dqcosapi_handler.send_request.assert_called_once_with(
            'dqcos_receive_cancellation_result',
            receive_cancellation_result_data)
        self.mock_ising_instance.send_request.assert_called()

    @patch('qcos.log.qcos_log.QCOSLogger.error')
    async def test_receive_cancellation_result_error(self, mock_logger):
        '''
        测试 receive_cancellation_result 方法错误场景
        '''
        # 模拟任务取消结果
        receive_cancellation_result_data = {
            'cancellation': {
                'results': [
                    {
                        'id': 'task_id1',
                        'isCancelled': False
                    },
                    {
                        'id': 'task_id2',
                        'isCancelled': False
                    }
                ]
            }
        }
        self.handler.ising_task_dict = {'task_id1': 'id1'}
        qcos_dqcosapi_handler.send_request = AsyncMock()
        # 模拟 send_request 的返回
        error_status_code = 404
        check_response_data = {'data': {'status': 0}}

        self.mock_ising_instance.send_request.side_effect = [
            (error_status_code, check_response_data)]

        task_id_list = ['task_id1', 'task_id2']
        # 调用 receive_cancellation_result 方法
        await self.handler.receive_cancellation_result(task_id_list)

        # 验证结果
        qcos_dqcosapi_handler.send_request.assert_called_once_with(
            'dqcos_receive_cancellation_result',
            receive_cancellation_result_data)
        self.mock_ising_instance.send_request.assert_called()
        mock_logger.assert_called_with('Task task_id2 not in ising_task_dict')

    @patch('qcos.log.qcos_log.QCOSLogger.error')
    @patch('os.path.exists')
    @patch('os.remove')
    @patch('zipfile.ZipFile')
    async def test_send_results(
            self,
            mock_zipfile,
            mock_remove,
            mock_exists,
            mock_logger):
        ''''
        测试 send_results 方法
        '''
        # 模拟的处理结果
        receive_workload_result_data = {
            'workload':
                {
                    'results': [
                        {
                            'id': 'ising_task_completed',
                            'result': 'task_result'
                        },
                        {
                            'id': 'ising_task_failed',
                            'message': 'failed'
                        }
                    ]
                }
        }
        # 模拟收到的任务列表
        self.handler.ising_task_dict = {
            'ising_task_completed': 'machine_task_completed',
            'ising_task_failed': 'machine_task_failed'}
        data_completed = {
            'data': {
                'id': 1,
                'task_id': 'test_id',
                'task_name': 'test_name',
                'status': 5,
                'description': 'success'}}
        data_failed = {
            'data': {
                'id': 2,
                'task_id': 'test_id',
                'task_name': 'test_name',
                'status': 6,
                'description': 'failed'}}
        # 模拟 send_request 的返回
        status_code = 200
        self.mock_ising_instance.send_request.side_effect = [
            (status_code,
             data_completed),
            (status_code,
             'mock_file_path'),
            (status_code,
             data_failed),
            (status_code,
             data_failed)]
        # 模拟结果文件解析
        mock_zipfile.return_value.__enter__.return_value.namelist.\
            return_value = ['mock_file_name']
        mock_zipfile.return_value.__enter__.return_value.open.return_value.\
            __enter__.return_value.read.return_value = b'task_result'
        # 模拟 qcos_dqcosapi_handler 的 send_request
        qcos_dqcosapi_handler.send_request = AsyncMock()

        # 调用 send_results 方法
        await asyncio.wait_for(self.handler.send_results(), timeout=1.0)

        # 验证 send_results 方法被正确调用
        qcos_dqcosapi_handler.send_request.assert_called_with(
            'dqcos_receive_workload_result', receive_workload_result_data)
        # 验证日志记录
        mock_logger.assert_called_once_with(
            'Failed to execute task ising_task_failed')

    @patch('qcos.log.qcos_log.QCOSLogger.error')
    async def test_send_results_error(self, mock_logger):
        ''''
        测试 send_results 方法
        '''
        # 模拟收到的任务列表
        self.handler.ising_task_dict = {'ising_task1': 'machine_task1',
                                        'ising_task2': 'machine_task2'}
        data_completed = {
            'data': {
                'id': 1,
                'task_id': 'test_id',
                'task_name': 'test_name',
                'status': 5,
                'description': 'success'}}
        # 模拟 send_request 的返回
        correct_status_code = 200
        error_status_code = 404
        self.mock_ising_instance.send_request.side_effect = [
            (error_status_code,
             data_completed),
            (correct_status_code,
             data_completed),
            (error_status_code,
             'mock_file_path'),
            asyncio.CancelledError]
        # 模拟 qcos_dqcosapi_handler 的 send_request
        qcos_dqcosapi_handler.send_request = AsyncMock()

        # 调用 send_results 方法
        await asyncio.wait_for(self.handler.send_results(), timeout=1.0)

        # 验证 ising_task_dict 未被处理
        self.assertEqual(
            self.handler.ising_task_dict,
            {'ising_task1': 'machine_task1', 'ising_task2': 'machine_task2'})
        # 验证日志记录
        mock_logger.assert_called_with(
            'Failed to obtain task result on task ising_task2, errcode is 404')


class TestXTERNALTaskHandler(unittest.IsolatedAsyncioTestCase):
    '''
    测试 XTERNALTaskHandler 类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''
        # 创建一个模拟的 openqasm 实例
        self.mock_openqasm_instance = Mock()
        # 确保 execute_openqasm 被模拟为异步方法
        self.mock_openqasm_instance.execute_openqasm = AsyncMock()
        # 创建 XTERNALTaskHandler 实例
        self.handler = XTERNALTaskHandler(self.mock_openqasm_instance)

    async def test_fetch_tasks(self):
        '''
        测试 fetch_tasks 方法
        '''
        # 模拟返回的任务列表
        mock_tasks = [
            {
                'id': 'test_id',
                'openqasm': 'test_openqasm'
            },
        ]
        # 设置模拟的 send_request 方法返回值
        self.mock_openqasm_instance.send_request.return_value = mock_tasks

        # 调用 fetch_tasks 方法
        tasks = await self.handler.fetch_tasks()

        # 验证结果
        self.assertEqual(tasks, mock_tasks)
        # 验证 send_request 方法被正确调用
        self.mock_openqasm_instance.send_request.assert_called_once_with(
            'xternal_fetch_openqasm')

    async def test_send_results(self):
        '''
        测试 send_results 方法
        '''
        try:
            await self.handler.send_results()
        except Exception as e:
            self.fail(f'send_results raised {type(e).__name__} unexpectedly!')


class TestQCOSTaskHandlerFactory(unittest.TestCase):
    '''
    测试 QCOSTaskHandlerFactory 类
    '''

    def test_get_task_source_dqcos(self):
        '''
        测试获取 DQCOS 任务源
        '''
        # 创建模拟的 QCOS 实例
        mock_qcos_instance = Mock()
        # 获取 DQCOS 任务源
        task_source = QCOSTaskHandlerFactory.get_task_source(
            'DQCOS', mock_qcos_instance)
        # 验证返回的是 DQCOSTaskHandler 实例
        self.assertIsInstance(task_source, DQCOSTaskHandler)

    def test_get_task_source_xternal(self):
        '''
        测试获取 XTERNAL 任务源
        '''
        # 获取 XTERNAL 任务源
        task_source = QCOSTaskHandlerFactory.get_task_source('XTERNAL')
        # 验证返回的是 XTERNALTaskHandler 实例
        self.assertIsInstance(task_source, XTERNALTaskHandler)

    def test_get_task_source_invalid(self):
        '''
        测试获取无效任务源
        '''
        # 尝试获取无效的任务源类型
        with self.assertRaises(ValueError):
            QCOSTaskHandlerFactory.get_task_source('INVALID')


class TestQCOSTaskManager(unittest.IsolatedAsyncioTestCase):
    '''
    测试 QCOSTaskManager 类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''
        # 创建模拟的配置对象
        self.mock_config = Mock()
        self.mock_config.get_task_sources.return_value = ['DQCOS', 'XTERNAL']
        self.mock_config.get_fetch_interval.return_value = 1
        self.mock_config.get_error_wait_time.return_value = 5

        # 创建 QCOSTaskManager 实例
        self.manager = QCOSTaskManager(self.mock_config)
        # 添加运行标志位
        self.manager.running = True

    async def test_process_task(self):
        '''
        测试 process_task 方法
        '''
        # 创建模拟任务
        mock_task = {'id': 1, 'task': 'test'}
        # 处理任务
        result = await self.manager.process_task(mock_task)
        # 验证结果
        expected_result = {
            'id': 1,
            'result': 'success',
            'message': ''
        }
        self.assertEqual(result, expected_result)

    @patch('asyncio.run')
    async def test_run(self, mock_run):
        mock_task_source = AsyncMock(spec=DQCOSTaskHandler)
        mock_task_source.fetch_tasks.return_value = ['task1', 'task2']
        mock_task_source.confirm_workload = AsyncMock()
        mock_task_source.send_results = AsyncMock()
        mock_task_source.fetch_cancellation.return_value = ['task1', 'task2']
        mock_task_source.receive_cancellation_result = AsyncMock()
        self.manager.task_sources = [mock_task_source]

        async def run_with_timeout():
            try:
                await asyncio.wait_for(self.manager.run(), timeout=1.0)

            except asyncio.TimeoutError:
                qcos_logger.error('Operation timed out')
                # 可能需要清理或重试逻辑
            except asyncio.CancelledError:
                qcos_logger.error('Operation was cancelled')

            finally:
                self.manager.running = False

        await run_with_timeout()

        # 验证方法调用
        self.assertTrue(mock_task_source.fetch_tasks.called)
        self.assertTrue(mock_task_source.send_results.called)
        self.assertTrue(mock_task_source.fetch_cancellation.called)
        self.assertTrue(mock_task_source.confirm_workload.called)
        self.assertTrue(mock_task_source.receive_cancellation_result.called)

        # 打印调用次数，用于调试
        qcos_logger.debug(
            f'fetch_tasks called {
                mock_task_source.fetch_tasks.call_count} times')

        # 验证至少调用了一次
        mock_task_source.fetch_tasks.assert_called()
        mock_task_source.send_results.assert_called()
        mock_task_source.fetch_cancellation.assert_called()
        mock_task_source.confirm_workload.assert_called_with(
            ['task1', 'task2'])
        mock_task_source.receive_cancellation_result.assert_called_with(
            ['task1', 'task2'])


if __name__ == '__main__':
    unittest.main()
