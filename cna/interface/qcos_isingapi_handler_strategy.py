#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Modified by Bowen Zhang at 2024-12
# ------------------------


import requests
from qcos.config.qcos_config_manager import qcos_configer
from qcos.log.qcos_log import QCOSLogger
from enum import Enum, unique
import string
import csv
import random
import tempfile
import os
from datetime import datetime
import json
import time


# 创建日志记录器实例
qcos_logger = QCOSLogger()


@unique
class IsingTaskType(Enum):
    """
    任务请求策略类型枚举
    """

    # 任务--个人任务列表
    TERMINAL_MACHINE_TASK = 0
    # 任务--任务管理列表
    TERMINAL_TASK = 1
    # 任务--个人任务详情
    TERMINAL_MACHINE_TASK_INFO = 2
    # 任务--任务管理详情
    TERMINAL_TASK_INFO = 3
    # 任务--个人任务删除
    TERMINAL_MACHINE_TASK_DELETE = 4
    # 任务--任务管理删除
    TERMINAL_TASK_DELETE = 5
    # 任务--个人任务上传矩阵
    TERMINAL_UPLOAD_FILE = 6
    # 任务--QUBO Value 结果图片
    TERMINAL_TASK_IMAGES = 7
    # 任务--个人任务批量提交
    TERMINAL_BATCH_TASK = 8
    # 任务--个人任务名称校验
    TERMINAL_BATCH_CHECK_TASK_NAME = 9
    # 任务--个人任务批量下载
    TERMINAL_DOWNLOAD_TASK = 10
    # 任务--矩阵上传到结果返回的任务计算流程
    TERMINAL_TASK_COMPUTE = 11


@unique
class IsingTaskBoardType(Enum):
    """
    任务看板请求策略类型枚举
    """

    # 任务看板--任务数
    TERMINAL_TASK_COUNT = 0
    # 任务看板--历史占比
    TERMINAL_TASK_RATIO = 1
    # 任务看板--时段占比
    TERMINAL_TASK_RATIO_SEARCH = 2
    # 任务看板--任务趋势
    TERMINAL_TASK_TREND = 3
    # 任务看板--时效统计
    TERMINAL_TASK_TIMELINESS = 4
    # 任务看板--规模统计
    TERMINAL_TASK_QUANTITY_NUM = 5


@unique
class IsingHardwareMonitorType(Enum):
    """
    硬件监控请求策略类型枚举
    """

    # 硬件监控--无故障运行天数
    HARDWARE_OPERATION_DAY = 0
    # 硬件监控--比特资源利用率
    HARDWARE_RESOURCE_RATIO = 1
    # 硬件监控--耦合资源利用率
    HARDWARE_COUPLING_RESOURCE_RATIO = 2
    # 硬件监控--设备运行温度
    HARDWARE_DEVICE_TEMPERATURE = 3
    # 硬件监控--磁盘监控
    HARDWARE_DISK_MONITOR = 4


@unique
class IsingUserCenterType(Enum):
    """
    个人中心请求策略枚举
    """

    # 登陆
    LOGIN = 0
    # 个人信息
    USER_INFO = 1
    # 重置密码
    USER_RESET_PASSWORD = 2
    # 软件更新静态资源 -- 用于升级弧光客户端接口，无需使用
    GET_FILE = 3
    # 用量总览
    TASK_DATA = 4


@unique
class IsingUserManageType(Enum):
    """
    用户管理请求策略类型枚举
    """

    # 用户管理--用户列表
    USER_LIST = 0
    # 用户管理--新增用户
    ADD_USER = 1
    # 用户管理--用户重置密码
    RESET_PASSWORD = 2
    # 用户管理--编辑用户
    EDIT_USER = 3
    # 用户管理--删除用户
    DELETE_USER = 4


@unique
class IsingRoleManageType(Enum):
    """
    角色管理请求策略类型枚举
    """

    # 角色管理--角色列表
    ROLE_LIST = 0
    # 角色管理--角色新增
    ADD_ROLE = 1
    # 角色管理--角色删除
    DELETE_ROLE = 2
    # 角色管理--角色编辑
    EDIT_ROLE = 3
    # 角色管理--角色修改权限
    MODIFY_ROLE_PERMISSION = 4


@unique
class IsingMachineInfoAndSelfTestType(Enum):
    """
    真机信息&自检请求策略枚举
    """

    # 系统自检信息
    SELF_TEST_INFO = 0
    # 开始自检
    SELF_TEST_START = 1
    # 真机信息
    MACHINE_INFO = 2


@unique
class IsingProjectType(Enum):
    """
    项目请求策略类型枚举
    """

    # 项目--所有项目枚举
    PROJECT_ALL_ENUM = 0
    # 项目--个人项目枚举
    PROJECT_ENUM = 1
    # 项目--个人项目列表
    PROJECT_LIST = 2
    # 项目--个人项目创建
    PROJECT_CREATE = 3
    # 项目--个人项目编辑
    PROJECT_EDIT = 4
    # 项目--个人项目删除
    PROJECT_DELETE = 5


