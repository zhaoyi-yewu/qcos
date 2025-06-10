#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-09
# ------------------------
import asyncio
import copy
import queue
import threading
import time
import unittest
from collections import deque
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from qcos.cna import NASingleRoute
from qcos.config.qcos_config_manager import qcos_configer
from qcos.interface.qcos_task_manager import qcos_task_id_generator
from qcos.memory.qcos_mem_task_manager import QuantumCircuitTask
from qcos.memory.qcos_mem_task_scheduler import TaskStatus, TaskObserver, \
    TaskSubject, BaseTask, PriorityTask, ResponseRatioTask, \
    ShortestJobFirstTask, TimePrecedenceTask, PeriodicTask, DependentTask, \
    BatchTask, RealTimeTask, TaskFactory, QuantumTaskScheduler, TaskStatusLogger
from qcos.log.qcos_log import QCOSLogger


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TestTaskStatus(unittest.TestCase):
    '''
    测试TaskStatus枚举类
    '''

    def test_task_status_enum(self):
        '''
        测试TaskStatus枚举值
        '''
        # 验证TaskStatus枚举值
        self.assertEqual(TaskStatus.PENDING.value, 1)
        self.assertEqual(TaskStatus.RUNNING.value, 2)
        self.assertEqual(TaskStatus.COMPLETED.value, 3)
        self.assertEqual(TaskStatus.FAILED.value, 4)
        self.assertEqual(TaskStatus.CANCELLED.value, 5)


class TestTaskObserver(unittest.TestCase):
    '''
    测试TaskObserver抽象基类
    '''

    def test_task_observer_abstract(self):
        '''
        测试TaskObserver是否为抽象基类
        '''
        # 验证无法直接实例化TaskObserver
        with self.assertRaises(TypeError):
            TaskObserver()


class TestTaskSubject(unittest.TestCase):
    '''
    测试TaskSubject类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''

        # 创建一个具体的TaskSubject子类用于测试
        class ConcreteTaskSubject(TaskSubject):
            '''
            具体的TaskSubject子类用于测试
            '''
            pass

        self.subject = ConcreteTaskSubject()
        self.observer = Mock(spec=TaskObserver)

    def test_attach_observer(self):
        '''
        测试附加观察者
        '''
        # 附加观察者
        self.subject.attach(self.observer)
        # 验证观察者已被添加到列表中
        self.assertIn(self.observer, self.subject._observers)

    def test_detach_observer(self):
        '''
        测试分离观察者
        '''
        # 先附加观察者
        self.subject.attach(self.observer)
        # 分离观察者
        self.subject.detach(self.observer)
        # 验证观察者已从列表中移除
        self.assertNotIn(self.observer, self.subject._observers)

    def test_notify_observers(self):
        '''
        测试通知观察者
        '''
        # 附加观察者
        self.subject.attach(self.observer)
        # 通知观察者
        self.subject.notify()
        # 验证观察者的update方法被调用
        self.observer.update.assert_called_once_with(self.subject)


class ConcreteBaseTask(BaseTask):
    '''
    BaseTask 的子类
    '''
    def __init__(self, priority, shots):
        super().__init__(priority, shots)

    def execute(self):
        # 实现具体的任务逻辑
        pass

    def __lt__(self, other):
        # 让任务可以比较大小
        return self.priority < other.priority


class TestBaseTask(unittest.TestCase):
    '''
    测试BaseTask抽象基类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''

        # 创建一个具体的BaseTask子类用于测试
        class ConcreteBaseTask(BaseTask):
            '''
            具体的BaseTask子类用于测试
            '''
            async def execute(self):
                pass

        self.task = ConcreteBaseTask(priority=1, shots=100)

    def test_init(self):
        '''
        测试BaseTask初始化
        '''
        # 验证初始化属性
        self.assertEqual(self.task.priority, 1)
        self.assertEqual(self.task.response_ratio, 0)
        self.assertEqual(self.task.status, TaskStatus.PENDING)
        self.assertIsNone(self.task.result)
        self.assertIsInstance(self.task.created_time, float)
        self.assertEqual(self.task.run_cost, 0)
        self.assertIsInstance(self.task.task_queue, asyncio.PriorityQueue)

    def test_status_property(self):
        '''
        测试status属性
        '''
        # 设置状态
        self.task.status = TaskStatus.RUNNING
        # 验证状态已更新
        self.assertEqual(self.task.status, TaskStatus.RUNNING)

    @patch.object(BaseTask, 'notify')
    def test_status_setter_notifies(self, mock_notify):
        '''
        测试设置状态时会通知观察者
        '''
        # 设置状态
        self.task.status = TaskStatus.COMPLETED
        # 验证notify方法被调用
        mock_notify.assert_called_once()

    def test_lt_comparison(self):
        '''
        测试任务比较
        '''
        # 创建两个任务进行比较
        task1 = ConcreteBaseTask(priority=1, shots=100)
        task2 = ConcreteBaseTask(priority=2, shots=100)
        # 验证比较结果
        self.assertTrue(task1 < task2)


