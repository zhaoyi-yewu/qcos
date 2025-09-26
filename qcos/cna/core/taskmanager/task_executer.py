#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Arclight, modified by Xu Dong at 2024-09
# ----------------------------------------------------------------------


import time
from ..compiler import compile
from ..sequencer import *
from ..instrument.fpga import FPGA
from ..instrument.awg import AWG
from ..instrument.awgmocker import AWGMocker
from ..instrument.instrument_base import InstrumentBase
from ..instrument.simulator_pulser import SimulatorPulser
from ..instrument.error import *
from ..config import GlobalSetting
from ..config import InstrumentType
from ..pulse import awg_trigger
import subprocess


test_chapter_dict = {
    'Doppler': '00000000 00000000 00000000', 
    'Doppler_Only': '00000000 00000000 00001111,[10000000 00000000 00000000, 1],[10000000 00000000 00010000,1]',
    'Pumping': '01100000 11000000 00000000', 
    'Microwave': '10000000 00100000 00000000',
    'Detection': '01010000 10000000 00001111,[11000000 00000000 00000000, 1],[11000000 00000000 00010000,1]', 
    'Raman': '11000000 10010000 00000000',
    'Zero': '11000000 10000000 00000000', 
    'Strong': '11111111 11111111 11111111', 
    'MolmerSorensen': '11000000 10010000 00000000',
}

def execute_on_empty_instrument(id: int, shots: int, source: str, log_path) -> str:
    """
    无真实硬件，无模拟器时调用此函数

    参数：id (int): 任务id
         shots (int): 执行次数
         source (str): 量子线路
         log_path (str): 日志路径
    返回值：任务执行结果
    """

    log = open(log_path, 'a')
    print("empty method execute_on_empty_instrument")
    time.sleep(shots)
    print(f"executed task {id} ({source}) for {shots} shots on hardware", file=log)
    log.close()
    return ""

def execute_on_simulator_pulser(id: int, shots: int, source: str, log_path) -> str:
    """
    调用模拟器执行任务

    参数：id (int): 任务id
         shots (int): 执行次数
         source (str): 量子线路
         log_path (str): 日志路径
    返回值：任务执行结果
    """

    log = open(log_path, 'a')
    print("method execute_on_simulator_pulser")
    qnum, pulses, meas = compile(source)
    try:
        pulser = InstrumentBase.find_instrument('pulser')
    except:
        pulser = SimulatorPulser('pulser', qnum, shots)
    result = pulser.comm(pulses)
    log.close()
    return result

def execute_on_real_hardware(id: int, shots: int, source: str, log_path) -> str:
    """
    调用真实硬件执行任务

    参数：id (int): 任务id
         shots (int): 执行次数
         source (str): 量子线路
         log_path (str): 日志路径
    返回值：任务执行结果
    """

    # 系统校准
    if (source == ''):
        log = open(log_path, 'a')
        print(f"=====start calibrate=====", file=log)
        p = subprocess.run(['python', 'calibrate.py'], stdout=subprocess.PIPE)
        out = str(p.stdout, encoding='utf-8')
        print(f"calib res: {out}", file=log)
        print(f"=====calibrate end=====", file=log)
        log.close()
        return out
    # 用户任务
    else:
        try:
            fpga = InstrumentBase.find_instrument('fpga')
        except:
            fpga = FPGA('fpga', clock_period=5E-3, bytes_returned=12, port="COM5", test_time = 0.1)

        try:
            awg = InstrumentBase.find_instrument('awg')
        except:
            awgConfig = {"channelList": [1, 2, 3, 4], 'addr_ip': '192.168.1.1'}
            awg = AWGMocker('awg', awgConfig)

        qnum, pulses, meas = compile(source)
        exp = Experiment(qubit_number=qnum, chapter_dict=test_chapter_dict, fpga=fpga, awg=awg, repeat=shots)
        seqs = exp.new_sequence()
        seqs.set_sequence(awg_trigger(), pulses)
        res, rea_res = exp.run_once()
        for i in range(shots):
            t = [ str(v) for v in np.where(res[i] > 0.5, 1, 0)]
            meas += ''.join(t)
        log = open(log_path, 'a')
        print(f"executed task {id} on hardware successfully", file=log)
        log.close()
        return meas

def execute_task(id: int, shots: int, source: str) -> str:
    """
    任务实际执行函数
    系统任务：调用校准脚本执行
    用户任务：进行低阶编译、序列分析、硬件运行后返回测量结果

    参数：id (int): 任务id
         shots (int): 执行次数
         source (str): 量子线路
    返回值：任务执行结果
    """
    log_path = GlobalSetting.get_log()
    result = ""
    instrument_type = GlobalSetting.get_instrument_type()
    if instrument_type == InstrumentType.INSTRUMENT_HW_FPGA_AWG:
        result = execute_on_real_hardware(id, shots, source, log_path)
    elif instrument_type == InstrumentType.INSTRUMENT_SIMULATOR_PULSER:
        result = execute_on_simulator_pulser(id, shots, source, log_path)
    else:
        result = execute_on_empty_instrument(id, shots, source, log_path)
    return result
