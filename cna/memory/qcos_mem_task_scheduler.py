#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-08
# ------------------------


import os
import queue
import threading
import numpy as np
import asyncio
import heapq
from typing import Callable, Any, Dict, List, Optional, Type, Iterator, Tuple
from enum import Enum, auto
import time
from collections import deque
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import lru_cache
from qcos.cna.core.mapping.na_mapping import *
from qcos.cna.core.compiler.parser import *
from qcos.cna.core.config import GlobalSetting, InstrumentType
from qcos.memory.qcos_mem_task_manager import QuantumCircuitTask
from qcos.interface.qcos_task_manager import *
from qcos.config.qcos_config_manager import qcos_configer
from qcos.log.qcos_log import QCOSLogger
from qcos.cna.core.pulse import awg_trigger
from qcos.cna.core.compiler.decompose import GateType


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TaskStatus(Enum):
    """
    表示任务的不同状态
    """
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class TaskObserver(ABC):
    """
    任务观察者接口，用于实现观察者模式
    """

    @abstractmethod
    def update(self, task: 'BaseTask'):
        """
        更新方法，当被观察的任务状态改变时调用

        参数:
        task (BaseTask): 状态发生变化的任务
        """
        pass


class TaskSubject(ABC):
    """
    被观察者基类，用于实现观察者模式
    """

    def __init__(self):
        """
        初始化被观察者
        """
        self._observers: List[TaskObserver] = []

    def attach(self, observer: TaskObserver):
        """
        添加观察者

        参数:
        observer (TaskObserver): 要添加的观察者
        """
        self._observers.append(observer)

    def detach(self, observer: TaskObserver):
        """
        移除观察者

        参数:
        observer (TaskObserver): 要移除的观察者
        """
        self._observers.remove(observer)

    def notify(self):
        """
        通知所有观察者
        """
        for observer in self._observers:
            observer.update(self)


class BaseTask(TaskSubject):
    """
    所有任务类型的抽象基类
    """

    def __init__(self, priority: int, shots: int):
        """
        初始化基础任务

        参数:
        priority (int): 任务优先级
        shots (int): 执行次数
        """
        super().__init__()
        self.task = QuantumCircuitTask
        self.priority = priority
        self.shots = shots
        self.response_ratio = 0
        self._status = TaskStatus.PENDING
        self.result = None
        self.created_time = time.time()
        self.run_cost = 0
        self.task_queue = asyncio.PriorityQueue()

    @property
    def status(self) -> TaskStatus:
        """
        获取任务状态

        返回:
        TaskStatus: 当前任务状态
        """
        return self._status

    @status.setter
    def status(self, value: TaskStatus):
        """
        设置任务状态并通知观察者

        参数:
        value (TaskStatus): 新的任务状态
        """
        self._status = value
        self.notify()

    @abstractmethod
    async def execute(self):
        """
        执行任务的抽象方法
        """
        pass

    def __lt__(self, other):
        """
        比较任务优先级

        参数:
        other (BaseTask): 另一个任务

        返回:
        bool: 当前任务是否优先级更高
        """
        return (self.priority, -self.response_ratio, self.run_cost, self.created_time) < (
            other.priority, -other.response_ratio, other.run_cost, other.created_time)


class PriorityTask(BaseTask):
    """
    表示一个带有优先级的量子任务
    """

    def __init__(self, priority: int, shots: int, task: QuantumCircuitTask):
        """
        初始化优先级任务

        参数:
        priority (int): 任务优先级
        shots (int): 执行次数
        task (QuantumCircuitTask): 量子电路任务
        """
        super().__init__(priority, shots)
        self.task = task

    async def execute(self):
        """
        执行优先级任务
        """
        self.status = TaskStatus.RUNNING
        try:
            self.result = await self.task.execute()
            # self.status = TaskStatus.COMPLETED
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.result = str(e)
            qcos_logger.error(f"Task {self.task.task_id} failed: {e}")


