#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-10
# ------------------------


from typing import Any, Dict
from .quantum_hardware_interface import QuantumHardwareInterface
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    control_systems.awg_control_system import \
    AWGControlSystem
# from qcos.\
# quantum_heterogeneous_hw_unified_and_management_engine.\
# hw_driverd.awg_driver import *
from qcos.config.qcos_config_manager import qcos_configer
from qcos.log.qcos_log import QCOSLogger
from qcos.cna.core.instrument.awgDriver import SD_Wave, SD_AOU
import os
import json
import numpy as np

qcos_logger = QCOSLogger()


class AWGInterface(QuantumHardwareInterface):
    '''
    AWG接口类
    '''

    def __init__(self, sd_object=None):
        '''
        初始化AWG接口
        '''
        self.connection = None
        self.status = 'Disconnected'
        self.waveform_data = None
        self.initialize()

        if not qcos_configer.get_debug_mode():
            self.module = SD_AOU()
        else:
            self.module = self._create_default_module()
        self.module_id = self.module.open_with_serial_number(
            qcos_configer.get_awg_product(),
            qcos_configer.get_awg_serial_number())
        if self.module_id < 0:
            raise qcos_logger.error('warning: Module open '
                                    'error:{self.module_id}')
        self.sampling_rate_mhz = qcos_configer.get_awg_sampling_rate()
        self.channel_list = qcos_configer.get_awg_channel()
        # 测试反馈说 (0.05 -> 100mV) awg最大只能输出 0.5  （也就是1V的 amp）
        self.amp = qcos_configer.get_awg_amplitude()
        wave_id_file = qcos_configer.get_awg_wave_id_file()
        self.wave_id = {}
        if not os.path.exists(wave_id_file):
            self.wave_id = self.load_queue_wave2_awg()
        else:
            with open(wave_id_file, 'r') as f:
                self.wave_id = json.loads(f.read())

        for channel, amp in zip(self.channel_list, self.amp):
            ecode = self.module.channel_amplitude(channel, amp)  # 不要注释此行！！！
            ecode = self.module.channel_wave_shape(
                channel, 6)  # SD_Waveshapes.AOU_AWG=6
            # 设置触发
            trigger = 0  # 触发口
            trigger_behavior = 3  # 上升沿
            mode = 0
            self.module.awg_trigger_external_config(
                channel, trigger, trigger_behavior, mode)
            self.module.awg_flush(channel)

        self.trigger_mode = qcos_configer.get_awg_trigger_mode()
        self.start_delay = 0     # 延迟
        self.cycles = 1         # 执行次数 0表示无限循环执行，实际实验中设置为1
        self.prescaler = 0      # 缩减因子
        self.waveform_type = 0   # 波形类型，采用Analog 16 Bits,即自定义波形

        self.generator = GenerateDynamicC3C4(awg_freq=self.sampling_rate_mhz)

    def terminal_holding(self, channel_list=None):
        '''
        保持末端输出
        '''
        if channel_list is None:
            channel_list = self.channel_list
        for channel in channel_list:
            self.set_queue_wave_into_channel(
                channel, self.wave_id['final_wave'],
                trigger='software', cycles=0)
        self.start_multip_channel(channelList=channel_list)

    def _create_default_module(self):
        '''
        创建默认的SD_AOU类实例（模拟）。
        如果没有实际实现，返回一个模拟对象。
        '''

        class MockSdAou(object):
            '''
            模拟SD AOU
            '''
            # 返回模拟的模块ID

            def open_with_serial_number(self, product, serial_number):
                return 1

            # 假设设置成功
            def clock_get_frequency(self):
                return 100e6  # 返回模拟的频率

            def clock_set_frequency(self, mode, frequency):
                return 0

            # 模拟的触发设置
            def awg_trigger_external_config(
                    self, channel, trigger, behavior, mode):
                pass

            # 模拟的AWG刷新
            def awg_flush(self, channel):
                pass

            # 模拟的关闭操作
            def close(self):
                pass

            # 模拟的波形刷新
            def waveform_flush(self):
                pass

            # 模拟的通道幅度
            def channel_amplitude(self, n_channel, amplitude):
                pass

            # 模拟的通道波形数据形状
            def channel_wave_shape(self, n_channel, wave_shape):
                pass

            # 模拟的awg波形数组
            def awg_from_array(
                    self, n_awg, trigger_mode, start_delay,
                    cycles, prescaler, waveform_type, waveform_data_a,
                    waveform_data_b=None, padding_mode=0):
                pass

            # 模拟的awg队列波形
            def awg_queue_waveform(
                    self, n_awg, waveform_number, trigger_mode,
                    start_delay, cycles, prescaler):
                pass

            # 模拟的启动awg多通道
            def awg_start_multiple(self, awg_mask):
                pass

        return MockSdAou()

    def initialize(self):
        '''
        初始化硬件接口
        '''
        # self.waveform_data = self.config.get('waveform_data')
        qcos_logger.debug('Initialized AWG interface')

    def connect(self):
        '''
        连接硬件
        '''
        self.connection = AWGControlSystem(qcos_configer.get_awg_address())
        self.connection.load_waveform(self.waveform_data)
        if self.connection.verify_awg():
            self.status = 'Connected'
            qcos_logger.debug('Successfully connected to AWG')
        else:
            qcos_logger.error('Failed to verify AWG')
            raise ConnectionError('Failed to verify AWG')

    def disconnect(self):
        '''
        断开硬件连接
        '''
        self.module.close()
        self.status = 'Disconnected'
        qcos_logger.debug('Disconnected from AWG')

    def execute_operation(self, operation: Dict[str, Any]):
        '''
        执行操作

        参数:
        operation (Dict[str, Any]): 操作参数

        返回:
        Any: 操作结果
        '''
        if self.status != 'Connected':
            qcos_logger.error('Hardware not connected')
            raise ConnectionError('Hardware not connected')
        return self.connection.execute(operation)

    def get_status(self) -> Dict[str, Any]:
        '''
        获取硬件状态

        返回:
        Dict[str, Any]: 状态信息
        '''
        return {
            'status': self.status,
            'waveform_data': self.waveform_data
        }

    def calibrate(self):
        '''
        校准硬件
        '''
        if self.status != 'Connected':
            qcos_logger.error('Hardware not connected')
            raise ConnectionError('Hardware not connected')
        # self.connection.run_awg_sequence()
        qcos_logger.debug('Calibration completed successfully')

    def send_data(self, data: Any):
        '''
        发送数据

        参数:
        data (Any): 要发送的数据
        '''
        # self.connection.send_data(data)
        qcos_logger.debug('Data sent successfully')

    def receive_data(self) -> Any:
        '''
        接收数据

        返回:
        Any: 接收到的数据
        '''
        # data = self.connection.receive_data()
        qcos_logger.debug('Data received successfully')
        # return data

    def set_sampling_rate_on_hardware(self, freq_mhz: float) -> int:
        '''
        设置硬件的采样频率。

        参数:
        freq_mhz (float): 采样频率，以 MHz 为单位。

        返回:
        int: 错误代码。-8032 表示中性原子设备不支持直接设置该频率。
        '''
        # 目前中性原子设备无法支持直接设置
        error_id = self.module.clock_set_frequency(
            mode=self.module_id, frequency=freq_mhz * 1e6)  # 此行返回 error = -8032
        # 此处使用的是self._create_default_module中的MockSdAou类方法，error_id = 0
        return error_id

    def get_sampleing_rate_mhz_on_hardware(self) -> float:
        '''
        获取硬件的采样频率。

        返回:
        float: 当前采样频率，以 MHz 为单位。
        '''
        return float(self.module.clock_get_frequency()) / 1e6

    def send_single_channel(
            self, wave: list, channel_id: int,
            trigger: str = 'external', flush: bool = True,
            cycles: int = 1, amp: float = None, **kw):
        '''
        发送自定义波形到channel，主要发送ch3, ch4的通道数据 此函数自带 awgStart

        Args:
            wave (list): wave array data
            channel_id (int): channel-id
            trigger (str, optional):
                'external' / 'externalcycle / 'software'
                . Defaults to 'external'.
            flush (bool, optional): _description_. Defaults to True.
            cycles (int, optional): _description_. Defaults to 1.
            amp (float, optional): _description_. Defaults to None.
        '''
        if flush:
            self.module.awg_flush(channel_id)
        if trigger.lower() == 'external':
            # SD_TriggerModes.EXTTRIG=2  Hardware trigger.
            # The AWG waits for an external trigger.
            trigger_mode = 2
        elif trigger.lower() == 'software':
            # SD_TriggerModes.AUTOTRIG=0
            # The waveform is launched after AWGstart,
            # or when the previous waveform in the queue finishes
            trigger_mode = 0
        elif trigger.lower() == 'externalcycle':
            # SD_TriggerModes.EXTTRIG_CYCLE=6  trigger to get each cycle
            trigger_mode = 6
        else:
            raise ValueError(f'undefined trigger={trigger}')

        if amp is not None:
            self.module.channel_amplitude(channel_id, amp)

        delay = 0
        prescaler = 0
        return_code = self.module.awg_from_array(
            channel_id, trigger_mode, delay, cycles,
            prescaler, self.waveform_type, wave)
        return return_code

    def set_queue_wave_into_channel(
            self, channel: int, qid: int, trigger: str = 'external',
            flush: bool = True, cycles: int = 1, amp: float = None, **kwargs):
        '''
        从queue中调取波形到channel去，主要发送ch1,
        ch2的通道数据  remenber to call start_multip_channel()

        Args:
            channel (int): channel-id
            qid (int): queue-id
            trigger (str, optional):
                'external' / 'software' . Defaults to 'external'.
            flush (bool, optional):
                _description_. Defaults to True.
            cycles (int, optional):
                _description_. Defaults to 1.
            amp (float, optional):
                _description_. Defaults to None.
        '''
        # 此函数没有awgStart, 需要自己call start_multip_channel
        if flush:
            self.module.awg_flush(channel)
        if trigger.lower() == 'external':
            # SD_TriggerModes.EXTTRIG=2  Hardware trigger.
            # The AWG waits for an external trigger.
            trigger_mode = 2
        elif trigger.lower() == 'software':
            # SD_TriggerModes.AUTOTRIG=0
            # The waveform is launched after AWGstart,
            # or when the previous waveform in the queue finishes
            trigger_mode = 0
        else:
            raise ValueError(f'undefined trigger={trigger}')

        if amp is not None:
            self.module.channel_amplitude(channel, amp)
        trigger_mode = trigger_mode
        delay = 0
        prescaler = 0
        self.module.awg_queue_waveform(
            n_awg=channel, waveform_number=qid, trigger_mode=trigger_mode,
            start_delay=delay, cycles=cycles, prescaler=prescaler)

    def set_raman_wave(self, waves, **kwargs):
        '''
        设置Raman波形

        Args:
            waves (_type_): Raman波形名称
        '''
        channel_list = kwargs.get('channelList', self.channel_list)
        channel_num = len(channel_list)
        if len(waves) != channel_num:
            raise Exception(f'dimsion of input data [{len(waves)}] '
                            f'do not match number of '
                            f'channels {len(channel_list)}')

        amp = kwargs.get('amp', self.amp)

        for i in range(channel_num):
            self.module.channel_amplitude(
                channel_list[i], amp[channel_list[i] - 1])
            self.module.awg_flush(channel_list[i])
            for j, wave in enumerate(waves[i]):
                trigger = 'software'
                if j == 0:
                    trigger = 'external'
                self.set_queue_wave_into_channel(
                    channel=channel_list[i], qid=self.wave_id[wave],
                    trigger=trigger, flush=False)

    def append_queue_wave(self, qid: int, data_file_path: str):
        '''
        波形加载

        Args:
            qid (int): 波形id
            data_file_path (str): 数据文件路径
        '''
        if not qcos_configer.get_debug_mode():
            sd_wave = SD_Wave()
        else:
            sd_wave = self._create_default_sd_wave()
        c = sd_wave.new_from_file(data_file_path)
        qcos_logger.debug(f'load file-data into queue with return code = {c}')
        self.module.waveformLoad(sd_wave, qid)

    def _create_default_sd_wave(self):
        '''
        创建默认的SD_AOU类实例（模拟）。
        如果没有实际实现，返回一个模拟对象。
        '''

        class MockSdWave(object):
            '''
            模拟SD波形
            '''
            # 返回模拟的模块ID

            def new_from_file(self, data_file_path):
                pass

        return MockSdWave()

    def set_arrange_wave(self, waves, **kwargs):
        '''
        重排波形发送

        Args:
            waves (_type_): 重排操作对应波形名称
        '''
        channel_list = kwargs.get('channelList', self.channel_list)
        channel_num = len(channel_list)

        if len(waves) != channel_num:
            raise Exception(f'dimsion of input data [{len(waves)}] '
                            f'do not match number of '
                            f'channels {len(channel_list)}')

        amp = kwargs.get('amp', self.amp)
        # SD_TriggerModes.AUTOTRIG=0
        # The waveform is launched automatically after AWGstart,
        # or when the previous waveform in the queue finishes
        trigger_mode = 0
        cycles = 1
        delay = 0
        prescaler = 0

        for i in range(channel_num):
            self.module.channel_amplitude(
                channel_list[i], amp[channel_list[i] - 1])
            self.module.awg_flush(channel_list[i])
            for wave in waves[i]:
                self.module.awg_queue_waveform(
                    n_awg=channel_list[i],
                    waveform_number=self.wave_id[wave],
                    trigger_mode=trigger_mode,
                    start_delay=delay, cycles=cycles,
                    prescaler=prescaler)
            self.module.awg_queue_waveform(
                n_awg=channel_list[i],
                waveform_number=self.wave_id['final_wave'],
                trigger_mode=trigger_mode,
                start_delay=delay, cycles=10,
                prescaler=prescaler)

    def start_multip_channel(self, **kwargs):
        '''
        开启AWG多通道
        '''
        channel_list = kwargs.get('channelList', self.channel_list)
        awg_mask = self.convert_to_decimal(channel_list)
        self.module.awg_start_multiple(awg_mask)

    @staticmethod
    def convert_to_decimal(channel_list):
        '''
        将通道编号列表转换为单个十进制数

        参数：
            channel_list (list): 要转换的通道编号列表
        返回：
            result (int): 表示通道编号列表的二进制编码的十进制数
        '''
        channel_list = [i - 1 for i in channel_list]
        result = 0
        for bit_position in channel_list:
            result |= 1 << bit_position
        return result

    def load_queue_wave2_awg(self):
        '''
        从波形文件中加载波形到awg
        '''
        dir_path = qcos_configer.get_awg_wave_file_dir()
        if dir_path is None:
            raise ValueError('wavefile-path not set')
        self.module.waveform_flush()
        files = os.listdir(dir_path)
        qid = 0
        wave_id = {}
        for file in files:
            if file.endswith('.dat'):
                self.append_queue_wave(
                    qid, os.path.normpath(os.path.join(dir_path, file)))
                wave_id[file[:-4]] = qid
                qid += 1
        with open('./wave_id.json', 'w') as file:
            file.write(json.dumps(wave_id))
        return wave_id


