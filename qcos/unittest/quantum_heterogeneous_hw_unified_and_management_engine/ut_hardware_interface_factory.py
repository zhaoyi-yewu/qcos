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


import unittest
from unittest.mock import patch, MagicMock


# 在导入会加载 DLL 的模块之前，先模拟 cdll.LoadLibrary
with patch('ctypes.cdll.LoadLibrary') as mock_load_library:
    # 设置模拟的 DLL 对象
    mock_dll = MagicMock()
    # 将 LoadLibrary 返回值设置为模拟的 DLL 对象
    mock_load_library.return_value = mock_dll

    from typing import Any, Dict
    from qcos.\
        quantum_heterogeneous_hw_unified_and_management_engine.\
        hardware_interface_factory import \
        HardwareInterfaceFactory
    from qcos.\
        quantum_heterogeneous_hw_unified_and_management_engine.\
        hardware_interfaces.awg_interface import \
        AWGInterface
    from qcos.\
        quantum_heterogeneous_hw_unified_and_management_engine.\
        hardware_interfaces.superconducting_processor_interface import \
        SuperconductingProcessorInterface
    from qcos.\
        quantum_heterogeneous_hw_unified_and_management_engine.\
        hardware_interfaces.ni_chassis_interface import \
        NIChassisInterface
    from qcos.\
        quantum_heterogeneous_hw_unified_and_management_engine.\
        hardware_interfaces.neutral_atom_processor_interface import \
        NeutralAtomProcessorInterface
    from qcos.\
        quantum_heterogeneous_hw_unified_and_management_engine.\
        hardware_interfaces.ion_trap_processor_interface import \
        IonTrapProcessorInterface
    from qcos.\
        quantum_heterogeneous_hw_unified_and_management_engine.\
        hardware_interfaces.fpga_interface import \
        FPGAInterface

    class TestHardwareInterfaceFactory(unittest.TestCase):
        '''
        测试 HardwareInterfaceFactory 类的单元测试类
        '''

        def setUp(self):
            '''
            初始化测试环境
            '''
            # 准备配置数据
            self.config = {}

        @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
               'hardware_interfaces.awg_interface.'
               'AWGInterface.load_queue_wave2_awg')
        def test_create_awg_interface(self, mock_awg):
            '''
            测试创建 AWG 接口实例
            '''
            # 创建模拟的 SD_AOU 实例
            mock_module_instance = MagicMock()

            # 设置 open_with_serial_number 方法返回一个有效的整数
            mock_module_instance.open_with_serial_number.return_value = 1

            # 调用工厂方法创建 AWG 接口实例
            interface = HardwareInterfaceFactory.create_interface(
                'awg', self.config)

            # 断言接口实例是 AWGInterface 类型
            self.assertIsInstance(interface, AWGInterface)

            # 验证 module_id 是否被正确设置
            self.assertEqual(interface.module_id, 1)

        def test_create_superconducting_interface(self):
            '''
            测试创建超导处理器接口实例
            '''
            # 调用工厂方法创建超导处理器接口实例
            interface = HardwareInterfaceFactory.create_interface(
                'superconducting', self.config)
            # 断言接口实例是 SuperconductingProcessorInterface 类型
            self.assertIsInstance(interface, SuperconductingProcessorInterface)

        def test_create_neutral_atom_interface(self):
            '''
            测试创建中性原子处理器接口实例
            '''
            # 调用工厂方法创建中性原子处理器接口实例
            interface = HardwareInterfaceFactory.create_interface(
                'neutral_atom', self.config)
            # 断言接口实例是 NeutralAtomProcessorInterface 类型
            self.assertIsInstance(interface, NeutralAtomProcessorInterface)

        def test_create_ion_trap_interface(self):
            '''
            测试创建离子阱处理器接口实例
            '''
            # 调用工厂方法创建离子阱处理器接口实例
            interface = HardwareInterfaceFactory.create_interface(
                'ion_trap', self.config)
            # 断言接口实例是 IonTrapProcessorInterface 类型
            self.assertIsInstance(interface, IonTrapProcessorInterface)

        @patch('nidaqmx.Task')
        def test_create_ni_chassis_interface(self, mock_nidaqmx_task):
            '''
            测试创建 NI 底盘接口实例
            '''
            # 调用工厂方法创建 NI 底盘接口实例
            interface = HardwareInterfaceFactory.create_interface(
                'ni_chassis', self.config)
            # 断言接口实例是 NIChassisInterface 类型
            self.assertIsInstance(interface, NIChassisInterface)

        def test_create_fpga_interface(self):
            '''
            测试创建 FPGA 接口实例
            '''
            # 调用工厂方法创建 FPGA 接口实例
            interface = HardwareInterfaceFactory.create_interface(
                'fpga', self.config)
            # 断言接口实例是 FPGAInterface 类型
            self.assertIsInstance(interface, FPGAInterface)

        def test_create_interface_invalid_type(self):
            '''
            测试创建接口时提供无效的硬件类型
            '''
            # 使用 assertRaises 断言抛出 ValueError 异常
            with self.assertRaises(ValueError):
                # 调用工厂方法创建无效类型的接口实例
                HardwareInterfaceFactory.create_interface(
                    'invalid_type', self.config)

    if __name__ == '__main__':
        unittest.main()