class TestPriorityTask(unittest.TestCase):
    '''
    测试PriorityTask类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''
        self.mock_quantum_task = Mock(spec=QuantumCircuitTask)
        self.task = PriorityTask(
            priority=1,
            shots=100,
            task=self.mock_quantum_task)

    @patch('asyncio.sleep', new_callable=AsyncMock)
    def test_execute(self, mock_sleep):
        '''
        测试execute方法
        '''
        # 模拟量子任务执行
        self.mock_quantum_task.execute.return_value = 'Result'
        # 执行任务
        asyncio.run(self.task.execute())
        # 验证任务状态和结果
        self.assertEqual(self.task.status, TaskStatus.RUNNING)
        self.assertEqual(self.task.result, 'Result')
        # 验证量子任务的execute方法被调用
        self.mock_quantum_task.execute.assert_called_once()

    @patch('qcos.log.qcos_log.QCOSLogger.error')
    @patch('asyncio.sleep', new_callable=AsyncMock)
    def test_execute_exception(self, mock_sleep, mock_logger):
        '''
        测试execute方法异常处理
        '''
        # 模拟量子任务执行异常
        self.mock_quantum_task.execute.side_effect = Exception('Test error')
        # 执行任务
        asyncio.run(self.task.execute())
        # 验证任务状态和结果
        self.assertEqual(self.task.status, TaskStatus.FAILED)
        self.assertEqual(self.task.result, 'Test error')


class TestResponseRatioTask(unittest.TestCase):
    '''
    测试ResponseRatioTask类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''
        self.mock_quantum_task = Mock(spec=QuantumCircuitTask)
        self.mock_quantum_task.openqasm_content = '''
                    OPENQASM 2.0;
                    include 'qelib1.inc';
                    qreg q[2];
                    creg c[2];
                    x q[0];
                    y q[0];
                    h q[1];
                    measure q -> c;
                    '''
        self.mock_task_queue = MagicMock()
        self.mock_task_queue['ResponseRatioTask'] = Mock(
            spec=asyncio.PriorityQueue)
        # 添加 _queue 属性
        self.mock_task_queue['ResponseRatioTask']._queue = []
        self.task = ResponseRatioTask(
            priority=1,
            shots=100,
            task=self.mock_quantum_task,
            task_queue=self.mock_task_queue,
        )

    def test_calculate_response_ratio(self):
        '''
        测试计算响应比
        '''
        # 模拟当前时间及任务执行消耗
        self.task.run_cost = 1
        current_time = self.task.created_time + 1
        # 计算响应比
        ratio = self.task._calculate_response_ratio(current_time)
        # 验证计算结果
        self.assertEqual(ratio, 2.0)

    def test_update_response_ratio(self):
        '''
        测试更新响应比
        '''
        # 创建模拟任务
        mock_task = Mock(spec=ResponseRatioTask)
        self.mock_task_queue['ResponseRatioTask']._queue = [mock_task]
        # 更新响应比
        self.task._update_response_ratio()
        # 验证模拟任务的_calculate_response_ratio方法被调用
        mock_task._calculate_response_ratio.assert_called_once()

    @patch('asyncio.sleep', new_callable=AsyncMock)
    def test_execute(self, mock_sleep):
        '''
        测试execute方法
        '''
        # 模拟量子任务执行
        self.mock_quantum_task.execute.return_value = 'Result'
        # 执行任务
        asyncio.run(self.task.execute())
        # 验证任务状态和结果
        self.assertEqual(self.task.status, TaskStatus.RUNNING)
        self.assertEqual(self.task.result, 'Result')
        # 验证量子任务的execute方法被调用
        self.mock_quantum_task.execute.assert_called_once()


