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
    control_systems.superconducting_control_system import \
    SuperconductingControlSystem
from qcos.log.qcos_log import QCOSLogger


qcos_logger = QCOSLogger()


class SuperconductingProcessorInterface(QuantumHardwareInterface):
    '''
    超导量子处理器接口类
    '''

    def __init__(self, config: Dict[str, Any]):
        '''
        初始化超导处理器接口
        参数:
        config (Dict[str, Any]): 配置信息
        '''
        # 配置信息
        self.config = config
        # 连接对象
        self.connection = None
        # 状态信息
        self.status = 'Disconnected'
        # 工作点信息
        self.working_point = None
        # 量子比特数量
        self.qubit_count = None
        # 初始化硬件
        self.initialize()

    def initialize(self):
        '''
        初始化硬件接口
        '''
        # 获取工作点信息
        self.working_point = float(self.config.get('working_point', 0))
        # 获取量子比特数量
        self.qubit_count = int(self.config.get('qubit_count', 0))
        # 记录初始化信息
        qcos_logger.info(
            f'Initialized superconducting processor with '
            f'{self.qubit_count} qubits')

    def connect(self):
        '''
        连接硬件
        '''
        # 建立与控制系统的连接
        self.connection = SuperconductingControlSystem(self.config['address'])
        # 设置工作点
        self.connection.set_working_point(self.working_point)
        # 验证量子比特数量
        if self.connection.verify_qubits(self.qubit_count):
            self.status = 'Connected'
            qcos_logger.info(
                'Successfully connected to superconducting processor')
        else:
            qcos_logger.error('Failed to verify qubits')
            raise ConnectionError('Failed to verify qubits')

    def disconnect(self):
        '''
        断开硬件连接
        '''
        # 关闭连接
        if self.connection:
            self.connection.close()
            self.connection = None
        self.status = 'Disconnected'
        qcos_logger.info('Disconnected from superconducting processor')

    def execute_operation(self, gate: str, qubits: List[int]):
        '''
        执行量子操作

        参数:
        gate (str): 量子门类型
        qubits (List[int]): 量子比特列表

        返回:
        Any: 操作结果
        '''
        # 检查连接状态
        if self.status != 'Connected':
            qcos_logger.error('Hardware not connected')
            raise ConnectionError('Hardware not connected')
        # 执行操作
        operation = {'type': 'quantum_gate', 'gate': gate, 'qubits': qubits}
        return self.connection.execute(operation)

    def get_status(self) -> Dict[str, Any]:
        '''
        获取硬件状态

        返回:
        Dict[str, Any]: 状态信息
        '''
        # 返回状态信息
        return {
            'status': self.status,
            'qubit_count': self.qubit_count,
            'working_point': self.working_point
        }

    def calibrate(self):
        '''
        校准硬件
        '''
        # 检查连接状态
        if self.status != 'Connected':
            qcos_logger.error('Hardware not connected')
            raise ConnectionError('Hardware not connected')
        # 执行校准序列
        self.connection.run_calibration_sequence()
        qcos_logger.info('Calibration completed successfully')

    def send_data(self, data: Any):
        '''
        发送数据

        参数:
        data (Any): 要发送的数据
        '''
        # 发送数据到控制系统
        self.connection.send_data(data)
        qcos_logger.info('Data sent successfully')

    def receive_data(self) -> Any:
        '''
        接收数据

        返回:
        Any: 接收到的数据
        '''
        # 从控制系统接收数据
        data = self.connection.receive_data()
        qcos_logger.info('Data received successfully')
        return data
