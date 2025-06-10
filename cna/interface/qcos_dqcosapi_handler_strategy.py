#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Modified by Bowen Zhang at 2024-06-17
# ------------------------


import requests
import json

from qcos.interface.qcos_isingapi_handler_strategy import IsingTaskType
from qcos.log.qcos_log import QCOSLogger
from qcos.interface.qcos_task_manager import qcos_hybird_task_manager


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class QCOSRequestStrategy:
    """
    所有请求策略的基类
    """

    def execute(self, url, data=None):
        """
               执行请求策略的抽象方法
               :param url: 请求URL
               :param data: 请求数据
               :return: 请求响应
        """

        raise NotImplementedError("Each strategy must implement an execute method")


class DQcosHeartbeatStrategy(QCOSRequestStrategy):
    """
    心跳注册策略
    """

    def execute(self, url, data=None):
        url = f"{url}/heartbeat"
        headers = {
            'Content-Type': 'application/json',
            'X-Request-From': 'QCOS'
        }

        response = requests.post(url, headers=headers)

        qcos_logger.info(f"[interface: qcos_dqcosqpi_handler] 心跳注册策略请求返回：{response.status_code}")
        return response.status_code


class DQcosFetchWorkloadStrategy(QCOSRequestStrategy):
    """
    获取任务策略
    """

    def __init__(self):
        # 实例化任务管理对象
        self.task_manager = qcos_hybird_task_manager

    def execute(self, url, data=None):
        url = f"{url}/workload"
        headers = {
            'Content-Type': 'application/json',
            'X-Request-From': 'QCOS'
        }

        openqasm_task_list = []
        response = requests.post(url, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            try:
                response_data = response.json()

                # 解析响应体获取任务信息
                executions = response_data['workload']['executions']
                for execution in executions:
                    task_id = execution.get('id')
                    task_type = execution.get('qcosTaskType')
                    priority = execution.get('qcosTaskPriority')
                    shots = execution.get('content', {}).get('shots')
                    qubits = execution.get('content', {}).get('qubitCount')
                    # sequence表示获取到的openqasm指令集
                    sequence = execution.get('content', {}).get('source')
                    allow_circuit_aggregation = execution.get('content', {}).get('allowCircuitAggregation')
                    qcos_logger.debug(f"解析任务{task_id}: {execution}")

                    # 添加解析后的任务到待处理队列
                    self.task_manager.add_task(
                        task_id, shots, qubits, sequence, priority, task_type, allow_circuit_aggregation)
                    openqasm_task_list.append(task_id)

                qcos_logger.info(f"[interface: qcos_dqcosapi_handler] 任务获取策略请求返回：{openqasm_task_list}")
                return openqasm_task_list

            except ValueError:
                # 日志记录无法解析的JSON
                qcos_logger.error("Failed to decode JSON from response: " + response.text)
                return []
        else:
            # 日志记录非200的响应状态码和响应体
            qcos_logger.error(f"任务获取策略请求异常：{response.status_code}: {response.text}")
            return []


class DQcosFetchIsingWorkloadStrategy(QCOSRequestStrategy):
    """
    获取任务策略
    """

    def execute(self, url, data=None):
        url = f"{url}/workload"
        headers = {
            'Content-Type': 'application/json',
            'X-Request-From': 'QCOS'
        }

        ising_task_list = []
        response = requests.post(url, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            try:
                response_data = response.json()
                # 解析响应体获取任务信息
                executions = response_data['workload']['executions']
                for execution in executions:
                    task_id = execution.get('id')
                    priority = execution.get('priority')
                    machine_id = execution.get('machine_id')
                    task_name = execution.get('task_name')
                    estimated_datetime = execution.get('estimated_datetime')
                    expected_description = execution.get('expected_description')
                    project_id = execution.get('project_id')
                    page = execution.get('page', 1)
                    size = execution.get('size', 10)
                    content = execution.get('content')
                    matrix_setting = content.get('matrixSetting')
                    # 添加解析后的任务到待处理队列
                    ising_task_list.append((task_id, priority, machine_id, task_name, estimated_datetime,
                                            expected_description, project_id, page, size, matrix_setting))
                task_id_list = [ising_task[0] for ising_task in ising_task_list]
                qcos_logger.info(f"[interface: qcos_dqcosapi_handler] 任务获取策略请求返回：{task_id_list}")
                return ising_task_list

            except ValueError:
                # 日志记录无法解析的JSON
                qcos_logger.error("Failed to decode JSON from response: " + response.text)
                return []
        else:
            # 日志记录非200的响应状态码和响应体
            qcos_logger.error(f"任务获取策略请求异常：{response.status_code}: {response.text}")
            return []


class DQcosConfirmWorkloadStrategy(QCOSRequestStrategy):
    """
    任务确认策略
    """

    def execute(self, url, data=None):
        url = f"{url}/workload/confirmation"
        headers = {
            'Content-Type': 'application/json',
            'X-Request-From': 'QCOS'
        }

        response = requests.post(url, data=json.dumps(data), headers=headers)

        qcos_logger.info(f"[interface: qcos_dqcosqpi_handler] 任务确认策略请求返回：{response.status_code}")
        return response.status_code


class DQcosReceiveWorkloadResultStrategy(QCOSRequestStrategy):
    """
    任务结果上报策略
    """

    def execute(self, url, data=None):
        url = f"{url}/workload/result"
        headers = {
            'Content-Type': 'application/json',
            'X-Request-From': 'QCOS'
        }

        response = requests.post(url, data=json.dumps(data), headers=headers)

        qcos_logger.info(f"[interface: qcos_dqcosqpi_handler] 任务结果策略请求返回：{response.status_code}")
        return response.status_code


class DQcosFetchCancellationStrategy(QCOSRequestStrategy):
    """
    任务取消策略
    """

    def execute(self, url, data=None):
        url = f"{url}/cancellation"
        headers = {
            'Content-Type': 'application/json',
            'X-Request-From': 'QCOS'
        }

        response = requests.post(url, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            try:
                qcos_logger.info(f"[interface: qcos_dqcosqpi_handler] 任务取消策略请求返回：{response.json()}")
                return response.json()
            except ValueError:
                # 日志记录无法解析的JSON
                qcos_logger.error(f"Failed to decode JSON from response: {response.text}")
                return None
        else:
            # 日志记录非200的响应状态码和响应体
            qcos_logger.error(f"任务取消策略请求异常：{response.status_code}: {response.text}")
            return None


class DQcosReceiveCancellationResultStrategy(QCOSRequestStrategy):
    """
    任务取消结果策略
    """

    def execute(self, url, data=None):
        url = f"{url}/cancellation/result"
        headers = {
            'Content-Type': 'application/json',
            'X-Request-From': 'QCOS'
        }

        response = requests.post(url, data=json.dumps(data), headers=headers)

        qcos_logger.info(f"[interface: qcos_dqcosqpi_handler] 取消结果策略请求返回：{response.status_code}")
        return response.status_code