class ResponseRatioTask(BaseTask):
    """
    高响应比调度执行任务
    """

    def __init__(self, priority: int, shots: int, task: QuantumCircuitTask, task_queue):
        """
        初始化高响应比优先级任务

        参数:
        priority (int): 任务优先级
        shots (int): 执行次数
        task (QuantumCircuitTask): 量子电路任务
        """
        super().__init__(priority, shots)
        self.task = task
        self.task_queue = task_queue["ResponseRatioTask"]
        # 利用OpenQASM指令的规模估计任务的执行消耗
        openqasm_size = sum(1 for line in self.task.openqasm_content.splitlines() if line.strip())
        self.run_cost = openqasm_size * self.shots
        # 计算任务的响应比
        self.response_ratio = self._calculate_response_ratio(time.time())
        # 更新任务列表中ResponseRatioTask类任务的响应比
        self._update_response_ratio()

    def _calculate_response_ratio(self, current_time):
        """
        计算量子任务的响应比

        参数：
        current_time (time_t): 当前时间

        返回:
        response_ratio (float): 任务响应比
        """
        if self.run_cost == 0:
            qcos_logger.error(f"量子电路执行消耗为0")
            return 0
        response_ratio = (current_time - self.created_time + self.run_cost) / self.run_cost
        return response_ratio

    def _update_response_ratio(self):
        """
        更新优先队列中ResponseRatioTask任务的响应比
        """
        # 统一当前时间
        current_time = time.time()
        # 更新响应比
        for task in self.task_queue._queue:
            if isinstance(task, ResponseRatioTask):
                task.response_ratio = task._calculate_response_ratio(current_time)

    async def execute(self):
        """
        执行高响应比优先级任务
        """
        self.status = TaskStatus.RUNNING
        try:
            self.result = await self.task.execute()
            # self.status = TaskStatus.COMPLETED
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.result = str(e)
            qcos_logger.error(f"Task {self.task.task_id} failed: {e}")


class ShortestJobFirstTask(BaseTask):
    """
    短作业优先调度执行任务
    """

    def __init__(self, priority: int, shots: int, task: QuantumCircuitTask):
        """
        初始化短作业优先调度任务

        参数:
        priority (int): 任务优先级
        shots (int): 执行次数
        task (QuantumCircuitTask): 量子电路任务
        """
        super().__init__(priority, shots)
        self.task = task
        # 利用OpenQASM指令的规模估计任务的执行消耗
        openqasm_size = sum(1 for line in self.task.openqasm_content.splitlines() if line.strip())
        self.run_cost = openqasm_size * self.shots

    async def execute(self):
        """
        执行短作业优先级任务
        """
        self.status = TaskStatus.RUNNING
        try:
            self.result = await self.task.execute()
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.result = str(e)
            qcos_logger.error(f"Task {self.task.task_id} failed: {e}")


class TimePrecedenceTask(BaseTask):
    """
    按任务创建时间顺序调度量子任务
    """

    def __init__(self, priority: int, shots: int, task: QuantumCircuitTask):
        """
        初始化按任务创建时间顺序调度任务

        参数:
        priority (int): 任务优先级
        shots (int): 执行次数
        task (QuantumCircuitTask): 量子电路任务
        """
        super().__init__(priority, shots)
        self.task = task
        self.priority = 1

    async def execute(self):
        """
        执行按任务创建时间顺序调度任务
        """
        self.status = TaskStatus.RUNNING
        try:
            self.result = await self.task.execute()
            # self.status = TaskStatus.COMPLETED
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.result = str(e)
            qcos_logger.error(f"Task {self.task.task_id} failed: {e}")


class PeriodicTask(BaseTask):
    """
    周期性执行的任务
    """

    def __init__(self, priority: int, shots: int, task: QuantumCircuitTask, interval: float):
        """
        初始化周期性任务

        参数:
        priority (int): 任务优先级
        shots (int): 执行次数
        task (QuantumCircuitTask): 要执行的量子任务
        interval (float): 任务执行间隔（秒）
        """
        super().__init__(priority, shots)
        self.task = task
        self.interval = interval

    async def execute(self):
        """
        执行周期性任务
        """
        while True:
            self.status = TaskStatus.RUNNING
            try:
                self.result = await self.task.execute()
                # self.status = TaskStatus.COMPLETED
            except Exception as e:
                self.status = TaskStatus.FAILED
                self.result = str(e)
            await asyncio.sleep(self.interval)


