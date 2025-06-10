#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-06
# ------------------------


import queue
import hashlib
import time
from qcos.log.qcos_log import QCOSLogger


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TaskManager:
    """
    TaskManager类用于管理OpenQASM任务，包括记录待处理任务、正在处理任务和已完成任务的数量，
    并存储每个任务对应的OpenQASM结构体和任务名称。
    """

    def __init__(self):
        """
        初始化TaskManager类，创建三个队列和一个字典用于管理任务。
        """

        # 初始化一个队列用于存储待处理的OpenQASM任务
        self.pending_tasks = queue.Queue()
        # 初始化一个队列用于存储正在处理任务
        self.processing_tasks = queue.Queue()
        # 初始化一个队列用于存储已完成任务
        self.completed_tasks = queue.Queue()

        # 存储任务详细信息的字典
        self.task_info = {}

    def add_task(self, task_id, shots, qubits, openqasm_sequence, priority, task_type, allow_aggregation=False):
        """
        添加一个新任务到待处理任务队列，并记录任务信息。

        参数:
            task_id (str): 任务唯一标识符
            shots（int）: 任务执行次数
            qubits（int）: 使用量子比特数
            openqasm_sequence (str): OpenQASM指令集
            priority (int): 任务优先级
            task_type (str): 任务类型
            allow_aggregation (bool): 任务是否允许聚合
        """

        # 将任务ID添加到待处理任务队列
        try:
            task_id = qcos_task_id_generator.generate_qcos_task_id(task_id)
            self.pending_tasks.put(task_id)
            qcos_logger.info(f"[interface: qcos_task_manager] 添加任务"
                             f"{qcos_task_id_generator.recover_qcos_task_id(task_id)}，生成qcos内部任务id：{task_id}")
        except Exception as err:
            qcos_logger.error(f"任务{qcos_task_id_generator.recover_qcos_task_id(task_id)}添加失败：{err}")

        # 记录任务详细信息
        self.task_info[task_id] = {
            "shots": shots,
            "qubits": qubits,
            "openqasm_sequence": openqasm_sequence,
            "priority": priority,
            "task_type": task_type,
            "allow_aggregation": allow_aggregation
        }

    def start_task(self):
        """
        将一个任务从待处理任务队列移动到正在处理任务队列。
        """

        # 检查待处理任务队列是否为空
        while not self.pending_tasks.empty():
            # 从待处理任务队列中获取一个任务ID
            task_id = self.pending_tasks.get()

            # 将任务ID添加到正在处理任务队列
            self.processing_tasks.put(task_id)
            qcos_logger.info(f"[interface: qcos_task_manager] 开始处理任务: id = {task_id}")

    def collect_tasks(self):
        """
        收集正在处理任务队列中队列元素

        返回:
            task_ids_list (list): 收集到的正在处理任务队列中的任务列表
        """

        task_ids_list = []
        while not self.processing_tasks.empty():
            task_id = self.processing_tasks.get()
            task_ids_list.append(task_id)

        qcos_logger.debug(f"收集正在处理的任务id列表: {task_ids_list}")
        return task_ids_list

    def complete_task(self, completed_task):
        """
        将一个任务从正在处理任务队列移动到已完成任务队列。

        参数：
            completed_task(list): 已完成任务列表
        """

        if completed_task:
            for task_id in completed_task:
                # 检查task_id是否在处理任务队列
                if task_id in self.processing_tasks.queue:
                    # 从正在处理任务队列中移除任务ID
                    self.processing_tasks.queue.remove(task_id)

                    # 将任务ID添加到已完成任务队列
                    self.completed_tasks.put(task_id)
                    qcos_logger.info(f"[interface: qcos_task_manager] 已完成任务: id = {task_id}")
        else:
            qcos_logger.debug(f"传入的已完成任务列表为空!")

    def get_task_info(self, task_id):
        """
        获取指定任务的详细信息。

        参数:
            task_id (str): 任务唯一标识符
        返回:
            dict: 包含任务名称和OpenQASM结构体的字典
        """

        # 返回任务详细信息，如果任务不存在则返回None
        return self.task_info.get(task_id, None)

    def get_task_counts(self):
        """
        获取各类任务的数量。

        返回:
            dict: 包含待处理任务、正在处理任务和已完成任务数量的字典
        """

        # 返回各类任务的数量
        return {
            "pending": self.pending_tasks.qsize(),  # 待处理任务数量
            "processing": self.processing_tasks.qsize(),  # 正在处理任务数量
            "completed": self.completed_tasks.qsize()  # 已完成任务数量
        }

    def get_pending_task_content(self, task_id):
        """
        获取待处理任务队列中指定任务的OpenQASM结构体。

        参数:
            task_id (str): 任务唯一标识符
        返回:
            str：任务task_id的信息，包括shots和qasm
        """

        if task_id in self.pending_tasks.queue:
            return f"{task_id} info: {self.task_info[task_id]}"
        else:
            return f"任务 {task_id} 不在待处理队列中"

    def get_processing_task_content(self, task_id):
        """
        获取正在处理任务队列中指定任务的OpenQASM结构体。

        参数:
            task_id (str): 任务唯一标识符
        返回:
            str：任务task_id的信息，包括shots和qasm
        """

        if task_id in self.processing_tasks.queue:
            return f"{task_id} info: {self.task_info[task_id]}"
        else:
            return f"任务 {task_id} 不在正在处理队列中"

    def get_completed_task_content(self, task_id):
        """
        获取已完成任务队列中指定任务的OpenQASM结构体。

        参数:
            task_id (str): 任务唯一标识符
        返回:
            str：任务task_id的信息，包括shots和qasm
        """

        if task_id in self.completed_tasks.queue:
            return f"{task_id} info: {self.task_info[task_id]}"
        else:
            return f"任务 {task_id} 不在已完成队列中"

    def task_process(self):
        """
        获取任务后的处理流程
        """

        task_counts = self.get_task_counts()
        qcos_logger.debug(task_counts)

        self.start_task()
        task_counts = self.get_task_counts()
        qcos_logger.debug(task_counts)

        completed_task = ['task1']
        self.complete_task(completed_task)

        self.start_task()
        task_counts = self.get_task_counts()
        qcos_logger.debug(task_counts)

        qcos_logger.debug(self.get_pending_task_content('task1'))
        qcos_logger.debug(self.get_processing_task_content('task2'))
        qcos_logger.debug(self.get_completed_task_content('task1'))


