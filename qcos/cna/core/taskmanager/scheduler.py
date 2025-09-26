from .task import Task

class Scheduler:
    """
    调度器

    Args:
        policy (str): 调度策略
    """
    def __init__(self, tasks, policy: str):
        self.tasks = tasks
        self.policy = policy

    @property
    def policy(self):
        return self._policy

    @policy.setter
    def policy(self, value: str):
        self._policy = value

    def run(self) -> Task:
        """
        根据调度策略，从数据库中找寻下一个可执行的任务
        """
        def base_keyfunc(task: Task) -> int:
            return 1e20 if task.deleted or task.status != "Queued" else 0
        if self._policy == "Time":
            keyfunc = lambda task: base_keyfunc(task)
        elif self._policy == "Priority":
            keyfunc = lambda task: base_keyfunc(task) + task.priority
        else:
            keyfunc = lambda task: base_keyfunc(task) + task.shots
        res = min(self.tasks, key=keyfunc, default=None)
        if res is None or res.deleted or res.status != "Queued":
            return None
        return res


class QuantumTaskControlBlock:
    def __init__(self, task_id, priority, quantum_circuit, shots):
        # 任务基础信息
        self.task_id = task_id
        self.state = "WAITING"  
        self.priority = priority
        self.quantum_circuit = quantum_circuit
        self.shots = shots
        self.executed = 0
        self.result = [] #测量结果

    def save_state(self):
        print(f"Saving state for task {self.task_id}")

    def restore_state(self):
        print(f"Restoring state for task {self.task_id}")

    def allocate_resources(self, resources):
        self.allocated_resources = resources
        print(f"Allocated resources for task {self.task_id}")

    def release_resources(self):
        self.allocated_resources = {}
        print(f"Released resources for task {self.task_id}")

    def execute(self):
        self.state = "RUNNING"
        print(f"Executing task {self.task_id}")
        self.state = "COMPLETED"
        self.result = [0,1]
        print(f"Task {self.task_id} completed")