class TestShortestJobFirstTask(unittest.TestCase):
    '''
    测试 ShortestJobFirstTask 类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''
        self.mock_quantum_task = Mock(spec=QuantumCircuitTask)
        self.mock_quantum_task.openqasm_content = '''
                    OPENQASM 2.0;
                    include 'qelib1.inc';
                    qreg q[2];
                    creg c[2];
                    x q[0];
                    y q[0];
                    h q[1];
                    measure q -> c;
                    '''
        # 实例化短作业优先任务
        self.task = ShortestJobFirstTask(
            priority=1, shots=100, task=self.mock_quantum_task
        )

    @patch('asyncio.sleep', new_callable=AsyncMock)
    def test_execute(self, mock_sleep):
        '''
        测试execute方法
        '''
        # 模拟量子任务执行
        self.mock_quantum_task.execute.return_value = 'mock_result'
        # 执行任务
        asyncio.run(self.task.execute())
        # 验证任务状态和结果
        self.assertEqual(self.task.status, TaskStatus.RUNNING)
        self.assertEqual(self.task.result, 'mock_result')
        # 验证量子任务的execute方法被调用
        self.mock_quantum_task.execute.assert_called_once()


class TestTimePrecedenceTask(unittest.TestCase):
    '''
    测试按任务创建时间顺序调度任务类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''
        self.mock_quantum_task = Mock(spec=QuantumCircuitTask)
        self.task = TimePrecedenceTask(
            priority=1, shots=100, task=self.mock_quantum_task
        )

    @patch('asyncio.sleep', new_callable=AsyncMock)
    def test_execute(self, mock_sleep):
        '''
        测试execute方法
        '''
        # 模拟量子任务执行
        self.mock_quantum_task.execute.return_value = 'Result'
        # 执行任务
        asyncio.run(self.task.execute())
        # 验证任务状态和结果
        self.assertEqual(self.task.status, TaskStatus.RUNNING)
        self.assertEqual(self.task.result, 'Result')
        # 验证量子任务的execute方法被调用
        self.mock_quantum_task.execute.assert_called_once()


class TestPeriodicTask(unittest.IsolatedAsyncioTestCase):
    '''
    测试PeriodicTask类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''
        self.mock_quantum_task = Mock(spec=QuantumCircuitTask)
        self.task = PeriodicTask(
            priority=1, shots=100, task=self.mock_quantum_task, interval=5
        )

    async def test_execute(self):
        '''
        测试execute方法
        '''
        # 模拟量子任务执行
        self.mock_quantum_task.execute.return_value = 'Result'
        # 执行任务
        try:
            await asyncio.wait_for(self.task.execute(), timeout=0.1)
        except asyncio.TimeoutError:
            pass
        # 验证任务状态和结果
        self.assertEqual(self.task.status, TaskStatus.RUNNING)
        self.assertEqual(self.task.result, 'Result')
        # 验证量子任务的execute方法被调用
        self.mock_quantum_task.execute.assert_called()


class TestDependentTask(unittest.TestCase):
    '''
    测试DependentTask类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''
        self.mock_quantum_task = Mock(spec=QuantumCircuitTask)
        self.mock_dependency1 = AsyncMock(spec=BaseTask)
        self.mock_dependency2 = AsyncMock(spec=BaseTask)
        self.task = DependentTask(
            priority=1,
            shots=100,
            task=self.mock_quantum_task,
            dependencies=[self.mock_dependency1, self.mock_dependency2],
        )

    @patch('asyncio.sleep', new_callable=AsyncMock)
    def test_execute(self, mock_sleep):
        '''
        测试execute方法
        '''
        # 模拟量子任务执行
        self.mock_quantum_task.execute.return_value = 'Result'
        # 执行任务
        asyncio.run(self.task.execute())
        # 验证依赖任务的execute方法被调用
        self.mock_dependency1.execute.assert_called_once()
        self.mock_dependency2.execute.assert_called_once()
        # 验证任务状态和结果
        self.assertEqual(self.task.status, TaskStatus.RUNNING)
        self.assertEqual(self.task.result, 'Result')
        # 验证量子任务的execute方法被调用
        self.mock_quantum_task.execute.assert_called_once()


