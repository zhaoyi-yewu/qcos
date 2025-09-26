#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-09
# ------------------------


import asyncio
import os.path
import zipfile
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from enum import Enum, unique
from qcos.interface.qcos_int_instance import qcos_isingapi_handler
from qcos.interface.qcos_isingapi_handler_strategy import IsingTaskType
from qcos.interface.qcos_task_manager import qcos_task_id_generator
from qcos.log.qcos_log import QCOSLogger
from qcos.config.qcos_config_manager import qcos_configer
from qcos.interface.qcos_int_instance import qcos_dqcosapi_handler, qcos_xternalapi_handler
from qcos.memory.qcos_mem_task_scheduler import TaskStatus, qcos_scheduler

qcos_logger = QCOSLogger()


@unique
class IsingTaskStatus(Enum):
    """
    Ising任务的状态
    """
    QUEUING = 0
    COMPUTING = 1
    COMPLETED = 5
    FAILED = 6


class QCOSTaskHandler(ABC):
    """
    任务源抽象基类
    """

    @abstractmethod
    async def fetch_tasks(self) -> List[Dict[str, Any]]:
        """
        获取任务的抽象方法

        返回:
        List[Dict[str, Any]]: 获取到的任务列表
        """
        pass

    @abstractmethod
    async def send_results(self):
        """
        发送任务处理结果的抽象方法

        参数:
        results (List[Dict[str, Any]]): 处理结果列表
        """
        pass


class DQCOSTaskHandler(QCOSTaskHandler):
    """
    DQCOS任务源类
    """

    def __init__(self, qcos_instance):
        """
        初始化DQCOSTaskSource实例

        参数:
        qcos_instance: QCOSInstance实例对象
        """
        self.qcos_instance = qcos_instance
        self.openqasm_task_list = []

    async def fetch_tasks(self) -> List:
        """
        从DQCOS获取任务

        返回:
        List: 获取到的任务列表
        """
        # 使用DqcosFetchWorkloadStrategy获取任务
        fetch_tasks_data = {
            "workload":
                {
                    "limit": qcos_configer.get_fetch_task_num(),
                    "strategyName": "fetch_workload"
                }
        }

        # 使用 DQcosFetchWorkloadStrategy 拉取任务
        tasks = await self.qcos_instance.send_request('dqcos_fetch_workload', fetch_tasks_data)

        if not tasks:
            return []
        self.openqasm_task_list.extend(tasks)
        return tasks

    async def confirm_workload(self, task_id_list):
        """
        收到待执行 task 列表后发起任务确认

        参数:
        task_id_list (list): 收到的 task 列表
        """
        confirm_workload_data = {
            "workload":
                {
                    "confirmations": []
                }
        }
        for task_id in task_id_list:
            confirm_workload_data['workload']['confirmations'].append(task_id)

        # 使用 DQcosConfirmWorkloadStrategy 反馈任务确定
        await self.qcos_instance.send_request('dqcos_confirm_workload', confirm_workload_data)

    async def fetch_cancellation(self):
        """
        向 DQCOS 拉取需要取消的任务
        """
        fetch_cancellation_data = {
            "cancellation": {
                "selection": {
                    "limit": qcos_configer.get_fetch_cancellation_task_num(),
                    "strategyName": "string"
                }
            }
        }
        # 使用 DQcosFetchCancellationStrategy 获取需要取消的任务列表
        cancellation_tasks = await self.qcos_instance.send_request('dqcos_fetch_cancellation', fetch_cancellation_data)
        return cancellation_tasks['cancellations']

    async def receive_cancellation_result(self, task_id_list):
        """
        向 DQCOS 上报需要取消的 OpenQASM 任务是否可以被取消

        参数:
        task_id_list (list): 收到需要取消的 task 列表
        """
        receive_cancellation_result_data = {
            "cancellation": {
                "results": []
            }
        }
        for task_id in task_id_list:
            task_status = qcos_scheduler.get_task_status(task_id)
            if not task_status: continue
            is_delete = False
            if task_status is TaskStatus.PENDING:
                # 取消任务
                is_delete = await qcos_scheduler.cancel_task(task_id)
                if is_delete:
                    receive_cancellation_result_data['cancellation']['results'].append(
                        {
                            "id": task_id,
                            "isCancelled": True
                        }
                    )
            if not is_delete:
                receive_cancellation_result_data['cancellation']['results'].append(
                    {
                        "id": task_id,
                        "isCancelled": False
                    }
                )

        # 使用 DQcosReceiveCancellationResultStrategy 反馈任务取消结果
        await self.qcos_instance.send_request('dqcos_receive_cancellation_result', receive_cancellation_result_data)

    async def send_results(self):
        """
        监听并向 DQCOS 发送执行完成任务的结果
        """
        while True:
            try:
                if not self.openqasm_task_list:
                    # 若没有需要发送的任务则等待一个周期
                    await asyncio.sleep(qcos_configer.get_send_task_wait_time())
                    continue

                receive_workload_result_data = {
                    "workload":
                        {
                            "results": []
                        }
                }
                # 监听调度器中任务的执行结果，完成后发送给 DQCOS
                ending_tasks = []
                for origin_id in self.openqasm_task_list:
                    task_id = next((k for k, v in qcos_task_id_generator.reverse_map.items() if v == origin_id), None)
                    if task_id is None: continue
                    if qcos_scheduler.get_task_status(task_id) == TaskStatus.COMPLETED:
                        result = {
                            "id": origin_id,
                            "result": qcos_scheduler.get_task_result(task_id)
                        }
                        receive_workload_result_data['workload']['results'].append(result)
                        ending_tasks.append(origin_id)
                    elif qcos_scheduler.get_task_status(task_id) in (TaskStatus.FAILED, TaskStatus.CANCELLED):
                        result = {
                            "id": origin_id,
                            "message": "Failed"
                        }
                        receive_workload_result_data['workload']['results'].append(result)
                        ending_tasks.append(origin_id)
                self.openqasm_task_list = [task for task in self.openqasm_task_list if task not in ending_tasks]

                # 使用 DQcosReceiveWorkloadResultStrategy 发送处理结果
                await self.qcos_instance.send_request('dqcos_receive_workload_result', receive_workload_result_data)
                receive_workload_result_data['workload']['results'].clear()
            except asyncio.CancelledError:
                break