@unique
class IsingLogManagerType(Enum):
    """
    日志管理请求策略类型枚举
    """

    # 日志管理--登录日志列表
    LOG_LOGIN_LIST = 0
    # 日志管理--操作日志列表
    LOG_OPERATION_LIST = 1
    # 日志管理--操作日志详情
    LOG_OPERATION_INFO = 2
    # 日志管理--告警日志列表
    LOG_FAULT_LIST = 3


class IsingRequestStrategy:
    """
    所有请求策略的基类
    """

    def execute(self, strategy_type, url, data=None):
        """
        执行请求策略的抽象方法
            :param strategy_type: 策略类型
            :param url: 请求URL
            :param data: 请求数据
            :return: 请求响应
        """

        raise NotImplementedError("Each strategy must implement an execute method")


class IsingTaskStrategy(IsingRequestStrategy):
    """
    Ising任务策略
    """

    def execute(self, ising_task_type, url, data=None):
        """
        执行请求策略
        """

        if ising_task_type == IsingTaskType.TERMINAL_MACHINE_TASK.value:
            return self.get_machine_task(url, data)
        elif ising_task_type == IsingTaskType.TERMINAL_TASK.value:
            return self.get_task(url, data)
        elif ising_task_type == IsingTaskType.TERMINAL_MACHINE_TASK_INFO.value:
            return self.get_machine_task_info(url, data)
        elif ising_task_type == IsingTaskType.TERMINAL_TASK_INFO.value:
            return self.get_task_info(url, data)
        elif ising_task_type == IsingTaskType.TERMINAL_MACHINE_TASK_DELETE.value:
            return self.delete_machine_task(url, data)
        elif ising_task_type == IsingTaskType.TERMINAL_TASK_DELETE.value:
            return self.delete_task(url, data)
        elif ising_task_type == IsingTaskType.TERMINAL_UPLOAD_FILE.value:
            return self.post_upload_file(url, data)
        elif ising_task_type == IsingTaskType.TERMINAL_TASK_IMAGES.value:
            return self.get_task_images(url, data)
        elif ising_task_type == IsingTaskType.TERMINAL_BATCH_TASK.value:
            return self.post_batch_task(url, data)
        elif ising_task_type == IsingTaskType.TERMINAL_BATCH_CHECK_TASK_NAME.value:
            return self.get_batch_check_task_name(url, data)
        elif ising_task_type == IsingTaskType.TERMINAL_DOWNLOAD_TASK.value:
            return self.get_download_task(url, data)
        elif ising_task_type == IsingTaskType.TERMINAL_TASK_COMPUTE.value:
            return self.task_compute(url, data)
        else:
            raise ValueError("未知的任务策略类型!")

    def get_machine_task(self, url, data=None):
        """
        发送GET请求获取个人任务列表

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/machine-task/"
        url_params = ["page", "size", "task_name"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送GET请求
        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取个人任务列表请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_task(self, url, data=None):
        """
        发送GET请求获取任务管理列表

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")
        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/task/"
        url_params = ["task_id", "username", "status", "project", "ordering", "page", "size"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送GET请求
        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取任务管理列表请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_machine_task_info(self, url, data=None):
        """
        发送GET请求获取个人任务详情

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        task_id = data["query_params"]["task_id"]

        url = f"{url}/kdev/terminal/machine-task/{task_id}/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送GET请求
        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取个人任务详情请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_task_info(self, url, data=None):
        """
        发送GET请求获取任务管理详情

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        task_id = data["query_params"]["task_id"]

        url = f"{url}/kdev/terminal/task/{task_id}/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送GET请求
        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取任务管理详情请求返回：{response.status_code}")
        return response.status_code, response_data

    def delete_machine_task(self, url, data=None):
        """
        发送DELETE请求个人任务删除

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        task_id = data["query_params"]["task_id"]

        url = f"{url}/kdev/terminal/machine-task/{task_id}/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送DELETE请求
        response = requests.delete(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 个人任务删除请求返回：{response.status_code}")
        return response.status_code, response_data

    def delete_task(self, url, data=None):
        """
        发送DELETE请求任务管理-删除

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        task_id = data["query_params"]["task_id"]

        url = f"{url}/kdev/terminal/task/{task_id}/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送DELETE请求
        response = requests.delete(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 任务管理删除请求返回：{response.status_code}")
        return response.status_code, response_data

    def post_upload_file(self, url, data=None):
        """
        上传矩阵, 矩阵来自于data，格式是json
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        # 获取用户输入矩阵
        matrix = data["query_params"]["matrix"]
        if matrix is None or len(matrix) == 0:
            raise ValueError("matrix is None or empty")

        # 上传csv文件到指定接口,
        url = f"{url}/kdev/terminal/upload_file/"

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 将矩阵转换为csv文件。
        # 这里给文件名加随机符号，防止多个上传任务同时发生时产生文件覆盖情况, 暂时先按照这种情况写。
        characters = string.ascii_letters + string.digits
        random_string = ''.join(random.choice(characters) for _ in range(6))
        csv_file_name = "once_task_" + random_string + ".csv"

        temp_dir = tempfile.gettempdir()
        csv_file_path = os.path.join(temp_dir, csv_file_name)

        try:
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                for row in matrix:
                    writer.writerow(row)

            # 重新打开文件以获取文件对象
            with open(csv_file_path, 'rb') as csv_file:
                file_name = os.path.basename(csv_file_path)
                files = {
                    'name': ('', file_name),
                    'url': (file_name, csv_file, 'text/csv')
                }
                response = requests.post(url=url, headers=headers, files=files)
                # Todo 解析响应体数据
                response_data = response.json()
        finally:
            if os.path.exists(csv_file_path):
                os.remove(csv_file_path)

        qcos_logger.info(f"[interface: qcos_isingapi_handler] 上传矩阵请求返回：{response.status_code}")

        return response.status_code, response_data

    def get_task_images(self, url, data=None):
        """
        获取 QUBO Value 结果图片
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        task_id = data["query_params"]["task_id"]

        url = f"{url}/kdev/terminal/task-images/{task_id}/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }
        response = requests.get(url=url, headers=headers)
        if response.status_code == 200:
            # 打开一个文件用于写入二进制数据
            image_path = qcos_configer.get_qubo_images_path()
            # 替换路径分隔符
            image_path = image_path.replace("/", os.sep).replace("\\", os.sep)
            if not os.path.exists(image_path):
                os.makedirs(image_path)

            image_name = f"result_qubo_image{task_id}.png"
            image_file = os.path.join(image_path, image_name)
            with open(image_file, 'wb') as file:
                file.write(response.content)
            qcos_logger.info(f"[interface: qcos_isingapi_handler] 查询QUBO结果图片请求成功，状态码：{response.status_code}")
            qcos_logger.info(f"[interface: qcos_isingapi_handler] 查询QUBO结果图片请求成功，图片为：{image_file}")
        else:
            qcos_logger.info(f"[interface: qcos_isingapi_handler] 查询QUBO结果图片请求失败，状态码：{response.status_code}")

        return response.status_code

    def post_batch_task(self, url, data=None):
        """
        批量提交任务
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        json_data = data["query_params"]["data"]

        url = f"{url}/kdev/terminal/batch-task/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }
        response = requests.post(url=url, headers=headers, json=json_data)
        # Todo 解析响应体数据
        response_data = response.json()

        qcos_logger.info(f"[interface: qcos_isingapi_handler] 批量提交任务请求返回：{response.status_code}")

        return response.status_code, response_data

    def get_batch_check_task_name(self, url, data=None):
        """
        个人任务，名称校验
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        task_names = data["query_params"]["task_names"]

        url = f"{url}/kdev/terminal/batch-check-task-name/"
        url += "?task_names=" + task_names

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        qcos_logger.info(f"[interface: qcos_isingapi_handler] 任务校验请求返回：{response.status_code}")

        return response.status_code, response_data

    def get_download_task(self, url, data=None):
        """
        批量下载任务
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和结果文件路径
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/download-task/"
        # type 1:下载结果，2: 下载报告
        url_params = ["type", "ids"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # 解析响应体中结果文件
        zip_file = ""
        if response.status_code == 200:
            # 打开一个文件用于写入二进制数据
            file_path = qcos_configer.get_zip_file_path()
            # 替换路径分隔符
            file_path = file_path.replace("/", os.sep).replace("\\", os.sep)
            if not os.path.exists(file_path):
                os.makedirs(file_path)

            current_time = datetime.now()
            file_name = f"downloaded_file{current_time.strftime('%y%m%d%H%M%S')}.zip"
            zip_file = os.path.join(file_path, file_name)
            with open(zip_file, 'wb') as file:
                file.write(response.content)
            qcos_logger.info(f"[interface: qcos_isingapi_handler] 下载任务请求成功，状态码：{response.status_code}")
            qcos_logger.info(f"[interface: qcos_isingapi_handler] 下载任务请求成功，文件为：{zip_file}")
        else:
            qcos_logger.info(f"[interface: qcos_isingapi_handler] 下载任务请求失败，状态码：{response.status_code}")

        return response.status_code, zip_file

    def task_compute(self, url, data=None):
        """
        上传QUBO矩阵到任务计算结果返回的计算流程
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """
        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        """上传矩阵"""
        upload_response_code, upload_response_data = self.post_upload_file(url, data)
        if upload_response_code != 200:
            raise ValueError("Upload file error!")

        """提交任务"""
        # 构建批量提交策略的请求参数
        batch_task_request_data = {
            "query_params": {
                "data": [
                    {
                        "priority": data["query_params"]["priority"],
                        "user_id": upload_response_data["data"]["creator"],
                        "machine_id": data["query_params"]["machine_id"],
                        "task_name": data["query_params"]["task_name"],
                        "file_id": upload_response_data["data"]["id"],
                        "csv_name": upload_response_data["data"]["name"],
                        "estimated_datetime": data["query_params"]["estimated_datetime"],
                        "expected_description": data["query_params"]["expected_description"],
                        "project_id": data["query_params"]["project_id"]
                    },
                ]
            }
        }
        batch_task_response_code, _ = self.post_batch_task(url, batch_task_request_data)
        if batch_task_response_code != 200:
            raise ValueError("Batch task error!")

        """获取个人任务列表，从中解析任务id"""
        machine_task_request_data = {
            "query_params": {
                "data": {
                        "page": data["query_params"]["page"],
                        "size": data["query_params"]["size"],
                        "task_name": data["query_params"]["task_name"]
                }
            }
        }
        machine_task_response_code, machine_task_response_data = self.get_machine_task(url, machine_task_request_data)
        if machine_task_response_code != 200:
            raise ValueError("Get machine task id error!")

        """下载任务结果"""
        download_result_request_data = {
            "query_params": {
                "type": data["query_params"]["type"],
                "ids": machine_task_response_data["data"]["data"][0]["id"],
            }
        }
        # 等待执行
        timeout = 600
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response_code, result_file_path = self.get_download_task(url, download_result_request_data)
                if response_code == 200:
                    return result_file_path
                else:
                    qcos_logger.error(f"下载任务结果请求失败，状态码： {response_code}")
            except requests.RequestException as err:
                # 请求异常，返回错误信息
                qcos_logger.error(f"下载任务结果请求异常：{err}")
        # 超时后记录错误提示
        qcos_logger.error("请求超时，未能在指定时间内获取计算结果")

        # 流程超时失败，没有获取到任务计算结果
        return None


class IsingTaskBoardStrategy(IsingRequestStrategy):
    """
    Ising任务看板策略
    """

    def execute(self, ising_task_type, url, data=None):
        """
        执行请求策略
        """

        if ising_task_type == IsingTaskBoardType.TERMINAL_TASK_COUNT.value:
            return self.get_task_count(url, data)
        elif ising_task_type == IsingTaskBoardType.TERMINAL_TASK_RATIO.value:
            return self.get_task_ratio(url, data)
        elif ising_task_type == IsingTaskBoardType.TERMINAL_TASK_RATIO_SEARCH.value:
            return self.get_task_ratio_search(url, data)
        elif ising_task_type == IsingTaskBoardType.TERMINAL_TASK_TREND.value:
            return self.get_task_trend(url, data)
        elif ising_task_type == IsingTaskBoardType.TERMINAL_TASK_TIMELINESS.value:
            return self.get_task_timeliness(url, data)
        elif ising_task_type == IsingTaskBoardType.TERMINAL_TASK_QUANTITY_NUM.value:
            return self.get_task_quantity_num(url, data)
        else:
            raise ValueError("未知的任务看板策略类型!")

    def get_task_count(self, url, data=None):
        """
        发送GET请求获取任务数

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        url = f"{url}/kdev/terminal/task-count/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送GET请求
        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取任务数请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_task_ratio(self, url, data=None):
        """
        发送GET请求获取历史占比

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        url = f"{url}/kdev/terminal/task-ratio/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送GET请求
        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取历史占比请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_task_ratio_search(self, url, data=None):
        """
        发送GET请求获取时段占比

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/task-ratio-search/"
        url_params = ["project_ids", "start_date", "end_date"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送GET请求
        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取时段占比请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_task_trend(self, url, data=None):
        """
        发送GET请求获取任务趋势

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/task-trend/"
        url_params = ["project_ids", "start_date", "end_date"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送GET请求
        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取任务趋势请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_task_timeliness(self, url, data=None):
        """
        发送GET请求获时效统计

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/task-timeliness/"
        url_params = ["project_ids", "start_date", "end_date"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送GET请求
        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取时效统计请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_task_quantity_num(self, url, data=None):
        """
        发送GET请求获取规模统计

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/task-quantity-num/"
        url_params = ["project_ids", "start_date", "end_date"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送GET请求
        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取规模统计请求返回：{response.status_code}")
        return response.status_code, response_data


class IsingHardwareMonitorStrategy(IsingRequestStrategy):
    """
    硬件监控基类
    """

    def execute(self, ising_task_type, url, data=None):
        """
        执行请求策略
        """

        if ising_task_type == IsingHardwareMonitorType.HARDWARE_OPERATION_DAY.value:
            return self.get_operation_day(url, data)
        elif ising_task_type == IsingHardwareMonitorType.HARDWARE_RESOURCE_RATIO.value:
            return self.get_resource_ratio(url, data)
        elif ising_task_type == IsingHardwareMonitorType.HARDWARE_COUPLING_RESOURCE_RATIO.value:
            return self.get_coupling_resource_ratio(url, data)
        elif ising_task_type == IsingHardwareMonitorType.HARDWARE_DEVICE_TEMPERATURE.value:
            return self.get_device_temperature(url, data)
        elif ising_task_type == IsingHardwareMonitorType.HARDWARE_DISK_MONITOR.value:
            return self.get_disk_monitor(url, data)
        else:
            raise ValueError(f'undefined ising hardware monitor type {ising_task_type}')

    def get_operation_day(self, url, data=None):
        """
        无故障运行天数
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/monitoring-num-data/"
        url_params = ["start_date", "end_date"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取无故障运行天数请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_resource_ratio(self, url, data=None):
        """
        比特资源利用率
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/monitoring-bit-data/"
        url_params = ["start_date", "end_date"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取比特资源利用率请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_coupling_resource_ratio(self, url, data=None):
        """
        耦合资源利用率
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/monitoring-resources-data/"
        url_params = ["start_date", "end_date"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取耦合资源利用率请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_device_temperature(self, url, data=None):
        """
        设备运行温度
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        url = f"{url}/kdev/terminal/monitoring-temperature-data"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取设备运行温度请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_disk_monitor(self, url, data=None):
        """
        磁盘监控
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        url = f"{url}/kdev/terminal/monitoring-metrics"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取磁盘监控请求返回：{response.status_code}")
        return response.status_code, response_data


class IsingUserCenterStrategy(IsingRequestStrategy):
        """
        个人中心基础类
        """

        def execute(self, strategy_type, url, data=None):
            """
            执行请求策略
            """

            if strategy_type == IsingUserCenterType.LOGIN.value:
                return self.post_login(url, data)
            elif strategy_type == IsingUserCenterType.USER_INFO.value:
                return self.get_user_info(url, data)
            elif strategy_type == IsingUserCenterType.USER_RESET_PASSWORD.value:
                return self.post_user_reset_password(url, data)
            elif strategy_type == IsingUserCenterType.GET_FILE.value:
                return self.get_file(url, data)
            elif strategy_type == IsingUserCenterType.TASK_DATA.value:
                return self.get_task_data(url, data)
            else:
                raise ValueError(f'undefined ising user center type {strategy_type}')

        def post_login(self, url, data=None):
            """
            发送post请求进行用户登陆

                :param url: 基础URL
                :param data: 包含查询参数的字典，默认为None
                :return: 状态码和响应体
            """

            if data is None:
                raise ValueError(f"data为空，缺少请求参数！")

            if "post_body" not in data:
                raise ValueError("no body info when login")

            if "username" not in data["post_body"] or "pwd" not in data["post_body"]:
                raise ValueError("both username and pwd are needed when login")

            username = data["post_body"]["username"]
            pwd = data["post_body"]["pwd"]

            url = f"{url}/kdev/terminal/login/"
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN",
            }
            response = requests.post(url=url, headers=headers, json={"username": username, "pwd": pwd})

            qcos_logger.info(f"[interface: qcos_isingapi_handler] 登陆请求返回：{response.status_code}")

            return response.status_code, response.json()

        def get_user_info(self, url, data=None):
            """
            发送get请求获取用户信息

                :param url: 基础URL
                :param data: 包含查询参数的字典，默认为None
                :return: 状态码和响应体
            """

            # 用户通过登陆获取JWT token，然后每次请求除登陆外其他接口都要将JWT token带上。
            # 所以下发任务时应该将JWT token也放在data中。
            # 目前对于仅仅需要JWT token而没有其他请求参数的接口，暂时不对其data及其中的JWT token是否为空做校验。

            url = f"{url}/kdev/terminal/user-info/"
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN",
                "authorization": "JWT token"
            }

            response = requests.get(url=url, headers=headers)

            qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取个人信息请求返回：{response.status_code}")
            return response.status_code, response.json()

        def post_user_reset_password(self, url, data=None):
            """
            发送post请求重置密码

                :param url: 基础URL
                :param data: 包含查询参数的字典，默认为None
                :return: 状态码和响应体
            """

            if data is None:
                raise ValueError(f"data为空，缺少请求参数！")

            if "post_body" not in data:
                raise ValueError("no body info when reset password")

            if ("old_pwd" not in data["post_body"] or "pwd" not in data["post_body"]
                    or "confirm_pwd" not in data["post_body"]):
                raise ValueError("all old_pwd, pwd and confirm_pwd are needed when reset password")

            # old_pwd，pwd，confirm_pwd的内容是真实值的MD5加密
            old_pwd = data["post_body"]["old_pwd"]
            pwd = data["post_body"]["pwd"]
            confirm_pwd = data["post_body"]["confirm_pwd"]

            url = f"{url}/kdev/terminal/user/user-reset-password/"
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN",
                "authorization": "JWT token"
            }

            response = requests.post(url=url, headers=headers,
                                     json={"old_pwd": old_pwd, "pwd": pwd, "confirm_pwd": confirm_pwd});

            qcos_logger.info(f"[interface: qcos_isingapi_handler] 重置密码请求返回：{response.status_code}")
            return response.status_code, response.json()

        def get_file(self, url, data=None):
            """
            发送get请求升级玻色客户端 -- 无需对接的接口，后续可以删除

                :param url: 基础URL
                :param data: 包含查询参数的字典，默认为None
                :return: 状态码和响应体
            """

            if data is None or "path_params" not in data or not isinstance(data["path_params"], list):
                raise ValueError("请求url缺少path路径变量")

            static_source = data["path_params"][0]

            if static_source != "latest.yml" and static_source != "CIM_install.exe":
                raise ValueError("不存在的静态资源")

            url = f"{url}/kdev/terminal/get-file/" + static_source
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN",
                "authorization": "JWT token"
            }
            response = requests.get(url=url, headers=headers)

            qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取软件静态资源请求返回：{response.status_code}")
            return response.status_code, None


        def get_task_data(self, url, data=None):
            """
            发送get请求用量总览

                :param url: 基础URL
                :param data: 包含查询参数的字典，默认为None
                :return: 状态码和响应体
            """

            if data is None:
                raise ValueError(f"data为空，缺少请求参数！")

            if "query_params" not in data:
                raise ValueError("no query params when get task data")

            if ("project_ids" not in data["query_params"] or "start_date" not in data["query_params"]
                    or "end_date" not in data["query_params"]):
                raise ValueError("all project_ids, start_date and end_date are needed when get task data")

            project_ids = data["query_params"]["project_ids"]
            start_date = data["query_params"]["start_date"]
            end_date = data["query_params"]["end_date"]

            url = f"{url}/kdev/terminal/task-data?project_ids={project_ids}&start_date={start_date}&end_date={end_date}"
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN",
                "authorization": "JWT token"
            }

            response = requests.get(url=url, headers=headers)

            qcos_logger.info(f"[interface: qcos_isingapi_handler] 用量总览请求返回：{response.status_code}")
            return response.status_code, response.json()


class IsingMachineInfoAndSelfTestStrategy(IsingRequestStrategy):
        """
        真机信息&自检基础类
        """

        def execute(self, strategy_type, url, data=None):
            """
            执行请求策略
            """

            if strategy_type == IsingMachineInfoAndSelfTestType.SELF_TEST_INFO.value:
                return self.get_self_test_info(url, data)
            elif strategy_type == IsingMachineInfoAndSelfTestType.MACHINE_INFO.value:
                return self.get_machine_info(url, data)
            elif strategy_type == IsingMachineInfoAndSelfTestType.SELF_TEST_START.value:
                return self.post_self_test_start(url, data)
            else:
                raise ValueError(f'undefined ising Machine Info and Self Test type {strategy_type}')

        def get_self_test_info(self, url, data=None):
            """
            发送get请求获取系统自检信息

                :param url: 基础URL
                :param data: 包含查询参数的字典，默认为None
                :return: 状态码和响应体
            """

            url = f"{url}/kdev/terminal/self-test/"
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN",
                "authorization": "JWT token"
            }

            response = requests.get(url=url, headers=headers)

            qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取系统自检信息请求返回：{response.status_code}")
            return response.status_code, response.json()

        def post_self_test_start(self, url, data=None):
            """
            发送post请求进行系统自检

                :param url: 基础URL
                :param data: 包含查询参数的字典，默认为None
                :return: 状态码和响应体

            """

            url = f"{url}/kdev/terminal/self-test/"
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN",
                "authorization": "JWT token"
            }

            response = requests.post(url=url, headers=headers)

            qcos_logger.info(f"[interface: qcos_isingapi_handler] 系统开始自检请求返回：{response.status_code}")
            return response.status_code, None

        def get_machine_info(self, url, data=None):
            """
            发送get请求获取真机信息

                :param url: 基础URL
                :param data: 包含查询参数的字典，默认为None
                :return: 状态码和响应体
            """

            if data is None:
                raise ValueError(f"data为空，缺少请求参数！")

            if "query_params" not in data:
                raise ValueError("no query params when get machine info")

            if "machine_id" not in data["query_params"]:
                raise ValueError("machine_id is needed get machine info")

            machine_id = data["query_params"]["machine_id"]

            url = f"{url}/kdev/terminal/machine?machine_id={machine_id}"
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN",
                "authorization": "JWT token"
            }

            response = requests.get(url=url, headers=headers)

            qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取真机信息请求返回：{response.status_code}")
            return response.status_code, response.json()


