from .interrupt_processer import InterruptProcesser
from .scheduler import Scheduler
from .task import Task
from multiprocessing.managers import ListProxy
import time

class TaskManager:
    def __init__(self, tasks: ListProxy):
        self.intp = InterruptProcesser(tasks)
        self.sch = Scheduler(tasks, "Time")
        self.tasks = tasks

    def add_task(self, user_id: int, priority: int, source: str, shots: int = 1) -> Task:
        """
        添加任务

        Args:
            user_id (int): 用户id
            source (str): 量子线路（openqasm2.0）
            shots (int, optional): 执行次数. Defaults to 1.
        """
        task_id = len(self.tasks)
        task = Task(task_id, user_id, priority, shots, source)
        self.tasks.append(task)
        return task

    def delete_task(self, task_id: int) -> bool:
        """
        删除任务

        Args:
            task_id (int): 任务id
        """
        if len(self.tasks) > task_id and not self.tasks[task_id].deleted:
            task: Task = self.tasks[task_id]
            task.deleted = True
            self.tasks[task_id] = task
            return True
        return False

    def modify_task(self, task_id: int, source: str) -> bool:
        """
        修改任务
        """
        if len(self.tasks) > task_id and not self.tasks[task_id].deleted:
            task: Task = self.tasks[task_id]
            task.source = source
            self.tasks[task_id] = task
            return True
        return False

    def query_result(self, task_id: int) -> str:
        """
        查询任务状态和结果

        Args:
            task_id (int): 任务id
        """
        if len(self.tasks) <= task_id or self.tasks[task_id].deleted:
            return "Task not found!"
        task: Task = self.tasks[task_id]
        status = task.status
        if status != "Succeed":
            return f"Task is {status}"
        return task.result

    def run(self):
        while True:
            task = self.sch.run()
            print(f"{task=}")
            if task:
                self.intp.run(task)
            else:
                time.sleep(1)