class ISINGTaskHandler(QCOSTaskHandler):
    """
    ISING 任务源类
    """

    def __init__(self, ising_instance):
        """
        初始化 ISING 任务源类

        参数:
        ising_instance: IsingInstance 实例对象
        """
        self.ising_instance = ising_instance
        self.ising_task_dict = {}

    async def fetch_tasks(self):
        """
        获取 Ising 任务

        返回:
        List: 获取到的任务列表
        """
        # 使用 DQcosFetchIsingWorkloadStrategy 从 DQCOS 获取任务
        fetch_tasks_data = {
            "workload":
                {
                    "limit": qcos_configer.get_fetch_task_num(),
                    "strategyName": "fetch_ising_workload"
                }
        }

        async def submit_task(ising_task):

            try:
                task_id, priority, machine_id, task_name, estimated_datetime, expected_description, project_id, page, size, matrix_setting = ising_task
            except ValueError as e:
                raise ValueError(f"Incorrect information on incoming ising task data: {e}")

            # 上传矩阵的csv文件
            upload_status_code, upload_response_data = await self.ising_instance.send_request("ising_task",
                                                                                              IsingTaskType.TERMINAL_UPLOAD_FILE.value,
                                                                                              matrix_setting)
            if upload_status_code != 200:
                qcos_logger.error(f"Failed to post upload file on task {task_id}, errcode is {upload_status_code}")
                return

            submit_request_data = {
                "query_params": {
                    "data": [{
                        "priority": priority,
                        "user_id": upload_response_data['data']['creator'],
                        "machine_id": machine_id,
                        "task_name": task_name,
                        "file_id": upload_response_data['data']['id'],
                        "csv_name": upload_response_data['data']['name'],
                        "estimated_datetime": estimated_datetime,
                        "expected_description": expected_description,
                        "project_id": project_id
                    }]
                }
            }
            # 提交任务
            submit_status_code, submit_response_data = await self.ising_instance.send_request("ising_task",
                                                                                              IsingTaskType.TERMINAL_BATCH_TASK.value,
                                                                                              submit_request_data)
            if submit_status_code != 200:
                qcos_logger.error(f"Failed to post batch task on task {task_id}, errcode is {submit_status_code}")
                return

            machine_task_request_data = {
                "query_params": {
                    "data": {
                        "page": page,
                        "size": size,
                        "task_name": task_name
                    }
                }
            }
            machine_task_status_code, machine_task_response_data = await self.ising_instance.send_request("ising_task",
                                                                                                          IsingTaskType.TERMINAL_MACHINE_TASK.value,
                                                                                                          machine_task_request_data)
            if machine_task_status_code != 200:
                qcos_logger.error(f"Failed to get machine task id on task {task_id}, errcode is {machine_task_status_code}")
                return
            self.ising_task_dict[task_id] = machine_task_response_data['data']['data'][0]['id']

        # 使用 DQcosFetchWorkloadStrategy 拉取任务
        ising_tasks = await qcos_dqcosapi_handler.send_request('dqcos_fetch_ising_workload', fetch_tasks_data)
        # 向伊辛机提交任务
        ending_tasks = [submit_task(ising_task) for ising_task in ising_tasks]
        await asyncio.gather(*ending_tasks)

        # Todo：从其他地方获取任务
        # response = await self.ising_instance.send_request(strategy_type, ising_task_type, data)

    async def receive_cancellation_result(self, task_id_list):
        """
        向 DQCOS 上报需要取消的 Ising 任务是否可以被取消

        参数:
        task_id_list (list): 收到需要取消的 task 列表
        """
        receive_cancellation_result_data = {
            "cancellation": {
                "results": []
            }
        }

        async def delete_task(task_id):

            fail_info = {
                "id": task_id,
                "isCancelled": False
            }

            if task_id not in self.ising_task_dict.keys():
                qcos_logger.error(f"Task {task_id} not in ising_task_dict")
                receive_cancellation_result_data['cancellation']['results'].append(fail_info)
                return
            # 使用 task_id 查询任务状态是否已经执行
            check_data = {
                "query_params":
                    {
                        "task_id": self.ising_task_dict[task_id]
                    }
            }
            check_status_code, check_response_data = await self.ising_instance.send_request("ising_task",
                                                                                            IsingTaskType.TERMINAL_MACHINE_TASK_INFO.value,
                                                                                            check_data)
            if check_status_code != 200:
                qcos_logger.error(f"Failed to obtain task status on task {task_id}, errcode is {check_status_code}")
                receive_cancellation_result_data['cancellation']['results'].append(fail_info)
                return
            delete_status_code = 404
            task_status = check_response_data['data']['status']
            if task_status == IsingTaskStatus.QUEUING.value:
                # 向 Ising 请求删除任务策略
                delete_status_code, _ = await self.ising_instance.send_request("ising_task",
                                                                               IsingTaskType.TERMINAL_MACHINE_TASK_DELETE.value,
                                                                               check_data)

                if delete_status_code == 200:
                    receive_cancellation_result_data['cancellation']['results'].append(
                        {
                            "id": task_id,
                            "isCancelled": True
                        }
                    )
            if delete_status_code != 200:
                receive_cancellation_result_data['cancellation']['results'].append(
                    {
                        "id": task_id,
                        "isCancelled": False
                    }
                )

        # 尝试取消任务
        cancel_tasks = [delete_task(ising_task_id) for ising_task_id in task_id_list]
        await asyncio.gather(*cancel_tasks)

        # 使用 DQcosReceiveCancellationResultStrategy 反馈任务取消结果
        await qcos_dqcosapi_handler.send_request('dqcos_receive_cancellation_result', receive_cancellation_result_data)

    async def send_results(self):
        """
        向 DQCOS 发送执行完成的 Ising 任务列表
        """
        while True:
            try:
                if not self.ising_task_dict:
                    # 若没有需要发送的任务则等待一个周期
                    await asyncio.sleep(qcos_configer.get_send_task_wait_time())
                    continue

                receive_workload_result_data = {
                    "workload":
                        {
                            "results": []
                        }
                }

                async def get_task_result(task_id):

                    # 使用 task_id 查询任务状态，如果任务状态是已完成，继续查询任务详情
                    check_data = {
                        "query_params":
                            {
                                "task_id": self.ising_task_dict[task_id]
                            }
                    }
                    status_code, response_data = await self.ising_instance.send_request("ising_task",
                                                                                        IsingTaskType.TERMINAL_MACHINE_TASK_INFO.value,
                                                                                        check_data)
                    if status_code != 200:
                        qcos_logger.error(f"Failed to obtain task status on task {task_id}, errcode is {status_code}")
                        return
                    task_status = response_data['data']['status']
                    if task_status == IsingTaskStatus.FAILED.value:
                        failed_result = {
                            "id": task_id,
                            "message": response_data['data']['description']
                        }
                        receive_workload_result_data['workload']['results'].append(failed_result)
                        qcos_logger.error(f"Failed to execute task {task_id}")
                        return task_id
                    elif task_status == IsingTaskStatus.COMPLETED.value:
                        # 下载任务结果, 即任务结果的解向量
                        download_data = {
                            "query_params": {
                                "type": 1,  # 1:下载结果 2：下载报告
                                "ids": self.ising_task_dict[task_id]
                            }
                        }
                        status_code, zip_file_path = await self.ising_instance.send_request("ising_task",
                                                                                            IsingTaskType.TERMINAL_DOWNLOAD_TASK.value,
                                                                                            download_data)
                        if status_code != 200:
                            qcos_logger.error(f"Failed to obtain task result on task {task_id}, errcode is {status_code}")
                            return
                        # 解析下载的结果文件
                        is_success = False
                        try:
                            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                                file_names = zip_ref.namelist()
                                if len(file_names) != 1:
                                    raise ValueError(f"Incorrect number of resultant documents on task {task_id}")
                                with zip_ref.open(file_names[0]) as file:
                                    result = file.read().decode('utf-8')
                                    task_result = {
                                        "id": task_id,
                                        "result": result
                                    }
                            receive_workload_result_data['workload']['results'].append(task_result)
                            is_success = True
                        except FileNotFoundError:
                            qcos_logger.error(f"Resulting document of task {task_id} not found: {zip_file_path} ")
                        except Exception as e:
                            qcos_logger.error(f"Failed to get task {task_id} result: {e}")
                        finally:
                            if os.path.exists(zip_file_path):
                                os.remove(zip_file_path)
                            if is_success: return task_id

                # 监听 Ising 任务的执行结果
                send_tasks = [get_task_result(ising_task_id) for ising_task_id in self.ising_task_dict.keys()]
                ending_tasks = await asyncio.gather(*send_tasks)

                self.ising_task_dict = {
                    key: value for key, value in self.ising_task_dict.items() if key not in ending_tasks}

                # 使用 DQcosReceiveWorkloadResultStrategy 发送处理结果
                if receive_workload_result_data['workload']['results']:
                    await qcos_dqcosapi_handler.send_request('dqcos_receive_workload_result', receive_workload_result_data)
            except asyncio.CancelledError:
                break


