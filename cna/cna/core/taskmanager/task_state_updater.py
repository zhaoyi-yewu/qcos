from .task import Task

class TaskStateUpdater():
    def __init__(self, tasks) -> None:
        self.tasks = tasks

    def set_task_status(self, task: Task, status: str) -> None:
        """
        任务状态更新
        """
        task.status = status
        self.tasks[task.task_id] = task
