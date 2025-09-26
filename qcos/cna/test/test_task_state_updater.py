from multiprocessing import Manager
from qcos.cna.core.taskmanager.task_state_updater import TaskStateUpdater
from qcos.cna.test.test_task_manager import my_add_task, TaskManager

def test_set_task_status():
    with Manager() as manager:
        tasks = manager.list([])
        tm = TaskManager(tasks)
        tsu = TaskStateUpdater(tasks)
        task = my_add_task(tm, 1)
        tsu.set_task_status(task, "Running")
        assert tasks[0].status == "Running"
