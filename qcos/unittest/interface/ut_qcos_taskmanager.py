#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-06
# ------------------------


import unittest
from qcos.interface.qcos_task_manager import TaskManager, QcosTaskIDGenerator
from qcos.log.qcos_log import QCOSLogger


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TestTaskManager(unittest.TestCase):
    '''
    测试TaskManager类的单元测试类。
    包含了对TaskManager类中各个方法的测试用例。
    '''

    def setUp(self):
        '''
        初始化测试环境，在每个测试方法执行前运行。
        创建TaskManager实例并打印初始化信息。
        '''

        # 创建TaskManager实例
        self.manager = TaskManager()
        # 打印初始化信息
        qcos_logger.debug('\n初始化TaskManager实例')

        # 创建qcos任务id生成器
        self.qcos_task_id_generator = QcosTaskIDGenerator()
        # 打印初始化信息
        qcos_logger.debug('\n初始化TaskManager实例')

    def test_add_task(self):
        '''
        测试add_task方法。
        验证任务是否成功添加到待处理任务队列，并检查任务信息是否正确记录。
        '''

        task_id = 'task1'
        shots = 500
        qubits = 2
        openqasm_sequence = 'sequence1'
        priority = 'qcosTaskPriority'
        task_type = 'qcosTaskType'

        qcos_logger.debug(f'添加任务：{task_id}')
        self.manager.add_task(
            task_id,
            shots,
            qubits,
            openqasm_sequence,
            priority,
            task_type)

        # 检查任务是否成功添加到待处理任务队列
        self.assertEqual(self.manager.pending_tasks.qsize(), 1)

        # 检查任务信息是否正确记录
        encode_id = self.manager.pending_tasks.queue[0]
        self.assertIn(encode_id, self.manager.task_info)
        self.assertEqual(self.manager.task_info[encode_id]['shots'], shots)
        self.assertEqual(self.manager.task_info[encode_id]['qubits'], qubits)
        self.assertEqual(
            self.manager.task_info[encode_id]['openqasm_sequence'],
            openqasm_sequence)
        self.assertEqual(
            self.manager.task_info[encode_id]['priority'],
            priority)
        self.assertEqual(
            self.manager.task_info[encode_id]['task_type'],
            task_type)

        # 打印检查结果
        qcos_logger.debug(f'任务添加成功：{self.manager.task_info[encode_id]}')

    def test_start_task(self):
        '''
        测试start_task方法。
        验证任务是否成功从待处理任务队列移动到正在处理任务队列。
        '''

        task_id = 'task1'
        shots = 500
        qubits = 2
        openqasm_sequence = 'sequence1'
        task_type = 'qcosTaskType'
        priority = 'qcosTaskPriority'

        # 添加任务并启动任务
        self.manager.add_task(
            task_id,
            shots,
            qubits,
            openqasm_sequence,
            priority,
            task_type)
        qcos_logger.debug(f'启动任务: {task_id}')
        self.manager.start_task()

        # 检查任务是否成功从待处理任务队列移动到正在处理任务队列
        self.assertEqual(self.manager.pending_tasks.qsize(), 0)
        self.assertEqual(self.manager.processing_tasks.qsize(), 1)

        # 打印检查结果
        qcos_logger.debug(
            f'任务启动成功：正在处理任务数量={
                self.manager.processing_tasks.qsize()}')

    async def test_collect_task(self):
        '''
        测试collect_task方法。
        验证任务是否成功从待处理任务队列移动到正在处理任务队列。
        '''

        # 定义任务1
        task_id1 = 'task1'
        shots1 = 500
        qubits1 = 2
        openqasm_sequence1 = 'sequence1'
        task_type1 = 'qcosTaskType1'
        priority1 = 'qcosTaskPriority1'

        # 定义任务2
        task_id2 = 'task2'
        shots2 = 1000
        qubits2 = 5
        openqasm_sequence2 = 'sequence2'
        task_type2 = 'qcosTaskType2'
        priority2 = 'qcosTaskPriority2'

        # 添加任务
        self.manager.add_task(
            task_id1,
            shots1,
            qubits1,
            openqasm_sequence1,
            priority1,
            task_type1)
        self.manager.add_task(
            task_id2,
            shots2,
            qubits2,
            openqasm_sequence2,
            priority2,
            task_type2)
        qcos_logger.debug(f'添加任务: {task_id1}, {task_id2}')

        # 启动任务
        self.manager.start_task()
        qcos_logger.debug(f'启动任务: {task_id1}')

        # 收集任务
        result = await self.manager.collect_tasks()

        # 检查任务是否成功从待处理任务队列移动到正在处理任务队列，并被正确收集
        self.assertEqual(self.manager.processing_tasks.qsize(), len(result))
        self.assertEqual(result[0], task_id1)

        # 打印检查结果
        qcos_logger.debug(
            f'任务收集成功：正在处理任务数量={
                self.manager.processing_tasks.qsize()}')

    def test_complete_task(self):
        '''
        测试complete_task方法。
        验证任务是否成功从正在处理任务队列移动到已完成任务队列。
        '''

        task_id = 'task1'
        shots = 500
        qubits = 2
        openqasm_sequence = 'sequence1'
        task_type = 'qcosTaskType'
        priority = 'qcosTaskPriority'

        # 添加任务、启动任务并完成任务
        self.manager.add_task(
            task_id,
            shots,
            qubits,
            openqasm_sequence,
            priority,
            task_type)
        self.manager.start_task()

        completed_task = [self.manager.processing_tasks.queue[0]]
        qcos_logger.debug(f'完成任务: {task_id}')
        self.manager.complete_task(completed_task)

        # 检查任务是否成功从正在处理任务队列移动到已完成任务队列
        self.assertEqual(self.manager.processing_tasks.qsize(), 0)
        self.assertEqual(self.manager.completed_tasks.qsize(), 1)

        # 打印检查结果
        qcos_logger.debug(
            f'任务完成成功：已完成任务数量={
                self.manager.completed_tasks.qsize()}')

    def test_get_task_info(self):
        '''
        测试get_task_info方法。
        验证是否能正确获取指定任务的信息。
        '''

        task_id = 'task1'
        shots = 500
        qubits = 2
        openqasm_sequence = 'sequence'
        task_type = 'qcosTaskType'
        priority = 'qcosTaskPriority'

        # 添加任务
        self.manager.add_task(
            task_id,
            shots,
            qubits,
            openqasm_sequence,
            priority,
            task_type)

        # 获取任务信息并检查其正确性
        qcos_logger.debug(f'获取 {task_id} 任务信息.')
        task_info = self.manager.get_task_info(
            self.manager.pending_tasks.queue[0])
        self.assertIsNotNone(task_info)
        self.assertEqual(task_info['shots'], shots)
        self.assertEqual(task_info['qubits'], qubits)
        self.assertEqual(task_info['openqasm_sequence'], openqasm_sequence)
        self.assertEqual(task_info['priority'], priority)
        self.assertEqual(task_info['task_type'], task_type)

        # 打印检查结果
        qcos_logger.debug(f'任务信息：{task_info}')

    def test_get_task_counts(self):
        '''
        测试get_task_counts方法。
        验证是否能正确获取各种状态任务的数量。
        '''

        # 定义任务1
        task_id1 = 'task1'
        shots1 = 500
        qubits1 = 2
        openqasm_sequence1 = 'sequence1'
        task_type1 = 'qcosTaskType1'
        priority1 = 'qcosTaskPriority1'

        # 定义任务2
        task_id2 = 'task2'
        shots2 = 1000
        qubits2 = 5
        openqasm_sequence2 = 'sequence2'
        task_type2 = 'qcosTaskType2'
        priority2 = 'qcosTaskPriority2'

        # 添加任务并启动和完成部分任务
        self.manager.add_task(
            task_id1,
            shots1,
            qubits1,
            openqasm_sequence1,
            priority1,
            task_type1)
        self.manager.add_task(
            task_id2,
            shots2,
            qubits2,
            openqasm_sequence2,
            priority2,
            task_type2)
        self.manager.start_task()

        completed_task = [self.manager.processing_tasks.queue[0]]
        qcos_logger.debug(f'完成任务: {task_id1}')
        self.manager.complete_task(completed_task)

        # 获取任务数量并检查其正确性
        qcos_logger.debug('获取任务数量')
        counts = self.manager.get_task_counts()
        self.assertEqual(counts['pending'], 0)
        self.assertEqual(counts['processing'], 1)
        self.assertEqual(counts['completed'], 1)

        # 打印检查结果
        qcos_logger.debug(f'任务数量：{counts}')

    def test_get_pending_task_content(self):
        '''
            测试get_pending_task_content方法。
            验证待处理任务内容的获取是否正确。
        '''

        task_id = 'task1'
        shots = 500
        qubits = 2
        openqasm_sequence = 'sequence'
        task_type = 'qcosTaskType'
        priority = 'qcosTaskPriority'

        # 测试待处理任务的内容获取
        result = self.manager.get_pending_task_content(task_id)
        self.assertEqual(result, f'任务 {task_id} 不在待处理队列中')

        self.manager.add_task(
            task_id,
            shots,
            qubits,
            openqasm_sequence,
            priority,
            task_type)
        encode_id = self.manager.pending_tasks.queue[0]
        result = self.manager.get_pending_task_content(encode_id)
        expected_result = f'{encode_id} info: ' + \
            str(self.manager.task_info[encode_id])
        self.assertEqual(result, expected_result)

    def test_get_processing_task_content(self):
        '''
            测试get_processing_task_content方法。
            验证正在处理任务内容的获取是否正确。
        '''

        # 定义任务1
        task_id1 = 'task1'
        shots1 = 500
        qubits1 = 2
        openqasm_sequence1 = 'sequence1'
        task_type1 = 'qcosTaskType1'
        priority1 = 'qcosTaskPriority1'

        # 定义任务2
        task_id2 = 'task2'
        shots2 = 1000
        qubits2 = 5
        openqasm_sequence2 = 'sequence2'
        task_type2 = 'qcosTaskType2'
        priority2 = 'qcosTaskPriority2'

        # 添加任务并启动和完成部分任务
        self.manager.add_task(
            task_id1,
            shots1,
            qubits1,
            openqasm_sequence1,
            priority1,
            task_type1)
        self.manager.add_task(
            task_id2,
            shots2,
            qubits2,
            openqasm_sequence2,
            priority2,
            task_type2)

        # 将任务移到正在处理任务队列
        self.manager.start_task()
        self.manager.start_task()

        encode_id1 = self.manager.processing_tasks.queue[0]
        encode_id2 = self.manager.processing_tasks.queue[1]
        # 将task1移到已完成任务队列
        completed_task = [encode_id1]
        qcos_logger.debug(f'完成任务{encode_id1}')
        self.manager.complete_task(completed_task)

        # 测试正在处理任务的内容获取
        result = self.manager.get_processing_task_content(encode_id2)
        expected_result = f'{encode_id2} info: ' + \
            str(self.manager.task_info[encode_id2])
        self.assertEqual(result, expected_result)

        result = self.manager.get_processing_task_content(encode_id1)
        self.assertEqual(result, f'任务 {encode_id1} 不在正在处理队列中')

    def test_get_completed_task_content(self):
        '''
            测试get_completed_task_content方法。
            验证已完成任务内容的获取是否正确。
        '''

        # 定义任务1
        task_id1 = 'task1'
        shots1 = 500
        qubits1 = 2
        openqasm_sequence1 = 'sequence1'
        task_type1 = 'qcosTaskType1'
        priority1 = 'qcosTaskPriority1'

        # 定义任务2
        task_id2 = 'task2'
        shots2 = 1000
        qubits2 = 5
        openqasm_sequence2 = 'sequence2'
        task_type2 = 'qcosTaskType2'
        priority2 = 'qcosTaskPriority2'

        # 添加任务并启动和完成部分任务
        self.manager.add_task(
            task_id1,
            shots1,
            qubits1,
            openqasm_sequence1,
            priority1,
            task_type1)
        self.manager.add_task(
            task_id2,
            shots2,
            qubits2,
            openqasm_sequence2,
            priority2,
            task_type2)

        # 将任务移到正在处理任务队列
        self.manager.start_task()
        self.manager.start_task()

        encode_id1 = self.manager.processing_tasks.queue[0]
        encode_id2 = self.manager.processing_tasks.queue[1]
        # 将task1移到已完成任务队列
        completed_task = [encode_id1]
        qcos_logger.debug(f'完成任务{encode_id1}')
        self.manager.complete_task(completed_task)

        # 测试已完成任务的内容获取
        result = self.manager.get_completed_task_content(encode_id1)
        expected_result = f'{encode_id1} info: ' + \
            str(self.manager.task_info[encode_id1])
        self.assertEqual(result, expected_result)

        result = self.manager.get_completed_task_content(encode_id2)
        self.assertEqual(result, f'任务 {encode_id2} 不在已完成队列中')


if __name__ == '__main__':
    unittest.main()
