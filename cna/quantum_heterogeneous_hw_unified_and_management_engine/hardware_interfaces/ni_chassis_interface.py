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


import nidaqmx
from nidaqmx.constants import AcquisitionType, LineGrouping
import numpy as np
from typing import Any, Dict
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.quantum_hardware_interface import \
    QuantumHardwareInterface
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    control_systems.ni_chassis_control_system import \
    NIChassisControlSystem
from qcos.config.qcos_config_manager import qcos_configer
from qcos.log.qcos_log import QCOSLogger


qcos_logger = QCOSLogger()


class NIChassisInterface(QuantumHardwareInterface):
    '''
    NI机箱接口类
    '''

    def __init__(self, config=None):
        '''
        初始化NI机箱接口
        '''
        # self.config = config
        self.address = None
        self.connection = None
        self.status = 'Disconnected'
        self.chassis_config = None
        self.task = nidaqmx.Task()
        self.initialize()

    def initialize(self):
        '''
        初始化硬件接口
        '''
        # self.chassis_config = self.config.get('chassis_config')
        qcos_logger.info('Initialized NI chassis interface')

    def connect(self):
        '''
        连接硬件
        '''
        # self.connection = NIChassisControlSystem(self.config['address'])
        self.connection = NIChassisControlSystem(self.address)
        # self.connection.configure_chassis(self.chassis_config)
        if self.connection.verify_chassis():
            self.status = 'Connected'
            qcos_logger.info('Successfully connected to NI chassis')
        else:
            qcos_logger.error('Failed to verify NI chassis')
            raise ConnectionError('Failed to verify NI chassis')

    def disconnect(self):
        '''
        断开硬件连接
        '''
        if self.connection:
            self.connection.close()
            self.connection = None
        self.status = 'Disconnected'
        qcos_logger.info('Disconnected from NI chassis')

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

    def stop_operation(self):
        '''
        停止操作
        '''
        pass

    def get_status(self) -> Dict[str, Any]:
        '''
        获取硬件状态
        返回:
        Dict[str, Any]: 状态信息
        '''
        return {
            'status': self.status,
            'chassis_config': self.chassis_config
        }

    def calibrate(self):
        '''
        校准硬件
        '''
        if self.status != 'Connected':
            qcos_logger.error('Hardware not connected')
            raise ConnectionError('Hardware not connected')
        self.connection.run_chassis_sequence()
        qcos_logger.info('Calibration completed successfully')

    def send_data(self, data: Any):
        '''
        发送数据
        参数:
        data (Any): 要发送的数据
        '''
        self.connection.send_data(data)
        qcos_logger.info('Data sent successfully')

    def receive_data(self) -> Any:
        '''
        接收数据
        返回:
        Any: 接收到的数据
        '''
        data = self.connection.receive_data()
        qcos_logger.info('Data received successfully')
        return data


