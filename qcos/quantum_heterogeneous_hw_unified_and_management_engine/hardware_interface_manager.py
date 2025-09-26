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


import threading
from typing import Any, Dict, List
from concurrent.futures import ThreadPoolExecutor
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    qcos_dynamic_config import DynamicConfig
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interface_factory import HardwareInterfaceFactory
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    observer.hardware_observer import HardwareObserver
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.quantum_hardware_interface import \
    QuantumHardwareInterface
from qcos.log.qcos_log import QCOSLogger


qcos_logger = QCOSLogger()


class HardwareInterfaceManager(object):
    '''
    硬件接口管理器类
    '''

    def __init__(self, config_path: str):
        '''
        初始化硬件接口管理器

        参数:
        config_path (str): 配置文件路径
        '''
        self.interfaces: Dict[str, QuantumHardwareInterface] = {}
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.observers: List[HardwareObserver] = []

    def connect_hardware(self, hw_name: str):
        '''
        连接指定的硬件

        参数:
        hw_name (str): 硬件名称
        '''
        with self.lock:
            interface = self.interfaces.get(hw_name)
            if interface:
                try:
                    interface.connect()
                    qcos_logger.debug(f'Connected to {hw_name}')
                    self._notify_observers(hw_name, interface.get_status())
                except Exception as e:
                    qcos_logger.error(
                        f'Failed to connect to {hw_name}: '
                        f'{str(e)}')
            else:
                qcos_logger.warning(f'Hardware {hw_name} not found')

    def disconnect_hardware(self, hw_name: str):
        '''
        断开指定的硬件连接

        参数:
        hw_name (str): 硬件名称
        '''
        with self.lock:
            interface = self.interfaces.get(hw_name)
            if interface:
                try:
                    interface.disconnect()
                    qcos_logger.debug(f'Disconnected from {hw_name}')
                    self._notify_observers(hw_name, interface.get_status())
                except Exception as e:
                    qcos_logger.error(
                        f'Failed to disconnect from {hw_name}: '
                        f'{str(e)}')
            else:
                qcos_logger.warning(f'Hardware {hw_name} not found')

    def get_hardware_status(self, hw_name: str) -> Dict[str, Any]:
        '''
        获取指定硬件的状态信息

        参数:
        hw_name (str): 硬件名称

        返回:
        Dict[str, Any]: 状态信息
        '''
        interface = self.interfaces.get(hw_name)
        if interface:
            try:
                return interface.get_status()
            except Exception as e:
                qcos_logger.error(
                    f'Failed to get status for {hw_name}: '
                    f'{str(e)}')
                return {}
        qcos_logger.warning(f'Hardware {hw_name} not found')
        return {}

    def execute_operation(
            self,
            hw_name: str,
            operation: 'QuantumOperation') -> Any:
        '''
        在指定硬件上执行操作

        参数:
        hw_name (str): 硬件名称
        operation (QuantumOperation): 量子操作

        返回:
        Any: 操作结果
        '''
        interface = self.interfaces.get(hw_name)
        if interface:
            try:
                return operation.execute(interface)
            except Exception as e:
                qcos_logger.error(
                    f'Failed to execute operation on {hw_name}: '
                    f'{str(e)}')
                raise
        else:
            qcos_logger.error(f'Hardware not found: {hw_name}')
            raise ValueError(f'Hardware not found: {hw_name}')

    def calibrate_hardware(self, hw_name: str):
        '''
        校准指定的硬件

        参数:
        hw_name (str): 硬件名称
        '''
        interface = self.interfaces.get(hw_name)
        if interface:
            try:
                interface.calibrate()
                qcos_logger.debug(f'Calibrated {hw_name}')
            except Exception as e:
                qcos_logger.error(f'Failed to calibrate {hw_name}: '
                                  f'{str(e)}')
        else:
            qcos_logger.warning(f'Hardware {hw_name} not found')

    def add_observer(self, observer: HardwareObserver):
        '''
        添加观察者
        参数:
        observer (HardwareObserver): 观察者对象
        '''
        self.observers.append(observer)

    def remove_observer(self, observer: HardwareObserver):
        '''
        移除观察者

        参数:
        observer (HardwareObserver): 观察者对象
        '''
        self.observers.remove(observer)

    def _notify_observers(self, hw_name: str, status: Dict[str, Any]):
        '''
        通知所有观察者

        参数:
        hw_name (str): 硬件名称
        status (Dict[str, Any]): 状态信息
        '''
        for observer in self.observers:
            observer.update(hw_name, status)