class WaveGenerator(object):
    '''
    波形生成器
    '''

    def __init__(self, awg_freq=500, **kw):
        self.awg_freq = awg_freq
        self.awg_dt = 1 / self.awg_freq / 1e6  # in sec
        self._z = 0.1 * self.awg_dt

    def generate_period_func(self, freq, cycle_num: int, func):
        '''
        生成任意波形

        Args:
            freq (_type_):
            cycle_num (int): number of cycles
            func (_type_): func(x) must preodic in [0,2pi]
        '''
        omega = 2 * np.pi * (freq * 1e6)
        time_list = np.arange(
            0, cycle_num / (freq * 1e6) + self._z, self.awg_dt)
        wave1 = np.array([func(x) for x in omega * time_list])
        return wave1

    def generate_sin_wave(self, freq, cycle_num: int):
        '''
        生成正弦函数波形

        参数：
            freq (int): 波形频率
            cycle_num (int): 循环数
        '''
        return self.generate_period_func(
            freq=freq, cycle_num=cycle_num, func=np.sin)

    def constant_array(self, seg_list: list[tuple[float, float]]):
        '''
        根据给定的分段列表生成一个常数数组

        参数：
            seg = [Amp, durationSec]
        '''
        res = []
        for (amp, duration) in seg_list:
            n = int((duration + self._z) / self.awg_dt)
            res += [amp] * n
        return res

    @staticmethod
    def helper_write_data2_file(data_list, file_path, name):
        '''
        将数据写入文件

        参数：
            data_list (list): 数据列表
            file_path (str): 文件路径
        '''
        n = len(data_list)
        with open(file_path, 'w') as f:
            f.write(f'waveformName,{name}\n')
            f.write(f'waveformPoints,{n}\n')
            f.write(f'waveform_type,WAVE_ANALOG_16\n')
            for d in data_list:
                f.write(f'{d:.5f}\n')