class XTERNALTaskHandler(QCOSTaskHandler):
    """
    XTERNAL任务源类
    """

    def __init__(self, openqasm_instance):
        """
        初始化XTERNAL任务源类

        参数:
        qcos_instance: OpenqasmInstance实例对象
        """
        self.openqasm_instance = openqasm_instance

    async def fetch_tasks(self) -> List[Dict[str, Any]]:
        """
        从XTERNAL获取任务

        返回:
        List[Dict[str, Any]]: 获取到的任务列表
        """

        # 使用XternalFetchWorkloadStrategy获取任务
        tasks = self.openqasm_instance.send_request('xternal_fetch_openqasm')
        if tasks:
            return tasks
        else:
            # raise ValueError(f"从xternal任务源获取openqasm任务失败： tasks={tasks}")
            qcos_logger.debug("当前未从xternal任务源获取到openqasm任务")

    async def send_results(self):
        """
        向XTERNAL发送任务处理结果

        参数:
        results (List[Dict[str, Any]]): 处理结果列表
        """
        # Todo
        # 实现XTERNAL特定的结果发送逻辑
        # task_result_path = self.openqasm_instance.execute_openqasm('xternal_save_openqasm', results)
        # print(f"结果保存到： {task_result_path}")
        pass


class QCOSTaskHandlerFactory:
    """
    任务源工厂类
    """

    @staticmethod
    def get_task_source(source_type: str, instance=None) -> QCOSTaskHandler:
        """
        获取指定类型的任务源实例

        参数:
        source_type (str): 任务源类型
        instance: QCOS实例对象或Openqasm实例对象（可选）

        返回:
        TaskSource: 任务源实例
        """
        if source_type == "DQCOS":
            return DQCOSTaskHandler(instance)
        elif source_type == "ISING":
            return ISINGTaskHandler(instance)
        elif source_type == "XTERNAL":
            return XTERNALTaskHandler(instance)
        else:
            raise ValueError(f"不支持的任务源类型: {source_type}")


