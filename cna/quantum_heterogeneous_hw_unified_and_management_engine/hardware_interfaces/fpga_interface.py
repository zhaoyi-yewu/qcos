#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
#  All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-10
# ------------------------


from typing import Any, Dict
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.quantum_hardware_interface import \
    QuantumHardwareInterface
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    control_systems.fpga_control_system import \
    FPGAControlSystem
from qcos.log.qcos_log import QCOSLogger
from qcos.cna.core.instrument.error import DeveiceParameterError
from qcos.config.qcos_config_manager import qcos_configer
import numpy as np

qcos_logger = QCOSLogger()


class FPGAInterface(QuantumHardwareInterface):
    '''
    FPGA接口类
    '''

    def __init__(self, name: str):
        '''
        初始化FPGA接口

        参数:
        name (str): 设备名称
        port (_type_, optional): 通信串口. Defaults to None.
        '''
        self.name = name
        # 通信串口
        self.port = qcos_configer.get_fpga_port_value()
        if self.port is None:
            raise DeveiceParameterError(
                f'Please specify the serial port for communication')
        # 时钟周期
        self.clock_period = qcos_configer.get_fpga_clock_period()
        # 返回数据字节数
        self.bytes_returned = qcos_configer.get_fpga_bytes_returned_value()
        self.test_time = qcos_configer.get_fpga_test_time()

        self.connection = None
        self.status = 'Disconnected'
        self.initialize()

    def initialize(self):
        '''
        初始化硬件接口
        '''
        # self.fpga_config = self.config.get('fpga_config')
        qcos_logger.info('Initialized FPGA interface')

    def connect(self):
        '''
        连接硬件
        '''
        self.connection = FPGAControlSystem(self.port)
        # 设备连接逻辑处理
        # self.connection.configure_fpga(self.fpga_config)
        connected = self.connection.connect()

        if self.connection.verify_fpga():
            self.status = 'Connected'
            qcos_logger.info('Successfully connected to FPGA')
        else:
            qcos_logger.error('Failed to verify FPGA')
            raise ConnectionError('Failed to verify FPGA')

    def disconnect(self):
        '''
        断开硬件连接
        '''
        if self.connection:
            self.connection.disconnect()
            self.connection = None
        self.status = 'Disconnected'
        qcos_logger.info('Disconnected from FPGA')

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
            # 'fpga_config': self.fpga_config
        }

    def calibrate(self):
        '''
        校准硬件
        '''
        if self.status != 'Connected':
            qcos_logger.error('Hardware not connected')
            raise ConnectionError('Hardware not connected')
        self.connection.run_fpga_sequence()
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

    def send_data_preprocess(self, send_data, **kwargs):
        '''
        数据预处理函数，将脉冲对应的控制信号按格式打包

        参数:
        send_data (Any): 要发送的原始数据
        kwargs (Any): 其他参数

        返回:
        packets (List): 预处理后的发送数据包
        '''
        repeat = kwargs.get('repeat', 100)
        # ext_trig表示信号模式，1为Continuous，0为ExtTrig
        ext_trig = qcos_configer.get_fpga_ext_trig()

        pulses = self.pre_binary(send_data, self.clock_period)
        packets = [
            self.packets_generator(
                pulses, ext_trig, repeat), int(
                repeat * self.bytes_returned)]
        return packets

    def receive_data_postprocess(self, received_data, **kwargs):
        '''
        数据后处理函数

        参数:
        received_data (Any): 接收到的原始数据
        kwargs (Any): 其他参数

        返回:
        res (List): 处理后的数据结果
        '''
        repeat = kwargs.get('repeat', 1)
        ion_number = kwargs.get('ion_number', 1)
        res = np.zeros(ion_number * repeat)
        channel = kwargs.get('channel', list(range(ion_number)))
        active_channel = kwargs.get('active_channel', channel)
        idx = [channel.index(c) for c in active_channel]
        for i in range(repeat):
            for j in idx:
                res[i * ion_number + j] = np.random.rand() * 256
        return res

    def process_and_transmit(self, send_data, **kwargs):
        '''
        对外通信接口，集成了数据预处理、发送、接收及数据后处理

        参数:
        send_data (Any): 要发送的数据
        kwargs (Any): 其他参数

        返回:
        received_data (list): 处理后的数据结果
        '''
        if hasattr(self, 'preprocess'):
            send_data = self.send_data_preprocess(send_data, **kwargs)
        self.send_data(send_data)
        received_data = self.receive_data()
        if hasattr(self, 'postprocess'):
            received_data = self.receive_data_postprocess(
                received_data, **kwargs)
        return received_data

    def timestamp(self, duration, clock_period):
        '''
        持续时间处理函数，将duration转换为40 bit的二进制串

        参数:
        duration (Int): 持续时间
        clock_period (Int): 时钟周期

        返回:
        (Str): 调用timestamp_generator函数生成的40 bit的二进制串
        '''
        n = int(duration / clock_period - 1)
        return self.timestamp_generator(n)

    def timestamp_generator(self, n):
        '''
        时间信息生成函数，将n bit的二进制串转换为w（w=40） bit的二进制串

        参数:
        n (Int): 原始二进制串长度

        返回:
        (Str): 生成的40 bit的二进制串
        '''
        w = 40
        t = (w - n) & (2 ** w - 1)
        t = '{0:040b}'.format(t)
        res = ''
        for i in range(w):
            j = (int(t[w - 1 - i:w], 2) <
                 i) | (int(t[w - 1 - i:w], 2) >= (1 << i) + i)
            res = str(int(j)) + res
        return res

    def chapter_padding(self, chapter):
        '''
        chapter数据格式化处理函数，在chapter的18位添加00000000和空格

        参数:
        chapter (str): 原始chapter数据

        返回:
        (Str): 格式化处理后的chapter数据
        '''
        return chapter[:18] + '{0:08b}'.format(0) + ' ' + chapter[18:]

    def pre_binary(self, pulses, clock_period):
        '''
        脉冲处理函数，将[chapter, duration]为二进制字符串

        参数:
        pulses (Any): 要发送的脉冲数据
        clock_period (Int): 时钟周期

        返回:
        duration_list (list): 转化后包含chapter和duration，以及clock_period信息的二进制字符串
        '''
        duration_list = []
        for element in pulses:
            duration_list = duration_list + [
                [self.chapter_padding(element[0]),
                 self.timestamp(element[1], clock_period)]]
        return duration_list

    def packets_generator(self, pulses, ext_trig, repeat):
        '''
        发送数据包生成函数

        参数:
        pulses (Any): 要发送的脉冲数据
        ext_trig (): 信号模式，1为Continuous，0为ExtTrig
        repeat (Int): 重复次数

        返回:
        pulse_packets_hex (str): 要发送的数据字符串
        '''
        start_packet = ('100' + str(int(ext_trig)) + '{0:052b}'.format(0) +
                        '{0:024b}'.format(int(repeat)))
        pulse_packets = [start_packet]
        i = 0
        time_packets_length = len(pulses) + 3
        # convert pulses to timestamp
        for element in pulses:
            packet = '010'
            packet = packet + \
                '{0:05b}'.format(0) + element[1] + element[0].replace(' ', '')
            pulse_packets = pulse_packets + [packet]
            i += 1
        # padding the time packet
        if time_packets_length < 15:
            for i in range(15 - time_packets_length):
                packet = '010'
                packet = (packet + '{0:05b}'.format(0) +
                          self.timestamp_generator(1 - 1) +
                          '{0:032b}'.format(0))
                pulse_packets = pulse_packets + [packet]
        elif time_packets_length % 5 != 0 and time_packets_length >= 15:
            for i in range(5 - time_packets_length % 5):
                packet = '010'
                packet = (packet + '{0:05b}'.format(0) +
                          self.timestamp_generator(1 - 1) +
                          '{0:032b}'.format(0))
                pulse_packets = pulse_packets + [packet]
        # generate end packets
        end_packets_3 = ('010' + '{0:05b}'.format(0) +
                         self.timestamp_generator(8 - 1) + '{0:032b}'.format(0))
        end_packets_2 = ('010' + '{0:05b}'.format(0) +
                         self.timestamp_generator(2 - 1) + '{0:032b}'.format(0))
        end_packets_1 = ('011' + '{0:05b}'.format(0) +
                         self.timestamp_generator(1 - 1) + '{0:032b}'.format(0))
        pulse_packets = pulse_packets + \
            [end_packets_3, end_packets_2, end_packets_1]
        pulse_packets_hex = ''
        for packet in pulse_packets:
            pulse_packets_hex = pulse_packets_hex + \
                hex(int(packet, 2))[2:] + ' '
        # end_packet
        return pulse_packets_hex
