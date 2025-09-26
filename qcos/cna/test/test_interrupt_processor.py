from multiprocessing import Manager
from qcos.cna.core.taskmanager.interrupt_processer import InterruptProcesser
from qcos.cna.test.test_task_manager import my_add_task
from qcos.cna.core.config import GlobalSetting
from qcos.cna.core.config import InstrumentType
from qcos.cna.core.taskmanager.task_manager import TaskManager

class TestInterrupt:

    def setup_method(self):
        GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_NONE)
    
    def teardown_method(self):
        GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_HW_FPGA_AWG)

    def test_get_shots(self):
        with Manager() as manager:
            tasks = manager.list([])
            sch = InterruptProcesser(tasks, 10)
            assert sch.shots == 10

    def test_set_shots(self):
        with Manager() as manager:
            tasks = manager.list([])
            sch = InterruptProcesser(tasks, 10)
            sch.shots = 15
            assert sch.shots == 15

    def test_run_single(self):
        open(GlobalSetting.get_log(), 'w').close()
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            intp = InterruptProcesser(tasks)
            task = my_add_task(tm, 1)
            intp.run(task)

            log = open(GlobalSetting.get_log(), 'r')
            assert "pri-1-shots-1" in log.readline()
            assert not log.readline()

    def test_run_interrupt(self):
        open(GlobalSetting.get_log(), 'w').close()
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            intp = InterruptProcesser(tasks)
            task = my_add_task(tm, 1)
            my_add_task(tm, 0)
            intp.run(task)

            log = open(GlobalSetting.get_log(), 'r')
            assert "pri-0-shots-1" in log.readline()
            assert "pri-1-shots-1" in log.readline()
            assert not log.readline()

    def test_run_interupt_in_middle(self):
        open(GlobalSetting.get_log(), 'w').close()
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            intp = InterruptProcesser(tasks)
            task = my_add_task(tm, 1)
            my_add_task(tm, 0)
            intp.run(task)

            log = open(GlobalSetting.get_log(), 'r')
            assert "pri-0-shots-1" in log.readline()
            assert "pri-1-shots-1" in log.readline()
            assert not log.readline()

    def test_run_real(self, con):
        open(GlobalSetting.get_log(), 'w').close()
        GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_HW_FPGA_AWG)
        with Manager() as manager:
            tasks = manager.list([])
            tm = TaskManager(tasks)
            intp = InterruptProcesser(tasks)
            data = '''
                OPENQASM 2.0;
                include "qelib1.inc";

                qreg q[2];
                x q[0];
                cz q[0], q[1];
            '''
            task = tm.add_task(1, 1, data)
            intp.run(task)

            log = open(GlobalSetting.get_log(), 'r')
            assert "successfully" in log.readline()
            assert not log.readline()