class DependentTask(BaseTask):
    """
    依赖于其他任务完成的任务
    """

    def __init__(self, priority: int, shots: int, task: QuantumCircuitTask, dependencies: List[BaseTask]):
        """
        初始化依赖任务

        参数:
        priority (int): 任务优先级
        shots (int): 执行次数
        task (QuantumCircuitTask): 要执行的量子任务
        dependencies (List[BaseTask]): 依赖的任务列表
        """
        super().__init__(priority, shots)
        self.task = task
        self.dependencies = dependencies

    async def execute(self):
        """
        执行依赖任务
        """
        await asyncio.gather(*[dep.execute() for dep in self.dependencies])
        self.status = TaskStatus.RUNNING
        try:
            self.result = await self.task.execute()
            # self.status = TaskStatus.COMPLETED
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.result = str(e)


class BatchTask(BaseTask):
    """
    批量处理多个子任务的任务
    """

    def __init__(self, priority: int, shots: int, tasks: List[QuantumCircuitTask], **kwargs):
        """
        初始化批处理任务

        参数:
        priority (int): 任务优先级
        shots (int): 执行次数
        tasks (List[QuantumCircuitTask]): 要批量执行的量子任务列表
        """
        super().__init__(priority, shots)
        self.tasks = tasks

    async def execute(self):
        """
        执行批处理任务
        """
        self.status = TaskStatus.RUNNING
        try:
            self.result = await asyncio.gather(*[task.execute() for task in self.tasks])
            # self.status = TaskStatus.COMPLETED
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.result = str(e)


class RealTimeTask(BaseTask):
    """
    需要实时响应的任务
    """

    def __init__(self, priority: int, shots: int, task: QuantumCircuitTask, deadline: float):
        """
        初始化实时任务

        参数:
        priority (int): 任务优先级
        shots (int): 执行次数
        task (QuantumCircuitTask): 要执行的量子任务
        deadline (float): 任务截止时间（秒）
        """
        super().__init__(priority, shots)
        self.task = task
        self.deadline = deadline

    async def execute(self):
        """
        执行实时任务
        """
        self.status = TaskStatus.RUNNING
        try:
            self.result = await asyncio.wait_for(self.task.execute(), timeout=self.deadline)
            # self.status = TaskStatus.COMPLETED
        except asyncio.TimeoutError:
            self.status = TaskStatus.FAILED
            self.result = "任务超时"
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.result = str(e)


class TaskFactory:
    """
    创建不同类型的任务的工厂类
    """
    _task_mapping: Dict[str, Type[BaseTask]] = {
        "PriorityTask": PriorityTask,
        "ResponseRatioTask": ResponseRatioTask,
        "ShortestJobFirstTask": ShortestJobFirstTask,
        "TimePrecedenceTask": TimePrecedenceTask,
        "PeriodicTask": PeriodicTask,
        "DependentTask": DependentTask,
        "BatchTask": BatchTask,
        "RealTimeTask": RealTimeTask,
    }

    @classmethod
    def register_task_type(cls, task_type: str, task_class: Type[BaseTask]):
        """
        注册新的任务类型

        参数:
        task_type (str): 任务类型名称
        task_class (Type[BaseTask]): 任务类
        """
        cls._task_mapping[task_type] = task_class

    @classmethod
    def create_task(cls, task_type: str, priority: int, shots: int, **kwargs) -> BaseTask:
        """
        创建指定类型的任务

        参数:
        task_type (str): 任务类型
        priority (int): 任务优先级
        shots (int): 执行次数
        **kwargs: 任务参数

        返回:
        BaseTask: 创建的任务

        抛出:
        ValueError: 如果任务类型未知
        """
        TaskClass = cls._task_mapping.get(task_type)
        if TaskClass:
            return TaskClass(priority, shots, **kwargs)
        raise ValueError(f"未知的任务类型: {task_type}")


class TaskStatusLogger(TaskObserver):
    """
    任务状态日志记录器
    """

    def update(self, task: BaseTask):
        """
        更新任务状态日志

        参数:
        task (BaseTask): 状态发生变化的任务
        """
        qcos_logger.info(f"任务 {task.task.task_id} 状态更新为: {task.status}")


