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

import logging
from typing import Any, Dict, List
from .quantum_hardware_interface import QuantumHardwareInterface
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    control_systems.ion_trap_control_system import \
    IonTrapControlSystem
from qcos.log.qcos_log import QCOSLogger


qcos_logger = QCOSLogger()


class IonTrapProcessorInterface(QuantumHardwareInterface):
    '''
    离子阱量子处理器接口类
    '''

    def __init__(self, config: Dict[str, Any]):
        '''
        初始化离子阱处理器接口
        参数:
        config (Dict[str, Any]): 配置信息
        '''
        self.config = config
        self.connection = None
        self.status = 'Disconnected'
        self.trap_frequency = None
        self.ion_count = None
        self.initialize()

    def initialize(self):
        '''
        初始化硬件接口
        '''
        self.trap_frequency = float(self.config.get('trap_frequency', 0))
        self.ion_count = int(self.config.get('ion_count', 0))
        qcos_logger.info(
            f'Initialized ion trap processor with '
            f'{self.ion_count} ions')

    def connect(self):
        '''
        连接硬件
        '''
        self.connection = IonTrapControlSystem(self.config['address'])
        self.connection.set_trap_frequency(self.trap_frequency)
        if self.connection.verify_ions(self.ion_count):
            self.status = 'Connected'
            qcos_logger.info('Successfully connected to ion trap processor')
        else:
            qcos_logger.error('Failed to verify ions')
            raise ConnectionError('Failed to verify ions')

    def disconnect(self):
        '''
        断开硬件连接
        '''
        if self.connection:
            self.connection.close()
            self.connection = None
        self.status = 'Disconnected'
        qcos_logger.info('Disconnected from ion trap processor')

    def execute_operation(self, gate: str, qubits: List[int]):
        '''
        执行量子操作
        参数:
        gate (str): 量子门类型
        qubits (List[int]): 量子比特列表
        返回:
        Any: 操作结果
        '''
        if self.status != 'Connected':
            qcos_logger.error('Hardware not connected')
            raise ConnectionError('Hardware not connected')
        operation = {'type': 'quantum_gate', 'gate': gate, 'qubits': qubits}
        return self.connection.execute(operation)

    def get_status(self) -> Dict[str, Any]:
        '''
        获取硬件状态
        返回:
        Dict[str, Any]: 状态信息
        '''
        return {
            'status': self.status,
            'ion_count': self.ion_count,
            'trap_frequency': self.trap_frequency
        }

    def calibrate(self):
        '''
        校准硬件
        '''
        if self.status != 'Connected':
            qcos_logger.error('Hardware not connected')
            raise ConnectionError('Hardware not connected')
        self.connection.run_ion_cooling_sequence()
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

