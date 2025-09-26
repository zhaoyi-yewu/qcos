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
from unittest.mock import patch, MagicMock, mock_open
from qcos.config.qcos_config_manager import QcosConfigManager
import os
import json


class TestQcosConfigManager(unittest.TestCase):
    '''
    QcosConfigManager 类的单元测试
    '''

    def setUp(self):
        '''
        在每个测试方法之前设置测试环境
        '''
        # 创建一个模拟的 ConfigParser 对象
        self.mock_config = MagicMock()
        # 使用 patch 装饰器来模拟 configparser.ConfigParser
        self.patcher = patch(
            'configparser.ConfigParser',
            return_value=self.mock_config)
        self.patcher.start()

        # 创建 QcosConfigManager 实例
        self.qcos_config = QcosConfigManager()

    def tearDown(self):
        '''
        在每个测试方法之后清理测试环境
        '''
        # 停止 patch
        self.patcher.stop()

    def test_get_log_dir(self):
        '''
        测试 get_log_dir 方法
        '''
        # 设置模拟的返回值
        self.mock_config.get.return_value = '/test/log/dir'
        # 调用被测试的方法
        result = self.qcos_config.get_log_dir()
        # 断言结果是否符合预期
        self.assertEqual(result, '/test/log/dir')
        # 验证 get 方法是否被正确调用
        self.mock_config.get.assert_called_once_with(
            'log', 'log_dir', fallback='runtime_log/qcos/')

    def test_get_log_file_size(self):
        '''
        测试 get_log_file_size 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 20971520
        # 调用被测试的方法
        result = self.qcos_config.get_log_file_size()
        # 断言结果是否符合预期
        self.assertEqual(result, 20971520)
        # 验证 getint 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'log', 'log_file_size', fallback=10485760)

    def test_get_log_file_count(self):
        '''
        测试 get_log_file_count 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 10
        # 调用被测试的方法
        result = self.qcos_config.get_log_file_count()
        # 断言结果是否符合预期
        self.assertEqual(result, 10)
        # 验证 getint 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'log', 'log_file_count', fallback=5)

    @patch('os.path.dirname')
    def test_get_config_path(self, mock_dirname):
        '''
        测试 get_config_path 方法
        '''
        # 设置模拟的返回值
        mock_dirname.return_value = '/'
        # 调用被测试的方法
        result = self.qcos_config.get_config_path()
        # 断言结果是否符合预期
        self.assertEqual(result, '/')

    def test_get_original_openqasm_file_path(self):
        '''
        测试 get_original_openqasm_file_path 方法
        '''
        # 设置模拟的返回值
        self.mock_config.get.return_value = '/test/openqasm/path'
        # 调用被测试的方法
        result = self.qcos_config.get_original_openqasm_file_path()
        # 断言结果是否符合预期
        self.assertIn('/test/openqasm/path', result)
        # 验证 get 方法是否被正确调用
        self.mock_config.get.assert_called_once_with(
            'openqasm',
            'original_openqasm_file_path',
            fallback='user_task/user_original_task')

    def test_get_processing_openqasm_file_path(self):
        '''
        测试 get_processing_openqasm_file_path 方法
        '''
        # 设置模拟的返回值
        self.mock_config.get.return_value = '/test/openqasm/path'
        # 调用被测试的方法
        result = self.qcos_config.get_processing_openqasm_file_path()
        # 断言结果是否符合预期
        self.assertIn('/test/openqasm/path', result)
        # 验证 get 方法是否被正确调用
        self.mock_config.get.assert_called_once_with(
            'openqasm',
            'processing_openqasm_file_path',
            fallback='user_task/qcos_processing_task')

    def test_get_qubit_nums(self):
        '''
        测试 get_qubit_nums 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 20
        # 调用被测试的方法
        result = self.qcos_config.get_qubit_nums()
        # 断言结果是否符合预期
        self.assertEqual(result, 20)
        # 验证 getint 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'openqasm', 'qubit_nums', fallback=10)

    def test_get_shots_num(self):
        '''
        测试 get_shots_num 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 2000
        # 调用被测试的方法
        result = self.qcos_config.get_shots_num()
        # 断言结果是否符合预期
        self.assertEqual(result, 2000)
        # 验证 getint 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'openqasm', 'shots_num', fallback=1000)

    def test_get_task_priority(self):
        '''
        测试 get_task_priority 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 1
        # 调用被测试的方法
        result = self.qcos_config.get_task_priority()
        # 断言结果是否符合预期
        self.assertEqual(result, 1)
        # 验证 getint 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'openqasm', 'priority', fallback=1)

    def test_get_task_type(self):
        '''
        测试 get_task_type 方法
        '''
        # 设置模拟的返回值
        self.mock_config.get.return_value = 'XternalOpenqasmTask'
        # 调用被测试的方法
        result = self.qcos_config.get_task_type()
        # 断言结果是否符合预期
        self.assertEqual(result, 'XternalOpenqasmTask')
        # 验证 getint 方法是否被正确调用
        self.mock_config.get.assert_called_once_with(
            'openqasm', 'task_type', fallback='PriorityTask')

    @patch('os.path.dirname')
    def test_get_task_result_path(self, mock_dirname):
        '''
        测试 get_task_result_path 方法
        '''
        # 设置模拟的返回值
        self.mock_config.get.return_value = 'test/result/path'
        mock_dirname.return_value = ''
        # 调用被测试的方法
        result = self.qcos_config.get_task_result_path()
        # 断言结果是否符合预期
        self.assertEqual(result, 'test/result/path')
        # 验证 get 方法是否被正确调用
        self.mock_config.get.assert_called_once_with(
            'openqasm', 'task_result_path', fallback='task_result/xternal')

    def test_get_fetch_interval(self):
        '''
        测试 get_fetch_interval 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 120
        # 调用被测试的方法
        result = self.qcos_config.get_fetch_interval()
        # 断言结果是否符合预期
        self.assertEqual(result, 120)
        # 验证 getint 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'task', 'fetch_interval', fallback=60)

    def test_get_task_sources(self):
        '''
        测试 get_task_sources 方法
        '''
        # 设置模拟的返回值
        self.mock_config.get.return_value = 'DQCOS, QCLOUD'
        # 调用被测试的方法
        result = self.qcos_config.get_task_sources()
        # 断言结果是否符合预期
        self.assertEqual(result, ['DQCOS', 'QCLOUD'])
        # 验证 get 方法是否被正确调用
        self.mock_config.get.assert_called_once_with(
            'task', 'sources', fallback='DQCOS')

    def test_get_fetch_task_num(self):
        '''
        测试 get_fetch_task_num 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 10
        # 调用被测试的方法
        result = self.qcos_config.get_fetch_task_num()
        # 断言结果是否符合预期
        self.assertEqual(result, 10)
        # 验证 get 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'task', 'fetch_task_num', fallback=5)

    def test_get_fetch_cancellation_task_num(self):
        '''
        测试 get_fetch_cancellation_task_num 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 10
        # 调用被测试的方法
        result = self.qcos_config.get_fetch_cancellation_task_num()
        # 断言结果是否符合预期
        self.assertEqual(result, 10)
        # 验证 get 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'task', 'fetch_cancellation_task_num', fallback=5)

    def test_get_send_task_wait_time(self):
        '''
        测试 get_send_task_wait_time 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 60
        # 调用被测试的方法
        result = self.qcos_config.get_send_task_wait_time()
        # 断言结果是否符合预期
        self.assertEqual(result, 60)
        # 验证 getint 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'task', 'send_task_wait_time', fallback=30)

    def test_get_error_wait_time(self):
        '''
        测试 get_error_wait_time 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 600
        # 调用被测试的方法
        result = self.qcos_config.get_error_wait_time()
        # 断言结果是否符合预期
        self.assertEqual(result, 600)
        # 验证 getint 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'task', 'error_wait_time', fallback=300)

    def test_get_scheduler_wait_time(self):
        '''
        测试 get_scheduler_wait_time 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 60
        # 调用被测试的方法
        result = self.qcos_config.get_scheduler_wait_time()
        # 断言结果是否符合预期
        self.assertEqual(result, 60)
        # 验证 getint 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'task', 'scheduler_wait_time', fallback=30)

    def test_get_max_concurrent_tasks(self):
        '''
        测试 get_max_concurrent_tasks 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 10
        # 调用被测试的方法
        result = self.qcos_config.get_max_concurrent_tasks()
        # 断言结果是否符合预期
        self.assertEqual(result, 10)
        # 验证 getint 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'task', 'max_concurrent_tasks', fallback=5)

    def test_get_task_aggregation_upper_threshold(self):
        '''
        测试 get_task_aggregation_upper_threshold 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 7
        # 调用被测试的方法
        result = self.qcos_config.get_task_aggregation_upper_threshold()
        # 断言结果是否符合预期
        self.assertEqual(result, 7)
        # 验证 getint 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'task', 'task_aggregation_upper_threshold', fallback=5)

    def test_get_task_aggregation_lower_threshold(self):
        '''
        测试 get_task_aggregation_lower_threshold 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 1
        # 调用被测试的方法
        result = self.qcos_config.get_task_aggregation_lower_threshold()
        # 断言结果是否符合预期
        self.assertEqual(result, 1)
        # 验证 getint 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'task', 'task_aggregation_lower_threshold', fallback=2)

    def test_get_task_aggregation_switch(self):
        '''
        测试 get_task_aggregation_switch 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getboolean.return_value = True
        # 调用被测试的方法
        result = self.qcos_config.get_task_aggregation_switch()
        # 断言结果是否符合预期
        self.assertTrue(result)
        # 验证 getboolean 方法是否被正确调用
        self.mock_config.getboolean.assert_called_once_with(
            'task', 'task_aggregation_switch', fallback=False)

    def test_get_collect_task_num(self):
        '''
        测试 get_collect_task_num 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getint.return_value = 1
        # 调用被测试的方法
        result = self.qcos_config.get_collect_task_num()
        # 断言结果是否符合预期
        self.assertEqual(result, 1)
        # 验证 getboolean 方法是否被正确调用
        self.mock_config.getint.assert_called_once_with(
            'task', 'collect_task_num', fallback=1)

    def test_get_single_gate_cost(self):
        '''
        测试 get_single_gate_cost 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getfloat.return_value = 10
        # 调用被测试的方法
        result = self.qcos_config.get_single_gate_cost()
        # 断言结果是否符合预期
        self.assertEqual(result, 10)
        # 验证 getboolean 方法是否被正确调用
        self.mock_config.getfloat.assert_called_once_with(
            'task', 'single_gate_cost', fallback=6E-6)

    def test_get_multi_gate_cost(self):
        '''
        测试 get_multi_gate_cost 方法
        '''
        # 设置模拟的返回值
        self.mock_config.getfloat.return_value = 5
        # 调用被测试的方法
        result = self.qcos_config.get_multi_gate_cost()
        # 断言结果是否符合预期
        self.assertEqual(result, 5)
        # 验证 getboolean 方法是否被正确调用
        self.mock_config.getfloat.assert_called_once_with(
            'task', 'multi_gate_cost', fallback=2E-6)

    def test_get_dqcos_url(self):
        '''
        测试 get_dqcos_url 方法
        '''
        # 设置模拟的返回值
        self.mock_config.get.return_value = 'http://testserver:8080'
        # 调用被测试的方法
        result = self.qcos_config.get_dqcos_url()
        # 断言结果是否符合预期
        self.assertEqual(result, 'http://testserver:8080')
        # 验证 get 方法是否被正确调用
        self.mock_config.get.assert_called_once_with(
            'qcos', 'dqcos_url', fallback='http://127.0.0.1:5000')

    def test_get_device_id(self):
        '''
        测试 get_device_id 方法
        '''
        # 设置模拟的返回值
        self.mock_config.get.return_value = 'test_device'
        # 调用被测试的方法
        result = self.qcos_config.get_device_id()
        # 断言结果是否符合预期
        self.assertEqual(result, 'test_device')
        # 验证 get 方法是否被正确调用
        self.mock_config.get.assert_called_once_with(
            'qcos', 'device_id', fallback='1')

    def test_get_autotest_url(self):
        '''
        测试 get_autotest_url 方法
        '''
        # 设置模拟的返回值
        self.mock_config.get.return_value = 'http://example.com:8080'
        # 调用被测试的方法
        result = self.qcos_config.get_autotest_url()
        # 断言结果是否符合预期
        self.assertEqual(result, 'http://example.com:8080')
        # 验证 get 方法是否被正确调用
        self.mock_config.get.assert_called_once_with(
            'qcos', 'autotest_url', fallback='http://100.78.61.1:8385')

    def test_get_topo_file(self):
        '''
        测试 get_topo_file 方法
        '''
        self.mock_config.get.return_value = 'na_file.json'
        # 模拟打开json文件
        mock_data = {'overview': {'key': 'value'}}
        with patch(
                target='builtins.open', new_callable=mock_open,
                read_data=json.dumps(mock_data)
        ) as mock_file:
            # 调用被测试的方法
            result = self.qcos_config.get_topo_file()
            # 断言结果是否符合预期
            self.assertEqual(result, {'key': 'value'})
            # 验证 get 方法是否被正确调用
            self.mock_config.get.assert_called_once_with(
                'topology', 'topo_file', fallback='na_file.json')

    def test_get_topo_file_without_file(self):
        '''
        测试 get_topo_file 方法没有topo文件的场景
        '''
        self.mock_config.get.return_value = 'test\\topology.json'
        # 模拟json文件不存在
        with patch('builtins.open', new_callable=mock_open) as mock_file:
            mock_file.side_effect = FileNotFoundError('File not found')
            # 调用被测试的方法
            result = self.qcos_config.get_topo_file()

            # 获取当前文件的绝对路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 构建json文件的绝对路径
            topo_file_path = os.path.join(
                current_dir,
                f'../../config/{self.mock_config.get.return_value}')
            topo_file_path = os.path.normpath(topo_file_path)

            # 验证是否尝试打开文件
            mock_file.assert_called_once_with(topo_file_path, 'r')

            # 断言结果是否符合预期
            self.assertEqual(result, {})

    @patch('os.path.dirname')
    def test_get_na_file(self, mock_dirname):
        '''
        测试 get_na_file 方法
        '''
        self.mock_config.get.return_value = 'na_file.json'
        mock_dirname.return_value = ''
        # 调用被测试的方法
        result = self.qcos_config.get_na_file()
        # 断言结果是否符合预期
        self.assertEqual(result, 'na_file.json')
        self.mock_config.get.assert_called_once_with(
            'topology', 'topo_file', fallback='na_file.json')

    def test_get_awg_sampling_rate(self):
        '''
        测试 get_awg_sampling_rate 方法
        '''
        self.mock_config.getint.return_value = 10000
        result = self.qcos_config.get_awg_sampling_rate()
        # 断言结果是否符合预期
        self.assertEqual(result, 10000)
        self.mock_config.getint.assert_called_once_with(
            'AWG', 'samplingRateMHz', fallback=500)

    def test_get_awg_delay_value(self):
        '''
        测试 get_awg_delay_value 方法
        '''
        self.mock_config.getint.return_value = 10
        result = self.qcos_config.get_awg_delay_value()
        # 断言结果是否符合预期
        self.assertEqual(result, 10)
        self.mock_config.getint.assert_called_once_with(
            'AWG', 'delay', fallback=0)

    def test_get_awg_test_time(self):
        '''
        测试 get_awg_test_time 方法
        '''
        self.mock_config.getfloat.return_value = 10.5
        result = self.qcos_config.get_awg_test_time()
        # 断言结果是否符合预期
        self.assertEqual(result, 10.5)
        self.mock_config.getfloat.assert_called_once_with(
            'AWG', 'test_time', fallback=0.5)

    def test_get_awg_address(self):
        '''
        测试 get_awg_address 方法
        '''
        self.mock_config.get.return_value = '1.2.3.4'
        result = self.qcos_config.get_awg_address()
        # 断言结果是否符合预期
        self.assertEqual(result, '1.2.3.4')
        self.mock_config.get.assert_called_once_with(
            'AWG', 'awg_address', fallback='192.168.1.1')

    def test_get_awg_channel(self):
        '''
        测试 get_awg_channel 方法
        '''
        self.mock_config.get.return_value = '[1]'
        result = self.qcos_config.get_awg_channel()
        # 断言结果是否符合预期
        self.assertEqual(result, [1])
        self.mock_config.get.assert_called_once_with(
            'AWG', 'channel', fallback=[1, 2, 3, 4])

    def test_get_awg_serial_number(self):
        '''
        测试 get_awg_serial_number 方法
        '''
        self.mock_config.get.return_value = 'MY12345678'
        result = self.qcos_config.get_awg_serial_number()
        # 断言结果是否符合预期
        self.assertEqual(result, 'MY12345678')
        self.mock_config.get.assert_called_once_with(
            'AWG', 'serialNumber', fallback='MY63400261')

    def test_get_awg_product(self):
        '''
        测试 get_awg_product 方法
        '''
        self.mock_config.get.return_value = 'M3202A'
        result = self.qcos_config.get_awg_product()
        # 断言结果是否符合预期
        self.assertEqual(result, 'M3202A')
        self.mock_config.get.assert_called_once_with(
            'AWG', 'product', fallback='M3201A')

    def test_get_awg_amplitude(self):
        '''
        测试 get_awg_amplitude 方法
        '''
        self.mock_config.get.return_value = '[0.2, 1.2, 0.2, 0.2]'
        result = self.qcos_config.get_awg_amplitude()
        # 断言结果是否符合预期
        self.assertEqual(result, [0.2, 1.2, 0.2, 0.2])
        self.mock_config.get.assert_called_once_with(
            'AWG', 'amp', fallback=[0.2, 1.2, 0.2, 0.2])

    def test_get_awg_trigger_mode(self):
        '''
        测试 get_awg_trigger_mode 方法
        '''
        self.mock_config.getint.return_value = 0
        result = self.qcos_config.get_awg_trigger_mode()
        # 断言结果是否符合预期
        self.assertEqual(result, 0)
        self.mock_config.getint.assert_called_once_with(
            'AWG', 'trigger_mode', fallback=2)

    def test_get_awg_lib_path(self):
        '''
        测试 get_awg_lib_path 方法
        '''
        self.mock_config.get.return_value = 'test_awg_lib_path'
        result = self.qcos_config.get_awg_lib_path()
        # 断言结果是否符合预期
        self.assertEqual(result, 'test_awg_lib_path')
        self.mock_config.get.assert_called_once_with(
            'AWG',
            'awg_lib_path',
            fallback='C:/Program Files/Keysight/SD1/shared/SD1core')

    def test_get_awg_wave_id_file(self):
        '''
        测试 get_awg_wave_id_file 方法
        '''
        self.mock_config.get.return_value = 'test_awg_wave_id_file'
        result = self.qcos_config.get_awg_wave_id_file()
        # 断言结果是否符合预期
        self.assertEqual(result, 'test_awg_wave_id_file')
        self.mock_config.get.assert_called_once_with('AWG', 'wave_id_file',
                                                     fallback='./wave_id.json')

    def test_get_awg_wave_file_dir(self):
        '''
        测试 get_awg_wave_file_dir 方法
        '''
        self.mock_config.get.return_value = 'test_awg_wave_file_dir'
        result = self.qcos_config.get_awg_wave_file_dir()
        # 断言结果是否符合预期
        self.assertEqual(result, 'test_awg_wave_file_dir')
        self.mock_config.get.assert_called_once_with('AWG', 'wave_file_dir',
                                                     fallback='./wave_file')

    def test_get_debug_mode(self):
        '''
        测试 get_debug_mode 方法
        '''
        self.mock_config.getboolean.return_value = True
        result = self.qcos_config.get_debug_mode()
        # 断言结果是否符合预期
        self.assertEqual(result, True)
        self.mock_config.getboolean.assert_called_once_with(
            'AWG', 'debug_mode', fallback=True)

    def test_get_fpga_port_value(self):
        '''
        测试 get_fpga_port_value 方法，能正常获取配置值
        '''
        self.mock_config.get.return_value = 'COM6'
        result = self.qcos_config.get_fpga_port_value()
        # 断言结果是否符合预期
        self.assertEqual(result, 'COM6')
        self.mock_config.get.assert_called_once_with(
            'FPGA', 'port', fallback='COM5')

    def test_get_fpga_clock_period(self):
        '''
        测试 get_fpga_clock_period 方法，能正常获取配置值
        '''
        self.mock_config.getfloat.return_value = 1E05
        result = self.qcos_config.get_fpga_clock_period()
        # 断言结果是否符合预期
        self.assertEqual(result, 1E05)
        self.mock_config.getfloat.assert_called_once_with(
            'FPGA', 'clock_period', fallback=1E-3)

    def test_get_fpga_test_time(self):
        '''
        测试 get_fpga_test_time 方法，能正常获取配置值
        '''
        self.mock_config.getfloat.return_value = 10.5
        result = self.qcos_config.get_fpga_test_time()
        # 断言结果是否符合预期
        self.assertEqual(result, 10.5)
        self.mock_config.getfloat.assert_called_once_with(
            'FPGA', 'test_time', fallback=0.5)

    def test_get_fpga_bytes_returned_value(self):
        '''
        测试 get_fpga_bytes_returned_value 方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 10
        result = self.qcos_config.get_fpga_bytes_returned_value()
        # 断言结果是否符合预期
        self.assertEqual(result, 10)
        self.mock_config.getint.assert_called_once_with(
            'FPGA', 'bytes_returned', fallback=12)

    def test_get_fpga_ext_trig(self):
        '''
        测试 get_fpga_ext_trig 方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 10
        result = self.qcos_config.get_fpga_ext_trig()
        # 断言结果是否符合预期
        self.assertEqual(result, 10)
        self.mock_config.getint.assert_called_once_with(
            'FPGA', 'ext_trig', fallback=1)

    def test_get_ni_ao_type(self):
        '''
        测试 get_ni_ao_type 方法，能正常获取配置值
        '''
        self.mock_config.get.return_value = 'niao, nido, nidi'
        result = self.qcos_config.get_ni_ao_type()
        # 断言结果是否符合预期
        self.assertEqual(result, 'niao')
        self.mock_config.get.assert_called_once_with(
            'NI', 'type', fallback='niao')

    def test_get_ni_ao_address(self):
        '''
        测试 get_ni_ao_address 方法，能正常获取配置值
        '''
        self.mock_config.get.return_value = ('/dev1/ao0:6,'
                                             '/dev2/port0/line0:7 |'
                                             '/dev2/port1/line0:5,')
        fallback = [
            '/dev1/ao0',
            '/dev1/ao3',
            '/dev1/ao4',
            '/dev1/ao7',
            '/dev1/ao8',
            '/dev1/ao9',
            '/dev1/ao15',
            '/dev1/ao16',
            '/dev1/ao17',
            '/dev1/ao18']
        result = self.qcos_config.get_ni_ao_address()
        # 断言结果是否符合预期
        self.assertEqual(result, ['/dev1/ao0:6'])
        self.mock_config.get.assert_called_once_with(
            'NI', 'address', fallback=fallback)

    def test_get_ni_ao_rate(self):
        '''
        测试 get_ni_ao_rate 方法，能正常获取配置值
        '''
        self.mock_config.get.return_value = '4e5,5e5'
        result = self.qcos_config.get_ni_ao_rate()
        # 断言结果是否符合预期
        self.assertEqual(result, 4e5)
        self.mock_config.get.assert_called_once_with(
            'NI', 'rate', fallback=4e5)

    def test_get_ni_ao_trigger_source(self):
        '''
        测试 get_ni_ao_trigger_source 方法，能正常获取配置值
        '''
        self.mock_config.get.return_value = '/PXI1Slot3/PXI_Trig1'
        result = self.qcos_config.get_ni_ao_trigger_source()
        # 断言结果是否符合预期
        self.assertEqual(result, '/PXI1Slot3/PXI_Trig1')
        self.mock_config.get.assert_called_once_with(
            'NI', 'trigger_source', fallback='/dev1/PFI0')

    def test_get_ni_do_type(self):
        '''
        测试 get_ni_do_type 方法，能正常获取配置值
        '''
        self.mock_config.get.return_value = 'niao, nido, nidi'
        result = self.qcos_config.get_ni_do_type()
        # 断言结果是否符合预期
        self.assertEqual(result, 'nido')
        self.mock_config.get.assert_called_once_with(
            'NI', 'type', fallback='nido')

    def test_get_ni_do_address(self):
        '''
        测试 get_ni_do_address 方法，能正常获取配置值
        '''
        self.mock_config.get.return_value = ('/dev1/ao0:6,'
                                             '/dev2/port0/line0:7|'
                                             '/dev2/port1/line0:5,')
        fallback = [
            '/dev2/port0/line0:7',
            '/dev2/port1/line0:3',
            '/dev2/port2/line6',
            '/dev2/port3/line2',
            '/dev2/port3/line3',
            '/dev2/port3/line6']
        result = self.qcos_config.get_ni_do_address()
        # 断言结果是否符合预期
        self.assertEqual(
            result, [
                '/dev2/port0/line0:7', '/dev2/port1/line0:5'])
        self.mock_config.get.assert_called_once_with(
            'NI', 'address', fallback=fallback)

    def test_get_ni_do_rate(self):
        '''
        测试 get_ni_do_rate 方法，能正常获取配置值
        '''
        self.mock_config.get.return_value = '4e5,5e5'
        result = self.qcos_config.get_ni_do_rate()
        # 断言结果是否符合预期
        self.assertEqual(result, 5e5)
        self.mock_config.get.assert_called_once_with(
            'NI', 'rate', fallback=5e5)

    def test_get_ni_di_type(self):
        '''
        测试 get_ni_di_type 方法，能正常获取配置值
        '''
        self.mock_config.get.return_value = 'niao, nido, nidi'
        result = self.qcos_config.get_ni_di_type()
        # 断言结果是否符合预期
        self.assertEqual(result, 'nidi')
        self.mock_config.get.assert_called_once_with(
            'NI', 'type', fallback='nidi')

    def test_get_ni_di_address(self):
        '''
        测试 get_ni_di_address 方法，能正常获取配置值
        '''
        self.mock_config.get.return_value = ('/dev1/ao0:6,'
                                             '/dev2/port0/line0:7 |'
                                             '/dev2/port1/line0:5,')
        result = self.qcos_config.get_ni_di_address()
        # 断言结果是否符合预期
        self.assertEqual(result, [''])
        self.mock_config.get.assert_called_once_with(
            'NI', 'address', fallback=[''])

    def test_get_delay_time(self):
        '''
        测试 get_delay_time 方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 1
        result = self.qcos_config.get_delay_time()
        # 断言结果是否符合预期
        self.assertEqual(result, 1)
        self.mock_config.getint.assert_called_once_with(
            'NI', 'delay_time', fallback=0)

    def test_get_delay_start(self):
        '''
        测试 get_delay_start 方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 1
        result = self.qcos_config.get_delay_start()
        # 断言结果是否符合预期
        self.assertEqual(result, 1)
        self.mock_config.getint.assert_called_once_with(
            'NI', 'delay_start', fallback=0)

    def test_get_do0_pgc_cooling_time(self):
        '''
        测试 get_do0_pgc_cooling_time 方法
        '''
        self.mock_config.getfloat.return_value = 0.1
        result = self.qcos_config.get_do0_pgc_cooling_time()
        # 断言结果是否符合预期
        self.assertEqual(result, 0.1)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'do0_pgc_cooling_time', fallback=0)

    def test_get_do0_meas_cooling_time(self):
        '''
        测试 get_do0_meas_cooling_time 方法
        '''
        self.mock_config.getfloat.return_value = 0.2
        result = self.qcos_config.get_do0_meas_cooling_time()
        # 断言结果是否符合预期
        self.assertEqual(result, 0.2)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'do0_meas_cooling_time', fallback=0)

    def test_get_do2_pgc_pump_time(self):
        '''
        测试 get_do2_pgc_pump_time 方法
        '''
        self.mock_config.getfloat.return_value = 0.3
        result = self.qcos_config.get_do2_pgc_pump_time()
        # 断言结果是否符合预期
        self.assertEqual(result, 0.3)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'do2_pgc_pump_time', fallback=0)

    def test_get_do2_meas_pump_time(self):
        '''
        测试 get_do2_meas_pump_time 方法
        '''
        self.mock_config.getfloat.return_value = 0.4
        result = self.qcos_config.get_do2_meas_pump_time()
        # 断言结果是否符合预期
        self.assertEqual(result, 0.4)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'do2_meas_pump_time', fallback=0)

    def test_get_ao1_pgc_cooling_detune(self):
        '''
        测试 get_ao1_pgc_cooling_detune 方法
        '''
        self.mock_config.getfloat.return_value = 3.0
        result = self.qcos_config.get_ao1_pgc_cooling_detune()
        # 断言结果是否符合预期
        self.assertEqual(result, 3.0)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'ao1_pgc_cooling_detune', fallback=3.2)

    def test_get_ao1_meas_cooling_detune(self):
        '''
        测试 get_ao1_meas_cooling_detune 方法
        '''
        self.mock_config.getfloat.return_value = 3.1
        result = self.qcos_config.get_ao1_meas_cooling_detune()
        # 断言结果是否符合预期
        self.assertEqual(result, 3.1)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'ao1_meas_cooling_detune', fallback=3.2)

    def test_get_ao1_meas_cooling_freq(self):
        '''
        测试 get_ao1_meas_cooling_freq 方法
        '''
        self.mock_config.getfloat.return_value = 6.0
        result = self.qcos_config.get_ao1_meas_cooling_freq()
        # 断言结果是否符合预期
        self.assertEqual(result, 6.0)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'ao1_meas_cooling_freq', fallback=6.4)

    def test_get_ao3_pgc_pump_detune(self):
        '''
        测试 get_ao3_pgc_pump_detune 方法
        '''
        self.mock_config.getfloat.return_value = 3.3
        result = self.qcos_config.get_ao3_pgc_pump_detune()
        # 断言结果是否符合预期
        self.assertEqual(result, 3.3)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'ao3_pgc_pump_detune', fallback=3.4)

    def test_get_ao3_meas_pump_detune(self):
        '''
        测试 get_ao3_meas_pump_detune 方法
        '''
        self.mock_config.getfloat.return_value = 3.5
        result = self.qcos_config.get_ao3_meas_pump_detune()
        # 断言结果是否符合预期
        self.assertEqual(result, 3.5)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'ao3_meas_pump_detune', fallback=4)

    def test_get_ao4_pgc_comp_mag(self):
        '''
        测试 get_ao4_pgc_comp_mag 方法
        '''
        self.mock_config.getfloat.return_value = 1.2
        result = self.qcos_config.get_ao4_pgc_comp_mag()
        # 断言结果是否符合预期
        self.assertEqual(result, 1.2)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'ao4_pgc_comp_mag', fallback=1.277)

    def test_get_ao5_pgc_comp_mag(self):
        '''
        测试 get_ao5_pgc_comp_mag 方法
        '''
        self.mock_config.getfloat.return_value = 1.3
        result = self.qcos_config.get_ao5_pgc_comp_mag()
        # 断言结果是否符合预期
        self.assertEqual(result, 1.3)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'ao5_pgc_comp_mag', fallback=1.261)

    def test_get_ao6_pgc_comp_mag(self):
        '''
        测试 get_ao6_pgc_comp_mag 方法
        '''
        self.mock_config.getfloat.return_value = 1.4
        result = self.qcos_config.get_ao6_pgc_comp_mag()
        # 断言结果是否符合预期
        self.assertEqual(result, 1.4)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'ao6_pgc_comp_mag', fallback=1.325)

    def test_get_ao7_raman_source_freq(self):
        '''
        测试 get_ao7_raman_source_freq 方法
        '''
        self.mock_config.getfloat.return_value = 1.4
        result = self.qcos_config.get_ao7_raman_source_freq()
        # 断言结果是否符合预期
        self.assertEqual(result, 1.4)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'ao7_raman_source_freq', fallback=1.325)

    def test_get_ao8_pgc_pump_amp(self):
        '''
        测试 get_ao8_pgc_pump_amp 方法
        '''
        self.mock_config.getfloat.return_value = 4
        result = self.qcos_config.get_ao8_pgc_pump_amp()
        # 断言结果是否符合预期
        self.assertEqual(result, 4)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'ao8_pgc_pump_amp', fallback=5)

    def test_get_ao8_meas_pump_amp(self):
        '''
        测试 get_ao8_meas_pump_amp 方法
        '''
        self.mock_config.getfloat.return_value = 3
        result = self.qcos_config.get_ao8_meas_pump_amp()
        # 断言结果是否符合预期
        self.assertEqual(result, 3)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'ao8_meas_pump_amp', fallback=5)

    def test_get_ao9_pgc_cooling_amp(self):
        '''
        测试 get_ao9_pgc_cooling_amp 方法
        '''
        self.mock_config.getfloat.return_value = 2
        result = self.qcos_config.get_ao9_pgc_cooling_amp()
        # 断言结果是否符合预期
        self.assertEqual(result, 2)
        self.mock_config.getfloat.assert_called_once_with(
            'NI', 'ao9_pgc_cooling_amp', fallback=5)

    def test_get_qubit_number(self):
        '''
        测试 get_qubit_number 方法
        '''
        self.mock_config.getint.return_value = 100
        result = self.qcos_config.get_qubit_number()
        # 断言结果是否符合预期
        self.assertEqual(result, 100)
        self.mock_config.getint.assert_called_once_with(
            'execute', 'qubit_number', fallback=64)

    def test_get_row_num(self):
        '''
        测试 get_row_num 方法
        '''
        self.mock_config.getint.return_value = 10
        result = self.qcos_config.get_row_num()
        # 断言结果是否符合预期
        self.assertEqual(result, 10)
        self.mock_config.getint.assert_called_once_with(
            'execute', 'row_num', fallback=8)

    def test_get_col_num(self):
        '''
        测试 get_col_num 方法
        '''
        self.mock_config.getint.return_value = 20
        result = self.qcos_config.get_col_num()
        # 断言结果是否符合预期
        self.assertEqual(result, 20)
        self.mock_config.getint.assert_called_once_with(
            'execute', 'col_num', fallback=8)

    def test_get_rea_region(self):
        '''
        测试 get_rea_region 方法
        '''
        self.mock_config.get.return_value = '[1, 2, 3, 4]'
        result = self.qcos_config.get_rea_region()
        # 断言结果是否符合预期
        self.assertEqual(result, [1, 2, 3, 4])
        self.mock_config.get.assert_called_once_with(
            'execute', 'rea_region', fallback=[3, 5, 3, 5])

    def test_get_rea_dll_path(self):
        '''
        测试 get_rea_dll_path 方法
        '''
        self.mock_config.get.return_value = './test1.dll'
        result = self.qcos_config.get_rea_dll_path()
        # 断言结果是否符合预期
        self.assertEqual(result, './test1.dll')
        self.mock_config.get.assert_called_once_with(
            'execute', 'rea_dll_path', fallback='./test.dll')

    def test_get_raman_channel(self):
        '''
        测试 get_raman_channel 方法
        '''
        self.mock_config.get.return_value = '[1, 2, 3]'
        result = self.qcos_config.get_raman_channel()
        # 断言结果是否符合预期
        self.assertEqual(result, [1, 2, 3])
        self.mock_config.get.assert_called_once_with(
            'execute', 'raman_channel', fallback=[1, 2, 3, 4])

    def test_get_rea_channel(self):
        '''
        测试 get_rea_channel 方法
        '''
        self.mock_config.get.return_value = '[1, 2, 3]'
        result = self.qcos_config.get_rea_channel()
        # 断言结果是否符合预期
        self.assertEqual(result, [1, 2, 3])
        self.mock_config.get.assert_called_once_with(
            'execute', 'rea_channel', fallback=[1, 2])

    def test_get_rea_amp(self):
        '''
        测试 get_rea_amp 方法
        '''
        self.mock_config.get.return_value = '[0.2, 1.2]'
        result = self.qcos_config.get_rea_amp()
        # 断言结果是否符合预期
        self.assertEqual(result, [0.2, 1.2])
        self.mock_config.get.assert_called_once_with(
            'execute', 'rea_amp', fallback=[0.2, 1.2])

    @patch('os.path.dirname')
    def test_get_calib_img_path(self, mock_dirname):
        '''
        测试 get_calib_img_path 方法
        '''
        self.mock_config.get.return_value = 'calib_img.png'
        mock_dirname.return_value = ''
        # 调用被测试的方法
        result = self.qcos_config.get_calib_img_path()
        # 断言结果是否符合预期
        self.assertEqual(result, 'calib_img.png')
        self.mock_config.get.assert_called_once_with(
            'measure', 'calib_img_path', fallback='calib_img.png')

    @patch('os.path.dirname')
    def test_get_quantum_task_res_img_path(self, mock_dirname):
        '''
        测试 get_quantum_task_res_img_path 方法
        '''
        self.mock_config.get.return_value = 'quantum_task_res_img.png'
        mock_dirname.return_value = ''
        # 调用被测试的方法
        result = self.qcos_config.get_quantum_task_res_img_path()
        # 断言结果是否符合预期
        self.assertEqual(result, 'quantum_task_res_img.png')
        self.mock_config.get.assert_called_once_with(
            'measure',
            'quantum_task_res_img_path',
            fallback='quantum_task_res_img.png')

    def test_get_threshold(self):
        '''
        测试 get_threshold 方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 0
        result = self.qcos_config.get_measure_threshold()
        # 断言结果是否符合预期
        self.assertEqual(result, 0)
        self.mock_config.getint.assert_called_once_with(
            'measure', 'threshold', fallback=100)

    def test_get_threshold_block(self):
        '''
        测试 get_threshold_block 方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 0
        result = self.qcos_config.get_measure_threshold_block()
        # 断言结果是否符合预期
        self.assertEqual(result, 0)
        self.mock_config.getint.assert_called_once_with(
            'measure', 'threshold_block', fallback=3)

    def test_get_camera_dll_path(self):
        '''
        测试 get_camera_dll_path 方法
        '''
        self.mock_config.get.return_value = 'test_dll_path'
        fallback = ('D:/SourceCode/arclight/WuYueOs_Arclight/quantumOS/'
                    'camera_test/lib/x64/TUCam.dll')
        # 调用被测试的方法
        result = self.qcos_config.get_camera_dll_path()
        # 断言结果是否符合预期
        self.assertEqual(result, 'test_dll_path')
        self.mock_config.get.assert_called_once_with(
            'measure', 'dll_path', fallback=fallback)

    def test_get_init_path(self):
        '''
        测试 get_init_path 方法
        '''
        self.mock_config.get.return_value = 'test_init_path'
        fallback = ('D:/SourceCode/arclight/WuYueOs_Arclight/quantumOS/'
                    'camera_test/')
        # 调用被测试的方法
        result = self.qcos_config.get_camera_init_path()
        # 断言结果是否符合预期
        self.assertEqual(result, 'test_init_path')
        self.mock_config.get.assert_called_once_with(
            'measure', 'init_path', fallback=fallback)

    def test_get_exposure_time(self):
        '''
        测试 get_exposure_time方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 0
        result = self.qcos_config.get_exposure_time()
        # 断言结果是否符合预期
        self.assertEqual(result, 0)
        self.mock_config.getint.assert_called_once_with(
            'measure', 'exposure_time', fallback=50)

    def test_get_width_offset(self):
        '''
        测试 get_width_offset 方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 0
        result = self.qcos_config.get_width_offset()
        # 断言结果是否符合预期
        self.assertEqual(result, 0)
        self.mock_config.getint.assert_called_once_with(
            'measure', 'width_offset', fallback=840)

    def test_get_height_offset(self):
        '''
        测试 get_height_offset 方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 0
        result = self.qcos_config.get_height_offset()
        # 断言结果是否符合预期
        self.assertEqual(result, 0)
        self.mock_config.getint.assert_called_once_with(
            'measure', 'height_offset', fallback=865)

    def test_get_roi_width(self):
        '''
        测试 get_roi_width 方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 0
        result = self.qcos_config.get_roi_width()
        # 断言结果是否符合预期
        self.assertEqual(result, 0)
        self.mock_config.getint.assert_called_once_with(
            'measure', 'roi_width', fallback=232)

    def test_get_roi_height(self):
        '''
        测试 get_roi_height 方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 0
        result = self.qcos_config.get_roi_height()
        # 断言结果是否符合预期
        self.assertEqual(result, 0)
        self.mock_config.getint.assert_called_once_with(
            'measure', 'roi_height', fallback=232)

    def test_get_total_width(self):
        '''
        测试 get_total_width 方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 0
        result = self.qcos_config.get_total_width()
        # 断言结果是否符合预期
        self.assertEqual(result, 0)
        self.mock_config.getint.assert_called_once_with(
            'measure', 'total_width', fallback=2048)

    def test_get_total_height(self):
        '''
        测试 get_total_height 方法，能正常获取配置值
        '''
        self.mock_config.getint.return_value = 0
        result = self.qcos_config.get_total_height()
        # 断言结果是否符合预期
        self.assertEqual(result, 0)
        self.mock_config.getint.assert_called_once_with(
            'measure', 'total_height', fallback=2048)

    @patch('os.path.dirname')
    def test_get_qubo_images_path(self, mock_dirname):
        '''
        测试 get_qubo_images_path 方法
        '''
        # 设置模拟的返回值
        self.mock_config.get.return_value = 'test/qubo_images_path'
        mock_dirname.return_value = ''
        # 调用被测试的方法
        result = self.qcos_config.get_qubo_images_path()
        # 断言结果是否符合预期
        self.assertEqual(result, 'test/qubo_images_path')
        # 验证 get 方法是否被正确调用
        self.mock_config.get.assert_called_once_with(
            'ising',
            'qubo_images_path',
            fallback='ising_response_result/qubo_images')

    @patch('os.path.dirname')
    def test_get_zip_file_path(self, mock_dirname):
        '''
        测试 get_zip_file_path 方法
        '''
        # 设置模拟的返回值
        self.mock_config.get.return_value = 'test/zip_file_path'
        mock_dirname.return_value = ''
        # 调用被测试的方法
        result = self.qcos_config.get_zip_file_path()
        # 断言结果是否符合预期
        self.assertEqual(result, 'test/zip_file_path')
        # 验证 get 方法是否被正确调用
        self.mock_config.get.assert_called_once_with(
            'ising',
            'zip_file_path',
            fallback='ising_response_result/result_files')

    def test_get_ising_machine_ip(self):
        '''
        测试 get_ising_machine_ip 方法，能正常获取配置值
        '''
        self.mock_config.get.return_value = 'test_url'
        result = self.qcos_config.get_ising_machine_ip()
        # 断言结果是否符合预期
        self.assertEqual(result, 'test_url')
        self.mock_config.get.assert_called_once_with(
            'ising',
            'ising_machine_ip',
            fallback='http://127.0.0.1:8088')


if __name__ == '__main__':
    unittest.main()
