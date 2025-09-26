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
import json
from unittest.mock import patch
from qcos.interface.qcos_dqcosapi_handler_strategy import (
    DQcosHeartbeatStrategy,
    DQcosFetchWorkloadStrategy,
    DQcosConfirmWorkloadStrategy,
    DQcosReceiveWorkloadResultStrategy,
    DQcosFetchCancellationStrategy,
    DQcosReceiveCancellationResultStrategy,
    QCOSRequestStrategy,
    DQcosFetchIsingWorkloadStrategy)
from qcos.log.qcos_log import QCOSLogger
from qcos.interface.qcos_task_manager import TaskManager

# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TestQCOSRequestStrategy(unittest.TestCase):
    '''
    测试QCOSRequestStrategy策略类及其子类的单元测试类。
    该类包括对各种HTTP请求策略的测试，确保每种策略都能按照预期执行并处理HTTP响应。
    '''

    def test_qcosrequest_strategy(self):
        '''
        测试基类QCOSRequest策略的执行
        '''

        strategy = QCOSRequestStrategy()
        url = 'http://example.com'

        with self.assertRaises(NotImplementedError) as context:
            strategy.execute(url)

        # 检查异常消息是否正确
        self.assertEqual(
            str(context.exception),
            'Each strategy must implement an execute method')

    @patch('requests.post')
    def test_heartbeat_strategy(self, mock_post):
        '''
        测试心跳策略的执行情况
        :param mock_post: 被模拟的requests.post方法
        '''

        # 设置模拟请求的返回值
        mock_post.return_value.status_code = 200

        strategy = DQcosHeartbeatStrategy()
        url = 'http://example.com'
        result = strategy.execute(url)

        qcos_logger.debug(f'测试心跳策略：'
                          f'\n请求URL:{url}/heartbeat'
                          f'\n返回状态码:{result}')

        # 验证请求是否正确发送
        mock_post.assert_called_once_with(
            f'{url}/heartbeat',
            headers={
                'Content-Type': 'application/json',
                'X-Request-From': 'QCOS'})
        # 验证方法返回的状态码是否为200
        self.assertEqual(result, 200)

    @patch('requests.post')
    def test_fetch_workload_strategy(self, mock_post):
        '''
        测试获取任务策略的execute方法是否能正确处理返回的JSON数据，并执行任务管理。
        :param mock_post: 被模拟的requests.post方法
        '''

        # case1：statue_code=200, json_data was correctly decoded
        # 模拟返回的JSON数据和状态码
        json_data = {
            'workload': {
                'executions': [
                    {
                        'id': 'task1',

                        # qcos专用
                        'qcosTaskPriority': 0,
                        'qcosTaskType': 'TimePrecedenceTask',

                        'content': {
                            'shots': 500,
                            'qubitCount': 2,
                            'source': 'source1'
                        }
                    },
                    {
                        'id': 'task2',

                        # qcos专用
                        'qcosTaskPriority': 0,
                        'qcosTaskType': 'TimePrecedenceTask',

                        'content': {
                            'shots': 1000,
                            'qubitCount': 5,
                            'source': 'source2'
                        }
                    }
                ]
            }
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = json_data
        mock_post.return_value.json.task_list = ['task1', 'task2']

        # 测试execute函数
        strategy = DQcosFetchWorkloadStrategy()
        url = 'http://example.com'
        data = {
            'workload': {
                'selection': {
                    'limit': 2,
                    'strategyName': 'fetch_workload'
                }
            }
        }

        result = strategy.execute(url, data)
        self.assertIsNotNone(result)

        qcos_logger.debug(f'测试获取任务策略：'
                          f'\n请求URL:{url}/workload'
                          f'\n请求数据:{data}'
                          f'\n解析后的任务:{result}')

        # 验证结果
        self.assertEqual(result, mock_post.return_value.json.task_list)
        # 验证请求是否按预期发送
        mock_post.assert_called_once_with(
            f'{url}/workload',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'X-Request-From': 'QCOS'})

        # 验证TaskManager的add_task是否被调用
        with patch.object(TaskManager, 'add_task') as mock_add_task:
            # 确保TaskManager的实例化和add_task方法的调用
            task_manager = TaskManager()
            task_manager.add_task(
                'task1', 500, 2, 'source1', 0, 'TimePrecedenceTask')
            task_manager.add_task(
                'task2', 1000, 5, 'source2', 0, 'TimePrecedenceTask')

            # 检查add_task是否被调用
            mock_add_task.assert_any_call(
                'task1', 500, 2, 'source1', 0, 'TimePrecedenceTask')
            mock_add_task.assert_any_call(
                'task2', 1000, 5, 'source2', 0, 'TimePrecedenceTask')

        # case2：statue_code=200, failed to decode JSON
        mock_post.return_value.json.side_effect = ValueError(
            'Simulated JSON decode error')
        mock_post.return_value.text = 'Invalid JSON'
        result = strategy.execute(url)
        # 验证任务列表是否为空
        self.assertEqual(result, [])

        # case3：statue_code!=200
        mock_post.return_value.status_code = 404
        mock_post.return_value.json.return_value = {'error': 'Not found'}
        mock_post.return_value.text = json.dumps({'error': 'Not found'})
        result = strategy.execute(url)
        # 验证任务列表是否为空
        self.assertEqual(result, [])

    @patch('requests.post')
    def test_fetch_ising_workload_strategy(self, mock_post):
        '''
        测试获取任务策略的execute方法是否能正确处理返回的JSON数据，并执行任务管理。
        :param mock_post: 被模拟的requests.post方法
        '''

        # case1：statue_code=200, json_data was correctly decoded
        # 模拟返回的JSON数据和状态码
        json_data = {
            'workload': {
                'executions': [
                    {
                        'id': 'task1',
                        'priority': 1,
                        'machine_id': 1,
                        'task_name': 'test_task_name',
                        'estimated_datetime': '2025-2-14 23:59:59',
                        'expected_description': 'test',
                        'project_id': 1,
                        'content': {
                            'matrixSetting': {
                                'type': 'ISING',
                                'matrix': [
                                    [-1, 1, 1],
                                    [-1, 1, 1]
                                ]
                            }
                        }
                    }
                ]
            }
        }
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = json_data
        mock_post.return_value.json.results = [('task1',
                                                1,
                                                1,
                                                'test_task_name',
                                                '2025-2-14 23:59:59',
                                                'test',
                                                1,
                                                1,
                                                10,
                                                {'type': 'ISING',
                                                 'matrix': [[-1,
                                                             1,
                                                             1],
                                                            [-1,
                                                             1,
                                                             1]]})]

        strategy = DQcosFetchIsingWorkloadStrategy()
        url = 'http://example.com'
        data = {
            'workload': {
                'selection': {
                    'limit': 1,
                    'strategyName': 'fetch_workload'
                }
            }
        }
        # 调用 DQcosFetchIsingWorkloadStrategy 的execute方法
        result = strategy.execute(url, data)

        # 验证方法被成功调用
        self.assertEqual(result, mock_post.return_value.json.results)
        mock_post.assert_called_once_with(
            f'{url}/workload',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'X-Request-From': 'QCOS'})

        # case2：statue_code=200, failed to decode JSON
        mock_post.return_value.json.side_effect = ValueError(
            'Simulated JSON decode error')
        mock_post.return_value.text = 'Invalid JSON'
        result = strategy.execute(url)
        # 验证任务列表是否为空
        self.assertEqual(result, [])

        # case3：statue_code!=200
        mock_post.return_value.status_code = 404
        mock_post.return_value.json.return_value = {404: 'Not found'}
        mock_post.return_value.text = json.dumps({404: 'Not found'})
        result = strategy.execute(url)
        # 验证任务列表是否为空
        self.assertEqual(result, [])

    @patch('requests.post')
    def test_confirmation_strategy(self, mock_post):
        '''
        测试任务确认策略是否能正确返回响应状态码。
        :param mock_post: 被模拟的requests.post方法
        '''

        # 设置模拟请求的返回值
        mock_post.return_value.status_code = 200
        strategy = DQcosConfirmWorkloadStrategy()
        url = 'http://example.com'
        data = {
            'workload': {
                'confirmations': ['task1', 'task2'],
            }
        }
        result = strategy.execute(url, data)

        qcos_logger.debug(f'测试任务确认策略：'
                          f'\n请求URL:{url}/workload/confirmation'
                          f'\n请求数据:{data}'
                          f'\n解析后的JSON数据:{result}')

        # 验证请求是否按预期发送
        mock_post.assert_called_once_with(
            f'{url}/workload/confirmation',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'X-Request-From': 'QCOS'})
        # 验证是否正确解析JSON数据
        self.assertEqual(result, 200)
        qcos_logger.debug('测试任务确认策略的执行情况通过！')

    @patch('requests.post')
    def test_fetch_cancellation_strategy(self, mock_post):
        '''
        测试任务取消策略的执行情况。
        :param mock_post: 被模拟的requests.post方法
        '''

        # case1：statue_code=200, json_data was correctly decoded
        # 设置模拟请求的返回值
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'cancellations': ['task2']}
        mock_post.return_value.text = '{\'cancellations\': [\'task2\']}'

        strategy = DQcosFetchCancellationStrategy()
        url = 'http://example.com'
        data = {
            'cancellation': {
                'selection': {
                    'limit': 1,
                    'strategyName': 'cancellations'
                }
            }
        }
        result = strategy.execute(url, data)

        qcos_logger.debug(f'测试任务取消策略：'
                          f'\n请求URL:{url}/cancellation'
                          f'\n请求数据:{data}'
                          f'\n解析后的JSON数据:{result}')

        # 验证请求是否按预期发送
        mock_post.assert_called_once_with(
            f'{url}/cancellation',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'X-Request-From': 'QCOS'})
        # 验证是否正确解析JSON数据
        self.assertEqual(result, {'cancellations': ['task2']})
        qcos_logger.debug('测试任务取消策略的执行情况通过！')

        # case2：statue_code=200, failed to decode JSON
        mock_post.return_value.json.side_effect = ValueError(
            'Simulated JSON decode error')
        mock_post.return_value.text = 'Invalid JSON'
        result = strategy.execute(url)
        # 验证结果是否为None
        self.assertIsNone(result)

        # case3：statue_code!=200
        mock_post.return_value.status_code = 404
        mock_post.return_value.json.return_value = {'error': 'Not found'}
        mock_post.return_value.text = json.dumps({'error': 'Not found'})
        result = strategy.execute(url)
        # 验证结果是否为None
        self.assertIsNone(result)

    @patch('requests.post')
    def test_receive_cancellation_result_strategy(self, mock_post):
        '''
        测试任务取消结果策略的执行情况。
        :param mock_post: 被模拟的requests.post方法
        '''

        # 设置模拟请求的返回值
        mock_post.return_value.status_code = 200

        strategy = DQcosReceiveCancellationResultStrategy()
        url = 'http://example.com'
        data = {
            'cancellation': {
                'result': [{
                    'id': 'task1',
                    'isCancelled': False
                }, {
                    'id': 'task2',
                    'isCancelled': True
                }]
            }
        }
        result = strategy.execute(url, data)

        qcos_logger.debug(f'测试任务取消结果策略：'
                          f'\n请求URL:{url}/cancellation/result'
                          f'\n请求数据:{data}'
                          f'\n解析后的JSON数据:{result}')

        # 验证请求是否按预期发送
        mock_post.assert_called_once_with(
            f'{url}/cancellation/result',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'X-Request-From': 'QCOS'})
        # 验证是否正确解析JSON数据
        self.assertEqual(result, 200)
        qcos_logger.debug('测试任务取消结果策略的执行情况通过！')

    @patch('requests.post')
    def test_receive_workload_result_strategy(self, mock_post):
        '''
        测试任务结果上报策略的执行情况。
        :param mock_post: 被模拟的requests.post方法
        '''
        # 设置模拟请求的返回值
        mock_post.return_value.status_code = 200
        strategy = DQcosReceiveWorkloadResultStrategy()
        url = 'http://example.com'
        data = {
            'workload': {
                'results': [{
                    'id': 'task1',
                    'result': {'00': 47, '01': 0, '10': 0, '11': 53},
                    'message': ''
                }]
            }
        }
        result = strategy.execute(url, data)

        qcos_logger.debug(f'测试任务结果上报策略：'
                          f'\n请求URL:{url}/workload/result'
                          f'\n请求数据:{data}'
                          f'\n解析后的JSON数据:{result}')

        # 验证请求是否按预期发送
        mock_post.assert_called_once_with(
            f'{url}/workload/result',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'X-Request-From': 'QCOS'})
        # 验证是否正确解析JSON数据
        self.assertEqual(result, 200)
        qcos_logger.debug('测试任务结果上报策略的执行情况通过！')


if __name__ == '__main__':
    unittest.main()
