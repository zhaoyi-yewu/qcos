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


import abc
from typing import Any, Dict


class QuantumHardwareInterface(abc.ABC):
    '''
    量子硬件接口抽象基类
    '''

    @abc.abstractmethod
    def initialize(self):
        '''
        初始化硬件接口
        '''
        pass

    @abc.abstractmethod
    def connect(self):
        '''
        连接硬件
        '''
        pass

    @abc.abstractmethod
    def disconnect(self):
        '''
        断开硬件连接
        '''
        pass

    @abc.abstractmethod
    def execute_operation(self, gate: str, qubits: list):
        '''
        执行量子操作

        参数:
        gate (str): 量子门类型
        qubits (list): 量子比特列表

        返回:
        Any: 操作结果
        '''
        pass

    @abc.abstractmethod
    def get_status(self) -> Dict[str, Any]:
        '''
        获取硬件状态

        返回:
        Dict[str, Any]: 状态信息
        '''
        pass

    @abc.abstractmethod
    def calibrate(self):
        '''
        校准硬件
        '''
        pass

    @abc.abstractmethod
    def send_data(self, data: Any):
        '''
        发送数据

        参数:
        data (Any): 要发送的数据
        '''
        pass

    @abc.abstractmethod
    def receive_data(self) -> Any:
        '''
        接收数据

        返回:
        Any: 接收到的数据
        '''
        pass