class TestBatchTask(unittest.TestCase):
    '''
    测试BatchTask类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''
        self.mock_quantum_task1 = Mock(spec=QuantumCircuitTask)
        self.mock_quantum_task2 = Mock(spec=QuantumCircuitTask)
        self.task = BatchTask(
            priority=1,
            shots=100,
            tasks=[self.mock_quantum_task1, self.mock_quantum_task2],
        )

    @patch('asyncio.sleep', new_callable=AsyncMock)
    def test_execute(self, mock_sleep):
        '''
        测试execute方法
        '''
        # 模拟量子任务执行
        self.mock_quantum_task1.execute.return_value = 'Result1'
        self.mock_quantum_task2.execute.return_value = 'Result2'
        # 执行任务
        asyncio.run(self.task.execute())
        # 验证任务状态和结果
        self.assertEqual(self.task.status, TaskStatus.RUNNING)
        self.assertEqual(self.task.result, ['Result1', 'Result2'])
        # 验证量子任务的execute方法被调用
        self.mock_quantum_task1.execute.assert_called_once()
        self.mock_quantum_task2.execute.assert_called_once()


class TestRealTimeTask(unittest.TestCase):
    '''
    测试RealTimeTask类
    '''

    def setUp(self):
        '''
        测试前的准备工作
        '''
        self.mock_quantum_task = Mock(spec=QuantumCircuitTask)
        self.task = RealTimeTask(
            priority=1, shots=100, task=self.mock_quantum_task, deadline=2
        )

    @patch('asyncio.sleep', new_callable=AsyncMock)
    def test_execute_success(self, mock_sleep):
        '''
        测试execute方法成功执行
        '''
        # 模拟量子任务执行
        self.mock_quantum_task.execute.return_value = 'Result'
        # 执行任务
        asyncio.run(self.task.execute())
        # 验证任务状态和结果
        self.assertEqual(self.task.status, TaskStatus.RUNNING)
        self.assertEqual(self.task.result, 'Result')
        # 验证量子任务的execute方法被调用
        self.mock_quantum_task.execute.assert_called_once()

    @patch('asyncio.sleep', new_callable=AsyncMock)
    def test_execute_timeout(self, mock_sleep):
        '''
        测试execute方法超时
        '''
        # 模拟量子任务执行超时
        self.mock_quantum_task.execute.side_effect = asyncio.TimeoutError()
        # 执行任务
        asyncio.run(self.task.execute())
        # 验证任务状态和结果
        self.assertEqual(self.task.status, TaskStatus.FAILED)
        self.assertEqual(self.task.result, '任务超时')


class TestTaskFactory(unittest.TestCase):
    '''
    测试TaskFactory类
    '''

    def test_create_task(self):
        '''
        测试create_task方法
        '''
        # 创建PriorityTask
        mock_quantum_task = Mock(spec=QuantumCircuitTask)
        task = TaskFactory.create_task(
            'PriorityTask', priority=1, shots=100, task=mock_quantum_task
        )
        # 验证创建的任务类型
        self.assertIsInstance(task, PriorityTask)
        self.assertEqual(task.priority, 1)

    def test_create_unknown_task(self):
        '''
        测试创建未知任务类型
        '''
        # 尝试创建未知任务类型
        with self.assertRaises(ValueError):
            TaskFactory.create_task('UnknownTask', priority=1, shots=100)

    def test_register_task_type(self):
        '''
        测试注册新的任务类型
        '''

        # 创建一个新的任务类
        class NewTask(BaseTask):
            '''
            新的任务类
            '''
            async def execute(self):
                pass

        # 注册新任务类型
        TaskFactory.register_task_type('NewTask', NewTask)

        # 创建新类型的任务
        task = TaskFactory.create_task('NewTask', priority=1, shots=100)

        # 验证创建的任务类型
        self.assertIsInstance(task, NewTask)


class TestTaskStatusLogger(unittest.TestCase):
    '''
    测试TaskStatusLogger类
    '''

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_update(self, mock_logger):
        '''
        测试update方法
        '''
        # 创建TaskStatusLogger实例
        logger = TaskStatusLogger()

        # 创建模拟任务
        mock_task = Mock(spec=BaseTask)
        mock_task.task = Mock()  # 为 task 属性创建一个 Mock 对象
        mock_task.task.task_id = 'test_id'  # 设置 task_id
        mock_task.status = TaskStatus.COMPLETED

        # 调用update方法
        logger.update(mock_task)

        # 验证日志记录
        mock_logger.assert_called_once_with(
            '任务 test_id 状态更新为: TaskStatus.COMPLETED'
        )


class TestQuantumTaskScheduler(unittest.IsolatedAsyncioTestCase):
    '''
    测试QuantumTaskScheduler类
    '''

    @patch('threading.Thread')
    def setUp(self, mock_thread):
        '''
        测试前的准备工作
        '''
        mock_thread.start = Mock()
        self.scheduler = QuantumTaskScheduler(max_concurrent_tasks=2)

    @patch('qcos.log.qcos_log.QCOSLogger.warning')
    async def test_add_task(self, mock_warning):
        '''
        测试add_task方法
        '''

        # 测试添加单任务且单任务OpenQASM文件为空的场景
        await self.scheduler.add_task('test_id', 'PriorityTask', 1, 100)
        mock_warning.assert_called_with(f'OpenQASM代码内容为空，任务 test_id 添加失败')

        # 测试添加聚合任务但聚合参数未给定的场景
        await self.scheduler.add_task(
            'test_id', 'PriorityTask', 1, 100, is_aggregation=True
        )
        mock_warning.assert_called_with(f'任务分区聚合有误，聚合任务 test_id 添加失败')

        # 测试添加任务失败场景
        await self.scheduler.add_task(
            'test_id', 'TestType', 1, 100, openqasm_content='OpenQASM 2,0;'
        )
        mock_warning.assert_called_with(
            f'任务创建时出错:未知的任务类型: TestType，任务 test_id 添加失败'
        )

        # 测试成功添加任务场景
        task_id = await self.scheduler.add_task(
            'test_id', 'PriorityTask', 1, 100, openqasm_content='OPENQASM 2.0;'
        )
        # 验证任务添加结果
        self.assertEqual(task_id, 'test_id')

    async def test_put_in_queue(self):
        '''
        测试_put_in_queue方法
        '''
        # 创建模拟任务
        mock_task = Mock(spec=BaseTask)
        # 调用_put_in_queue方法
        for queue_type in self.scheduler.task_queue.keys():
            await self.scheduler._put_in_queue(mock_task, queue_type)

        # 验证队列中的任务情况
        for queue_type in self.scheduler.task_queue.keys():
            self.assertEqual(self.scheduler.task_queue[queue_type].qsize(), 1)

    @patch('asyncio.sleep', new_callable=AsyncMock)
    async def test_stop(self, mock_sleep):
        '''
        测试stop方法
        '''
        # 模拟任务队列和队列中的任务
        self.scheduler.task_queue['PriorityTask'] = Mock()
        mock_task = Mock(spec=BaseTask)
        mock_task.status = Mock
        # 模拟任务队列的empty()和get()
        self.scheduler.task_queue['PriorityTask'].empty.side_effect = [
            False, True]
        self.scheduler.task_queue['PriorityTask'].get = AsyncMock(
            return_value=mock_task
        )

        # 模拟预处理结果队列和队列中的任务数量
        self.scheduler.result_queue = Mock()
        self.scheduler.result_queue.empty.side_effect = [False, True]
        self.scheduler.result_queue.qsize.return_value = 1
        qcos_configer.get_collect_task_num = MagicMock(return_value=2)
        # 模拟_collect_processed_tasks函数返回结果
        self.scheduler._collect_processed_tasks = AsyncMock()

        # 调用stop方法
        await self.scheduler.stop()

        # 验证任务取消和等待
        self.scheduler.task_queue['PriorityTask'].get.assert_called_once()
        self.scheduler._collect_processed_tasks.assert_called_once()
        mock_sleep.assert_called_once()

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    async def test_run_tasks(self, mock_logger):
        '''
        测试run_tasks方法
        '''
        # 模拟任务队列和执行函数
        mock_task = Mock(spec=BaseTask)
        mock_task.task = Mock()
        mock_task.task.task_id = 'test_id'
        self.scheduler.task_queue['PriorityTask'] = Mock()
        self.scheduler.task_queue['PriorityTask'].get_nowait.side_effect = [
            mock_task
        ] + [asyncio.QueueEmpty for _ in range(50)]
        self.scheduler.task_queue['PriorityTask'].empty.side_effect = [
            False, True]

        # 模拟执行函数，设置正在执行的任务
        self.scheduler.max_concurrent_tasks = 2
        self.scheduler._execute_task = AsyncMock()

        # 调用run_tasks方法
        await asyncio.wait_for(self.scheduler.run_tasks('PriorityTask'),
                               timeout=0.1)

        # 验证任务执行
        self.scheduler.task_queue['PriorityTask'].get_nowait.assert_called()
        self.scheduler._execute_task.assert_called_once()

    async def test_execute_task(self):
        '''
        测试_execute_task方法
        '''
        # 创建模拟任务
        mock_task = Mock(spec=BaseTask)
        mock_task.task = Mock()
        mock_task.task.task_id = 'test_id'
        mock_task.execute = AsyncMock()
        self.scheduler.running_tasks[mock_task.task.task_id] = mock_task

        # 执行任务
        await self.scheduler._execute_task(mock_task)

        # 验证任务执行和结果处理
        mock_task.execute.assert_called_once()
        self.assertIn(mock_task, self.scheduler.result_queue._queue)
        self.assertNotIn(mock_task.task.task_id, self.scheduler.running_tasks)

    @patch('qcos.log.qcos_log.QCOSLogger.error')
    async def test_execute_task_timeout(self, mock_error):
        '''
        测试_execute_task方法中的failed场景
        '''
        # 创建模拟任务
        mock_task = Mock(spec=BaseTask)
        mock_task.task = Mock()
        mock_task.status = TaskStatus.FAILED
        mock_task.task.task_id = 'test_id'
        mock_task.execute.side_effect = asyncio.TimeoutError()
        self.scheduler.running_tasks[mock_task.task.task_id] = mock_task

        # 执行任务
        await self.scheduler._execute_task(mock_task)

        # 验证任务执行和结果处理
        mock_task.execute.assert_called_once()
        mock_error.assert_called()
        self.assertIn(mock_task, self.scheduler.completed_tasks)
        self.assertNotIn(mock_task.task.task_id, self.scheduler.running_tasks)

    @patch('qcos.log.qcos_log.QCOSLogger.warning')
    async def test_collect_processed_tasks(self, mock_logger):
        '''
        测试_collect_processed_tasks方法
        '''
        # 模拟结果队列
        self.scheduler.result_queue = Mock()
        qcos_configer.get_collect_task_num = MagicMock(return_value=2)
        self.scheduler.result_queue.qsize.return_value = 2
        self.scheduler.result_queue.get_nowait.side_effect = [
            Mock(spec=BaseTask),
            queue.Empty,
        ]

        # 收集处理后的任务
        await self.scheduler._collect_processed_tasks()

        # 验证收集结果
        self.assertEqual(len(self.scheduler.parsed_tasks), 1)
        self.assertTrue(self.scheduler.result_queue._queue.empty)
        mock_logger.assert_called_once_with('结果队列为空，获取任务结果失败')

    @patch('qcos.log.qcos_log.QCOSLogger.error')
    def test_measure_task_result(self, mock_error):
        '''
        测试measure_task_result方法
        '''
        # 模拟execute_task_on_quantum方法
        # 模拟聚合任务对应的属性与方法
        stop_event = threading.Event()
        stop_event.clear()  # 确保停止事件最初是未设置的
        bulk_task = Mock(spec=PriorityTask)
        bulk_task.result = 'test_bulk_task_result'
        bulk_task.shots = 100
        bulk_task.task = Mock(spec=QuantumCircuitTask)
        bulk_task.task.aggregation_tasks = [
            ('task1', 'PriorityTask', 1, 100, 'openqasm', {})
        ]
        bulk_task.task.aggregation_mappings = [{0: 'S0', 1: 'S1'}]
        bulk_task.task.measure_qubit_status = MagicMock(return_value=[[1, 0]])
        bulk_task.task.task_result = MagicMock(return_value={'task1': ''})
        # 模拟单独执行任务对应的属性与方法
        single_task = Mock(spec=PriorityTask)
        single_task.result = 'test_single_task_result'
        single_task.shots = 100
        single_task.task = Mock(spec=QuantumCircuitTask)
        single_task.task.task_id = 'task2'
        single_task.task.measure_qubit_status = MagicMock(
            return_value=[[1, 0]])
        single_task.task.na_map = Mock(spec=NASingleRoute)
        single_task.task.na_map.qnum = 2
        single_task.task.na_map.mapping = {0: 'S0', 1: 'S1'}
        single_task.task.task_result = MagicMock(return_value={'task2': ''})
        # 线程关闭时的任务处理场景
        stop_task = copy.deepcopy(single_task)

        # 对应聚合任务、单独执行任务、线程关闭三种场景
        self.scheduler.parsed_tasks = [bulk_task, single_task, stop_task]
        stop_event.is_set = Mock(side_effect=[False, False, True])
        for task in self.scheduler.parsed_tasks:
            task.task = MagicMock()
            task.task.execute_task_on_quantum.return_value = (
                ['00', '10'],
                ['10', '11'],
            )

        self.scheduler._save_task_result = MagicMock()

        # 调用measure_task_result方法
        self.scheduler.measure_task_result(stop_event)

        # 验证error日志是否没有被记录
        mock_error.assert_not_called()

        # 验证_save_task_result是否被正确调用
        # self.scheduler._save_task_result.assert_called()

        # 验证任务状态是否被正确设置（前两个为COMPLETED，最后一个为FAILED）
        for index, task in enumerate(self.scheduler.completed_tasks):
            if index < 2:
                self.assertEqual(task.status, TaskStatus.COMPLETED)
            else:
                self.assertEqual(task.status, TaskStatus.FAILED)

        # 验证完成的任务数量
        self.assertEqual(len(self.scheduler.completed_tasks), 3)

    @patch('builtins.open', new_callable=MagicMock)
    @patch('os.path.join')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_save_task_result(
            self,
            mock_exists,
            mock_makedirs,
            mock_join,
            mock_open):
        '''
        测试_save_task_result方法
        '''
        # 模拟函数参数
        qcos_task_id_generator.reverse_map = {'encode_id': 'task_id'}
        mock_exists.return_value = False
        mock_join.return_value = '***.txt'
        mock_file = mock_open.return_value.__enter__.return_value

        # 调用_save_task_result函数
        self.scheduler._save_task_result('encode_id', ['1'])

        # 验证函数是否被正确调用
        mock_open.assert_called_once_with('***.txt', 'w')

        # 验证文件内容是否被写入
        mock_file.write.assert_called_once_with('1\n')
        mock_makedirs.assert_called_once_with('***.txt')

    def test_get_task_status(self):
        '''
        测试get_task_status方法
        '''
        # 添加运行中和已完成的任务
        running_task = Mock(spec=BaseTask)
        # 为 running_task 添加 task 属性
        running_task.task = Mock()
        # 设置 task_id
        running_task.task.task_id = 'running_id'
        running_task.status = TaskStatus.RUNNING

        completed_task = Mock(spec=BaseTask)
        # 为 completed_task 添加 task 属性
        completed_task.task = Mock()
        # 设置 task_id
        completed_task.task.task_id = 'completed_id'
        completed_task.status = TaskStatus.COMPLETED

        # 将这些任务添加到相应的列表
        self.scheduler.running_tasks['running_id'] = running_task
        self.scheduler.completed_tasks.append(completed_task)

        # 获取任务状态并验证
        self.assertEqual(
            self.scheduler.get_task_status('running_id'), TaskStatus.RUNNING
        )
        self.assertEqual(
            self.scheduler.get_task_status('completed_id'),
            TaskStatus.COMPLETED)
        self.assertIsNone(self.scheduler.get_task_status('unknown_id'))

    def test_get_task_result(self):
        '''
        测试get_task_result方法
        '''
        # 添加已完成的任务
        completed_task = Mock(spec=BaseTask)
        # 为 completed_task 添加 task 属性
        completed_task.task = Mock()
        # 设置 task_id
        completed_task.task.task_id = 'completed_id'
        completed_task.result = 'Task result'

        # 将该任务添加到已完成任务列表
        self.scheduler.completed_tasks.append(completed_task)

        # 获取任务结果
        result = self.scheduler.get_task_result('completed_id')

        # 验证任务结果
        self.assertEqual(result, 'Task result')
        self.assertIsNone(self.scheduler.get_task_result('unknown_id'))

    @patch('heapq.heapify')
    async def test_cancel_task(self, mock_heapify):
        '''
        测试cancel_task方法
        '''
        # 创建模拟任务
        mock_task = Mock(spec=BaseTask)
        mock_task.task = Mock
        mock_task.task.task_id = 'test_id'
        self.scheduler.task_queue['PriorityTask']._queue = [mock_task]

        # 取消任务
        result = await self.scheduler.cancel_task('test_id')

        # 验证任务取消结果
        self.assertTrue(result)
        self.assertEqual(
            len(self.scheduler.task_queue['PriorityTask']._queue), 0)
        mock_heapify.assert_called_once()

    def test_get_task_count(self):
        '''
        测试get_task_count方法
        '''
        # 设置任务数量
        self.scheduler.task_queue['PriorityTask'] = Mock()
        self.scheduler.task_queue['PriorityTask'].qsize.return_value = 5
        self.scheduler.running_tasks = {'task1': Mock(), 'task2': Mock()}
        self.scheduler.completed_tasks = deque([Mock() for _ in range(3)])

        # 获取任务数量
        count = self.scheduler.get_task_count()

        # 验证任务数量
        self.assertEqual(count, {'pending': 5, 'running': 2, 'completed': 3})

    def test_cleanup_completed_tasks(self):
        '''
        测试cleanup_completed_tasks方法
        '''
        # 创建模拟任务
        current_time = time.time()
        old_task = Mock(spec=BaseTask)
        # 1小时+100秒前创建
        old_task.created_time = current_time - 3700
        new_task = Mock(spec=BaseTask)
        # 30分钟前创建
        new_task.created_time = current_time - 1800
        self.scheduler.completed_tasks = deque([old_task, new_task])

        # 清理已完成的旧任务
        self.scheduler.cleanup_completed_tasks()

        # 验证清理结果
        self.assertEqual(len(self.scheduler.completed_tasks), 1)
        self.assertIs(self.scheduler.completed_tasks[0], new_task)

    @patch('asyncio.sleep', new_callable=AsyncMock)
    async def test_monitor_task_progress(self, mock_sleep):
        '''
        测试monitor_task_progress方法
        '''
        # 模拟任务状态变化
        self.scheduler.get_task_status = Mock(
            side_effect=[
                TaskStatus.PENDING,
                TaskStatus.RUNNING,
                TaskStatus.COMPLETED])

        # 监控任务进度
        await self.scheduler.monitor_task_progress('test_id', interval=0.1)

        # 验证状态检查次数
        self.assertEqual(self.scheduler.get_task_status.call_count, 3)
        mock_sleep.assert_called_with(0.1)

    def test_get_task_statistics(self):
        '''
        测试get_task_statistics方法
        '''
        # 设置任务数量和时间
        self.scheduler.task_queue['PriorityTask'] = Mock()
        self.scheduler.task_queue['PriorityTask'].qsize.return_value = 5
        self.scheduler.running_tasks = {'task1': Mock(), 'task2': Mock()}
        completed_task = Mock(spec=PriorityTask)
        completed_task.task = Mock(spec=QuantumCircuitTask)
        completed_task.task.aggregation_tasks = [
            ('task1', 'PriorityTask', 1, 100, 'openqasm', {})
        ]
        self.scheduler.completed_tasks = deque(
            [completed_task for _ in range(3)])
        self.scheduler._calculate_average_waiting_time = Mock(
            return_value=10.5)
        self.scheduler._calculate_average_execution_time = Mock(
            return_value=5.2)

        # 获取任务统计信息
        stats = self.scheduler.get_task_statistics()

        # 验证统计信息
        self.assertEqual(stats['total_tasks'], 10)
        self.assertEqual(stats['total_sub_tasks'], 3)
        self.assertEqual(stats['average_waiting_time'], 10.5)
        self.assertEqual(stats['average_execution_time'], 5.2)
        self.assertEqual(
            stats['task_distribution'], {
                'pending': 5, 'running': 2, 'completed': 3})

    def test_calculate_average_waiting_time(self):
        '''
        测试_calculate_average_waiting_time方法
        '''
        # 创建模拟任务
        current_time = time.time()
        task1 = Mock(spec=BaseTask)
        task1.created_time = current_time - 10
        task2 = Mock(spec=BaseTask)
        task2.created_time = current_time - 20
        self.scheduler.task_queue['PriorityTask']._queue = [task1, task2]

        # 计算平均等待时间
        avg_waiting_time = self.scheduler._calculate_average_waiting_time()

        # 验证计算结果
        self.assertAlmostEqual(avg_waiting_time, 15, delta=1)

    def test_calculate_average_execution_time(self):
        '''
        测试_calculate_average_execution_time方法
        '''
        # 创建模拟BatchTask任务及其子任务
        task1 = Mock(spec=BatchTask)
        task1.status = TaskStatus.COMPLETED
        task1.created_time = 100
        task1.task = Mock()
        task_child = Mock()
        task_child.last_active_time = 110
        task1.tasks = [task_child]

        # 创建模拟BaseTask任务
        task2 = Mock(spec=BaseTask)
        task2.status = TaskStatus.COMPLETED
        task2.created_time = 200
        task2.task = Mock()
        task2.task.last_active_time = 220

        self.scheduler.completed_tasks = deque([task1, task2])

        # 计算平均执行时间
        avg_execution_time = self.scheduler._calculate_average_execution_time()

        # 验证计算结果
        self.assertEqual(avg_execution_time, 15)


if __name__ == '__main__':
    unittest.main()