class QCOSTaskManager:
    """
    量子操作系统任务管理器类
    负责管理多个任务源、处理任务并发送结果
    """

    def __init__(self, config):
        """
        QCOSTaskManager

        参数:
        config (QCOSConfig): 配置对象
        """
        self.config = config
        self.logger = QCOSLogger()
        self.task_sources = []
        for source_type in config.get_task_sources():
            if source_type == "DQCOS":
                self.task_sources.append(QCOSTaskHandlerFactory.get_task_source(source_type, qcos_dqcosapi_handler))
            elif source_type == "XTERNAL":
                self.task_sources.append(QCOSTaskHandlerFactory.get_task_source(source_type, qcos_xternalapi_handler))
            elif source_type == "ISING":
                self.task_sources.append(QCOSTaskHandlerFactory.get_task_source(source_type, qcos_isingapi_handler))
            else:
                raise ValueError(f"不支持的任务源类型: {source_type}")

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个任务

        参数:
        task (Dict[str, Any]): 待处理的任务

        返回:
        Dict[str, Any]: 处理结果
        """
        # TODO:实现实际的任务处理逻辑
        # 当前假设所有任务都处理成功
        qcos_logger.debug(f"处理单任务：{task['id']}")
        return {
            "id": task['id'],
            "result": "success",
            # "isFailed": False,
            "message": ""
        }

    async def run(self):
        """
        运行任务处理循环
        """
        self.logger.info("[interface: qcos_api_manager] 获取待处理任务")

        for task_source in self.task_sources:
            # 监听任务，返回执行结果
            if isinstance(task_source, (DQCOSTaskHandler, ISINGTaskHandler)):
                asyncio.run(task_source.send_results())

        while True:
            try:
                cancellation_tasks = []
                for task_source in self.task_sources:
                    # 获取任务
                    tasks = await task_source.fetch_tasks()
                    if isinstance(task_source, DQCOSTaskHandler):
                        if tasks:
                            # 收到待执行 task 列表后发起任务确认
                            await task_source.confirm_workload(tasks)
                        # 向 DQCOS 拉取需要取消的任务
                        cancellation_tasks = await task_source.fetch_cancellation()

                    # 如果需要取消任务，则 DQCOSTaskHandler 与 ISINGTaskHandler 分别向 DQCOS 反馈任务取消结果
                    if cancellation_tasks and isinstance(task_source, (DQCOSTaskHandler, ISINGTaskHandler)):
                        await task_source.receive_cancellation_result(cancellation_tasks)

                # 等待指定的时间间隔
                await asyncio.sleep(self.config.get_fetch_interval())

            except Exception as e:
                qcos_logger.debug(f"任务处理过程信息: {str(e)}")
                # 发生错误时等待一段时间再继续
                await asyncio.sleep(self.config.get_error_wait_time())


async def main():
    """
    主函数，初始化并运行QCOSTaskManager
    """
    # 初始化配置
    # config = qcos_configer

    # 初始化配置,创建并运行任务管理器
    manager = QCOSTaskManager(qcos_configer)
    await manager.run()


qcos_api_inst_manager = QCOSTaskManager(qcos_configer)

if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())