class IsingProjectStrategy(IsingRequestStrategy):
    """
    项目基类
    """

    def execute(self, ising_task_type, url, data=None):
        """
        执行请求策略
        """

        if ising_task_type == IsingProjectType.PROJECT_ALL_ENUM.value:
            return self.get_project_all_enum(url, data)
        elif ising_task_type == IsingProjectType.PROJECT_ENUM.value:
            return self.get_project_enum(url, data)
        elif ising_task_type == IsingProjectType.PROJECT_LIST.value:
            return self.get_project_list(url, data)
        elif ising_task_type == IsingProjectType.PROJECT_CREATE.value:
            return self.post_project_create(url, data)
        elif ising_task_type == IsingProjectType.PROJECT_EDIT.value:
            return self.put_project_edit(url, data)
        elif ising_task_type == IsingProjectType.PROJECT_DELETE.value:
            return self.delete_project_personal(url, data)
        else:
            raise ValueError(f'undefined ising project type {ising_task_type}')

    def get_project_all_enum(self, url, data=None):
        """
        所有项目枚举
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        url = f"{url}/kdev/terminal/project-all-list/"

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取所有项目枚举请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_project_enum(self, url, data=None):
        """
        个人项目枚举
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        url = f"{url}/kdev/terminal/project-list/"

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取个人项目枚举请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_project_list(self, url, data=None):
        """
        个人项目列表
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/project/"
        url_params = ["project_name", "page", "size"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取个人项目列表请求返回：{response.status_code}")
        return response.status_code, response_data

    def post_project_create(self, url, data=None):
        """
        个人项目创建
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        json_data = data["query_params"]["data"]

        url = f"{url}/kdev/terminal/project/"

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.post(url=url, headers=headers, json=json_data)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取个人项目创建请求返回：{response.status_code}")
        return response.status_code, response_data

    def put_project_edit(self, url, data=None):
        """
        个人项目编辑
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        json_data = data["query_params"]["data"]
        project_id = data["query_params"]["project_id"]

        url = f"{url}/kdev/terminal/project/{project_id}/"

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.put(url=url, headers=headers, json=json_data)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取个人项目编辑请求返回：{response.status_code}")
        return response.status_code, response_data

    def delete_project_personal(self, url, data=None):
        """
        个人项目删除
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        project_id = data["query_params"]["project_id"]

        url = f"{url}/kdev/terminal/project/{project_id}/"

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.delete(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取个人项目删除请求返回：{response.status_code}")
        return response.status_code, response_data


class IsingLogManagerStrategy(IsingRequestStrategy):
    """
    日志管理基类
    """

    def execute(self, ising_task_type, url, data=None):
        """
        执行请求策略
        """

        if ising_task_type == IsingLogManagerType.LOG_LOGIN_LIST.value:
            return self.get_log_login_list(url, data)
        elif ising_task_type == IsingLogManagerType.LOG_OPERATION_LIST.value:
            return self.get_log_operation_list(url, data)
        elif ising_task_type == IsingLogManagerType.LOG_OPERATION_INFO.value:
            return self.get_log_operation_info(url, data)
        elif ising_task_type == IsingLogManagerType.LOG_FAULT_LIST.value:
            return self.get_log_fault_list(url, data)
        else:
            raise ValueError(f'undefined ising log manager type {ising_task_type}')

    def get_log_login_list(self, url, data=None):
        """
        登录日志列表
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/login-log/"
        url_params = ["username", "id", "ip", "page", "size"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取登录日志列表请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_log_operation_list(self, url, data=None):
        """
        操作日志列表
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/operation-log/"
        url_params = ["request_modular", "request_path", "request_ip", "request_method", "page", "size"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取操作日志列表请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_log_operation_info(self, url, data=None):
        """
        操作日志详情
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        log_id = data["query_params"]["log_id"]

        url = f"{url}/kdev/terminal/operation-log/{log_id}/"

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取操作日志详情请求返回：{response.status_code}")
        return response.status_code, response_data

    def get_log_fault_list(self, url, data=None):
        """
        告警日志列表
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")

        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/fault-list/"
        url_params = ["faultNumber", "faultStatus", "ordering", "page", "size"]
        url_element = []
        if data_query_params:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + "="

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取告警日志列表请求返回：{response.status_code}")
        return response.status_code, response_data


class IsingUserManageStrategy(IsingRequestStrategy):
    """
    Ising用户管理策略
    """

    def execute(self, ising_task_type, url, data=None):
        """
        执行请求策略
        """

        if ising_task_type == IsingUserManageType.USER_LIST.value:
            return self.get_user_list(url, data)
        elif ising_task_type == IsingUserManageType.ADD_USER.value:
            return self.post_add_user(url, data)
        elif ising_task_type == IsingUserManageType.RESET_PASSWORD.value:
            return self.post_reset_password(url, data)
        elif ising_task_type == IsingUserManageType.EDIT_USER.value:
            return self.put_edit_user(url, data)
        elif ising_task_type == IsingUserManageType.DELETE_USER.value:
            return self.delete_user(url, data)
        else:
            raise ValueError("未知的任务策略类型!")

    def get_user_list(self, url, data=None):
        """
        发送GET请求以获取用户列表

            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")
        data_query_params = data.get("query_params")

        url = f"{url}/kdev/terminal/user/"
        url_params = ["username", "is_active", "ordering", "page", "size"]
        url_element = []
        if data_query_params is not None:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + '='
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送GET请求
        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取用户列表请求返回：{response.status_code}")
        return response.status_code, response_data

    def post_add_user(self, url, data=None):
        """
        发送POST请求上传用户信息以新增用户
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")
        json_data = data["query_params"]["data"]

        url = f"{url}/kdev/terminal/user/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送POST请求
        response = requests.post(url=url, headers=headers, json=json_data)
        # Todo 解析响应体数据
        response_data = response.json()

        qcos_logger.info(f"[interface: qcos_isingapi_handler] 新增用户请求返回：{response.status_code}")

        return response.status_code, response_data

    def post_reset_password(self, url, data=None):
        """
        发送POST请求上传新密码以重置原密码
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")
        json_data = data["query_params"]["data"]

        url = f"{url}/kdev/terminal/user/reset-password/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送POST请求
        response = requests.post(url=url, headers=headers, json=json_data)
        # Todo 解析响应体数据
        response_data = response.json()

        qcos_logger.info(f"[interface: qcos_isingapi_handler] 重置密码请求返回：{response.status_code}")

        return response.status_code, response_data

    def put_edit_user(self, url, data=None):
        """
        发送PUT请求上传用户信息以编辑用户
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")
        user_id = data["query_params"]["user_id"]
        json_data = data["query_params"]["data"]

        url = f"{url}/kdev/terminal/user/{user_id}/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送PUT请求
        response = requests.put(url=url, headers=headers, json=json_data)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 编辑用户信息请求返回：{response.status_code}")
        return response.status_code, response_data

    def delete_user(self, url, data=None):
        """
        发送PUT请求以删除用户
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        # Todo 解析data获取指定的user_id
        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")
        user_id = data["query_params"]["user_id"]

        url = f"{url}/kdev/terminal/user/{user_id}/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送DELETE请求
        response = requests.delete(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 删除用户请求返回：{response.status_code}")
        return response.status_code, response_data


class IsingRoleManageStrategy(IsingRequestStrategy):
    """
    Ising角色管理策略
    """

    def execute(self, ising_task_type, url, data=None):
        """
        执行请求策略
        """

        if ising_task_type == IsingRoleManageType.ROLE_LIST.value:
            return self.get_role_list(url, data)
        elif ising_task_type == IsingRoleManageType.ADD_ROLE.value:
            return self.post_add_role(url, data)
        elif ising_task_type == IsingRoleManageType.DELETE_ROLE.value:
            return self.delete_role(url, data)
        elif ising_task_type == IsingRoleManageType.EDIT_ROLE.value:
            return self.put_edit_role(url, data)
        elif ising_task_type == IsingRoleManageType.MODIFY_ROLE_PERMISSION.value:
            return self.post_modify_role_permission(url, data)
        else:
            raise ValueError("未知的任务策略类型!")

    def get_role_list(self, url, data=None):
        """
        发送GET请求以获取角色列表
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")
        data_query_params = data["query_params"]

        url = f"{url}/kdev/terminal/role/"
        url_params = ["name", "status", "ordering", "page", "size"]
        url_element = []
        if data_query_params is not None:
            for param in url_params:
                if param in data_query_params:
                    url_element.append(f"{param}={data_query_params[param]}")
                else:
                    url_element.append(f"{param}=")
            url = url + "?" + '&'.join(url_element)
        else:
            url = url + "?" + '=&'.join(url_params) + '='
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送GET请求
        response = requests.get(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 获取角色列表请求返回：{response.status_code}")
        return response.status_code, response_data

    def post_add_role(self, url, data=None):
        """
        发送POST请求上传角色信息以新增角色
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")
        json_data = data["query_params"]["data"]

        url = f"{url}/kdev/terminal/role/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送POST请求
        response = requests.post(url=url, headers=headers, json=json_data)
        # Todo 解析响应体数据
        response_data = response.json()

        qcos_logger.info(f"[interface: qcos_isingapi_handler] 新增角色请求返回：{response.status_code}")

        return response.status_code, response_data

    def delete_role(self, url, data=None):
        """
        发送DELETE请求以删除角色
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        # Todo 解析data获取指定的role_id
        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")
        role_id = data["query_params"]["role_id"]

        url = f"{url}/kdev/terminal/role/{role_id}/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送DELETE请求
        response = requests.delete(url=url, headers=headers)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 删除角色请求返回：{response.status_code}")
        return response.status_code, response_data

    def put_edit_role(self, url, data=None):
        """
        发送PUT请求上传角色信息以编辑角色
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")
        role_id = data["query_params"]["role_id"]
        json_data = data["query_params"]["data"]

        url = f"{url}/kdev/terminal/role/{role_id}/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送PUT请求
        response = requests.put(url=url, headers=headers, json=json_data)
        # Todo 解析响应体数据
        response_data = response.json()

        # 记录日志
        qcos_logger.info(f"[interface: qcos_isingapi_handler] 编辑角色信息请求返回：{response.status_code}")
        return response.status_code, response_data

    def post_modify_role_permission(self, url, data=None):
        """
        发送POST请求上传具体角色权限信息以修改角色权限
            :param url: 基础URL
            :param data: 包含查询参数的字典，默认为None
            :return: 状态码和响应体
        """

        if data is None or "query_params" not in data:
            raise ValueError("Parameter error!")
        json_data = data["query_params"]["data"]

        url = f"{url}/kdev/terminal/role/put-role/"
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN",
            "authorization": "JWT token"
        }

        # 发送POST请求
        response = requests.post(url=url, headers=headers, json=json_data)
        # Todo 解析响应体数据
        response_data = response.json()

        qcos_logger.info(f"[interface: qcos_isingapi_handler] 修改角色权限请求返回：{response.status_code}")

        return response.status_code, response_data
