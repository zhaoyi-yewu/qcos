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


from typing import Any, List, Union
from .quantum_operation import QuantumOperation


class QuantumGateOperation(QuantumOperation):
    """
    量子门操作类
    """

    def __init__(self, gate: str, qubits: Union[int, List[int]]):
        """
        初始化量子门操作

        参数:
        gate (str): 量子门类型
        qubits (Union[int, List[int]]): 作用的量子比特
        """
        # 量子门类型
        self.gate = gate
        # 量子比特列表
        self.qubits \
            = qubits if isinstance(qubits, list) else [qubits]

    def execute(self, interface: 'QuantumHardwareInterface') -> Any:
        """
        执行量子门操作

        参数:
        interface (QuantumHardwareInterface): 硬件接口

        返回:
        Any: 操作结果
        """
        # 执行量子门操作
        return interface.execute_operation(self.gate, self.qubits)
