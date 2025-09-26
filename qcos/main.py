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


import os
import asyncio
import aioconsole
from qcos.cna import HierarchyTree, get_block, get_abs_tree, get_ir
from qcos.interface.qcos_openqasm_int import openqasm_manager
from qcos.memory.qcos_mem_task_scheduler import qcos_scheduler
from qcos.log.qcos_log import QCOSLogger
from qcos.config.qcos_config_manager import qcos_configer
from qcos.interface.qcos_api_manager import qcos_api_inst_manager
from qcos.interface.qcos_task_manager import qcos_hybird_task_manager


# 创建日志记录器实例
qcos_logger = QCOSLogger()

# 量子任务
tasks_dict = {
    'PriorityTask': [],
    'ResponseRatioTask': [],
    'TimePrecedenceTask': [],
    'PeriodicTask': [],
    'DependentTask': [],
    'BatchTask': [],
    'RealTimeTask': []}


async def get_tasks():
    '''
    从对外接口处理器获取任务并进行任务数据解析
    '''
    while True:
        try:
            # 启动对外接口处理器中量子任务执行功能
            qcos_hybird_task_manager.start_task()
            task_ids_list = qcos_hybird_task_manager.collect_tasks()
            for task_id in task_ids_list:
                task_type = qcos_hybird_task_manager.task_info[task_id][
                    'task_type']
                if task_type not in tasks_dict:
                    qcos_logger.warning(f'调度任务类型错误，任务{task_id}添加失败')
                    continue
                tasks_dict[task_type].append(
                    (task_id,
                     qcos_hybird_task_manager.task_info[task_id][
                         'task_type'],
                     qcos_hybird_task_manager.task_info[task_id][
                         'priority'],
                     qcos_hybird_task_manager.task_info[task_id][
                         'shots'],
                     qcos_hybird_task_manager.task_info[task_id][
                         'openqasm_sequence'],
                     qcos_hybird_task_manager.task_info[task_id][
                         'allow_aggregation'],
                     {}))
            await asyncio.sleep(qcos_configer.get_scheduler_wait_time())
        except asyncio.CancelledError:
            qcos_logger.info('停止获取量子任务')
            break


async def aggregate_tasks(task_type: str):
    '''
    划分任务类型进行任务聚合，并将任务添加到任务调度队列中
    参数:
    task_type (str): 任务类型
    qcos_scheduler (QuantumTaskScheduler): 任务调度器
    '''
    # 读取硬件配置文件
    hw_config = qcos_configer.get_topo_file()

    while True:
        try:
            # 没有任务时等待一段时间
            if not tasks_dict[task_type]:
                await asyncio.sleep(qcos_configer.get_scheduler_wait_time())
                continue

            # 当前待执行的首个任务若可聚合，则统计任务列表中所有可聚合任务
            current_task = tasks_dict[task_type].pop(0)
            allow_aggregation_tasks = []
            if current_task[5]:
                allow_aggregation_tasks = [
                    task for task in tasks_dict[task_type] if task[5]]
            # 判断是单独执行任务 or 聚合执行任务
            # 聚合条件：1.当前任务允许聚合；2.配置文件中的聚合开关已打开；3.任务列表中可聚合任务数大于配置文件中的最低聚合阈值
            if (not current_task[5] or
                    not qcos_configer.get_task_aggregation_switch() or
                    len(allow_aggregation_tasks) + 1 <
                    qcos_configer.get_task_aggregation_lower_threshold()):
                # 单独执行任务
                for (_task_id,
                     _task_type,
                     priority,
                     shots,
                     openqasm_content,
                     _,
                     extra_args) in [current_task]:
                    await qcos_scheduler.add_task(
                        _task_id,
                        _task_type,
                        priority,
                        shots,
                        openqasm_content=openqasm_content,
                        **extra_args)
                    qcos_logger.info(f'添加了 {_task_type} 任务 {_task_id}')
            else:
                # 多任务聚合
                abs_tree = get_abs_tree(current_task[4])
                q_num, _ = get_ir(abs_tree)
                sum_q_num = q_num
                if q_num > hw_config['qubits']:
                    raise MemoryError('任务比特数量超过硬件支持的最大量子比特数')
                qpu_file = qcos_configer.get_na_file()
                ht = HierarchyTree(qpu_file=qpu_file, w=1)
                ht.construct()
                blocks = [get_block(ht, q_num)]
                multi_tasks = [current_task]
                for task in allow_aggregation_tasks:
                    # 如果两个任务shots不同则无法聚合
                    if task[3] != current_task[3]:
                        continue
                    abs_tree = get_abs_tree(task[4])
                    q_num, _ = get_ir(abs_tree)
                    block = get_block(ht, q_num)
                    if block is not None:
                        sum_q_num += q_num
                        blocks.append(block)
                        multi_tasks.append(task)
                        if (len(multi_tasks) >= qcos_configer.
                                get_task_aggregation_upper_threshold()):
                            break
                for (_task_id,
                     _task_type,
                     priority,
                     shots,
                     openqasm_content,
                     extra_args) in [current_task]:
                    await qcos_scheduler.add_task(
                        _task_id,
                        _task_type,
                        priority,
                        shots,
                        True,
                        aggregation_tasks=multi_tasks,
                        blocks=blocks,
                        sum_qubit=sum_q_num,
                        **extra_args)
                    qcos_logger.info(f'添加了 {_task_type} 聚合任务 {_task_id}')
                # 从任务列表中去除聚合的任务
                tasks_dict[task_type] = [task for task in tasks_dict[task_type]
                                         if task not in multi_tasks]
        except asyncio.CancelledError:
            qcos_logger.info(f'停止向 {task_type} 调度队列添加量子任务')
            break


