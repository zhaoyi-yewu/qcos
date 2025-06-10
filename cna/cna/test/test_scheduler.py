from multiprocessing import Manager
from qcos.cna.core.taskmanager.scheduler import Scheduler, QuantumTaskControlBlock
from qcos.cna.test.test_task_manager import my_add_task, TaskManager
from qcos.cna.core.config import GlobalSetting

def test_scheduler_get_policy():
    with Manager() as manager:
        tasks = manager.list([])
        sch = Scheduler(tasks, "Time")
        assert sch.policy == "Time"

def test_scheduler_set_policy():
    with Manager() as manager:
        tasks = manager.list([])
        sch = Scheduler(tasks, "Time")
        sch.policy = "Shots"
        assert sch._policy == "Shots"

def test_schedule_return_none():
    with Manager() as manager:
        tasks = manager.list([])
        sch = Scheduler(tasks, "Time")
        assert sch.run() is None

def test_schedule_tasks_by_time():
    with Manager() as manager:
        tasks = manager.list([])
        tm = TaskManager(tasks)
        task1 = my_add_task(tm, 1)
        my_add_task(tm, 2, 10)
        my_add_task(tm, 1, 20)

        sch = Scheduler(tasks, "Time")
        task = sch.run()
        assert task == task1

def test_schedule_tasks_by_pri():
    with Manager() as manager:
        tasks = manager.list([])
        tm = TaskManager(tasks)
        my_add_task(tm, 2)
        my_add_task(tm, 2, 10)
        task3 = my_add_task(tm, 1, 20)

        sch = Scheduler(tasks, "Priority")
        task = sch.run()
        assert task == task3

def test_schedule_tasks_by_shots():
    with Manager() as manager:
        tasks = manager.list([])
        tm = TaskManager(tasks)
        my_add_task(tm, 1, 20)
        my_add_task(tm, 2, 10)
        task = my_add_task(tm, 1)

        sch = Scheduler(tasks, "Shots")
        res = sch.run()
        assert res == task
