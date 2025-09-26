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
from unittest.mock import patch
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    observer.status_monitor_observer import StatusMonitorObserver


class TestStatusMonitorObserver(unittest.TestCase):
    '''
    测试 StatusMonitorObserver 类的单元测试类
    '''

    @patch('qcos.'
           'quantum_heterogeneous_hw_unified_and_management_engine.'
           'observer.status_monitor_observer.qcos_logger')
    def test_update(self, mock_qcos_logger):
        '''
        测试 update 方法
        '''
        # 创建 StatusMonitorObserver 实例
        observer = StatusMonitorObserver()

        # 模拟硬件名称和状态
        hw_name = 'TestHardware'
        status = {'state': 'active', 'temperature': 45}

        # 调用 update 方法
        observer.update(hw_name, status)

        # 验证 logger 的 debug 方法被正确调用
        expected_message = f'Status update for {hw_name}: {status}'
        mock_qcos_logger.debug.assert_called_once_with(expected_message)


if __name__ == '__main__':
    unittest.main()