class NIAOInterface(NIChassisInterface):
    '''
    模拟信号生成板卡 (NIAO) 接口类
    '''

    def __init__(self):
        '''
        初始化 NIAO 接口
        '''
        super().__init__()
        self.connections = []
        self.type = qcos_configer.get_ni_ao_type()
        self.addresses = qcos_configer.get_ni_ao_address()
        self.rate = qcos_configer.get_ni_ao_rate()
        self.trigger_source = qcos_configer.get_ni_ao_trigger_source()
        self.delay_time = qcos_configer.get_delay_time()
        self.delay_start = qcos_configer.get_delay_start()
        # AO 参数
        self.ao1_pgc_cooling_detune = qcos_configer.get_ao1_pgc_cooling_detune()
        self.ao1_meas_cooling_detune = (
            qcos_configer.get_ao1_meas_cooling_detune())
        self.ao1_meas_cooling_freq = qcos_configer.get_ao1_meas_cooling_freq()
        self.ao3_pgc_pump_detune = qcos_configer.get_ao3_pgc_pump_detune()
        self.ao3_meas_pump_detune = qcos_configer.get_ao3_meas_pump_detune()
        self.ao4_pgc_comp_mag = qcos_configer.get_ao4_pgc_comp_mag()
        self.ao5_pgc_comp_mag = qcos_configer.get_ao5_pgc_comp_mag()
        self.ao6_pgc_comp_mag = qcos_configer.get_ao6_pgc_comp_mag()
        self.ao7_raman_source_freq = qcos_configer.get_ao7_raman_source_freq()
        self.ao8_pgc_pump_amp = qcos_configer.get_ao8_pgc_pump_amp()
        self.ao8_meas_pump_amp = qcos_configer.get_ao8_meas_pump_amp()
        self.ao9_pgc_cooling_amp = qcos_configer.get_ao9_pgc_cooling_amp()

    def connect(self):
        '''
        连接 NIAO
        '''
        for dev in self.addresses:
            self.connections.append(NIChassisControlSystem(dev))
        min_v = getattr(self, 'min_val', -10.0)
        max_v = getattr(self, 'max_val', 10.0)
        try:
            for dev in self.addresses:
                self.task.ao_channels.add_ao_voltage_chan(
                    dev, min_val=min_v, max_val=max_v)
            self.task.triggers.start_trigger.cfg_dig_edge_start_trig(
                trigger_source=self.trigger_source)
            for connection in self.connections:
                connection.connect()
        except Exception as e:
            qcos_logger.error('Failed to connected NIAO')
            raise ConnectionError(f'Failed to connected NIAO: '
                                  f'{str(e)}')
        self.status = 'Connected'
        qcos_logger.info('Successfully connected to NIAO')

    def disconnect(self):
        '''
        断开 NIAO 连接
        '''
        if self.status != 'Connected':
            if hasattr(self, 'task'):
                try:
                    self.task.close()
                    for connection in self.connections:
                        connection.disconnect()
                except Exception as e:
                    qcos_logger.error(
                        f'Failed to disconnected from NIAO: '
                        f'{str(e)}')
        self.status = 'Disconnected'
        qcos_logger.info('Disconnected from NIAO')

    def execute_operation(self):
        '''
        执行 AO 信号输出
        '''
        if self.status != 'Connected':
            qcos_logger.error('NIAO is not connected')
            raise ConnectionError('NIAO is not connected')
        self.task.start()
        qcos_logger.info('Start outputting AO signals')

    def stop_operation(self):
        '''
        等待 AO 信号发送完成，并停掉任务
        '''
        if self.status != 'Connected':
            qcos_logger.error('NIAO is not connected')
            raise ConnectionError('NIAO is not connected')
        self.task.wait_until_done()
        self.task.stop()
        qcos_logger.info('Stop outputting AO signals')

    def send_data(self):
        '''
        发送数据到 NIAO
        '''
        if self.status != 'Connected':
            qcos_logger.error('NIAO is not connected')
            raise ConnectionError('NIAO is not connected')
        # 板卡数据集成
        package_data = self.get_all_ao()
        # 配置定时选项
        self.task.timing.cfg_samp_clk_timing(
            rate=self.rate,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=len(
                package_data[0]))
        # 发送数据到板卡
        self.task.write(package_data, auto_start=False)
        qcos_logger.info('Data sent to NIAO successfully')

    def receive_data(self):
        '''
        接收数据
        '''
        raise RuntimeError(
            'There are no input channels in '
            'this task to which data can be read.')

    def ao_package_generator(self, time, sample_func=None):
        '''
        模拟信号生成，根据采样函数、时间以及板卡采样率进行采用

        参数:
        time (float): 采样时间
        sample_func (Any): 采样函数

        返回:
        Any: 模拟信号
        '''
        if sample_func is None:
            sample_func = np.sin
        sample_num = int(np.round(time * self.rate / 1e6))
        sample_time = np.linspace(0, time, sample_num + 1)
        return sample_func(sample_time)

    def get_all_ao(self, unit=1e-3):
        '''
        板卡数据集成

        返回:
        Array: 集成的板卡数据
        unit (float): 数据单位
        '''
        ao_datas = [
            self.ao0_mot_signal(),
            self.ao1_fm_signal(),
            self.ao2_amp_signal(),
            self.ao3_signal(),
            self.ao4_signal(),
            self.ao5_signal(),
            self.ao6_signal()
        ]

        if self.delay_time != 0:
            for i in range(len(ao_datas)):
                data = ao_datas[i].tolist()
                idx = int(np.round(self.delay_start * self.rate * unit))
                v = data[idx]
                data = (data[:idx] + [v] * \
                    int(np.round(self.delay_time * self.rate * unit))
                        + data[idx:])
                ao_datas[i] = data
        return np.vstack(ao_datas)

    def ao_package_from_signal(self, signal, unit=1e-3):
        '''
        将AO信号格式对齐、封装
        参数:
        signal (List): AO信号
        unit (float): 数据单位
        返回:
        Array: AO信号数据
        '''
        data = []
        for i, (t, s) in enumerate(signal):
            if i == len(signal) - 1:
                data.append(s)
            else:
                time = signal[i + 1][0] - t
                if time == 0:
                    continue
                data += np.linspace(
                    s,signal[i + 1][1],
                    int(np.round(
                    time * self.rate * unit))).tolist()
        return np.array(data)

    def ao0_mot_signal(self):
        signal = [(0, 0), (100, 0), (150, 0),
                  (180, 0), (550, 0), (660, 0),
                  (750, 0), (800, 0), (800, 0.7), (805, 0.7)]
        return self.ao_package_from_signal(signal)

    def ao1_fm_signal(self):
        signal = [(0, 3.7), (20, 3.7), (70, 2.1), (70, 3.7),
                  (100, 3.7), (100, 3.9), (150, 3.9),
                  (180, 3.9), (180, 3.7),(490, 3.7),
                  (520, 2.1), (520, 3.7), (550, 3.7),
                  (550, 3.9), (600, 3.9), (600, 3.8),
                  (620, 3.8), (620, 3.7), (659, 2.1),
                  (659, 3.8), (660, 3.8), (660, 3.9),
                  (705, 3.9), (705, 5), (720, 5),
                  (720, 3.9), (750, 3.9), (800, 3.9),
                  (800, 3.8), (805, 3.8)]
        return self.ao_package_from_signal(signal)

    def ao2_amp_signal(self):
        signal = [(0, 1.4), (5, 1.4), (5, 1.5),
                  (10, 1.3), (691.2, 1.3), (693.2, 0.6),
                  (713.933, 0.6), (718.933, 0.6), (720.933, 1.3),
                  (805, 1.3)]
        return self.ao_package_from_signal(signal)

    def ao3_signal(self):
        signal = [(0, 5), (20, 5), (20, 2.8), (70, 2.8),
                  (70, 5), (100, 5), (100, 2.8),
                  (150, 2.8), (150, 5), (490, 5),
                  (490, 2.8), (520, 2.8), (520, 5),
                  (550, 5), (550, 2.8), (620, 2.8),
                  (660, 2.8), (660, 5), (683, 5),
                  (683, 2.8), (693, 2.8), (693, 5),
                  (750, 5), (750, 2.8), (800, 2.8),
                  (800, 5), (805, 5)]
        return self.ao_package_from_signal(signal)

    def ao4_signal(self):
        signal = [(0, 0.035), (10, 0.035), (80, 0.035),
                  (90, 0.035), (90, 0.045), (470, 0.045),
                  (470, 0.035),(480, 0.035), (520, 0.035),
                  (530, 0.035), (600, 0.035), (600, 0.035),
                  (610, 0.035), (659, 0.035),(660, 0.035),
                  (670, 0.035), (680, 0.02), (720, 0.02),
                  (730, 0.035), (805, 0.035)]
        return self.ao_package_from_signal(signal)

    def ao5_signal(self):
        signal = [(0, 0), (10, 0), (80, 0), (90, 0),
                  (470, 0), (480, 0), (520, 0), (530, 0),
                  (600, 0), (610, 0), (659, 0), (660, 0),
                  (665, 0), (675, 2), (720, 2), (730, 0), (805, 0)]
        return self.ao_package_from_signal(signal)

    def ao6_signal(self):
        signal = [(0, 0.04), (10, 0.04), (80, 0.04), (90, 0.04),
                  (470, 0.04), (480, 0.04), (520, 0.04), (530, 0.04),
                  (600, 0.04), (610, 0.04), (659, 0.04), (660, 0.04),
                  (670, 0.04), (680, -0.02), (720, -0.02),
                  (730, 0.04), (805, 0.04)]
        return self.ao_package_from_signal(signal)


