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


from typing import Any, Dict, List
from .quantum_hardware_interface import QuantumHardwareInterface
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    control_systems.neutral_atom_control_system import \
    NeutralAtomControlSystem
from qcos.log.qcos_log import QCOSLogger


qcos_logger = QCOSLogger()


class NeutralAtomProcessorInterface(QuantumHardwareInterface):
    '''
    中性原子量子处理器接口类
    '''

    def __init__(self, config: Dict[str, Any]):
        '''
        初始化中性原子处理器接口

        参数:
        config (Dict[str, Any]): 配置信息
        '''
        self.config = config
        self.connection = None
        self.status = 'Disconnected'
        self.lattice_configuration = None
        self.atom_count = None
        self.initialize()

    def initialize(self):
        '''
        初始化硬件接口
        '''
        self.lattice_configuration = self.config.get('lattice_configuration')
        self.atom_count = int(self.config.get('atom_count', 0))
        qcos_logger.info(
            f'Initialized neutral atom processor with '
            f'{self.atom_count} atoms')

    def connect(self):
        '''
        连接硬件
        '''
        self.connection = NeutralAtomControlSystem(self.config['address'])
        self.connection.configure_lattice(self.lattice_configuration)
        if self.connection.verify_atoms(self.atom_count):
            self.status = 'Connected'
            qcos_logger.info(
                'Successfully connected to neutral atom processor')
        else:
            qcos_logger.error('Failed to verify atoms')
            raise ConnectionError('Failed to verify atoms')

    def disconnect(self):
        '''
        断开硬件连接
        '''
        if self.connection:
            self.connection.close()
            self.connection = None
        self.status = 'Disconnected'
        qcos_logger.info('Disconnected from neutral atom processor')

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
            'atom_count': self.atom_count,
            'lattice_configuration': self.lattice_configuration
        }

    def calibrate(self):
        '''
        校准硬件
        '''
        if self.status != 'Connected':
            qcos_logger.error('Hardware not connected')
            raise ConnectionError('Hardware not connected')
        self.connection.run_atom_trapping_sequence()
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

