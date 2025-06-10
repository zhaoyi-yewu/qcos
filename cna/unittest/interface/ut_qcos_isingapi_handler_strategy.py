#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Bowen Zhang at 2024-12
# ------------------------


import unittest
import json
import os
from unittest.mock import patch, MagicMock, Mock
from qcos.interface.qcos_isingapi_handler_strategy import (
    IsingTaskType,
    IsingTaskBoardType,
    IsingHardwareMonitorType,
    IsingProjectType,
    IsingLogManagerType,
    IsingUserCenterType,
    IsingMachineInfoAndSelfTestType,
    IsingUserManageType,
    IsingRoleManageType,
    IsingRequestStrategy,
    IsingTaskStrategy,
    IsingTaskBoardStrategy,
    IsingHardwareMonitorStrategy,
    IsingProjectStrategy,
    IsingMachineInfoAndSelfTestStrategy,
    IsingUserCenterStrategy,
    IsingLogManagerStrategy,
    IsingUserManageStrategy,
    IsingRoleManageStrategy)
from qcos.log.qcos_log import QCOSLogger


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TestIsingTaskTypeEnum(unittest.TestCase):
    '''
    测试IsingTaskTypeEnum类。
    '''

    def test_enum_values(self):
        # 测试枚举值是否正确
        self.assertEqual(
            IsingTaskType.TERMINAL_MACHINE_TASK.value, 0)
        self.assertEqual(
            IsingTaskType.TERMINAL_TASK.value, 1)
        self.assertEqual(
            IsingTaskType.TERMINAL_MACHINE_TASK_INFO.value, 2)
        self.assertEqual(
            IsingTaskType.TERMINAL_TASK_INFO.value, 3)
        self.assertEqual(
            IsingTaskType.TERMINAL_MACHINE_TASK_DELETE.value, 4)
        self.assertEqual(
            IsingTaskType.TERMINAL_TASK_DELETE.value, 5)
        self.assertEqual(
            IsingTaskType.TERMINAL_UPLOAD_FILE.value, 6)
        self.assertEqual(
            IsingTaskType.TERMINAL_TASK_IMAGES.value, 7)
        self.assertEqual(
            IsingTaskType.TERMINAL_BATCH_TASK.value, 8)
        self.assertEqual(
            IsingTaskType.TERMINAL_BATCH_CHECK_TASK_NAME.value, 9)
        self.assertEqual(
            IsingTaskType.TERMINAL_DOWNLOAD_TASK.value, 10)
        self.assertEqual(
            IsingTaskType.TERMINAL_TASK_COMPUTE.value, 11)


class TestIsingTaskBoardTypeEnum(unittest.TestCase):
    '''
    测试IsingTaskBoardTypeEnum类。
    '''

    def test_enum_values(self):
        # 测试枚举值是否正确
        self.assertEqual(
            IsingTaskBoardType.TERMINAL_TASK_COUNT.value, 0)
        self.assertEqual(
            IsingTaskBoardType.TERMINAL_TASK_RATIO.value, 1)
        self.assertEqual(
            IsingTaskBoardType.TERMINAL_TASK_RATIO_SEARCH.value, 2)
        self.assertEqual(
            IsingTaskBoardType.TERMINAL_TASK_TREND.value, 3)
        self.assertEqual(
            IsingTaskBoardType.TERMINAL_TASK_TIMELINESS.value, 4)
        self.assertEqual(
            IsingTaskBoardType.TERMINAL_TASK_QUANTITY_NUM.value, 5)


class TestIsingHardwareMonitorTypeEnum(unittest.TestCase):
    '''
    测试IsingHardwareMonitorTypeEnum类。
    '''

    def test_enum_values(self):
        # 测试枚举值是否正确
        self.assertEqual(
            IsingHardwareMonitorType.HARDWARE_OPERATION_DAY.value, 0)
        self.assertEqual(
            IsingHardwareMonitorType.HARDWARE_RESOURCE_RATIO.value, 1)
        self.assertEqual(
            IsingHardwareMonitorType.HARDWARE_COUPLING_RESOURCE_RATIO.value, 2)
        self.assertEqual(
            IsingHardwareMonitorType.HARDWARE_DEVICE_TEMPERATURE.value, 3)
        self.assertEqual(
            IsingHardwareMonitorType.HARDWARE_DISK_MONITOR.value, 4)


class TestIsingProjectTypeEnum(unittest.TestCase):
    '''
    测试IsingProjectTypeEnum类。
    '''

    def test_enum_values(self):
        # 测试枚举值是否正确
        self.assertEqual(
            IsingProjectType.PROJECT_ALL_ENUM.value, 0)
        self.assertEqual(
            IsingProjectType.PROJECT_ENUM.value, 1)
        self.assertEqual(
            IsingProjectType.PROJECT_LIST.value, 2)
        self.assertEqual(
            IsingProjectType.PROJECT_CREATE.value, 3)
        self.assertEqual(
            IsingProjectType.PROJECT_EDIT.value, 4)
        self.assertEqual(
            IsingProjectType.PROJECT_DELETE.value, 5)


class TestIsingLogManagerTypeEnum(unittest.TestCase):
    '''
    测试IsingLogManagerTypeEnum类。
    '''

    def test_enum_values(self):
        # 测试枚举值是否正确
        self.assertEqual(
            IsingLogManagerType.LOG_LOGIN_LIST.value, 0)
        self.assertEqual(
            IsingLogManagerType.LOG_OPERATION_LIST.value, 1)
        self.assertEqual(
            IsingLogManagerType.LOG_OPERATION_INFO.value, 2)
        self.assertEqual(
            IsingLogManagerType.LOG_FAULT_LIST.value, 3)


class TestIsingUserCenterTypeEnum(unittest.TestCase):
    '''
    测试IsingUserCenterTypeEnum类。
    '''

    def test_enum_values(self):
        # 测试枚举值是否正确
        self.assertEqual(
            IsingUserCenterType.LOGIN.value, 0)
        self.assertEqual(
            IsingUserCenterType.USER_INFO.value, 1)
        self.assertEqual(
            IsingUserCenterType.USER_RESET_PASSWORD.value, 2)
        self.assertEqual(
            IsingUserCenterType.GET_FILE.value, 3)
        self.assertEqual(
            IsingUserCenterType.TASK_DATA.value, 4)


