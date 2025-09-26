#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-06
# ------------------------


import os
import queue
from qcos.config.qcos_config_manager import qcos_configer
from qcos.log.qcos_log import QCOSLogger


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class OpenQASMManager:
    """
       OpenQASMManager类用于管理OpenQASM任务的加载和处理。
    """

    def __init__(self):
        # 初始化一个队列用于存储OpenQASM任务
        self.task_queue = queue.Queue()
        # 从配置文件中读取任务优先级
        self.task_priority_config = qcos_configer.get_task_priority()
        # 从配置文件中读取任务类型
        self.task_type_config = qcos_configer.get_task_type()
        # 完整的原始openqasm文件路径
        self.original_openqasm_path = qcos_configer.get_original_openqasm_file_path()
        os.makedirs(self.original_openqasm_path, exist_ok=True)
        # 完整的系统处理openqasm文件路径
        self.processing_openqasm_path = qcos_configer.get_processing_openqasm_file_path()
        os.makedirs(self.processing_openqasm_path, exist_ok=True)
        # 完整任务结果文件路径
        self.task_result_path = qcos_configer.get_task_result_path()
        os.makedirs(self.task_result_path, exist_ok=True)

    def get_openqasm_tasks(self):
        """
        获取由服务器创建发起的OpenQASM任务序列
        返回:
            openqasm_struct (dict): 包含OpenQASM任务序列，所需物理量子比特数目，所需shots数目的结构体
        """

        qcos_logger.debug(f"获取由服务器创建发起的OpenQASM任务")
        # 检查队列是否为空
        if self.task_queue.empty():
            return None  # 如果队列为空，返回None

        # 从队列中获取一个OpenQASM任务结构体
        openqasm_struct = self.task_queue.get()

        # 返回获取的OpenQASM任务结构体
        return openqasm_struct

    def load_openqasm_file(self):
        """
        加载指定目录下的OpenQASM文件
        返回:
            openqasm_struct (dict): 包含OpenQASM任务序列，所需物理量子比特数目，所需shots数目的结构体
        """

        qcos_logger.info(f"[interface: qcos_openqasm_int] 加载OpenQASM文件并解析构建OpenQASM任务结构体")

        openqasm_files_found = False
        # 遍历指定目录中的所有文件
        for filename in os.listdir(self.original_openqasm_path):

            # 初始化一个结构体用于存储OpenQASM任务信息
            openqasm_struct = {
                "openqasm_sequence": None,
                "qcos_qubits_num": 0,
                "qcos_shots_num": 0,
                "qcos_task_name": None,
                "qcos_task_priority": self.task_priority_config,
                "qcos_task_type": self.task_type_config
            }
            # 只处理以.qasm结尾的文件
            if filename.endswith('.qasm'):
                openqasm_files_found = True
                # 构建文件的完整路径
                filepath = os.path.join(self.original_openqasm_path, filename)

                # 打开并读取文件内容
                with open(filepath, 'r') as file:
                    lines = file.readlines()

                    # 初始化变量用于存储任务序列、量子比特数目和shots数目
                    openqasm_sequence = ""
                    num_qubits = 0
                    shots = 0

                    # 遍历文件的每一行
                    for line in lines:
                        # 识别并提取物理量子比特数目
                        if line.startswith('qcos_qubits_num'):
                            num_qubits = int(line.split('=')[1].strip())
                        # 识别并提取shots数目
                        elif line.startswith('qcos_shots_num'):
                            shots = int(line.split('=')[1].strip())
                        else:
                            # 拼接OpenQASM任务序列
                            openqasm_sequence += line

                    # 更新结构体中的信息
                    openqasm_struct["qcos_task_name"] = filename
                    openqasm_struct["openqasm_sequence"] = openqasm_sequence
                    openqasm_struct["qcos_qubits_num"] = num_qubits
                    openqasm_struct["qcos_shots_num"] = shots

                # 将读取到的OpenQASM任务结构体放入队列中
                self.task_queue.put(openqasm_struct)

        # 遍历指定目录中的所有文件后没有发现以.qasm结尾的文件
        if not openqasm_files_found:
            # raise FileNotFoundError(f"No *.qasm files found in the {self.original_openqasm_path}.")
            qcos_logger.debug("当前暂无更多任务被添加")

        # 返回读取到的OpenQASM任务结构体
        # return openqasm_struct


# 实例化 OpenQASMManager 类
openqasm_manager = OpenQASMManager()


# # 示例使用
#
# # 加载指定目录下的OpenQASM文件
# loaded_task = openqasm_manager.load_openqasm_file()
# qcos_logger.debug(loaded_task)
#
# # 获取OpenQASM任务序列
# task = openqasm_manager.get_openqasm_tasks()
# qcos_logger.debug(task)
