#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Xu Dong at 2024-09
# ----------------------------------------------------------------------


from qcos.cna.core.config import GlobalSetting
from qcos.cna.core.config import InstrumentType
from qcos.cna.core.taskmanager.task_executer import execute_task


DEFAULT_TASK_ID = 10
DEFAULT_SHOTS_NUMBER = 2

if __name__ == "__main__":
    """
    测试任务执行(execute_task)相关的函数
    """

    openqasm_str = '''
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg c[2];
    x q[0];
    cx q[0], q[1];
    measure q->c;
    '''

    GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_NONE)
    result = execute_task(DEFAULT_TASK_ID, DEFAULT_SHOTS_NUMBER, openqasm_str)
    print(f"Exec result is {result}")

    GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_HW_FPGA_AWG)
    result = execute_task(DEFAULT_TASK_ID, DEFAULT_SHOTS_NUMBER, openqasm_str)
    print(f"Exec result is {result}")

    GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_SIMULATOR_PULSER)
    result = execute_task(DEFAULT_TASK_ID, DEFAULT_SHOTS_NUMBER, openqasm_str)
    print(f"Exec result is {result}")