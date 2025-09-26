from multiprocessing import Process, Manager, set_start_method
from qcos.cna.core.taskmanager.task import Task
from qcos.cna.core.taskmanager.task_manager import TaskManager
import time
from qcos.cna.core.config import GlobalSetting
from qcos.cna.core.config import InstrumentType

def my_add_task(tm: TaskManager, pri: int, shots: int = 1) -> Task:
    source = f"pri-{pri}-shots-{shots}"
    res = tm.add_task(pri, pri, source, shots)
    return res

def run_task_manager(tm: TaskManager):
    open(GlobalSetting.get_log(), 'w').close()
    GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_NONE)
    tm.run()
         
class TestTask:
    
    def setup_method(self):
        GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_NONE)
    
    def teardown_method(self):
        GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_NONE)

    def test_add_task(self):
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)

            def check_add_task(pri: int, shots: int = 1):
                task = my_add_task(tm, pri, shots)
                assert shots == task.shots
                assert pri == task.priority

            check_add_task(0)
            check_add_task(1, 10)
            check_add_task(2, 20)
            check_add_task(2)
            assert (len(tasks) == 4)
            for task in tasks:
                print(task)

    def test_delete_valid_task(self):
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            task = my_add_task(tm, 1, 10)
            assert tm.delete_task(task.task_id)

    def test_delete_nonexisting_task(self):
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            assert not tm.delete_task(100)

    def test_modify_task(self):
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            res = my_add_task(tm, 1, 10)
            new_source = "new source"
            assert tm.modify_task(res.task_id, new_source)

    def test_modify_nonexisting_task(self):
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            assert not tm.modify_task(1, "")

    def test_query_nonexisting_task(self):
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            assert tm.query_result(666) == "Task not found!"

    def test_query_unfinished_task(self):
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            task = my_add_task(tm, 2)
            assert tm.query_result(task.task_id) == "Task is Queued"

    def test_query_succeed_task(self):
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            task = my_add_task(tm, 2)
            task.status = "Succeed"
            task.result = "xxx"
            tm.tasks[0] = task
            assert tm.query_result(0) == "xxx"

    def test_not_schedule_deleted_tasks(self):
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            my_add_task(tm, 1)
            task = my_add_task(tm, 2, 10)
            my_add_task(tm, 1, 20)
            tm.delete_task(task.task_id)

            set_start_method("spawn", force=True)
            p = Process(target=run_task_manager, args=(tm,))
            p.start()
            time.sleep(30)
            p.kill()

            log = open(GlobalSetting.get_log(), 'r')
            assert "pri-1-shots-1" in log.readline()
            assert "pri-1-shots-20" in log.readline()
            assert not log.readline()

    def test_schedule_tasks_in_slices(self):
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            tm.intp.shots = 10
            my_add_task(tm, 1, 20)
            my_add_task(tm, 2, 10)
            my_add_task(tm, 1)
            set_start_method("spawn", force=True)
            p = Process(target=run_task_manager, args=(tm,))
            p.start()
            time.sleep(50)
            p.kill()

            log = open(GlobalSetting.get_log(), 'r')
            assert "(pri-1-shots-20) for 10 shots" in log.readline()
            assert "(pri-1-shots-20) for 10 shots" in log.readline()
            assert "(pri-2-shots-10) for 10 shots" in log.readline()
            assert "(pri-1-shots-1) for 1 shot" in log.readline()
            assert not log.readline()

    def test_schedule_newly_added_tasks(self):
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            tm.sch.policy = "Priority"
            tm.intp.shots = 10
            my_add_task(tm, 1, 10)
            my_add_task(tm, 2, 10)
            my_add_task(tm, 2)
            set_start_method("spawn", force=True)
            p = Process(target=run_task_manager, args=(tm,))
            p.start()
            time.sleep(3)
            my_add_task(tm, 1)
            time.sleep(30)
            p.kill()

            log = open(GlobalSetting.get_log(), 'r')
            assert "pri-1-shots-10" in log.readline()
            assert "pri-1-shots-1" in log.readline()
            assert "pri-2-shots-10" in log.readline()
            assert "pri-2-shots-1" in log.readline()
            assert not log.readline()

    def test_interrupt(self):
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            tm.intp.shots = 10
            tm.add_task(1, 1, "pri-1-shots-20", 20)
            tm.add_task(2, 2, "pri-2-shots-10", 10)
            tm.add_task(1, 1, "pri-1-shots-1")
            set_start_method("spawn", force=True)
            p = Process(target=run_task_manager, args=(tm,))
            p.start()
            time.sleep(10)
            tm.add_task(0, 0, "pri-0-shots-1")
            time.sleep(50)
            p.kill()

            log = open(GlobalSetting.get_log(), 'r')
            assert "(pri-1-shots-20) for 10 shots" in log.readline()
            assert "(pri-0-shots-1) for 1 shot" in log.readline()
            assert "(pri-1-shots-20) for 10 shots" in log.readline()
            assert "(pri-2-shots-10) for 10 shots" in log.readline()
            assert "(pri-1-shots-1) for 1 shot" in log.readline()
            assert not log.readline()
