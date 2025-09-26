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


from hardware_interface_manager import HardwareInterfaceManager
from observer.status_monitor_observer import StatusMonitorObserver
from operations.quantum_gate_operation import QuantumGateOperation
from qcos.log.qcos_log import QCOSLogger


qcos_logger = QCOSLogger()


def main():
    '''
    主函数，执行硬件管理流程
    '''
    qcos_logger.debug('初始化硬件接口管理器')
    config_path = 'D:/work/code/qcos/config/qcos_config.conf'

    manager = HardwareInterfaceManager(config_path)

    qcos_logger.debug('添加状态监控观察者')
    status_monitor = StatusMonitorObserver()
    manager.add_observer(status_monitor)

    try:
        qcos_logger.debug('开始连接量子硬件')
        for hw_name in manager.interfaces:
            qcos_logger.debug(f'正在连接 {hw_name}')
            manager.connect_hardware(hw_name)
            status = manager.get_hardware_status(hw_name)
            qcos_logger.debug(f'{hw_name} 连接状态: {status}')

        qcos_logger.debug('开始执行量子门操作')
        qcos_logger.debug('在超导处理器上执行 Hadamard 门操作')
        h_gate = QuantumGateOperation('H', 0)
        result = manager.execute_operation('superconducting_processor', h_gate)
        qcos_logger.debug(f'Hadamard 门结果: {result}')

        qcos_logger.debug('在中性原子处理器上执行 CNOT 门操作')
        cnot_gate = QuantumGateOperation('CNOT', [0, 1])
        result = manager.execute_operation('neutral_atom_processor', cnot_gate)
        qcos_logger.debug(f'CNOT 门结果: {result}')

        qcos_logger.debug('在离子阱处理器上执行测量操作')
        measure_op = QuantumGateOperation('Measure', 0)
        result = manager.execute_operation('ion_trap_processor', measure_op)
        qcos_logger.debug(f'测量结果: {result}')

        qcos_logger.debug('开始校准量子硬件')
        for hw_name in manager.interfaces:
            qcos_logger.debug(f'正在校准 {hw_name}')
            manager.calibrate_hardware(hw_name)
            status = manager.get_hardware_status(hw_name)
            qcos_logger.debug(f'{hw_name} 校准后状态: {status}')

    except Exception as e:
        logging.error(f'量子操作过程中发生错误: {str(e)}')
    finally:
        qcos_logger.debug('开始断开量子硬件连接')
        for hw_name in manager.interfaces:
            qcos_logger.debug(f'正在断开 {hw_name} 的连接')
            manager.disconnect_hardware(hw_name)
            status = manager.get_hardware_status(hw_name)
            qcos_logger.debug(f'{hw_name} 断开连接后状态: {status}')


if __name__ == '__main__':
    main()