class TestIsingMachineInfoAndSelfTestTypeEnum(unittest.TestCase):
    '''
    测试IsingMachineInfoAndSelfTestTypeEnum类。
    '''

    def test_enum_values(self):
        # 测试枚举值是否正确
        self.assertEqual(
            IsingMachineInfoAndSelfTestType.SELF_TEST_INFO.value, 0)
        self.assertEqual(
            IsingMachineInfoAndSelfTestType.SELF_TEST_START.value, 1)
        self.assertEqual(
            IsingMachineInfoAndSelfTestType.MACHINE_INFO.value, 2)


class TestIsingUserManageType(unittest.TestCase):
    '''
    测试IsingUserManageType类。
    '''

    def test_enum_values(self):
        # 测试枚举值是否正确
        self.assertEqual(
            IsingUserManageType.USER_LIST.value, 0)
        self.assertEqual(
            IsingUserManageType.ADD_USER.value, 1)
        self.assertEqual(
            IsingUserManageType.RESET_PASSWORD.value, 2)
        self.assertEqual(
            IsingUserManageType.EDIT_USER.value, 3)
        self.assertEqual(
            IsingUserManageType.DELETE_USER.value, 4)


class TestIsingRoleManageType(unittest.TestCase):
    '''
    测试IsingRoleManageType类。
    '''

    def test_enum_values(self):
        # 测试枚举值是否正确
        self.assertEqual(
            IsingRoleManageType.ROLE_LIST.value, 0)
        self.assertEqual(
            IsingRoleManageType.ADD_ROLE.value, 1)
        self.assertEqual(
            IsingRoleManageType.DELETE_ROLE.value, 2)
        self.assertEqual(
            IsingRoleManageType.EDIT_ROLE.value, 3)
        self.assertEqual(
            IsingRoleManageType.MODIFY_ROLE_PERMISSION.value, 4)


class TestIsingRequestStrategy(unittest.TestCase):
    '''
    测试IsingRequestStrategy策略类。
    '''

    def test_execute(self):
        '''
        测试基类IsingRequestStrategy的执行
        '''

        strategy = IsingRequestStrategy()
        strategy_type = 'test_strategy_type'
        url = 'http://example.com'

        with self.assertRaises(NotImplementedError) as context:
            strategy.execute(strategy_type, url)

        # 检查异常消息是否正确
        self.assertEqual(
            str(context.exception),
            'Each strategy must implement an execute method')