class QcosTaskIDGenerator:
    """
    QcosTaskIDGenerator 类用于生成唯一的哈希值标识符，并能够根据生成的哈希值恢复原始输入字符串。
    该类使用 MD5 哈希算法结合当前时间戳生成唯一标识符。
    """

    def __init__(self):
        """
        初始化 QcosTaskIDGenerator 类的实例，创建一个空的映射字典用于存储哈希值与任务ID原始输入字符串的映射。
        """
        # 初始化一个字典，用于存储生成的哈希值和原始输入字符串的映射关系
        self.reverse_map = {}

    def generate_qcos_task_id(self, task_id):
        """
        根据输入字符串生成唯一的 MD5 哈希值，哈希值结合了当前时间戳以确保唯一性。

        参数:
        task_id (str): 需要生成哈希值的原始输入任务ID

        返回:
        unique_hash (str): 生成的唯一 MD5 哈希值标识符
        """
        # 获取当前时间戳，转换为字符串形式
        timestamp = str(time.time())

        # 将输入字符串和时间戳组合，并计算 MD5 哈希
        hash_input = task_id.encode() + timestamp.encode()
        # 创建 MD5 哈希对象
        hash_object = hashlib.md5(hash_input)
        # 获取哈希结果的十六进制表示,使用完整的 MD5 哈希值作为唯一标识符
        unique_hash = hash_object.hexdigest()

        # 存储哈希值和输入字符串的映射关系
        self.reverse_map[unique_hash] = task_id

        # 返回生成的唯一哈希值
        return unique_hash

    def recover_qcos_task_id(self, unique_hash):
        """
        根据输入的哈希值恢复原始的输入字符串。

        参数:
        unique_hash (str): 输入的哈希值，用于查找对应的任务ID原始字符串

        返回:
        str: 对应的任务ID原始输入字符串，如果哈希值不存在于映射中则返回 None
        """
        # 检查哈希值是否存在于 reverse_map 中
        if unique_hash in self.reverse_map:
            # 直接返回对应的原始输入字符串
            return self.reverse_map[unique_hash]
        else:
            # 如果哈希值不在映射中，返回 None
            return None


# 创建qcos任务id生成器
qcos_task_id_generator = QcosTaskIDGenerator()
qcos_hybird_task_manager = TaskManager()