class GenerateDynamicC3C4(object):
    '''                                               ┊                            ┊                        ┊
                      ┌─────┐                 ─────────┐     ┌──────         ───────┐     ┌──────     ───────┐
    channel3    ──────┘  t3 └─────                     └─────┘  t3                  └─────┘  t3          t3  └─────
                   ┊  ┊     ┊  ┊                       ┊  ┊  ┊                      ┊  ┊  ┊                  ┊  ┊
                   ┊t1┊     ┊t2┊                       ┊t2┊t1┊                      ┊t2┊t1┊                  ┊t2┊
                   ┊  ┊     ┊  ┊                       ┊  ┊  ┊                      ┊  ┊  ┊                  ┊  ┊
                 t0┌───────────┐ t5                    ┊  ┌─────────         ──────────┐  ┊           ──────────┐
    channel4    ───┘    t4     └──            ────────────┘    t4                   ┊  └─────────            ┊  └──
                                                       ┊                            ┊
                       Ry                            Rx + Ry                        Ry + Rx               Ry + end

    '''

    def __init__(
            self, awg_freq: float = 500, amp3=1,
            amp4=1, t0_us=10, t1_us=10, t2_us=10, t5_us=100):
        self.wave_generator = WaveGenerator(awgFreMhz=awg_freq)
        self.awg_fre_mhz = awg_freq
        self._dt = self.wave_generator.awg_dt  # sec
        self._t0 = t0_us  # very beginning, all in MuSec
        self._t1 = t1_us
        self._t2 = t2_us
        self._t5 = t5_us  # very final
        self.amp3 = amp3
        self.amp4 = amp4
        self._z = self.wave_generator._z

    def generate_c3_c4(
            self, action_list: list[tuple[bool, float]]) -> tuple[list, list]:
        '''
        对于一个已经对准(机械移动已经完成)的激光口，将对qubit的所有操作转换成一个波形

        Args:
            action_list (list[tuple[bool,float]]): example -> item = (T,  0.53)
            * T/F represents Ry/Rx,  t = 0.53 muSec represents   exp(-iHt)
        Returns:
            tuple[list,list]: c3Wave,c4Wave
        '''
        a3, a4 = self.amp3, self.amp4
        c3 = self.wave_generator.constant_array([(0, self._t0 * 1e-6)])
        c4 = list(c3)
        pre_ry = False
        t1 = self._t1 * 1e-6
        t2 = self._t2 * 1e-6
        for (ry, t) in action_list:
            t3 = t * 1e-6
            if ry:
                if pre_ry:
                    # Ry + Ry
                    c3 += self.wave_generator.constant_array(
                        [(a3, t3)])
                    c4 += self.wave_generator.constant_array(
                        [(a4, t3)])
                else:
                    # Rx + Ry
                    c3 += self.wave_generator.constant_array([
                        (0, t1 + t2), (a3, t3)])
                    c4 += self.wave_generator.constant_array(
                        [(0, t2), (a4, t1 + t3)])
            else:
                if pre_ry:
                    # Ry + Rx
                    c3 += self.wave_generator.constant_array(
                        [(0, t1 + t2), (a3, t3)])
                    c4 += self.wave_generator.constant_array(
                        [(a4, t2), (0, t1 + t3)])
                else:
                    # Rx + Rx
                    c3 += self.wave_generator.constant_array([(a3, t3)])
                    c4 += self.wave_generator.constant_array([(0, t3)])
            pre_ry = ry
        if pre_ry:
            c3 += self.wave_generator.constant_array([(0, t2)])
            c4 += self.wave_generator.constant_array([(a4, t2)])

        fi = self.wave_generator.constant_array([(0, self._t5 * 1e-6)])
        c3 += fi
        c4 += fi
        return c3, c4

    def generate_c3_c4_with_fix_length(
            self, action_list: list[tuple[bool, float]], fix_n: int):
        '''
        对于一个已经对准(机械移动已经完成)的激光口，将对qubit的所有操作转换成一个波形

        Args:
            action_list (list[tuple[bool,float]]): example -> item = (T,  0.53)
            fix_n (int): 设置定长
        Returns:
            tuple[list,list, int]: c3Wave, c4Wave, total_time_mu_sec
        '''
        c3, c4 = self.generate_c3_c4(action_list=action_list)
        len3, len4 = len(c3), len(c4)
        total_time_mu_sec = (max(len3, len4) * self._dt) * 1e6
        if fix_n <= min(len3, len4):
            raise Exception('cycle length too short!')
        c3 = [0] * (fix_n - len3) + c3
        c4 = [0] * (fix_n - len4) + c4
        return c3, c4, total_time_mu_sec

    def generate_full_wave(
            self, t_cycle_mu_sec: float,
            gates: list[list[tuple[bool, float]]]) \
            -> tuple[list[float], list[float]]:
        '''
        生成完整的波形数据，用于控制量子比特的门操作

        参数：
            t_cycle_mu_sec (float): 微秒级的周期时间
            gates (list[list[tuple[bool, float]]]): 量子比特门操作的列表
            每个量子比特的操作是一个元组列表，元组包含门的类型和持续时间
        返回：
            tuple[list[float], list[float]]: 两个列表，分别包含c3和c4的通道波形数据。
        '''
        res_c3, res_c4 = [], []
        fix_n = int((t_cycle_mu_sec + self._z) * self.awg_fre_mhz)
        for qubit_gates in gates:
            c3, c4, total_time_mu_sec = (
                self.generate_c3_c4_with_fix_length(qubit_gates, fix_n))
            res_c3 += c3
            res_c4 += c4
        return res_c3, res_c4