class TestIsingTaskStrategy(unittest.TestCase):
    '''
    测试IsingTaskStrategy策略类。
    '''

    def setUp(self):
        self.ising_task_strategy = IsingTaskStrategy()

    @patch.object(IsingTaskStrategy, 'get_machine_task')
    @patch.object(IsingTaskStrategy, 'get_task')
    @patch.object(IsingTaskStrategy, 'get_machine_task_info')
    @patch.object(IsingTaskStrategy, 'get_task_info')
    @patch.object(IsingTaskStrategy, 'delete_machine_task')
    @patch.object(IsingTaskStrategy, 'delete_task')
    @patch.object(IsingTaskStrategy, 'post_upload_file')
    @patch.object(IsingTaskStrategy, 'get_task_images')
    @patch.object(IsingTaskStrategy, 'post_batch_task')
    @patch.object(IsingTaskStrategy, 'get_batch_check_task_name')
    @patch.object(IsingTaskStrategy, 'get_download_task')
    @patch.object(IsingTaskStrategy, 'task_compute')
    def test_execute_with_task_type(
            self,
            mock_task_compute,
            mock_get_download_task,
            mock_get_batch_check_task_name,
            mock_post_batch_task,
            mock_get_task_images,
            mock_post_upload_file,
            mock_delete_task,
            mock_delete_machine_task,
            mock_get_task_info,
            mock_get_machine_task_info,
            mock_get_task,
            mock_get_machine_task):
        '''
        测试基类IsingTaskStrategy的执行
        '''

        url = 'http://example.com'
        data = {'key': 'value'}

        # 测试不同的任务类型
        for _, task_type in IsingTaskType.__members__.items():
            self.ising_task_strategy.execute(task_type.value, url, data)

        # 验证每个任务类型是否调用了正确的方法
        mock_get_machine_task.assert_called_once_with(url, data)
        mock_get_task.assert_called_once_with(url, data)
        mock_get_machine_task_info.assert_called_once_with(url, data)
        mock_get_task_info.assert_called_once_with(url, data)
        mock_delete_machine_task.assert_called_once_with(url, data)
        mock_delete_task.assert_called_once_with(url, data)
        mock_post_upload_file.assert_called_once_with(url, data)
        mock_get_task_images.assert_called_once_with(url, data)
        mock_post_batch_task.assert_called_once_with(url, data)
        mock_get_batch_check_task_name.assert_called_once_with(url, data)
        mock_get_download_task.assert_called_once_with(url, data)
        mock_task_compute.assert_called_once_with(url, data)

    def test_execute_unknown_task_type(self):
        # 测试未知的任务类型
        with self.assertRaises(ValueError):
            self.ising_task_strategy.execute(
                'unknown_type', 'http://example.com', {'key': 'value'})

    @patch('requests.get')
    def test_get_machine_task_with_data(self, mock_get):
        '''
        测试给定data时成功的get_machine_task请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'page': '1',
                'size': '10',
                'task_name': 'test_task_name'
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_strategy.get_machine_task(url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/machine-task/?'
                      'page=1&size=10&task_name=test_task_name',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_machine_task_without_data(self, mock_get):
        '''
        测试data为None时失败的get_machine_task请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_strategy.get_machine_task(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_task_with_data(self, mock_get):
        '''
        测试给定data时成功的get_task请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'task_id': '1',
                'username': 'test_name',
                'status': '1',
                'project': '1',
                'ordering': '-create_datetime',
                'page': '1',
                'size': '10',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_strategy.get_task(url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/task/?task_id=1&username=test_name&'
                      'status=1&project=1&ordering=-create_datetime'
            '&page=1&size=10',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_task_without_data(self, mock_get):
        '''
        测试data为None时失败的get_task请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_strategy.get_task(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_machine_task_info(self, mock_get):
        '''
        测试给定data时成功的get_machine_task_info请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'task_id': '1',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_strategy.get_machine_task_info(url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/machine-task/1/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.get')
    def test_get_machine_task_info_without_data(self, mock_get):
        '''
        测试data为None时失败的get_machine_task_info请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_strategy.get_machine_task_info(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_task_info(self, mock_get):
        '''
        测试给定data时成功的get_task_info请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'task_id': '1',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_strategy.get_task_info(url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/task/1/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.get')
    def test_get_task_info_without_data(self, mock_get):
        '''
        测试data为None时失败的get_task_info请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_strategy.get_task_info(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.delete')
    def test_delete_machine_task(self, mock_delete):
        '''
        测试给定data时成功的delete_machine_task请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'task_id': '1',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_strategy.delete_machine_task(url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_delete.assert_called_once_with(
            url=url + '/kdev/terminal/machine-task/1/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.delete')
    def test_delete_machine_task_without_data(self, mock_delete):
        '''
        测试data为None时失败的delete_machine_task请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_strategy.delete_machine_task(url)

        # 验证调用
        mock_delete.assert_not_called()

    @patch('requests.delete')
    def test_delete_task(self, mock_delete):
        '''
        测试给定data时成功的delete_task请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'task_id': '1',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_strategy.delete_task(url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_delete.assert_called_once_with(
            url=url + '/kdev/terminal/task/1/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.delete')
    def test_delete_task_without_data(self, mock_delete):
        '''
        测试data为None时失败的delete_task请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_strategy.delete_task(url)

        # 验证调用
        mock_delete.assert_not_called()

    @patch('requests.post')
    def test_post_upload_file_with_data(self, mock_post):
        '''
        测试给定data时成功的post_upload_file请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'matrix': [[-1, 1, 1],
                           [-1, 1, 1],
                           [-1, 1, 1]]
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_strategy.post_upload_file(url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_post_upload_file_without_data(self, mock_post):
        '''
        测试data为None时失败的post_upload_file请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_strategy.post_upload_file(url)

        # 验证调用
        mock_post.assert_not_called()

    @patch('requests.get')
    def test_get_task_images_with_data(self, mock_get):
        '''
        测试给定data时成功的get_task_images请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'task_id': '1',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = (b'PK\x03\x04\x14\x00\x00'
                                 b'\x00\x08\x00\x00\x00\x00\x00')
        mock_get.return_value = mock_response

        # 调用函数
        result = self.ising_task_strategy.get_task_images(url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/task-images/1/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )
        # 获取当前脚本在系统中的绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建目标文件在系统中的绝对路径，并标准化路径表达
        test_image_path = os.path.join(
            script_dir,
            '../../ising_response_result/qubo_images/result_qubo_image1.png')
        test_image_path = os.path.normpath(test_image_path)
        self.assertTrue(os.path.exists(test_image_path))
        # 删除生成的图片文件
        if os.path.exists(test_image_path):
            os.remove(test_image_path)

    @patch('requests.get')
    def test_get_task_images_without_data(self, mock_get):
        '''
        测试data为None时失败的get_task_images请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_strategy.get_task_images(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.post')
    def test_post_batch_task_with_data(self, mock_post):
        '''
        测试给定data时成功的post_batch_task请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'data': 'test_ising_data',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_strategy.post_batch_task(url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_post.assert_called_once_with(
            url=url + '/kdev/terminal/batch-task/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            },
            json='test_ising_data'
        )

    @patch('requests.post')
    def test_post_batch_task_without_data(self, mock_post):
        '''
        测试data为None时失败的post_batch_task请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_strategy.post_batch_task(url)

        # 验证调用
        mock_post.assert_not_called()

    @patch('requests.get')
    def test_get_batch_check_task_name_with_data(self, mock_get):
        '''
        测试给定data时成功的get_batch_check_task_name请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'task_names': 'test_ising_task_name',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_strategy.get_batch_check_task_name(
            url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/batch-check-task-name/?'
                      'task_names=test_ising_task_name',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_batch_check_task_name_without_data(self, mock_get):
        '''
        测试data为None时失败的get_batch_check_task_name请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_strategy.get_batch_check_task_name(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_download_task_with_data(self, mock_get):
        '''
        测试给定data时成功的get_download_task请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'type': 'test_ising_type',
                'ids': 'test_ising_ids',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'PK\x03\x04\x14\x00\x00\x00\x08'
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_strategy.get_download_task(url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/download-task/?'
                      'type=test_ising_type&ids=test_ising_ids',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

        # 验证并删除生成的zip文件
        from datetime import datetime
        current_time = datetime.now()
        # 获取当前脚本在系统中的绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建目标文件在系统中的绝对路径，并标准化路径表达
        file_name = os.path.join(
            script_dir,
            '../../ising_response_result/result_files',
            f'downloaded_file{
                current_time.strftime('%y%m%d%H%M%S')}.zip')
        file_name = os.path.normpath(file_name)
        self.assertTrue(os.path.exists(file_name))
        if os.path.exists(file_name):
            os.remove(file_name)

    @patch('requests.get')
    def test_get_download_task_without_data(self, mock_get):
        '''
        测试data为None时失败的get_download_task请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_strategy.get_download_task(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('qcos.interface.qcos_isingapi_handler_strategy.'
           'IsingTaskStrategy.post_upload_file')
    @patch('qcos.interface.qcos_isingapi_handler_strategy.'
           'IsingTaskStrategy.post_batch_task')
    @patch('qcos.interface.qcos_isingapi_handler_strategy.'
           'IsingTaskStrategy.get_machine_task')
    @patch('qcos.interface.qcos_isingapi_handler_strategy.'
           'IsingTaskStrategy.get_download_task')
    def test_task_compute_with_data(
            self,
            mock_get_download_task,
            mock_get_machine_task,
            mock_post_batch_task,
            mock_post_upload_file):
        '''
        测试给定data时成功的task_compute请求
        '''

        # 模拟 post_upload_file 的返回值
        upload_response_data = {
            'data': {
                'id': '123',
                'name': 'test_csv_name',
                'creator': 'test_user_id'
            }
        }
        mock_post_upload_file.return_value = (200, upload_response_data)
        # 模拟 post_batch_task 的返回值
        mock_post_batch_task.return_value = (
            200, {'message': 'test_batch_task'})
        # 模拟 get_machine_task_info 的返回值
        mock_get_machine_task.return_value = (200, {
            'data': {
                'data': [
                    {
                        'id': 1,
                        'task_id': 'test_id',
                        'task_name': 'test_name',
                    }
                ]
            }
        })
        # 模拟 get_download_task 的返回值
        mock_get_download_task.return_value = (200, 'path/to/result.csv')

        url = 'http://example.com'
        data = {
            'query_params': {
                'priority': 0,
                'machine_id': 1,
                'task_name': 'test_name',
                'estimated_datetime': 'test_datetime',
                'expected_description': 'test_description',
                'project_id': 1,
                'page': 1,
                'size': 10,
                'type': 'test_type'
            }
        }

        # 调用函数
        result = self.ising_task_strategy.task_compute(url, data)

        # 验证调用
        self.assertEqual(result, 'path/to/result.csv')

        mock_post_upload_file.assert_called_once_with(url, data)
        mock_post_batch_task.assert_called_once()
        mock_get_machine_task.assert_called_once_with(
            url,
            {
                'query_params': {
                    'data': {
                        'page': 1,
                        'size': 10,
                        'task_name': 'test_name'
                    }
                }
            }
        )
        mock_get_download_task.assert_called()


class TestIsingTaskBoardStrategy(unittest.TestCase):
    '''
    测试IsingTaskBoardStrategy策略类。
    '''

    def setUp(self):
        self.ising_task_board_strategy = IsingTaskBoardStrategy()

    @patch.object(IsingTaskBoardStrategy, 'get_task_count')
    @patch.object(IsingTaskBoardStrategy, 'get_task_ratio')
    @patch.object(IsingTaskBoardStrategy, 'get_task_ratio_search')
    @patch.object(IsingTaskBoardStrategy, 'get_task_trend')
    @patch.object(IsingTaskBoardStrategy, 'get_task_timeliness')
    @patch.object(IsingTaskBoardStrategy, 'get_task_quantity_num')
    def test_execute_with_task_type(
            self,
            mock_get_task_quantity_num,
            mock_get_task_timeliness,
            mock_get_task_trend,
            mock_get_task_ratio_search,
            mock_get_task_ratio,
            mock_get_task_count):
        '''
        测试基类IsingTaskBoardStrategy的执行
        '''

        url = 'http://example.com'
        data = {'key': 'value'}

        # 测试不同的任务类型
        for _, task_type in IsingTaskBoardType.__members__.items():
            self.ising_task_board_strategy.execute(task_type.value, url, data)

            # 验证每个任务类型是否调用了正确的方法
        mock_get_task_count.assert_called_once_with(url, data)
        mock_get_task_ratio.assert_called_once_with(url, data)
        mock_get_task_ratio_search.assert_called_once_with(url, data)
        mock_get_task_trend.assert_called_once_with(url, data)
        mock_get_task_timeliness.assert_called_once_with(url, data)
        mock_get_task_quantity_num.assert_called_once_with(url, data)

    def test_execute_unknown_task_type(self):
        # 测试未知的任务类型
        with self.assertRaises(ValueError):
            self.ising_task_board_strategy.execute(
                'unknown_type',
                'http://example.com',
                {'key': 'value'})

    @patch('requests.get')
    def test_get_task_count(self, mock_get):
        '''
        测试get_task_count请求
        '''

        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_board_strategy.get_task_count(url)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/task-count/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.get')
    def test_get_task_ratio(self, mock_get):
        '''
        测试get_task_ratio请求
        '''

        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_board_strategy.get_task_ratio(url)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/task-ratio/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.get')
    def test_get_task_ratio_search_with_data(self, mock_get):
        '''
        测试给定data时成功的get_task_ratio_search请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'project_ids': '1',
                'start_date': 'start_time',
                'end_date': 'end_time',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_board_strategy.get_task_ratio_search(
            url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/task-ratio-search/?project_ids=1&'
                      'start_date=start_time&end_date=end_time',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_task_ratio_search_without_data(self, mock_get):
        '''
        测试data为None时失败的get_task_ratio_search请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_board_strategy.get_task_ratio_search(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_task_trend_with_data(self, mock_get):
        '''
        测试给定data时成功的get_task_trend请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'project_ids': '1',
                'start_date': 'start_time',
                'end_date': 'end_time',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_board_strategy.get_task_trend(url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/task-trend/?project_ids=1&'
                      'start_date=start_time&end_date=end_time',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_task_trend_without_data(self, mock_get):
        '''
        测试data为None时失败的get_task_trend请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_board_strategy.get_task_trend(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_task_timeliness_with_data(self, mock_get):
        '''
        测试给定data时成功的get_task_timeliness请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'project_ids': '1',
                'start_date': 'start_time',
                'end_date': 'end_time',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_board_strategy.get_task_timeliness(
            url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/task-timeliness/?project_ids=1&'
                      'start_date=start_time&end_date=end_time',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_task_timeliness_without_data(self, mock_get):
        '''
        测试data为None时失败的get_task_timeliness请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_board_strategy.get_task_timeliness(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_task_quantity_num_with_data(self, mock_get):
        '''
        测试给定data时成功的get_task_quantity_num请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'project_ids': '1',
                'start_date': 'start_time',
                'end_date': 'end_time',
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_task_board_strategy.get_task_quantity_num(
            url, data)

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/task-quantity-num/?project_ids=1&'
                      'start_date=start_time&end_date=end_time',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_task_quantity_num_without_data(self, mock_get):
        '''
        测试data为None时失败的get_task_quantity_num请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_task_board_strategy.get_task_quantity_num(url)

        # 验证调用
        mock_get.assert_not_called()


class TestIsingHardwareMonitorStrategy(unittest.TestCase):
    '''
    测试IsingHardwareMonitorStrategy策略类。
    '''

    def setUp(self):
        self.ising_hardware_monitor_strategy = IsingHardwareMonitorStrategy()

    @patch.object(IsingHardwareMonitorStrategy, 'get_operation_day')
    @patch.object(IsingHardwareMonitorStrategy, 'get_resource_ratio')
    @patch.object(IsingHardwareMonitorStrategy, 'get_coupling_resource_ratio')
    @patch.object(IsingHardwareMonitorStrategy, 'get_device_temperature')
    @patch.object(IsingHardwareMonitorStrategy, 'get_disk_monitor')
    def test_execute_with_task_type(
            self,
            mock_get_resource_ratio,
            mock_get_operation_day,
            mock_get_coupling_resource_ratio,
            mock_get_device_temperature,
            mock_get_disk_monitor):
        '''
        测试基类IsingTaskBoardStrategy的执行
        '''

        url = 'http://example.com'
        data = {'key': 'value'}

        # 测试不同的任务类型
        for _, task_type in IsingHardwareMonitorType.__members__.items():
            self.ising_hardware_monitor_strategy.execute(
                task_type.value, url, data)

            # 验证每个任务类型是否调用了正确的方法
        mock_get_operation_day.assert_called_once_with(url, data)
        mock_get_resource_ratio.assert_called_once_with(url, data)
        mock_get_coupling_resource_ratio.assert_called_once_with(url, data)
        mock_get_device_temperature.assert_called_once_with(url, data)
        mock_get_disk_monitor.assert_called_once_with(url, data)

    def test_execute_unknown_task_type(self):
        # 测试未知的任务类型
        with self.assertRaises(ValueError):
            self.ising_hardware_monitor_strategy.execute(
                'unknown_type',
                'http://example.com',
                {'key': 'value'})

    @patch('requests.get')
    def test_get_operation_day_with_data(self, mock_get):
        '''
        测试给定data时成功的get_operation_day请求
        '''

        mock_get.return_value.status_code = 200
        url = 'http://example.com'
        data = {
            'query_params': {
                'start_date': 'start_time',
                'end_date': 'end_time'
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_hardware_monitor_strategy.get_operation_day(
            url, data)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/monitoring-num-data/?'
                      'start_date=start_time&end_date=end_time',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_operation_day_without_data(self, mock_get):
        '''
        测试data为None时失败的get_operation_day请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_hardware_monitor_strategy.get_operation_day(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_resource_ratio_with_data(self, mock_get):
        '''
        测试给定data时成功的get_resource_ratio请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'start_date': 'start_time',
                'end_date': 'end_time'
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_hardware_monitor_strategy.get_resource_ratio(
            url, data)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/monitoring-bit-data/?'
                      'start_date=start_time&end_date=end_time',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_resource_ratio_without_data(self, mock_get):
        '''
        测试data为None时失败的get_resource_ratio请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_hardware_monitor_strategy.get_resource_ratio(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_coupling_resource_ratio_with_data(self, mock_get):
        '''
        测试给定data时成功的get_coupling_resource_ratio请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'start_date': 'start_time',
                'end_date': 'end_time'
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_hardware_monitor_strategy.\
            get_coupling_resource_ratio(url, data)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/monitoring-resources-data/?'
                      'start_date=start_time&end_date=end_time',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_coupling_resource_ratio_without_data(self, mock_get):
        '''
        测试data为None时失败的get_coupling_resource_ratio请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_hardware_monitor_strategy.get_coupling_resource_ratio(
                url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_device_temperature(self, mock_get):
        '''
        测试get_device_temperature请求
        '''

        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_hardware_monitor_strategy.\
            get_device_temperature(url)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/monitoring-temperature-data',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.get')
    def test_get_disk_monitor(self, mock_get):
        '''
        测试get_disk_monitor请求
        '''

        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_hardware_monitor_strategy.get_disk_monitor(url)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/monitoring-metrics',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )


class TestIsingProjectStrategy(unittest.TestCase):
    '''
    测试IsingProjectStrategy策略类。
    '''

    def setUp(self):
        self.ising_project_strategy = IsingProjectStrategy()

    @patch.object(IsingProjectStrategy, 'get_project_all_enum')
    @patch.object(IsingProjectStrategy, 'get_project_enum')
    @patch.object(IsingProjectStrategy, 'get_project_list')
    @patch.object(IsingProjectStrategy, 'post_project_create')
    @patch.object(IsingProjectStrategy, 'put_project_edit')
    @patch.object(IsingProjectStrategy, 'delete_project_personal')
    def test_execute_with_task_type(
            self,
            mock_delete_project_personal,
            mock_put_project_edit,
            mock_post_project_create,
            mock_get_project_list,
            mock_get_project_enum,
            mock_get_project_all_enum):
        '''
        测试基类IsingProjectStrategy的执行
        '''

        url = 'http://example.com'
        data = {'key': 'value'}

        # 测试不同的任务类型
        for _, task_type in IsingProjectType.__members__.items():
            self.ising_project_strategy.execute(task_type.value, url, data)

            # 验证每个任务类型是否调用了正确的方法
        mock_get_project_all_enum.assert_called_once_with(url, data)
        mock_get_project_enum.assert_called_once_with(url, data)
        mock_get_project_list.assert_called_once_with(url, data)
        mock_post_project_create.assert_called_once_with(url, data)
        mock_put_project_edit.assert_called_once_with(url, data)
        mock_delete_project_personal.assert_called_once_with(url, data)

    def test_execute_unknown_task_type(self):
        # 测试未知的任务类型
        with self.assertRaises(ValueError):
            self.ising_project_strategy.execute(
                'unknown_type',
                'http://example.com',
                {'key': 'value'})

    @patch('requests.get')
    def test_get_project_all_enum(self, mock_get):
        '''
        测试get_project_all_enum请求
        '''

        mock_get.return_value.status_code = 200
        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_project_strategy.get_project_all_enum(url)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/project-all-list/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.get')
    def test_get_project_enum(self, mock_get):
        '''
        测试get_project_enum请求
        '''

        mock_get.return_value.status_code = 200
        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_project_strategy.get_project_enum(url)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/project-list/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.get')
    def test_get_project_list_with_data(self, mock_get):
        '''
        测试给定data时成功的get_project_list请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'project_name': 'test_project_name',
                'page': 1,
                'size': 10
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_project_strategy.get_project_list(url, data)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/project/?'
                      'project_name=test_project_name&page=1&size=10',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_project_list_without_data(self, mock_get):
        '''
        测试data为None时失败的get_project_list请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_project_strategy.get_project_list(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.post')
    def test_post_project_create_with_data(self, mock_post):
        '''
        测试给定data时成功的post_project_create请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'data': {
                    'body_data': 'test_body_data'
                }
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 调用函数
        result, _ = self.ising_project_strategy.post_project_create(url, data)
        mock_post.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_post.assert_called_once_with(
            url=url + '/kdev/terminal/project/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            },
            json={
                'body_data': 'test_body_data'
            }
        )

    @patch('requests.post')
    def test_post_project_create_without_data(self, mock_post):
        '''
        测试data为None时失败的post_project_create请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_project_strategy.post_project_create(url)

        # 验证调用
        mock_post.assert_not_called()

    @patch('requests.put')
    def test_put_project_edit_with_data(self, mock_put):
        '''
        测试给定data时成功的put_project_edit请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'project_id': 1,
                'data': {
                    'body_data': 'test_body_data'
                }
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response

        # 调用函数
        result, _ = self.ising_project_strategy.put_project_edit(url, data)
        mock_put.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_put.assert_called_once_with(
            url=url + '/kdev/terminal/project/1/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            },
            json={
                'body_data': 'test_body_data'
            }
        )

    @patch('requests.put')
    def test_put_project_edit_without_data(self, mock_put):
        '''
        测试data为None时失败的put_project_edit请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_project_strategy.put_project_edit(url)

        # 验证调用
        mock_put.assert_not_called()

    @patch('requests.delete')
    def test_delete_project_personal_with_data(self, mock_delete):
        '''
        测试给定data时成功的delete_project_personal请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'project_id': 1
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response

        # 调用函数
        result, _ = self.ising_project_strategy.delete_project_personal(
            url, data)
        mock_delete.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_delete.assert_called_once_with(
            url=url + '/kdev/terminal/project/1/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.delete')
    def test_delete_project_personal_without_data(self, mock_delete):
        '''
        测试data为None时失败的delete_project_personal请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_project_strategy.delete_project_personal(url)

        # 验证调用
        mock_delete.assert_not_called()


class TestIsingLogManagerStrategy(unittest.TestCase):
    '''
    测试IsingLogManagerStrategy策略类。
    '''

    def setUp(self):
        self.ising_log_manager_strategy = IsingLogManagerStrategy()

    @patch.object(IsingLogManagerStrategy, 'get_log_login_list')
    @patch.object(IsingLogManagerStrategy, 'get_log_operation_list')
    @patch.object(IsingLogManagerStrategy, 'get_log_operation_info')
    @patch.object(IsingLogManagerStrategy, 'get_log_fault_list')
    def test_execute_with_task_type(
            self,
            mock_get_log_fault_list,
            mock_get_log_operation_info,
            mock_get_log_operation_list,
            mock_get_log_login_list):
        '''
        测试基类IsingProjectStrategy的执行
        '''

        url = 'http://example.com'
        data = {'key': 'value'}

        # 测试不同的任务类型
        for _, task_type in IsingLogManagerType.__members__.items():
            self.ising_log_manager_strategy.execute(
                task_type.value,
                url,
                data)

            # 验证每个任务类型是否调用了正确的方法
        mock_get_log_fault_list.assert_called_once_with(url, data)
        mock_get_log_operation_info.assert_called_once_with(url, data)
        mock_get_log_operation_list.assert_called_once_with(url, data)
        mock_get_log_login_list.assert_called_once_with(url, data)

    def test_execute_unknown_task_type(self):
        # 测试未知的任务类型
        with self.assertRaises(ValueError):
            self.ising_log_manager_strategy.execute(
                'unknown_type',
                'http://example.com',
                {'key': 'value'})

    @patch('requests.get')
    def test_get_log_login_list_with_data(self, mock_get):
        '''
        测试给定data时成功的get_log_login_list请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'username': 'test_username',
                'id': 1,
                'ip': 'http://test_ip',
                'page': 1,
                'size': 10
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_log_manager_strategy.get_log_login_list(
            url, data)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/login-log/?username=test_username&'
                      'id=1&ip=http://test_ip&page=1&size=10',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_project_list_without_data(self, mock_get):
        '''
        测试data为None时失败的get_project_list请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_log_manager_strategy.get_log_login_list(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_log_operation_list_with_data(self, mock_get):
        '''
        测试给定data时成功的get_log_operation_list请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'request_modular': 'test_request_modular',
                'request_path': 'test_request_path',
                'request_ip': 'http://test_ip',
                'request_method': 'test_request_method',
                'page': 1,
                'size': 10
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_log_manager_strategy.get_log_operation_list(
            url, data)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/operation-log/?request_modular='
                      'test_request_modular&request_path=test_request_path'
                      '&request_ip=http://test_ip&request_method='
                      'test_request_method&page=1&size=10',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_log_operation_list_without_data(self, mock_get):
        '''
        测试data为None时失败的get_log_operation_list请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_log_manager_strategy.get_log_operation_list(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_log_operation_info_with_data(self, mock_get):
        '''
        测试给定data时成功的get_log_operation_info请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'log_id': 1
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_log_manager_strategy.get_log_operation_info(
            url, data)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/operation-log/1/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.get')
    def test_get_log_operation_info_without_data(self, mock_get):
        '''
        测试data为None时失败的get_log_operation_info请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_log_manager_strategy.get_log_operation_info(url)

        # 验证调用
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_get_log_fault_list_with_data(self, mock_get):
        '''
        测试给定data时成功的get_log_fault_list请求
        '''

        url = 'http://example.com'
        data = {
            'query_params': {
                'faultNumber': 'test_faultNumber',
                'faultStatus': 2,  # 0：所有状态，1：故障中，2：修复中，3：已修复
                'ordering': 1,  # 1：故障发生时间降序，2：故障发生时间升序，3：修复完成时间降序，4：修复完成时间升序
                'page': 1,
                'size': 10
            }
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用函数
        result, _ = self.ising_log_manager_strategy.get_log_fault_list(
            url, data)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/fault-list/?faultNumber=test_faultNumber'
                      '&faultStatus=2&ordering=1&page=1&size=10',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})

    @patch('requests.get')
    def test_get_log_fault_list_without_data(self, mock_get):
        '''
        测试data为None时失败的get_log_fault_list请求
        '''

        url = 'http://example.com'

        # 调用函数
        with self.assertRaises(ValueError):
            self.ising_log_manager_strategy.get_log_fault_list(url)

        # 验证调用
        mock_get.assert_not_called()


class TestIsingUserCenterStrategy(unittest.TestCase):
    '''
    测试IsingUserCenterStrategy策略类。
    '''

    def setUp(self):
        self.ising_user_center_strategy = IsingUserCenterStrategy()

    @patch('requests.post')
    def test_post_login(self, mock_post):
        '''
        测试用户登陆
        '''

        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        data = {
            'post_body': {
                'username': 'userA',
                'pwd': 'passwordA'
            }
        }

        result, _ = self.ising_user_center_strategy.post_login(url, data=data)
        mock_post.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_post.assert_called_once_with(
            url=url + '/kdev/terminal/login/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
            },
            json={'username': 'userA', 'pwd': 'passwordA'}
        )

    @patch('requests.get')
    def test_get_user_info(self, mock_get):
        '''
        测试获取用户信息
        '''

        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result, _ = self.ising_user_center_strategy.get_user_info(url)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/user-info/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.post')
    def test_post_user_reset_password(self, mock_post):
        '''
        测试重置用户密码
        '''

        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        data = {
            'post_body': {
                'old_pwd': 'old',
                'pwd': 'new',
                'confirm_pwd': 'new'
            }
        }

        result, _ = self.ising_user_center_strategy.post_user_reset_password(
            url, data=data)
        mock_post.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_post.assert_called_once_with(
            url=url + '/kdev/terminal/user/user-reset-password/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            },
            json={'old_pwd': 'old', 'pwd': 'new', 'confirm_pwd': 'new'}
        )

    @patch('requests.get')
    def test_get_file(self, mock_get):
        '''
        测试获取静态资源--用于升级玻色客户端，无意义的接口，后续删除
        '''

        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        data = {
            'path_params': ['latest.yml']
        }
        result, _ = self.ising_user_center_strategy.get_file(url, data)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/get-file/latest.yml',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.get')
    def test_get_task_data(self, mock_get):
        '''
        测试用量总览
        '''

        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        data = {
            'query_params': {
                'project_ids': '1,2,3',
                'start_date': '2025-02-06+00:00:00',
                'end_date': '2025-02-12+23:59:59'
            }
        }

        result, _ = self.ising_user_center_strategy.get_task_data(
            url, data=data)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/task-data?project_ids=1,2,3&start_date'
                      '=2025-02-06+00:00:00&end_date=2025-02-12+23:59:59',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})


class TestIsingMachineInfoAndSelfTestStrategy(unittest.TestCase):
    '''
    测试IsingMachineInfoAndSelfTestStrategy策略类。
    '''

    def setUp(self):
        self.ising_machine_info_and_self_test_strategy = (
            IsingMachineInfoAndSelfTestStrategy())

    @patch('requests.get')
    def test_get_self_test_info(self, mock_get):
        '''
        测试获取系统自检信息
        '''

        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result, _ = self.ising_machine_info_and_self_test_strategy.\
            get_self_test_info(url)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/self-test/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.post')
    def test_post_self_test_start(self, mock_post):
        '''
        测试开始系统自检
        '''

        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result, _ = self.ising_machine_info_and_self_test_strategy.\
            post_self_test_start(url)
        mock_post.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_post.assert_called_once_with(
            url=url + '/kdev/terminal/self-test/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )

    @patch('requests.get')
    def test_get_machine_info(self, mock_get):
        '''
        测试获取真机信息
        '''

        url = 'http://example.com'

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        data = {'query_params': {
            'machine_id': 1
        }}

        result, _ = self.ising_machine_info_and_self_test_strategy.\
            get_machine_info(url, data=data)
        mock_get.assert_called_once()

        # 验证调用
        self.assertEqual(result, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/machine?machine_id=1',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )


class TestIsingUserManageStrategy(unittest.TestCase):
    '''
    测试 IsingUserManageStrategy 策略类。
    '''

    def setUp(self):
        '''
        实例化 IsingUserManageStrategy 类
        '''

        self.ising_user_manage_strategy = IsingUserManageStrategy()

    @patch.object(IsingUserManageStrategy, 'delete_user')
    @patch.object(IsingUserManageStrategy, 'put_edit_user')
    @patch.object(IsingUserManageStrategy, 'post_reset_password')
    @patch.object(IsingUserManageStrategy, 'post_add_user')
    @patch.object(IsingUserManageStrategy, 'get_user_list')
    def test_execute(
            self,
            mock_get_user_list,
            mock_post_add_user,
            mock_post_reset_password,
            mock_put_edit_user,
            mock_delete_user):
        '''
        测试 IsingUserManageStrategy 中具体请求策略的执行
        '''

        # 准备参数，并调用函数进行测试
        url = Mock
        data = Mock
        for _, strategy_type in IsingUserManageType.__members__.items():
            self.ising_user_manage_strategy.execute(
                strategy_type.value, url, data)
        # 验证每个任务类型是否被成功调用
        mock_get_user_list.assert_called_once_with(url, data)
        mock_post_add_user.assert_called_once_with(url, data)
        mock_post_reset_password.assert_called_once_with(url, data)
        mock_put_edit_user.assert_called_once_with(url, data)
        mock_delete_user.assert_called_once_with(url, data)

        # 测试错误策略类型并验证输出结果
        try:
            self.ising_user_manage_strategy.execute(
                'unknow_type',
                url,
                data)
        except ValueError as e:
            assert e.args[0] == '未知的任务策略类型!'

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('requests.get')
    def test_get_user_list(self, mock_get, mock_info):
        '''
        测试 get_user_list 获取用户列表
        '''

        # 准备参数
        url = 'http://example.com'
        data = {
            'query_params': {
                'username': 'mock_user_name',
                'is_active': 'true',
                'ordering': '-create_datetime',
                'page': 1,
                'size': 10
            }
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用 get_user_list 方法
        status_code, _ = self.ising_user_manage_strategy.get_user_list(
            url, data)

        # 验证调用
        self.assertEqual(status_code, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/user/?username=mock_user_name&'
                      'is_active=true&ordering=-create_datetime'
            '&page=1&size=10',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})
        mock_info.assert_called_once_with(
            '[interface: qcos_isingapi_handler] 获取用户列表请求返回：200')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('requests.post')
    def test_post_add_user(self, mock_post, mock_info):
        '''
        测试 post_add_user 新增用户
        '''

        # 准备参数
        url = 'http://example.com'
        data = {
            'query_params': {
                'data': {
                    'mock_param': 'mock_data'
                }
            }
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 调用 post_add_user 方法
        status_code, _ = self.ising_user_manage_strategy.post_add_user(
            url, data)

        # 验证调用
        self.assertEqual(status_code, 200)
        mock_post.assert_called_once_with(
            url=url + '/kdev/terminal/user/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            },
            json={'mock_param': 'mock_data'}
        )
        mock_info.assert_called_once_with(
            '[interface: qcos_isingapi_handler] 新增用户请求返回：200')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('requests.post')
    def test_post_reset_password(self, mock_post, mock_info):
        '''
        测试 post_reset_password 重置用户密码
        '''

        # 准备参数
        url = 'http://example.com'
        data = {
            'query_params': {
                'data': {
                    'mock_param': 'mock_data'
                }
            }
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 调用 post_reset_password 方法
        status_code, _ = self.ising_user_manage_strategy.post_reset_password(
            url, data)

        # 验证调用
        self.assertEqual(status_code, 200)
        mock_post.assert_called_once_with(
            url=url + '/kdev/terminal/user/reset-password/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            },
            json={'mock_param': 'mock_data'}
        )
        mock_info.assert_called_once_with(
            '[interface: qcos_isingapi_handler] 重置密码请求返回：200')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('requests.put')
    def test_put_edit_user(self, mock_put, mock_info):
        '''
        测试 put_edit_user 编辑用户信息
        '''

        # 准备参数
        url = 'http://example.com'
        data = {
            'query_params': {
                'user_id': 'mock_user_id',
                'data': {
                    'mock_param': 'mock_data'
                }
            }
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response

        # 调用 put_edit_user 方法
        status_code, _ = self.ising_user_manage_strategy.put_edit_user(
            url, data)

        # 验证调用
        self.assertEqual(status_code, 200)
        mock_put.assert_called_once_with(
            url=url + '/kdev/terminal/user/mock_user_id/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            },
            json={'mock_param': 'mock_data'}
        )
        mock_info.assert_called_once_with(
            '[interface: qcos_isingapi_handler] 编辑用户信息请求返回：200')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('requests.delete')
    def test_delete_user(self, mock_delete, mock_info):
        '''
        测试 delete_user 删除用户
        '''

        # 准备参数
        url = 'http://example.com'
        data = {
            'query_params': {
                'user_id': 'mock_user_id'
            }
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response

        # 调用 delete_user 方法
        status_code, _ = self.ising_user_manage_strategy.\
            delete_user(url, data)

        # 验证调用
        self.assertEqual(status_code, 200)
        mock_delete.assert_called_once_with(
            url=url + '/kdev/terminal/user/mock_user_id/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )
        mock_info.assert_called_once_with(
            '[interface: qcos_isingapi_handler] 删除用户请求返回：200')


class TestIsingRoleManageStrategy(unittest.TestCase):
    '''
    测试 IsingRoleManageStrategy 策略类。
    '''

    def setUp(self):
        '''
        实例化 IsingRoleManageStrategy 类
        '''

        self.ising_role_manage_strategy = IsingRoleManageStrategy()

    @patch.object(IsingRoleManageStrategy, 'get_role_list')
    @patch.object(IsingRoleManageStrategy, 'post_add_role')
    @patch.object(IsingRoleManageStrategy, 'delete_role')
    @patch.object(IsingRoleManageStrategy, 'put_edit_role')
    @patch.object(IsingRoleManageStrategy, 'post_modify_role_permission')
    def test_execute(
            self,
            mock_get_role_list,
            mock_post_add_role,
            mock_delete_role,
            mock_put_edit_role,
            mock_post_modify_role_permission):
        '''
        测试 IsingRoleManageStrategy 中具体请求策略的执行
        '''

        # 准备参数，并调用函数进行测试
        url = Mock
        data = Mock
        for _, strategy_type in IsingRoleManageType.__members__.items():
            self.ising_role_manage_strategy.execute(
                strategy_type.value, url, data)
        # 验证每个任务类型是否被成功调用
        mock_get_role_list.assert_called_once_with(url, data)
        mock_post_add_role.assert_called_once_with(url, data)
        mock_delete_role.assert_called_once_with(url, data)
        mock_put_edit_role.assert_called_once_with(url, data)
        mock_post_modify_role_permission.assert_called_once_with(url, data)

        # 测试错误策略类型并验证输出结果
        try:
            self.ising_role_manage_strategy.execute(
                'unknow_type',
                url,
                data)
        except ValueError as e:
            assert e.args[0] == '未知的任务策略类型!'

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('requests.get')
    def test_get_role_list(self, mock_get, mock_info):
        '''
        测试 get_role_list 获取角色列表
        '''

        # 准备参数
        url = 'http://example.com'
        data = {
            'query_params': {
                'name': 'mock_role_name',
                'status': 'true',
                'ordering': 'create_datetime',
                'page': 1,
                'size': 10
            }
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # 调用 get_role_list 方法
        status_code, _ = self.ising_role_manage_strategy.get_role_list(
            url, data)

        # 验证调用
        self.assertEqual(status_code, 200)
        mock_get.assert_called_once_with(
            url=url + '/kdev/terminal/role/?name=mock_role_name&'
                      'status=true&ordering=create_datetime'
            '&page=1&size=10',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'})
        mock_info.assert_called_once_with(
            '[interface: qcos_isingapi_handler] 获取角色列表请求返回：200')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('requests.post')
    def test_post_add_role(self, mock_post, mock_info):
        '''
        测试 post_add_role 新增角色
        '''

        # 准备参数
        url = 'http://example.com'
        data = {
            'query_params': {
                'data': {
                    'mock_param': 'mock_data'
                }
            }
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 调用 post_add_role 方法
        status_code, _ = self.ising_role_manage_strategy.post_add_role(
            url, data)

        # 验证调用
        self.assertEqual(status_code, 200)
        mock_post.assert_called_once_with(
            url=url + '/kdev/terminal/role/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            },
            json={'mock_param': 'mock_data'}
        )
        mock_info.assert_called_once_with(
            '[interface: qcos_isingapi_handler] 新增角色请求返回：200')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('requests.delete')
    def test_delete_role(self, mock_delete, mock_info):
        '''
        测试 delete_role 删除角色
        '''

        # 准备参数
        url = 'http://example.com'
        data = {
            'query_params': {
                'role_id': 'mock_role_id'
            }
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response

        # 调用 delete_role 方法
        status_code, _ = self.ising_role_manage_strategy.\
            delete_role(url, data)

        # 验证调用
        self.assertEqual(status_code, 200)
        mock_delete.assert_called_once_with(
            url=url + '/kdev/terminal/role/mock_role_id/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            }
        )
        mock_info.assert_called_once_with(
            '[interface: qcos_isingapi_handler] 删除角色请求返回：200')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('requests.put')
    def test_put_edit_role(self, mock_put, mock_info):
        '''
        测试 put_edit_role 编辑用户信息
        '''

        # 准备参数
        url = 'http://example.com'
        data = {
            'query_params': {
                'role_id': 'mock_role_id',
                'data': {
                    'mock_param': 'mock_data'
                }
            }
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_put.return_value = mock_response

        # 调用 put_edit_role 方法
        status_code, _ = self.ising_role_manage_strategy.\
            put_edit_role(url, data)

        # 验证调用
        self.assertEqual(status_code, 200)
        mock_put.assert_called_once_with(
            url=url + '/kdev/terminal/role/mock_role_id/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            },
            json={'mock_param': 'mock_data'}
        )
        mock_info.assert_called_once_with(
            '[interface: qcos_isingapi_handler] 编辑角色信息请求返回：200')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('requests.post')
    def test_post_modify_role_permission(self, mock_post, mock_info):
        '''
        测试 post_modify_role_permission 修改角色权限
        '''

        # 准备参数
        url = 'http://example.com'
        data = {
            'query_params': {
                'data': {
                    'mock_param': 'mock_data'
                }
            }
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # 调用 post_modify_role_permission 方法
        status_code, _ = self.ising_role_manage_strategy.\
            post_modify_role_permission(url, data)

        # 验证调用
        self.assertEqual(status_code, 200)
        mock_post.assert_called_once_with(
            url=url + '/kdev/terminal/role/put-role/',
            headers={
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN',
                'authorization': 'JWT token'
            },
            json={'mock_param': 'mock_data'}
        )
        mock_info.assert_called_once_with(
            '[interface: qcos_isingapi_handler] 修改角色权限请求返回：200')


if __name__ == '__main__':
    unittest.main()