class NIDOInterface(NIChassisInterface):
    '''
    NIDO 接口类
    '''

    def __init__(self):
        '''
        初始化 NIDO 接口
        '''
        super().__init__()
        self.connections = []
        self.type = qcos_configer.get_ni_do_type()
        self.addresses = qcos_configer.get_ni_do_address()
        self.rate = qcos_configer.get_ni_do_rate()
        self.delay_time = qcos_configer.get_delay_time()
        self.delay_start = qcos_configer.get_delay_start()
        # DO 参数
        self.do0_pgc_cooling_time = qcos_configer.get_do0_pgc_cooling_time()
        self.do0_meas_cooling_time = qcos_configer.get_do0_meas_cooling_time()
        self.do2_pgc_pump_time = qcos_configer.get_do2_pgc_pump_time()
        self.do2_meas_pump_time = qcos_configer.get_do2_meas_pump_time()

    def connect(self):
        '''
        连接 NIDO
        '''
        for dev in self.addresses:
            self.connections.append(NIChassisControlSystem(dev))
        try:
            for dev in self.addresses:
                self.task.do_channels.add_do_chan(
                    dev, line_grouping=LineGrouping.CHAN_PER_LINE)
            for connection in self.connections:
                connection.connect()
        except Exception as e:
            qcos_logger.error('Failed to connected NIDO')
            raise ConnectionError(f'Failed to connected NIDO: '
                                  f'{str(e)}')
        self.status = 'Connected'
        qcos_logger.info('Successfully connected to NIDO')

    def disconnect(self):
        '''
        断开 NIDO 连接
        '''
        if self.status == 'Connected':
            if hasattr(self, 'task'):
                try:
                    self.task.close()
                    for connection in self.connections:
                        connection.disconnect()
                except Exception as e:
                    qcos_logger.error(
                        f'Failed to disconnected from NIDO: '
                        f'{str(e)}')
        self.status = 'Disconnected'
        qcos_logger.info('Disconnected from NIDO')

    def execute_operation(self):
        '''
        执行DO信号输出
        '''
        if self.status != 'Connected':
            qcos_logger.error('NIDO is not connected')
            raise ConnectionError('NIDO is not connected')
        self.task.start()
        qcos_logger.info('Start outputting DO signals')

    def stop_operation(self):
        '''
        等待 DO 信号发送完成，并停掉任务
        '''
        if self.status != 'Connected':
            qcos_logger.error('NIDO is not connected')
            raise ConnectionError('NIDO is not connected')
        self.task.wait_until_done()
        self.task.stop()
        qcos_logger.info('Stop outputting DO signals')

    def send_data(self):
        '''
        发送数据到 NIDO
        '''
        if self.status != 'Connected':
            qcos_logger.error('NIDO is not connected')
            raise ConnectionError('NIDO is not connected')
        # 板卡数据集成
        package_data = self.get_all_do()
        # 配置定时选项
        self.task.timing.cfg_samp_clk_timing(
            rate=self.rate,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=len(
                package_data[0]))
        # 发送数据到板卡
        self.task.write(package_data, auto_start=False)
        qcos_logger.info('Data sent to NIDO successfully')

    def receive_data(self):
        '''
        接收数据
        '''
        raise RuntimeError(
            'There are no input channels in '
            'this task to which data can be read.')

    def ttl_package_generator(self, data):
        '''
        对TTL信号数据进行格式解析和封装

        参数:
        data (Any): 要发送的数据

        返回:
        Array: 封装数据
        '''
        signal_data = []
        for (chapter, time) in data:
            ttl = int(chapter[:8], 2)
            signal_data += [ttl] * int(np.ceil(time * self.rate / 1e6))
        return np.array(signal_data, dtype=np.uint32)

    def get_all_do(self, unit=1e-3):
        '''
        NIDO 数据集成

        返回:
        Array: 集成的 NIDO 数据
        unit (float): 数据单位
        '''
        do_datas = [
            self.do0_kick_aom_signal(),
            self.do1_shutter_signal(),
            self.do2_aom_signal(),
            self.do3_shutter_signal(),
            self.do4_camera_signal(),
            self.do5_shutter_signal(),
            self.do6_aom_signal(),
            self.do7_shutter_signal(),
            self.do9_shutter_signal(),
            self.do11_light_signal(),
            self.do12_raman_signal(),
            self.do13_awg_start_signal(),
            self.do14_switch_signal(),
            self.do30_ao_start_signal()
        ]

        if self.delay_time != 0:
            for i in range(len(do_datas)):
                data = do_datas[i].tolist()
                idx = int(np.round(
                    self.delay_start * self.rate * unit))
                v = data[idx]
                data = data[:idx] + [v] * \
                    int(np.round(
                        self.delay_time * self.rate * unit)) + data[idx:]
                do_datas[i] = data
        return np.vstack(do_datas)

    def ttl_package_from_signal(self, signal, unit=1e-3):
        '''
        将TTL信号格式对齐、封装
        参数:
        signal (List): TTL信号
        unit (float): 数据单位
        返回:
        Array: TTL信号数据
        '''
        data = []
        for i, (t, s) in enumerate(signal):
            if i == len(signal) - 1:
                data.append(bool(s))
            else:
                time = signal[i + 1][0] - t
                data += [bool(s)] * int(np.round(time * self.rate * unit))
        return np.array(data)

    def do0_kick_aom_signal(self):
        signal = [(0, 0), (20, 1), (70, 0), (100, 1),
                  (150, 0), (490, 1), (520, 0), (550, 1),
                  (600, 0), (620, 1), (659, 0), (685, 1),
                  (692, 0), (708, 1), (709, 0), (750, 1), (805, 1)]
        return self.ttl_package_from_signal(signal)

    def do1_shutter_signal(self):
        signal = [(0, 1), (670, 0), (740, 1), (805, 1)]
        return self.ttl_package_from_signal(signal)

    def do2_aom_signal(self):
        signal = [(0, 0), (20, 1), (70, 0), (100, 1),
                  (150, 0), (490, 1), (520, 0),
                  (550, 1), (600, 0), (620, 1), (659, 0),
                  (689, 1), (689.5, 0), (750, 1), (805, 1)]
        return self.ttl_package_from_signal(signal)

    def do3_shutter_signal(self):
        signal = [(0, 1), (660, 0), (740, 1), (805, 1)]
        return self.ttl_package_from_signal(signal)

    def do4_camera_signal(self):
        signal = [(0, 0), (100, 1), (150, 0), (550, 1),
                  (600, 0), (750, 1), (800, 0), (805, 0)]
        return self.ttl_package_from_signal(signal)

    def do5_shutter_signal(self):
        signal = [(0, 0), (677, 1), (692, 0), (805, 0)]
        return self.ttl_package_from_signal(signal)

    def do6_aom_signal(self):
        signal = [(0, 0), (689, 1), (690.2, 0), (805, 0)]
        return self.ttl_package_from_signal(signal)

    def do7_shutter_signal(self):
        signal = [(0, 0), (670, 1), (690, 0), (805, 0)]
        return self.ttl_package_from_signal(signal)

    def do9_shutter_signal(self):
        signal = [(0, 0), (695, 1), (715, 0), (805, 0)]
        return self.ttl_package_from_signal(signal)

    def do11_light_signal(self):
        signal = [(0, 1), (805, 1)]
        return self.ttl_package_from_signal(signal)

    def do12_raman_signal(self):
        signal = [(0, 0), (700, 1), (700.008, 0), (805, 0)]
        return self.ttl_package_from_signal(signal)

    def do13_awg_start_signal(self):
        signal = [(0, 0), (200, 1), (202, 0), (805, 0)]
        return self.ttl_package_from_signal(signal)

    def do14_switch_signal(self):
        signal = [(0, 0), (60, 1), (560, 0), (805, 0)]
        return self.ttl_package_from_signal(signal)

    def do30_ao_start_signal(self):
        data = [True]
        data += [False] * int(np.round(805 * self.rate * 1e-3))
        return np.array(data)