class QuantumTaskScheduler:
    """
    管理和调度量子任务的执行
    """

    def __init__(self, max_concurrent_tasks: int = 10):
        """
        初始化量子任务调度器

        参数:
        max_concurrent_tasks (int): 最大并发任务数，默认为10
        """
        self.task_queue = {
            "PriorityTask": asyncio.PriorityQueue(),
            "ResponseRatioTask": asyncio.PriorityQueue(),
            "ShortestJobFirstTask": asyncio.PriorityQueue(),
            "TimePrecedenceTask": asyncio.PriorityQueue(),
            "PeriodicTask": asyncio.PriorityQueue(),
            "DependentTask": asyncio.PriorityQueue(),
            "BatchTask": asyncio.PriorityQueue(),
            "RealTimeTask": asyncio.PriorityQueue(),
        }
        self.running_tasks: Dict[str, BaseTask] = {}
        self.completed_tasks = deque(maxlen=1000)  # 限制已完成任务的最大数量
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_logger = TaskStatusLogger()
        self.task_id_counter = 0  # 增加一个任务ID计数器，用于生成唯一的任务ID
        self.result_queue = asyncio.PriorityQueue()  # 存储解析完成的任务
        self.parsed_tasks = []  # 存储待下发到硬件执行的任务
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.measure_thread = threading.Thread(target=self.measure_task_result,
                                               args=(self.stop_event,))  # 创建线程执行解析完成的任务

    @asynccontextmanager
    async def managed_thread_pool(self):
        """
        使用异步上下文管理器管理线程池
        """
        with ThreadPoolExecutor(max_workers=self.max_concurrent_tasks) as executor:
            yield executor

    async def add_task(self, task_id: str, task_type: str, priority: int, shots: int, is_aggregation=False,
                       openqasm_content=None, aggregation_tasks=None, qubit_blocks=None, sum_qubit=0, **kwargs) -> Optional[str]:
        """
        添加一个新任务到调度队列

        参数:
        task_id (str): 任务ID
        task_type (str): 任务类型
        priority (int): 任务优先级
        shots (int): 执行次数
        is_aggregation (int): 是否为聚合任务
        openqasm_content (str): OpenQASM 代码内容
        aggregation_tasks (list): 聚合的任务列表
        qubit_blocks (list): 聚合任务对应的比特分区
        sum_qubit (int): 聚合任务所用到的量子比特数
        **kwargs: 其他任务参数

        返回:
        Optional[str]: 任务ID，如果分配失败则返回None
        """
        if not is_aggregation and not openqasm_content:
            qcos_logger.warning(f"OpenQASM代码内容为空，任务 {task_id} 添加失败")
        elif is_aggregation and not (aggregation_tasks or qubit_blocks or sum_qubit):
            qcos_logger.warning(f"任务分区聚合有误，聚合任务 {task_id} 添加失败")
        else:
            # 分配量子电路任务
            quantum_task = QuantumCircuitTask(task_id)
            try:
                if is_aggregation:
                    quantum_task.set_aggregation_task(aggregation_tasks, qubit_blocks, sum_qubit, shots)
                else:
                    quantum_task.set_openqasm_content(openqasm_content, shots)
                # 创建任务并添加到队列
                task = TaskFactory.create_task(
                    task_type=task_type,
                    priority=priority,
                    shots=shots,
                    task=quantum_task,
                    **kwargs
                )
                task.attach(self.task_logger)
                await self._put_in_queue(task, task_type)
                return task_id
            except ValueError as e:
                qcos_logger.warning(f"任务创建时出错:{e}，任务 {task_id} 添加失败")
        return None

    async def _put_in_queue(self, task, task_type):
        """
        根据任务类型将任务划分到不同队列

        参数:
        task (BaseTask): 待添加的任务
        task_type (str): 任务类型
        """
        if task_type == "TimePrecedenceTask":
            await self.task_queue["TimePrecedenceTask"].put(task)
        elif task_type == "PriorityTask":
            await self.task_queue["PriorityTask"].put(task)
        elif task_type == "ResponseRatioTask":
            await self.task_queue["ResponseRatioTask"].put(task)
        elif task_type == "ShortestJobFirstTask":
            await self.task_queue["ShortestJobFirstTask"].put(task)
        elif task_type == "PeriodicTask":
            await self.task_queue["PeriodicTask"].put(task)
        elif task_type == "DependentTask":
            await self.task_queue["DependentTask"].put(task)
        elif task_type == "BatchTask":
            await self.task_queue["BatchTask"].put(task)
        elif task_type == "RealTimeTask":
            await self.task_queue["RealTimeTask"].put(task)
        else:
            raise ValueError(f"未知的任务类型: {task_type}")

    async def stop(self):
        """
        停止任务调度器
        """
        # 取消所有等待中的任务
        for queue in self.task_queue.values():
            while not queue.empty():
                task = await queue.get()
                task.status = TaskStatus.CANCELLED
        # 等待所有正在运行的任务完成
        while self.running_tasks:
            await asyncio.sleep(0.1)
        # 等待所有任务收集完成
        while not self.result_queue.empty():
            await asyncio.sleep(0.1)
            if self.result_queue.qsize() < qcos_configer.get_collect_task_num():
                await self._collect_processed_tasks()
        # 等待所有任务测量完成
        while self.parsed_tasks:
            await asyncio.sleep(0.1)
        # 停止处理线程
        self.stop_event.set()
        # 等待线程完成
        if self.measure_thread.is_alive():
            self.measure_thread.join()

    async def run_tasks(self, task_queue_type):
        """
        异步执行队列中的任务

        参数:
        task_queue_type (str): 调度队列的任务类型
        """
        if not self.measure_thread.is_alive():
            self.measure_thread.start()
        if task_queue_type not in self.task_queue:
            qcos_logger.error(f"未知类型任务队列：{task_queue_type}，任务调度失败")
            return

        async with self.managed_thread_pool() as executor:
            loop = asyncio.get_running_loop()
            try:
                while True:
                    if len(self.running_tasks) < self.max_concurrent_tasks:
                        try:
                            task = self.task_queue[task_queue_type].get_nowait()
                            self.running_tasks[task.task.task_id] = task
                            loop.run_in_executor(executor, asyncio.run, self._execute_task(task))
                            await asyncio.sleep(0)
                        except asyncio.QueueEmpty:
                            await asyncio.sleep(0.1)
                    else:
                        await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                # 清空待处理任务队列
                while not self.task_queue[task_queue_type].empty():
                    try:
                        task = self.task_queue[task_queue_type].get_nowait()
                        task.status = TaskStatus.CANCELLED
                    except asyncio.QueueEmpty:
                        break

                #  取消正在运行的任务
                for task_id, task in self.running_tasks.items():
                    if hasattr(task, 'cancel'):
                        task.cancel()
                    else:
                        # 如果任务不支持取消，设置一个标志位，让任务自行终止
                        task.status = TaskStatus.CANCELLED
                self.running_tasks.clear()

                qcos_logger.info(f"调度器已关闭，所有 {task_queue_type} 任务已停止。")
                # TODO:如果有其他需要关闭的资源，可以在这里处理
                # 最后重新抛出异常，或者直接返回

    async def _execute_task(self, task: BaseTask):
        """
        执行单个任务

        参数:
        task (BaseTask): 要执行的任务
        """
        '''
        #TODO:目前结束调度器以及取消任务，不取消正在执行的任务，后续可能会判断任务状态。从而中断线程池中任务
        if task.status == TaskStatus.CANCELLED:
            return
        '''
        try:
            await asyncio.wait_for(task.execute(), timeout=300)  # 5分钟超时
        except asyncio.TimeoutError:
            qcos_logger.error(f"任务 {task.task.task_id} 执行超时")
            task.status = TaskStatus.FAILED
        except Exception as e:
            qcos_logger.error(f"执行任务 {task.task.task_id} 时出错: {e}", exc_info=True)
            task.status = TaskStatus.FAILED
        else:
            if task.status != TaskStatus.FAILED:
                await self.result_queue.put(task)
                del self.running_tasks[task.task.task_id]
                with self.lock:
                    while self.result_queue.qsize() >= qcos_configer.get_collect_task_num():
                        await self._collect_processed_tasks()
        finally:
            if task.status == TaskStatus.FAILED:
                del self.running_tasks[task.task.task_id]
                self.completed_tasks.append(task)

    async def _collect_processed_tasks(self):
        """
        收集解析后的量子任务
        """
        for _ in range(min(qcos_configer.get_collect_task_num(), self.result_queue.qsize())):
            try:
                self.parsed_tasks.append(self.result_queue.get_nowait())
            except queue.Empty:
                qcos_logger.warning("结果队列为空，获取任务结果失败")
                break

    def measure_task_result(self, stop_event):
        """
        读取任务执行结果

        参数：
        stop_event (threading.Event): 线程事件
        """
        while not stop_event.is_set():
            if self.parsed_tasks:
                task = self.parsed_tasks.pop(0)
                """
                # 确定量子任务的执行结果
                GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_HW_FPGA_AWG)
                if task.task.is_aggregation:
                    # 真机执行聚合任务
                    measure_results, rea_results = task.task.execute_task_on_quantum(task.result)
                    # 聚合执行的任务
                    task_results = {key[0]: [] for key in task.task.aggregation_tasks}
                    rea_res = {key[0]: [] for key in task.task.aggregation_tasks}
                    qcos_logger.info(f"聚合任务 {task.task.task_id} 结果分别为：")
                    # 根据映射表，查找每个任务对应的结果，并分别存储
                    for ms, rs in zip(measure_results, rea_results):
                        for single_task, mapping in zip(task.task.aggregation_tasks, task.task.aggregation_mappings):
                            real_res = ['0'] * len(mapping)
                            effective_res = ['0'] * len(mapping)
                            for k, v in mapping.items():
                                real_res[k] = str(ms[int(v[1:])])
                                effective_res[k] = str(rs[int(v[1:])])
                            task_results[single_task[0]].append(''.join(real_res))
                            rea_res[single_task[0]].append(''.join(effective_res))

                    for task_id, task_result in task_results.items():
                        qcos_logger.info(f"{task_id}: {task_result}")
                        task.task.task_result[task_id] = task_result
                        self._save_task_result(task_id, task_result)

                        count = 0
                        rea_success = 0
                        for x, y in zip(rea_res[task_id], task_result):
                            if x == '1' * len(x):
                                rea_success += 1
                                if y == "00":
                                    count += 1
                        qcos_logger.info(f"重排成功率为： {count / max(rea_success, 1)}")
                else:
                    # 真机执行单任务
                    measure_results, rea_results = task.task.execute_task_on_quantum(task.result)
                    # 单独执行的任务
                    task_result = []
                    rea_res = []
                    for ms, rs in zip(measure_results, rea_results):
                        real_res = ['0'] * task.task.na_map.qnum
                        effective_res = ['0'] * task.task.na_map.qnum
                        for i in range(task.task.na_map.qnum):
                            if ms[int(task.task.na_map.mapping[i][1:])] == 1:
                                real_res[i] = '1'
                            if rs[int(task.task.na_map.mapping[i][1:])] == 1:
                                effective_res[i] = '1'
                        task_result.append(''.join(real_res))
                        rea_res.append(''.join(effective_res))
                    qcos_logger.info(f"任务 {task.task.task_id} 结果为：{task_result}")

                    count = 0
                    rea_success = 0
                    for x, y in zip(rea_res, task_result):
                        if x == '1' * len(x):
                            rea_success += 1
                            if y == "00":
                                count += 1
                    qcos_logger.info(f"重排成功率为： {count / max(rea_success, 1)}")

                    task.task.task_result[task.task.task_id] = task_result
                    self._save_task_result(task.task.task_id, task_result)
                """
                task.status = TaskStatus.COMPLETED
                self.completed_tasks.append(task)
            else:
                time.sleep(0.1)
        for task in self.parsed_tasks:
            task.status = TaskStatus.FAILED
            self.completed_tasks.append(task)

    def _save_task_result(self, task_id: str, task_result: List):
        """
        保存任务测量结果到config/task_result/xternal目录下

        参数：
        task_id (str): 任务ID
        task_result (List): 任务测量结果
        """
        if task_id in qcos_task_id_generator.reverse_map:
            original_task_id = qcos_task_id_generator.reverse_map[task_id]
        else:
            # 不通过交互接口获取任务则不会对任务进行编码
            original_task_id = task_id
            # qcos_logger.error(f"未在任务存储队列中任务 {task_id} ，任务结果为： {task_result}")
        if not os.path.exists(qcos_configer.get_task_result_path()):
            os.makedirs(qcos_configer.get_task_result_path())
        task_result_file = os.path.join(qcos_configer.get_task_result_path(), f"{original_task_id}.txt")
        with open(task_result_file, 'w') as file:
            for tr in task_result:
                file.write(tr + '\n')

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        获取指定任务的当前状态

        参数:
        task_id (str): 任务ID

        返回:
        Optional[TaskStatus]: 任务状态，如果任务不存在则返回None
        """
        if task_id in self.running_tasks:
            return self.running_tasks[task_id].status
        for task in self.completed_tasks:
            if task.task.task_id == task_id:
                return task.status
        return None

    def get_task_result(self, task_id: str) -> Any:
        """
        获取指定任务的执行结果

        参数:
        task_id (str): 任务ID

        返回:
        Any: 任务执行结果，如果任务不存在或未完成则返回None
        """
        for task in self.completed_tasks:
            if task.task.task_id == task_id:
                return task.result
        return None

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消指定的任务

        参数:
        task_id (str): 任务ID

        返回:
        bool: 是否成功取消任务
        """
        for single_queue in self.task_queue.values():
            for task in single_queue._queue:
                if task.task.task_id == task_id:
                    single_queue._queue.remove(task)
                    heapq.heapify(single_queue._queue)
                    return True
        return False

    @lru_cache(maxsize=128)
    def get_task_count(self) -> Dict[str, int]:
        """
        获取各状态的任务数量

        返回:
        Dict[str, int]: 各状态的任务数量
        """
        return {
            "pending": sum(single_queue.qsize() for single_queue in self.task_queue.values()),
            "running": len(self.running_tasks),
            "completed": len(self.completed_tasks)
        }

    def cleanup_completed_tasks(self, age: float = 3600):
        """
        清理已完成的旧任务

        参数:
        age (float): 任务完成后保留的时间(秒)，默认为1小时
        """
        current_time = time.time()
        while self.completed_tasks and current_time - self.completed_tasks[0].created_time > age:
            self.completed_tasks.popleft()

    async def monitor_task_progress(self, task_id: str, interval: float = 1.0):
        """
        监控指定任务的进度

        参数:
        task_id (str): 任务ID
        interval (float): 检查间隔时间(秒)
        """
        while True:
            status = self.get_task_status(task_id)
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                print(f"任务 {task_id} 已结束，状态: {status}")
                break
            print(f"任务 {task_id} 当前状态: {status}")
            await asyncio.sleep(interval)

    @lru_cache(maxsize=1)
    def get_task_statistics(self) -> Dict[str, Any]:
        """
        获取任务统计信息

        返回:
        Dict[str, Any]: 任务统计信息
        """
        total_tasks = (sum(single_queue.qsize() for single_queue in self.task_queue.values())
                       + len(self.running_tasks) + len(self.completed_tasks))
        sub_tasks = (sum(len(task.tasks) for task in self.completed_tasks if isinstance(task, BatchTask)) +
                     sum(len(task.task.aggregation_tasks) for task in self.completed_tasks))
        return {
            "total_tasks": total_tasks,
            "total_sub_tasks": sub_tasks,
            "average_waiting_time": self._calculate_average_waiting_time(),
            "average_execution_time": self._calculate_average_execution_time(),
            "task_distribution": self.get_task_count()
        }

    def _calculate_average_waiting_time(self) -> float:
        """
        计算平均等待时间

        返回:
        float: 平均等待时间(秒)
        """
        waiting_times = [time.time() - task.created_time for que in self.task_queue.values() for task in que._queue]
        return sum(waiting_times) / len(waiting_times) if waiting_times else 0

    def _calculate_average_execution_time(self) -> float:
        """
        计算平均执行时间

        返回:
        float: 平均执行时间(秒)
        """
        execution_times = (
            task.tasks[-1].last_active_time - task.created_time
            if isinstance(task, BatchTask) and task.tasks else
            task.task.last_active_time - task.created_time
            for task in self.completed_tasks
            if task.status == TaskStatus.COMPLETED and hasattr(task, 'task')
        )

        execution_times = list(execution_times)
        return sum(execution_times) / len(execution_times) if execution_times else 0


