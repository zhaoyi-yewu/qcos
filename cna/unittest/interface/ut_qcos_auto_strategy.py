#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Longfei Tian at 2024-09
# ------------------------


import unittest
import json
from unittest.mock import patch
from qcos.interface.qcos_auto_strategy import \
    AutoTestRequestStrategy, SystemTestResultStrategy
from qcos.log.qcos_log import QCOSLogger


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TestAutoTestRequestStrategy(unittest.TestCase):
    '''
    测试AutoTestRequestStrategy策略类及其子类的单元测试类。
    该类是对系统测试结果自动化发送策略的测试，确保能按照预期发送并返回响应结果
    '''

    def test_autotest_request_strategy(self):
        '''
        测试基类AutoTestRequestStrategy策略的执行
        '''

        strategy = AutoTestRequestStrategy()
        url = 'http://example.com'

        with self.assertRaises(NotImplementedError) as context:
            strategy.execute(url)

        # 检查异常消息是否正确
        self.assertEqual(
            str(context.exception),
            'Each strategy must implement an execute method')

    @patch('requests.post')
    def test_st_result_strategy(self, mock_post):
        '''
        测试系统测试结果发送策略的执行情况。
        :param mock_post: 被模拟的requests.post方法
        '''

        # 模拟返回的状态码
        mock_post.return_value.status_code = 200

        strategy = SystemTestResultStrategy()
        url = 'http://example.com'
        data = {
            'name': 'quantumOS',
            'test_cases': [
                {
                    'name': 'test_gate1',
                    'passed': True,
                    'detail': 'successful'},
                {
                    'name': 'test_gate2',
                    'passed': True,
                    'detail': 'successful'}
            ]
        }
        result = strategy.execute(url, data)

        qcos_logger.debug(f'系统测试结果发送策略：'
                          f'\n请求URL:{url}/autotest'
                          f'\n返回状态码:{result}')

        # 验证请求是否正确发送
        mock_post.assert_called_once_with(
            f'{url}/autotest',
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'X-Request-From': 'QCOS'})
        # 验证方法返回的状态码是否为200
        self.assertEqual(result, 200)
        qcos_logger.debug('测试系统测试结果发送策略的执行情况通过！')


if __name__ == '__main__':
    unittest.main()