class NIDIInterface(NIChassisInterface):
    '''
    NIDI 接口类
    '''

    def __init__(self):
        '''
        初始化 NIDI 接口
        '''
        super().__init__()
        self.connections = []
        self.type = qcos_configer.get_ni_di_type()
        self.addresses = qcos_configer.get_ni_di_address()

    def connect(self):
        '''
        连接 NIDI
        '''
        for dev in self.addresses:
            self.connections.append(NIChassisControlSystem(dev))
        try:
            for dev in self.addresses:
                self.task.di_channels.add_di_chan(dev)
            for connection in self.connections:
                connection.connect()
        except Exception as e:
            qcos_logger.error('Failed to connected NIDI')
            raise ConnectionError(f'Failed to connected NIDI: {str(e)}')
        self.status = 'Connected'
        qcos_logger.info('Successfully connected to NIDI')

    def disconnect(self):
        '''
        断开 NIDI 连接
        '''
        if self.status == 'Connected':
            if hasattr(self, 'task'):
                try:
                    self.task.close()
                    for connection in self.connections:
                        connection.disconnect()
                except Exception as e:
                    qcos_logger.error(
                        f'Failed to disconnected from NIDI: '
                        f'{str(e)}')
        self.status = 'Disconnected'
        qcos_logger.info('Disconnected from NIDI')

    def execute_operation(self):
        '''
        执行操作
        '''
        raise RuntimeError('There is no operation to execute.')

    def send_data(self):
        '''
        发送数据到板卡
        '''
        raise RuntimeError(
            'There are no output channels in '
            'this task to which data can be written.')

    def receive_data(self):
        '''
        接收数据
        返回:
        Any: 接收到的数据
        '''
        if self.status != 'Connected':
            qcos_logger.error('NIDI is not connected')
            raise ConnectionError('NIDI is not connected')
        data = self.task.read()
        qcos_logger.info('Data received successfully')
        return data

