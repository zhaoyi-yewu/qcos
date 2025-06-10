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
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.\
    superconducting_processor_interface import (
    SuperconductingProcessorInterface)
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.neutral_atom_processor_interface import (
    NeutralAtomProcessorInterface)
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.ion_trap_processor_interface import (
    IonTrapProcessorInterface)
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.ni_chassis_interface import (
    NIChassisInterface, NIAOInterface, NIDOInterface, NIDIInterface)
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.fpga_interface import (
    FPGAInterface)
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.awg_interface import (
    AWGInterface)
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.camera_interface import (
    CameraInterface)
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.quantum_hardware_interface import (
    QuantumHardwareInterface)


class HardwareInterfaceFactory(object):
    '''
    硬件接口工厂类
    '''
    # 硬件接口策略字典
    _strategies = {
        'superconducting': SuperconductingProcessorInterface,
        'neutral_atom': NeutralAtomProcessorInterface,
        'ion_trap': IonTrapProcessorInterface,
        'ni_chassis': NIChassisInterface,
        'niao': NIAOInterface,
        'nido': NIDOInterface,
        'nidi': NIDIInterface,
        'fpga': FPGAInterface,
        'awg': AWGInterface,
        'camera': CameraInterface,
    }

    @classmethod
    def create_interface(
            cls,hardware_type: str,
            config: Dict[str,Any]) -> (
            QuantumHardwareInterface):
        '''
        创建硬件接口实例

        参数:
        hardware_type (str): 硬件类型
        config (Dict[str, Any]): 配置信息

        返回:
        QuantumHardwareInterface: 硬件接口实例
        '''
        strategy = cls._strategies.get(hardware_type)
        if strategy:
            return strategy(config)
        else:
            raise ValueError(f'Unsupported hardware type: {hardware_type}')
