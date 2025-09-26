#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-09
# ------------------------


import ast
import configparser
from typing import List
import json
import os


class QcosConfigManager:
    """
    QCOS配置类，负责读取和管理配置信息
    """

    def __init__(self, config_path: str = "qcos_config.conf"):
        """
        初始化QCOSConfig实例

        参数:
        config_path (str): 配置文件路径，默认为"qcos_config.conf"
        """
        # 创建ConfigParser对象
        self.config = configparser.ConfigParser()
        # 配置config文件的绝对路径
        self.config_path = os.path.join(self.get_config_path(), config_path)
        # 读取配置文件
        with open(self.config_path, 'r', encoding='utf-8') as fp:
            self.config.read_file(fp)

    def get_log_dir(self) -> str:
        """
        获取日志目录路径

        返回:
        str: 日志目录路径
        """
        # 从配置文件中读取日志目录路径，如果不存在则使用默认值
        return self.config.get('log', 'log_dir', fallback='runtime_log/qcos/')

    def get_log_file_size(self) -> int:
        """
        获取日志文件大小限制

        返回:
        int: 日志文件大小限制（字节）
        """
        # 从配置文件中读取日志文件大小限制，如果不存在则使用默认值
        return self.config.getint('log', 'log_file_size', fallback=10485760)

    def get_log_file_count(self) -> int:
        """
        获取日志文件数量限制

        返回:
        int: 日志文件数量限制
        """
        # 从配置文件中读取日志文件数量限制，如果不存在则使用默认值
        return self.config.getint('log', 'log_file_count', fallback=5)

    def get_config_path(self) -> str:
        """
        获取config的目录路径

        返回：
        str: config的目录路径
        """
        return os.path.dirname(os.path.abspath(__file__))

    def get_original_openqasm_file_path(self) -> str:
        """
        获取original OpenQASM文件路径

        返回:
        str: original OpenQASM文件路径
        """
        # 从配置文件中读取original OpenQASM文件路径，如果不存在则使用默认值
        return os.path.join(os.path.dirname(self.get_config_path()),
                            self.config.get('openqasm', 'original_openqasm_file_path', fallback='user_task/user_original_task'))

    def get_processing_openqasm_file_path(self) -> str:
        """
        获取processing OpenQASM文件路径

        返回:
        str: processing OpenQASM文件路径
        """
        # 从配置文件中读取processing OpenQASM文件路径，如果不存在则使用默认值
        return os.path.join(os.path.dirname(self.get_config_path()),
                            self.config.get('openqasm', 'processing_openqasm_file_path', fallback='user_task/qcos_processing_task'))

    def get_qubit_nums(self) -> int:
        """
        获取量子比特数量

        返回:
        int: 量子比特数量
        """
        # 从配置文件中读取量子比特数量，如果不存在则使用默认值
        return self.config.getint('openqasm', 'qubit_nums', fallback=10)

    def get_shots_num(self) -> int:
        """
        获取测量次数

        返回:
        int: 测量次数
        """
        # 从配置文件中读取测量次数，如果不存在则使用默认值
        return self.config.getint('openqasm', 'shots_num', fallback=1000)

    def get_task_priority(self) -> int:
        """
        获取优先级

        返回:
        int: 任务优先级
        """
        # 从配置文件中读取优先级，如果不存在则使用默认值
        return self.config.getint('openqasm', 'priority', fallback=1)

    def get_task_type(self) -> str:
        """
        获取任务类型

        返回:
        str: 任务类型
        """
        # 从配置文件中读取任务类型，如果不存在则使用默认值
        return self.config.get('openqasm', 'task_type', fallback='PriorityTask')

    def get_task_result_path(self) -> str:
        """
        获取任务执行结果存放路径

        返回:
        str: 任务执行结果存放路径
        """
        # 从配置文件中读取任务执行结果存放路径，如果不存在则使用默认值
        return os.path.join(
            self.get_config_path(), self.config.get('openqasm', 'task_result_path', fallback='task_result/xternal'))

    def get_fetch_interval(self) -> int:
        """
        获取任务获取间隔时间

        返回:
        int: 任务获取间隔时间（秒）
        """
        # 从配置文件中读取任务获取间隔时间，如果不存在则使用默认值
        return self.config.getint('task', 'fetch_interval', fallback=60)

    def get_task_sources(self) -> List[str]:
        """
        获取任务源列表

        返回:
        List[str]: 任务源列表
        """
        # 从配置文件中读取任务源列表，如果不存在则使用默认值
        sources = self.config.get('task', 'sources', fallback="DQCOS")
        # 将逗号分隔的字符串转换为列表
        return [source.strip() for source in sources.split(',')]

    def get_fetch_task_num(self) -> int:
        """
        获取从 DQCOS 每次拉取的最大任务数量

        返回:
        int: 每次拉取的最大任务数量
        """
        # 从配置文件中读取拉取的最大任务数量，如果不存在则使用默认值
        return self.config.getint('task', 'fetch_task_num', fallback=5)

    def get_fetch_cancellation_task_num(self) -> int:
        """
        获取从 DQCOS 每次拉取需要取消的最大任务数量

        返回:
        int: 每次拉取需要取消的最大任务数量
        """
        # 从配置文件中读取每次拉取需要取消的最大任务数量，如果不存在则使用默认值
        return self.config.getint('task', 'fetch_cancellation_task_num', fallback=5)

    def get_send_task_wait_time(self) -> int:
        """
        获取监听并向 DQCOS 返回任务结果时的间隔时间

        返回:
        int: 返回任务结果的间隔时间（秒）
        """
        # 从配置文件中读取返回任务结果的间隔时间，如果不存在则使用默认值
        return self.config.getint('task', 'send_task_wait_time', fallback=30)

    def get_error_wait_time(self) -> int:
        """
        获取错误等待时间

        返回:
        int: 错误等待时间（秒）
        """
        # 从配置文件中读取错误等待时间，如果不存在则使用默认值
        return self.config.getint('task', 'error_wait_time', fallback=300)

    def get_scheduler_wait_time(self) -> int:
        """
        获取调度等待任务时间

        返回:
        int: 调度等待任务时间（秒）
        """
        # 从配置文件中读取调度等待任务时间，如果不存在则使用默认值
        return self.config.getint('task', 'scheduler_wait_time', fallback=30)

    def get_max_concurrent_tasks(self) -> int:
        """
        获取最大任务并发数

        返回:
        int: 最大任务并发数
        """
        # 从配置文件中读取错误等待时间，如果不存在则使用默认值
        return self.config.getint('task', 'max_concurrent_tasks', fallback=5)

    def get_task_aggregation_upper_threshold(self) -> int:
        """
        获取多任务聚合的上限阈值

        返回:
        int: 多任务聚合上限阈值
        """
        # 获取多任务聚合上限阈值
        return self.config.getint('task', 'task_aggregation_upper_threshold', fallback=5)

    def get_task_aggregation_lower_threshold(self) -> int:
        """
        获取多任务聚合的下限阈值

        返回:
        int: 多任务聚合下限阈值
        """
        # 获取多任务聚合下限阈值
        return self.config.getint('task', 'task_aggregation_lower_threshold', fallback=2)

    def get_task_aggregation_switch(self) -> bool:
        """
        获取多任务聚合开关状态

        返回:
        bool: 多任务聚合开关状态
        """
        # 获取多任务聚合开关状态，默认为 False
        return self.config.getboolean('task', 'task_aggregation_switch', fallback=False)

    def get_collect_task_num(self) -> int:
        """
        获取每次任务解析结果收集的数量

        返回：
        int: 每次任务解析结果收集的数量
        """
        # 从配置文件中获取每次任务解析结果收集的数量，如果不存在则使用默认值
        return self.config.getint('task', 'collect_task_num', fallback=1)

    def get_single_gate_cost(self) -> float:
        """
        获取校准的单比特门执行的平均耗时

        返回：
        float: 校准的单比特门执行的平均耗时（秒）
        """
        # 从配置文件中获取校准的单比特门执行的平均耗时，如果不存在则使用默认值
        return self.config.getfloat('task', 'single_gate_cost', fallback=6E-6)

    def get_multi_gate_cost(self) -> float:
        """
        获取校准的两比特门执行的平均耗时

        返回：
        float: 校准的两比特门执行的平均耗时（秒）
        """
        # 从配置文件中获取校准的两比特门执行的平均耗时，如果不存在则使用默认值
        return self.config.getfloat('task', 'multi_gate_cost', fallback=2E-6)

    def get_dqcos_url(self) -> str:
        """
        获取DQCOS_URL

        返回:
        str: DQCOS_URL
        """
        # 从配置文件中读取DQCOS_URL，如果不存在则使用默认值
        return self.config.get('qcos', 'dqcos_url', fallback='http://127.0.0.1:5000')

    def get_device_id(self) -> str:
        """
        获取设备ID

        返回:
        str: 设备ID
        """
        # 从配置文件中读取设备ID，如果不存在则使用默认值
        return self.config.get('qcos', 'device_id', fallback='1')

    def get_autotest_url(self) -> str:
        """
        获取自动化测试URL

        返回:
        str: AUTOTEST_URL
        """
        # 从配置文件中读取AUTOTEST_URL，如果不存在则使用默认值
        return self.config.get('qcos', 'autotest_url', fallback='http://100.78.61.1:8385')

    def get_topo_file(self) -> dict:
        """
        获取拓扑文件的内容，返回拓扑文件中overview部分的内容

        返回:
        dict: 拓扑文件中overview字段的内容，或一个空字典如果读取失败
        """
        # 从配置文件中读取拓扑文件路径，如果不存在则使用默认值
        topo_file_path = self.config.get('topology', 'topo_file', fallback='na_file.json')

        # 尝试读取拓扑文件并解析JSON中的overview部分
        if isinstance(topo_file_path, str):
            try:
                # 获取当前文件的绝对路径
                current_dir = os.path.dirname(os.path.abspath(__file__))
                # 构建json文件的绝对路径
                topo_file_path = os.path.join(current_dir, topo_file_path)
                with open(topo_file_path, 'r') as f:
                    config = json.load(f)  # 读取JSON文件
                    return config.get('overview', {})  # 返回overview部分，如果没有overview则返回空字典
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"无法读取拓扑文件或解析JSON: {e}")
                return {}

        # 如果topo_file不是字符串，返回一个空字典
        return {}

    def get_na_file(self) -> str:
        # 从配置文件中读取拓扑文件路径，如果不存在则使用默认值
        topo_file_path = self.config.get('topology', 'topo_file', fallback='na_file.json')
        # 获取当前文件的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建json文件的绝对路径
        na_file_path = os.path.join(current_dir, topo_file_path)
        return na_file_path

    def get_awg_sampling_rate(self) -> int:
        """
        获取AWG的采样频率

        返回:
        int: AWG的采样频率
        """
        # 从配置文件中获取AWG的采样频率，如果不存在则使用默认值
        return self.config.getint('AWG', 'samplingRateMHz', fallback=500)

    def get_awg_delay_value(self) -> int:
        """
        获取AWG的硬件延迟

        返回:
        int: AWG的硬件延迟
        """
        # 从配置文件中获取AWG的硬件延迟，如果不存在则使用默认值
        return self.config.getint('AWG', 'delay', fallback=0)

    def get_awg_test_time(self) -> float:
        """
        获取AWG的测试时间

        返回:
        float: AWG的测试时间
        """
        # 从配置文件中获取AWG的测试时间，如果不存在则使用默认值
        return self.config.getfloat('AWG', 'test_time', fallback=0.5)

    def get_awg_address(self) -> str:
        """
        获取AWG的设备地址

        返回:
        str: AWG的设备地址
        """
        # 从配置文件中获取AWG的设备地址，如果不存在则使用默认值
        return self.config.get('AWG', 'awg_address', fallback="192.168.1.1")

    def get_awg_channel(self) -> list:
        """
        获取AWG的通道

        返回:
        list: AWG的通道
        """
        # 从配置文件中获取AWG的通道数，如果不存在则使用默认值
        res = self.config.get('AWG', 'channel', fallback=[1, 2, 3, 4])
        # get方法返回字符串类型，使用ast.literal_eval()安全地将字符串转换为期望的列表类型
        return ast.literal_eval(res)

    def get_awg_serial_number(self) -> str:
        """
        获取AWG的序列号

        返回:
        str: AWG的序列号
        """
        # 从配置文件中获取AWG的序列号，如果不存在则使用默认值
        return self.config.get('AWG', 'serialNumber', fallback="MY63400261")

    def get_awg_product(self) -> str:
        """
        获取AWG的产品类型

        返回:
        str: AWG的产品类型
        """
        # 从配置文件中获取AWG的产品类型，如果不存在则使用默认值
        return self.config.get('AWG', 'product', fallback="M3201A")

    def get_awg_amplitude(self) -> list:
        """
        获取AWG的放大系数

        返回:
        float: AWG的放大系数
        """
        # 从配置文件中获取AWG的放大系数，如果不存在则使用默认值
        res = self.config.get('AWG', 'amp', fallback=[0.2, 1.2, 0.2, 0.2])
        return ast.literal_eval(res)

    def get_awg_trigger_mode(self) -> int:
        """
        获取AWG的触发模式

        返回:
        int: AWG的触发模式
        """
        # 从配置文件中获取AWG的触发模式，如果不存在则使用默认值
        return self.config.getint('AWG', 'trigger_mode', fallback=2)

    def get_awg_lib_path(self) -> str:
        """
        获取AWG依赖库路径

        返回:
        str: AWG依赖库路径
        """
        # 从配置文件中获取AWG的依赖库路径，如果不存在则使用默认值
        return self.config.get('AWG', 'awg_lib_path', fallback="C:/Program Files/Keysight/SD1/shared/SD1core")

    def get_awg_wave_id_file(self) -> str:
        """
        获取AWG波形id文件路径

        返回:
        str: AWG波形id文件路径
        """
        # 从配置文件中获取AWG的波形id文件路径，如果不存在则使用默认值
        return self.config.get('AWG', 'wave_id_file', fallback="./wave_id.json")

    def get_awg_wave_file_dir(self) -> str:
        """
        获取AWG波形文件路径

        返回:
        str: AWG波形文件路径
        """
        # 从配置文件中获取AWG的波形文件路径，如果不存在则使用默认值
        return self.config.get('AWG', 'wave_file_dir', fallback="./wave_file")

    def get_debug_mode(self) -> bool:
        """
        获取AWG的执行模式

        返回:
        bool: 执行模式， 0：调试模式 1：真机执行模式
        """
        # 从配置文件中获取AWG的执行模式，如果不存在则使用默认值
        return self.config.getboolean('AWG', 'debug_mode', fallback=True)

    def get_fpga_port_value(self) -> str:
        """
        获取FPGA的端口号

        返回:
        str: FPGA的端口号
        """
        # 从配置文件中获取FPGA的端口号，如果不存在则使用默认值
        return self.config.get('FPGA', 'port', fallback="COM5")

    def get_fpga_clock_period(self) -> float:
        """
        获取FPGA的时钟周期

        返回:
        float: FPGA的时钟周期
        """
        # 从配置文件中获取FPGA的时钟周期，如果不存在则使用默认值
        return self.config.getfloat('FPGA', 'clock_period', fallback=1E-3)

    def get_fpga_test_time(self) -> float:
        """
        获取FPGA的测试时间

        返回:
        float: FPGA的测试时间
        """
        # 从配置文件中获取FPGA的测试时间，如果不存在则使用默认值
        return self.config.getfloat('FPGA', 'test_time', fallback=0.5)

    def get_fpga_bytes_returned_value(self) -> int:
        """
        获取FPGA的返回数据字节数

        返回:
        int: FPGA的返回数据字节数
        """
        # 从配置文件中获取FPGA的设备地址，如果不存在则使用默认值
        return self.config.getint('FPGA', 'bytes_returned', fallback=12)

    def get_fpga_ext_trig(self) -> int:
        """
        获取FPGA的信号模式字段

        返回:
        int: FPGA的信号模式
        """
        # 从配置文件中获取FPGA的信号模式，如果不存在则使用默认值
        return self.config.getint('FPGA', 'ext_trig', fallback=1)

    def get_ni_ao_type(self) -> str:
        """
        获取NIAO的设备类型

        返回:
        str: NIAO的设备类型
        """
        fallback = 'niao'
        get_res = self.config.get('NI', 'type', fallback=fallback)
        if get_res == fallback or not get_res.split(','):
            return get_res
        return get_res.split(',')[0].strip()

    def get_ni_ao_address(self) -> list:
        """
        获取NIAO的设备地址

        返回:
        list: NIAO的设备地址
        """
        fallback = ["/dev1/ao0", "/dev1/ao3", "/dev1/ao4", "/dev1/ao7", "/dev1/ao8", "/dev1/ao9", "/dev1/ao15",
                    "/dev1/ao16", "/dev1/ao17", "/dev1/ao18"]
        get_res = self.config.get('NI', 'address', fallback=fallback)
        if get_res == fallback or not get_res.split(','):
            return get_res
        return get_res.split(',')[0].strip().split('|')

    def get_ni_ao_rate(self) -> float:
        """
        获取NIAO的设备采样率

        返回:
        float: NIAO的设备采样率
        """
        fallback = 4e5
        get_res = self.config.get('NI', 'rate', fallback=fallback)
        if get_res == fallback or not get_res.split(','):
            return float(get_res)
        return ast.literal_eval(get_res.split(',')[0].strip())

    def get_ni_ao_trigger_source(self) -> str:
        """
        获取NIAO的触发源

        返回:
        str: NIAO的触发源
        """
        return self.config.get('NI', 'trigger_source', fallback="/dev1/PFI0")

    def get_ni_do_type(self) -> str:
        """
        获取NIDO的设备类型

        返回:
        str: NIDO的设备类型
        """
        fallback = 'nido'
        get_res = self.config.get('NI', 'type', fallback=fallback)
        if get_res == fallback or len(get_res.split(',')) < 2:
            return get_res
        return get_res.split(',')[1].strip()

    def get_ni_do_address(self) -> list:
        """
        获取NIDO的设备地址

        返回:
        list: NIDO的设备地址
        """
        fallback = ["/dev2/port0/line0:7", "/dev2/port1/line0:3", "/dev2/port2/line6", "/dev2/port3/line2",
                    "/dev2/port3/line3", "/dev2/port3/line6"]
        get_res = self.config.get('NI', 'address', fallback=fallback)
        if get_res == fallback or len(get_res.split(',')) < 2:
            return get_res
        return get_res.split(',')[1].strip().split('|')

    def get_ni_do_rate(self) -> float:
        """
        获取NIDO的设备采样率

        返回:
        float: NIDO的设备采样率
        """
        fallback = 5e5
        get_res = self.config.get('NI', 'rate', fallback=fallback)
        if get_res == fallback or len(get_res.split(',')) < 2:
            return float(get_res)
        return ast.literal_eval(get_res.split(',')[1].strip())

    def get_ni_di_type(self) -> str:
        """
        获取NIDI的设备类型

        返回:
        str: NIDI的设备类型
        """
        fallback = 'nidi'
        get_res = self.config.get('NI', 'type', fallback=fallback)
        if get_res == fallback or len(get_res.split(',')) < 3:
            return get_res
        return get_res.split(',')[2].strip()

    def get_ni_di_address(self) -> list:
        """
        获取NIDI的设备地址

        返回:
        list: NIDI的设备地址
        """
        fallback = ['']
        get_res = self.config.get('NI', 'address', fallback=fallback)
        if get_res == fallback or len(get_res.split(',')) < 3:
            return get_res
        return get_res.split(',')[2].strip().split('|')

    def get_delay_time(self) -> int:
        """
         获取NI时序的延长时间

         返回:
         int: NI时序的延长时间
         """
        # 从配置文件中获取NI时序的延长时间，如果不存在则使用默认值
        return self.config.getint('NI', 'delay_time', fallback=0)

    def get_delay_start(self) -> int:
        """
         获取NI时序的开始时刻

         返回:
         int: NI时序的开始时刻
         """
        # 从配置文件中获取NI时序的开始时刻，如果不存在则使用默认值
        return self.config.getint('NI', 'delay_start', fallback=0)

    def get_do0_pgc_cooling_time(self) -> int:
        """
        获取PGC冷却光作用时间

        返回：
        int: PGC冷却光作用时间
        """
        # 从配置文件中获取PGC冷却光作用时间，如果不存在则使用默认值
        return self.config.getfloat('NI', 'do0_pgc_cooling_time', fallback=0)

    def get_do0_meas_cooling_time(self) -> int:
        """
        获取探测冷却光作用时间

        返回：
        int: 探测冷却光作用时间
        """
        # 从配置文件中获取探测冷却光作用时间，如果不存在则使用默认值
        return self.config.getfloat('NI', 'do0_meas_cooling_time', fallback=0)

    def get_do2_pgc_pump_time(self) -> int:
        """
        获取PGC回泵光作用时间

        返回：
        int: PGC回泵光作用时间
        """
        # 从配置文件中获取PGC回泵光作用时间，如果不存在则使用默认值
        return self.config.getfloat('NI', 'do2_pgc_pump_time', fallback=0)

    def get_do2_meas_pump_time(self) -> int:
        """
        获取探测回泵光作用时间

        返回：
        int: 探测回泵光作用时间
        """
        # 从配置文件中获取探测回泵光作用时间，如果不存在则使用默认值
        return self.config.getfloat('NI', 'do2_meas_pump_time', fallback=0)

    def get_ao1_pgc_cooling_detune(self) -> float:
        """
        获取PGC冷却光失谐

        返回：
        int: PGC冷却光失谐
        """
        # 从配置文件中获取PGC冷却光失谐，如果不存在则使用默认值
        return self.config.getfloat('NI', 'ao1_pgc_cooling_detune', fallback=3.2)

    def get_ao1_meas_cooling_detune(self) -> float:
        """
        获取探测冷却光失谐

        返回：
        int: 探测冷却光失谐
        """
        # 从配置文件中获取探测冷却光失谐，如果不存在则使用默认值
        return self.config.getfloat('NI', 'ao1_meas_cooling_detune', fallback=3.2)

    def get_ao1_meas_cooling_freq(self) -> float:
        """
        获取探测冷却光频率

        返回：
        int: 探测冷却光频率
        """
        # 从配置文件中获取探测冷却光频率，如果不存在则使用默认值
        return self.config.getfloat('NI', 'ao1_meas_cooling_freq', fallback=6.4)

    def get_ao3_pgc_pump_detune(self) -> float:
        """
        获取PGC回泵光失谐

        返回：
        int: PGC回泵光失谐
        """
        # 从配置文件中获取PGC回泵光失谐，如果不存在则使用默认值
        return self.config.getfloat('NI', 'ao3_pgc_pump_detune', fallback=3.4)

    def get_ao3_meas_pump_detune(self) -> int:
        """
        获取探测回泵光失谐

        返回：
        int: 探测回泵光失谐
        """
        # 从配置文件中获取探测回泵光失谐，如果不存在则使用默认值
        return self.config.getfloat('NI', 'ao3_meas_pump_detune', fallback=4)

    def get_ao4_pgc_comp_mag(self) -> float:
        """
        获取PGC水平补偿磁场

        返回：
        int: PGC水平补偿磁场
        """
        # 从配置文件中获取PGC水平补偿磁场，如果不存在则使用默认值
        return self.config.getfloat('NI', 'ao4_pgc_comp_mag', fallback=1.277)

    def get_ao5_pgc_comp_mag(self) -> float:
        """
        获取PGC阱方向补偿磁场

        返回：
        int: PGC阱方向补偿磁场
        """
        # 从配置文件中获取PGC阱方向补偿磁场，如果不存在则使用默认值
        return self.config.getfloat('NI', 'ao5_pgc_comp_mag', fallback=1.261)

    def get_ao6_pgc_comp_mag(self) -> float:
        """
        获取PGC上下补偿磁场

        返回：
        int: PGC上下补偿磁场
        """
        # 从配置文件中获取PGC上下补偿磁场，如果不存在则使用默认值
        return self.config.getfloat('NI', 'ao6_pgc_comp_mag', fallback=1.325)

    def get_ao7_raman_source_freq(self) -> float:
        """
        获取拉曼Rabi实验中吸收峰

        返回：
        int: 拉曼Rabi实验中吸收峰
        """
        # 从配置文件中获取拉曼Rabi实验中吸收峰，如果不存在则使用默认值
        return self.config.getfloat('NI', 'ao7_raman_source_freq', fallback=1.325)

    def get_ao8_pgc_pump_amp(self) -> float:
        """
        获取PGC回泵光幅度

        返回：
        int: PGC回泵光幅度
        """
        # 从配置文件中获取PGC回泵光幅度，如果不存在则使用默认值
        return self.config.getfloat('NI', 'ao8_pgc_pump_amp', fallback=5)

    def get_ao8_meas_pump_amp(self) -> float:
        """
        获取探测回泵光幅度

        返回：
        int: 探测回泵光幅度
        """
        # 从配置文件中获取探测回泵光幅度，如果不存在则使用默认值
        return self.config.getfloat('NI', 'ao8_meas_pump_amp', fallback=5)

    def get_ao9_pgc_cooling_amp(self) -> float:
        """
        获取PGC冷却光幅度

        返回：
        int: PGC冷却光幅度
        """
        # 从配置文件中获取PGC冷却光幅度，如果不存在则使用默认值
        return self.config.getfloat('NI', 'ao9_pgc_cooling_amp', fallback=5)

    def get_qubit_number(self) -> int:
        """
        获取真机原子阵列中的原子数量

        返回：
        int: 原子数量
        """
        # 从配置文件中获取原子数量，如果不存在则使用默认值
        return self.config.getint('execute', 'qubit_number', fallback=64)

    def get_row_num(self) -> int:
        """
        获取真机原子阵列的行数

        返回：
        int: 原子阵列的行数
        """
        # 从配置文件中获取原子阵列的行数，如果不存在则使用默认值
        return self.config.getint('execute', 'row_num', fallback=8)

    def get_col_num(self) -> int:
        """
        获取真机原子阵列的列数

        返回：
        int: 原子阵列的列数
        """
        # 从配置文件中获取原子阵列的列数，如果不存在则使用默认值
        return self.config.getint('execute', 'col_num', fallback=8)

    def get_rea_region(self) -> list:
        """
        获取原子重排区域

        返回：
        list: 原子重排区域
        """
        # 从配置文件中获取原子重排区域，如果不存在则使用默认值
        res = self.config.get('execute', 'rea_region', fallback=[3, 5, 3, 5])
        return ast.literal_eval(res)

    def get_rea_dll_path(self) -> str:
        """
        获取原子重排算法链接文件地址

        返回：
        list: 原子重排算法链接文件地址
        """
        # 从配置文件中获取原子重排算法链接文件地址，如果不存在则使用默认值
        return self.config.get('execute', 'rea_dll_path', fallback="./test.dll")

    def get_raman_channel(self) -> list:
        """
        获取拉曼波形传输的通道

        返回：
        list: 拉曼波形传输的通道
        """
        # 从配置文件中获取拉曼波形传输的通道，如果不存在则使用默认值
        res = self.config.get('execute', 'raman_channel', fallback=[1, 2, 3, 4])
        return ast.literal_eval(res)

    def get_rea_channel(self) -> list:
        """
        获取原子重排波形传输的通道

        返回：
        list: 原子重排波形传输的通道
        """
        # 从配置文件中获取重排波形传输的通道，如果不存在则使用默认值
        res = self.config.get('execute', 'rea_channel', fallback=[1, 2])
        return ast.literal_eval(res)

    def get_rea_amp(self) -> list:
        """
        获取原子重排幅度

        返回：
        list: 原子重排幅度
        """
        # 从配置文件中获取原子重排幅度，如果不存在则使用默认值
        res = self.config.get('execute', 'rea_amp', fallback=[0.2, 1.2])
        return ast.literal_eval(res)

    def get_calib_img_path(self) -> str:
        """
        获取校准图像的文件路径

        返回:
        str: 校准图像的文件路径
        """
        # 从配置文件中读取校准图像的文件路径，如果不存在则使用默认值
        return os.path.join(
            self.get_config_path(), self.config.get('measure', 'calib_img_path', fallback='calib_img.png'))

    def get_quantum_task_res_img_path(self) -> str:
        """
        获取量子电路任务结果图像的文件路径

        返回:
        str: 量子电路任务结果图像的文件路径
        """
        # 从配置文件中读取量子电路任务结果图像的文件路径，如果不存在则使用默认值
        return os.path.join(self.get_config_path(),
                            self.config.get('measure', 'quantum_task_res_img_path',
                                            fallback='quantum_task_res_img.png'))

    def get_measure_threshold(self) -> int:
        """
        获取量子比特状态的亮态阈值

        返回:
        int: 亮态阈值
        """
        return self.config.getint('measure', 'threshold', fallback=100)

    def get_measure_threshold_block(self) -> int:
        """
        获取有效像素点个数

        返回:
        int: 有效像素点个数
        """
        return self.config.getint('measure', 'threshold_block', fallback=3)

    def get_camera_dll_path(self) -> str:
        """
        获取相机的dll路径

        返回:
        str: dll路径
        """
        fallback = "D:/SourceCode/arclight/WuYueOs_Arclight/quantumOS/camera_test/lib/x64/TUCam.dll"
        return self.config.get('measure', 'dll_path', fallback=fallback)

    def get_camera_init_path(self) -> str:
        """
        获取相机SDK的初始路径

        返回:
        str: SDK的初始路径
        """
        return self.config.get('measure', 'init_path',
                               fallback="D:/SourceCode/arclight/WuYueOs_Arclight/quantumOS/camera_test/")

    def get_exposure_time(self) -> int:
        """
        获取曝光时间

        返回:
        int: 曝光时间
        """
        return self.config.getint('measure', 'exposure_time', fallback=50)

    def get_width_offset(self) -> int:
        """
        获取横向偏移

        返回:
        int: 横向偏移
        """
        return self.config.getint('measure', 'width_offset', fallback=840)

    def get_height_offset(self) -> int:
        """
        获取纵向偏移

        返回:
        int: 纵向偏移
        """
        return self.config.getint('measure', 'height_offset', fallback=865)

    def get_roi_width(self) -> int:
        """
        获取ROI区域宽度

        返回:
        int: ROI区域宽度
        """
        return self.config.getint('measure', 'roi_width', fallback=232)

    def get_roi_height(self) -> int:
        """
        获取ROI区域高度

        返回:
        int: ROI区域高度
        """
        return self.config.getint('measure', 'roi_height', fallback=232)

    def get_total_width(self) -> int:
        """
        获取相机分辨率的宽度

        返回:
        int: 相机分辨率的宽度
        """
        return self.config.getint('measure', 'total_width', fallback=2048)

    def get_total_height(self) -> int:
        """
        获取相机分辨率的长度

        返回:
        int: 相机分辨率的长度
        """
        return self.config.getint('measure', 'total_height', fallback=2048)

    def get_config_file_absolute_path(self) -> str:
        """
        获取当前配置文件的绝对路径

        返回:
        config_file_path (str): 配置文件的绝对路径
        """
        # 获取当前文件的目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建配置文件的完整路径
        config_file_path = os.path.join(current_dir, self.config_path)
        # 返回配置文件的绝对路径
        return os.path.abspath(config_file_path)

    def get_qubo_images_path(self) -> str:
        """
        获取ising的get_task_images策略响应体中QUBO Value 结果图片存放路径

        返回:
        str: QUBO Value 结果图片存放路径
        """
        # 从配置文件中读取QUBO Value 结果图片存放路径，如果不存在则使用默认值
        config_path = self.get_config_path()
        target_path = os.path.dirname(config_path)
        return os.path.join(
            target_path, self.config.get('ising', 'qubo_images_path',
                                                    fallback='ising_response_result/qubo_images'))

    def get_zip_file_path(self) -> str:
        """
        获取ising的get_download_task策略响应体中任务结果压缩文件存放路径

        返回:
        str: 任务结果压缩文件存放路径
        """
        # 从配置文件中读取任务结果压缩文件存放路径，如果不存在则使用默认值
        config_path = self.get_config_path()
        target_path = os.path.dirname(config_path)
        return os.path.join(
            target_path, self.config.get('ising', 'zip_file_path',
                                                    fallback='ising_response_result/result_files'))

    def get_ising_machine_ip(self) -> str:
        """
        获取ising量子计算机的ip地址

        返回:
        str: ising量子计算机的ip地址
        """
        # 从配置文件中读取ising量子计算机的ip地址，如果不存在则使用默认值
        return self.config.get('ising', 'ising_machine_ip', fallback="http://127.0.0.1:8088")


qcos_configer = QcosConfigManager()