import asyncio


async def main():
    # 初始化量子任务调度器，设置最大并发任务数为2
    scheduler = QuantumTaskScheduler(max_concurrent_tasks=1)

    # 使用有效的 OpenQASM 内容执行代码
    valid_openqasm1 = '''
                    OPENQASM 2.0;
                    include "qelib1.inc";
                    qreg q[2];
                    creg c[2];
                    x q[0];
                    y q[1];
                    measure q -> c;
                    '''
    valid_openqasm2 = '''
                    OPENQASM 2.0;
                    include "qelib1.inc";
                    qreg q[4];
                    creg c[4];
                    x q[0];
                    y q[1];
                    h q[2];
                    z q[3];
                    measure q -> c;
                    '''
    # 创建并添加不同类型的任务到调度队列中
    tasks = [
        ("task1", "ResponseRatioTask", 1, 100, valid_openqasm2, {"task_queue": scheduler.task_queue}),
        ("task2", "ResponseRatioTask", 1, 100, valid_openqasm1, {"task_queue": scheduler.task_queue}),
        ("task3", "PriorityTask", 2, 100, valid_openqasm1, {}),
        ("task8", "TimePrecedenceTask", 4, 100, valid_openqasm1, {}),
        # ("task4", "PeriodicTask", 2, 100, valid_openqasm1, {"interval": 5}),
        ("task5", "DependentTask", 3, 100, valid_openqasm1, {"dependencies": []}),
        # ("task6", "BatchTask", 4, 100, valid_openqasm1, {"tasks": [qmm.allocate() for _ in range(5)]}),
        ("task7", "RealTimeTask", 5, 100, valid_openqasm1, {"deadline": 10}),
        ("task9", "TimePrecedenceTask", 1, 100, valid_openqasm1, {}),
        ("task10", "ShortestJobFirstTask", 1, 100, valid_openqasm2, {}),
        ("task11", "ShortestJobFirstTask", 1, 100, valid_openqasm1, {})
    ]

    task_ids = []
    for task_id, task_type, priority, shots, openqasm_content, extra_args in tasks:
        await scheduler.add_task(task_id, task_type, priority, shots, openqasm_content=openqasm_content, **extra_args)
        qcos_logger.info(f"添加了 {task_type} 任务 {task_id}")
        task_ids.append(task_id)
        qcos_logger.info(f"添加了 {task_type} 任务 {task_id}")
        await asyncio.sleep(0.1)

    # 运行任务调度器来处理队列中的任务
    scheduler_tasks = [asyncio.create_task(scheduler.run_tasks(queue_type)) for queue_type in
                       scheduler.task_queue.keys()]

    # 等待一段时间让任务执行
    await asyncio.sleep(1)

    # 停止任务调度器
    await scheduler.stop()

    # 查询任务状态和结果
    for task_id, task_type, priority, _, _, _ in tasks:
        # task_id = priority  # 假设任务ID与优先级相同
        status = scheduler.get_task_status(task_id)
        result = scheduler.get_task_result(task_id)
        qcos_logger.info(f"{task_type} 任务 {task_id} 的状态: {status}, 结果: {result}")

    # 获取任务统计信息
    stats = scheduler.get_task_statistics()
    qcos_logger.info(f"任务统计信息: {stats}")

    for scheduler_task in scheduler_tasks:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

    # 清理完成的任务
    scheduler.cleanup_completed_tasks()


# 运行示例
if __name__ == "__main__":
    asyncio.run(main())


# 初始化量子任务调度器，读取配置文件设置最大并发任务数
qcos_scheduler = QuantumTaskScheduler(
    max_concurrent_tasks=qcos_configer.get_max_concurrent_tasks())