async def main():
    '''
    # 创建测试所用的openqasm任务文件
    openqasm_file1 = os.path.join(
        openqasm_manager.original_openqasm_path, 'test1.qasm')
    # 编辑openqasm文件并保存
    with open(openqasm_file1, 'w') as file:
        file.write(f'qcos_shots_num=100\n')
        file.write(f'qcos_qubits_num=2\n')
        file.write(f'OPENQASM 2.0;\n')
        file.write(f'include "qelib1.inc";\n')
        file.write(f'qreg q[2];\n')
        file.write(f'creg c[2];\n')
        file.write(f'x q[0];\n')
        file.write(f'x q[1];\n')
        file.write(f'measure q -> c;\n')
    '''

    # 加载api handler用于从应用获取任务
    fetch_tasks = asyncio.create_task(qcos_api_inst_manager.run())

    # 任务数据解析
    extract_task_info = asyncio.create_task(get_tasks())

    # 向任务调度器添加任务
    add_tasks = [asyncio.create_task(aggregate_tasks(
        task_type)) for task_type in tasks_dict.keys()]

    # 运行任务调度器来处理队列中的任务
    scheduler_tasks = [asyncio.create_task(qcos_scheduler.run_tasks(
        queue_type)) for queue_type in qcos_scheduler.task_queue.keys()]

    get_tasks_list = [fetch_tasks, extract_task_info]
    get_tasks_list.extend(add_tasks)

    # 阻塞程序向下执行，直至接收到键盘输入
    while True:
        await aioconsole.ainput()
        break

    # 停止任务的拉取与数据处理
    for task in get_tasks_list:
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass

    # 停止任务调度器
    await qcos_scheduler.stop()

    # 关闭任务调度器
    for task in scheduler_tasks:
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass

    # 查询任务状态和结果
    for task in qcos_scheduler.completed_tasks:
        status = qcos_scheduler.get_task_status(task.task.task_id)
        result = qcos_scheduler.get_task_result(task.task.task_id)
        qcos_logger.info(f'任务 {task.task.task_id} 的状态: {status}, 结果: {result}')

    # 获取任务统计信息
    stats = qcos_scheduler.get_task_statistics()
    qcos_logger.info(f'任务统计信息: {stats}')

    # 清理完成的任务
    qcos_scheduler.cleanup_completed_tasks()
    qcos_logger.info('量子计算操作系统关闭！')


# 用 asyncio.run 来执行异步 main 函数
if __name__ == '__main__':
    asyncio.run(main())
