#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Bowen Zhang at 2024-10
# ------------------------


from qcos.interface.qcos_openqasm_int import openqasm_manager
import os
import json
from qcos.log.qcos_log import QCOSLogger
from qcos.interface.qcos_task_manager import qcos_hybird_task_manager
from qcos.interface.qcos_task_manager import qcos_task_id_generator
import shutil


# 创建日志记录器实例
qcos_logger = QCOSLogger()
# 获取当前文件的绝对路径，并构造配置文件的完整路径
current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir, '../config/qcos_config.conf')


class OpenqasmStrategy:
    """
    xternal任务源openqasm任务获取策略的基类
    """

    def execute(self, data=None):
        """
        执行请求策略的抽象方法
        :param data: 请求数据
        :return: 请求响应
        """

        raise NotImplementedError("Each strategy must implement an execute method")


class XternalFetchOpenqasmStrategy(OpenqasmStrategy):
    """
    传送结果策略
    """

    def execute(self, data=None):

        # openqasm_struct = openqasm_manager.load_openqasm_file()
        openqasm_manager.load_openqasm_file()

        tasks = []
        for i in range(openqasm_manager.task_queue.qsize()):
            openqasm_struct = openqasm_manager.get_openqasm_tasks()

            # 解析结构体获取任务信息
            task_name = openqasm_struct.get('qcos_task_name')
            task_type = openqasm_struct.get('qcos_task_type')
            priority = openqasm_struct.get('qcos_task_priority')
            shots = openqasm_struct.get('qcos_shots_num')
            qubits = openqasm_struct.get('qcos_qubits_num')
            sequence = openqasm_struct.get('openqasm_sequence')
            qcos_logger.debug(f"解析任务 {task_name} 结构体: {openqasm_struct}")

            task = {
                "id": task_name,
                "openqasm": sequence
            }
            tasks += [task]

            # 添加解析后的任务
            qcos_hybird_task_manager.add_task(task_name, shots, qubits, sequence, priority, task_type)

            # 将对应的原始openqasm文件移动到qcos_processing_task路径下
            try:
                file_name = task_name
                src_file_path = os.path.join(openqasm_manager.original_openqasm_path, file_name)
                dst_file_path = os.path.join(openqasm_manager.processing_openqasm_path, file_name)
                if os.path.exists(dst_file_path):
                    os.remove(dst_file_path)
                shutil.move(src_file_path, dst_file_path)
                qcos_logger.debug(f"OpenQASM文件成功移动到 {openqasm_manager.processing_openqasm_path}")
            except Exception as err:
                qcos_logger.warning(f"将OpenQASM文件从{openqasm_manager.original_openqasm_path}移动到"
                                    f"{openqasm_manager.processing_openqasm_path}失败: {err}")

        qcos_logger.info(f"[interface: qcos_xternalapi_handler] 任务获取策略请求返回：{tasks}")

        return tasks


class XternalSaveOpenqasmStrategy(OpenqasmStrategy):
    """
    传送结果策略
    """

    def execute(self, data=None):
        result_path = openqasm_manager.task_result_path

        # 解析openqasm_struct中的task_id字段
        openqasm_struct = data
        task_id = openqasm_struct["id"]
        # 根据task_id哈希值恢复原始的输入字符串用以生成结果保存文件名
        task_name = qcos_task_id_generator.recover_qcos_task_id(task_id)

        # 拆分task_name得到文件名，并构建存放openqasm_struct的文件路径
        base_name, _ = os.path.splitext(task_name)
        result_file_name = base_name + ".json"
        result_file_path = os.path.join(result_path, result_file_name)

        # 保存openqasm_struct
        with open(result_file_path, "w") as file:
            json.dump(openqasm_struct, file, indent=4)
        qcos_logger.info(f"[interface: qcos_xternalapi_handler] OpenQASM任务结果保存到： {result_file_path}")

        """完成结果保存，对应流程结束，删除task_info中的任务信息和processing_openqasm_path路径下的openqasm文件"""
        # 删除task_info中保存的对应信息
        if task_id in qcos_hybird_task_manager.task_info:
            del qcos_hybird_task_manager.task_info[task_id]
        else:
            qcos_logger.warning(f"{task_id} 不在task_info中，无法删除 {task_name} 对应的task_info信息")

        # 删除qcos_processing_task路径下对应的openqasm文件
        file_path = os.path.join(openqasm_manager.processing_openqasm_path, task_name)
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            qcos_logger.warning(f"{file_path} 不存在，无法删除 {task_name} 对应的openqasm文件")

        return result_file_path
