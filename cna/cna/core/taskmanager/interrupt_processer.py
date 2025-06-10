from typing import List
from .task import Task
from .task_state_updater import TaskStateUpdater
from .task_executer import execute_task

class InterruptProcesser():
    """
    任务执行类，内含中断操作

    Args:
        con (sqlite3.Connection): 数据库
        shots (int, optional): 每个时间片的执行次数. Defaults to 20.
    """
    def __init__(self, tasks, shots: int = 20):
        self.tasks = tasks
        self.shots = shots
        self.stack = []
        self.updater = TaskStateUpdater(tasks)

    @property
    def shots(self):
        return self._shots

    @shots.setter
    def shots(self, value: int):
        self._shots = value

    def get_current_task(self):
        """
        切换待执行任务
        """
        return self.stack.pop()

    def run(self, task: Task):
        """
        按照时间片方式运行指定任务，通知监控中断情况
        """
        self.stack.append(task)
        while self.stack:
            task = self.get_current_task()
            self.updater.set_task_status(task, "Running")
            while task.executed_shots < task.shots:
                found_interrupt = False
                for interrupt in self.tasks:
                    if interrupt.priority == 0 and interrupt.status == "Queued" and not interrupt.deleted:
                        self.stack.append(task)
                        self.stack.append(interrupt)
                        self.updater.set_task_status(task, "Halt")
                        found_interrupt = True
                        break
                if found_interrupt:
                    break
                shots = min(task.shots - task.executed_shots, self.shots)
                try:
                    res = execute_task(task.task_id, shots, task.source)
                    task.executed_shots += shots
                    task.result += res
                except:
                    self.updater.set_task_status(task, "Failed")
                    break
            else:
                self.updater.set_task_status(task, "Succeed")
