from dataclasses import dataclass

@dataclass
class Task():
    task_id: int
    user_id: int
    priority: int
    shots: int
    source: str
    executed_shots: int = 0
    result: str = ""
    status: str = "Queued"
    qubits: int = 0
    deleted: bool = False
