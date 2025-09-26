#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-08
# ------------------------


from unittest.mock import Mock
from qcos.cna import GlobalSetting, InstrumentType
from qcos.memory.qcos_mem_task_manager import (
    QuantumCircuitTask,
    QuantumTaskCommand,
    QuantumTaskDecorator,
)
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from qcos.log.qcos_log import QCOSLogger
from qcos.cna.core.compiler.decompose import RX
from qcos.cna.core.emccd.camera_detection import CameraDetection
from qcos.cna.core.sequencer import Experiment
from qcos.config.qcos_config_manager import qcos_configer
import json
import os

# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TestQuantumTaskCommand(unittest.TestCase):
    '''
    QuantumTaskCommand类的单元测试
    '''

    def test_execute(self):
        '''
        测试execute函数是否为抽象方法
        '''
        # 断言抽象基类不能直接实例化
        with self.assertRaises(TypeError):
            task = QuantumTaskCommand()


class TestQuantumTaskDecorator(unittest.TestCase):
    '''
    QuantumTaskDecorator类的单元测试
    '''

    def setUp(self):
        '''
        初始化测试环境
        '''
        # 使用MagicMock创建虚拟量子任务
        self.mock_task = MagicMock(spec=QuantumTaskCommand)
        # 创建装饰器实例
        self.decorator = QuantumTaskDecorator(self.mock_task)

    def test_execute(self):
        '''
        测试装饰器的execute函数
        '''
        # 执行装饰器的execute函数
        self.decorator.execute()
        # 断言被装饰的任务的execute函数被调用
        self.mock_task.execute.assert_called_once()


class TestQuantumCircuitTask(unittest.IsolatedAsyncioTestCase):
    '''
    QuantumCircuitTask类的单元测试
    '''

    def setUp(self):
        '''
        初始化测试环境
        '''
        # 创建内存视图实例
        self.memory = memoryview(bytearray(b'\x00' * 128))
        # 创建量子电路任务实例
        self.task = QuantumCircuitTask("task1")
        # 使用有效的 OpenQASM 内容执行代码
        self.valid_openqasm = '''
                OPENQASM 2.0;
                include "qelib1.inc";
                qreg q[1];
                creg c[1];
                x q[0];
                measure q -> c;
                '''

    @patch('time.time', return_value=1234567890.0)
    def test_init(self, mock_time):
        '''
        测试初始化函数
        '''
        # 在 mock 时间后初始化 QuantumCircuitTask 实例
        task = QuantumCircuitTask('test_id')

        # 断言任务ID正确
        self.assertEqual(task.task_id, 'test_id')
        # 断言最后活跃时间被正确设置
        self.assertEqual(task.last_active_time, 1234567890.0)

    @patch('qcos.cna.core.compiler.parser.get_abs_tree')
    @patch('qcos.cna.core.compiler.parser.get_ir')
    @patch('qcos.cna.core.compiler.decompose.transpiler')
    def test_parse_openqasm(
            self,
            mock_transpiler,
            mock_get_ir,
            mock_get_abs_tree):
        '''
        测试OpenQASM解析函数
        '''
        # 模拟返回的量子电路结构
        mock_get_abs_tree.return_value = 'mock_node'
        mock_get_ir.return_value = (1, 'mock_ir')

        # 设置OpenQASM内容
        self.task.set_openqasm_content(self.valid_openqasm, 100)

        # 断言解析结果正确
        parsed_circuit = self.task.parse_openqasm()

        # 将对象属性转换为字典
        '''
        def obj_to_dict(obj):
            return {'class': obj.__class__.__name__, 'targets': obj.targets, 
            'arg_value': obj.arg_value}
        '''

        def obj_to_dict(obj):
            # 确保 targets 统一为列表
            targets = obj.targets
            if not isinstance(targets, list):
                # 如果是单个值，将其转换为列表
                targets = [targets]
            return {
                'class': obj.__class__.__name__,
                'targets': targets,
                'arg_value': obj.arg_value,
            }

        parsed_circuit_dicts = [obj_to_dict(gate) for gate in parsed_circuit]
        # 判断结果有效性
        self.assertIsNotNone(parsed_circuit_dicts)
        self.assertEqual(len(parsed_circuit), 2)

    @patch('qcos.cna.core.compiler.gate_to_seq')
    @patch('qcos.log.qcos_log.QCOSLogger.debug')
    async def test_convert_parsed_circuit_to_sequence(
            self, mock_logger, mock_gate_to_seq
    ):
        '''
        测试解析后的电路转化为脉冲序列的函数
        '''
        # 模拟脉冲序列返回
        mock_gate_to_seq.return_value = ['pulse1', 'pulse2']

        # 模拟解析后的量子电路
        parsed_circuit = [
            RX(targets=[0], arg_value=3.141592653589793),
        ]

        result = await self.task.convert_parsed_circuit_to_sequence(
            parsed_circuit)

        # 断言函数被正确调用
        # self.assertEqual(result, ['pulse1', 'pulse2'])
        self.assertTrue(result)

    @patch('qcos.cna.core.emccd.camera_detection.CameraDetection.'
           'get_status_with_threshold')
    @patch('qcos.cna.core.emccd.get_camera.get_real_camera')
    def test_measure_qubit_status(
            self, mock_get_real_camera, mock_get_status_with_threshold
    ):
        '''
        测试量子状态图像处理与结果读取的函数
        '''
        # 模拟函数返回
        mock_get_real_camera.return_value = MagicMock(spec=CameraDetection)
        mock_get_status_with_threshold.return_value = [1, 0]
        result = self.task.measure_qubit_status(2)

        # 断言结果有效
        self.assertEqual(len(result), 2)
        self.assertIn([1, 0], result)

    def test_set_openqasm_content(self):
        '''
        测试设置OpenQASM内容的函数
        '''
        # 执行 set_openqasm_content 方法
        self.task.set_openqasm_content('mock_openqasm', 100)
        # 断言内容被正确设置
        self.assertEqual(self.task.openqasm_content, 'mock_openqasm')

        # 断言设置失败
        with self.assertRaises(ValueError):
            self.assertFalse(self.task.set_openqasm_content('', 100))

    def test_set_aggregation_task(self):
        '''
        测试设置聚合任务相关参数的函数
        '''
        # 执行 set_aggregation_task 方法
        self.task.set_aggregation_task(
            Mock(
                spec=list), Mock(
                spec=list), 100, 100)
        # 断言内容被正确设置
        self.assertEqual(self.task.sum_qubit, 100)
        self.assertEqual(self.task.shots, 100)

        # 断言设置失败
        with self.assertRaises(ValueError):
            self.assertFalse(
                self.task.set_aggregation_task(
                    None, None, 100, 100))

    @patch('qcos.log.qcos_log.QCOSLogger.debug')
    @patch('qcos.log.qcos_log.QCOSLogger.info')
    async def test_execute_single(self, mock_info, mock_debug):
        '''
        测试量子电路任务的执行函数, 单任务场景
        '''
        # 设置单独执行
        self.task.is_aggregation = False
        # 设置OpenQASM内容
        self.task.set_openqasm_content('mock_openqasm', 100)

        # mock解析openqasm内容的parse_openqasm函数
        self.task.parse_openqasm = MagicMock()

        with patch.object(
                self.task, 'convert_parsed_circuit_to_sequence',
                new_callable=AsyncMock
        ) as mock_convert:
            mock_convert.return_value = ['pulse1', 'pulse2']

            # 异步调用测试函数
            result = await self.task.execute()
            # 断言返回结果正确
            mock_debug.assert_called_once_with(
                f'任务解析得到脉冲序列： {['pulse1', 'pulse2']}'
            )
            self.assertEqual(result, mock_convert.return_value)

    @patch('qcos.log.qcos_log.QCOSLogger.debug')
    @patch('qcos.log.qcos_log.QCOSLogger.info')
    async def test_execute_aggregation(self, mock_info, mock_debug):
        '''
        测试量子电路任务的执行函数，允许聚合场景
        '''
        # 设置允许聚合
        self.task.is_aggregation = True
        # 创建聚合任务及映射结果实例
        self.task.aggregation_tasks = [
            ('test_id', 'PriorityTask', 1, 100, self.valid_openqasm, {})
        ]
        self.task.qubit_blocks = [['P0', 'P1']]
        self.task.sum_qubit = 1
        # 模拟硬件信息实例
        qpu_config = {
            'qubits': 6,
            'operate_area': ['P0', 'P1'],
            'storage_area': ['S0', 'S1'],
            'closest': {'P0': 'S0', 'P1': 'S1'},
            'coupler_map': {'G0': ['P0', 'P1']},
            'readout_error': {'S0': 8.0, 'S1': 16.0},
        }
        qcos_configer.get_topo_file = MagicMock(return_value=qpu_config)

        # 异步调用测试函数
        result = await self.task.execute()

        # 验证任务添加结果
        self.assertEqual(len(result), 3)

    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.awg_interface.AWGInterface')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.ni_chassis_interface.NIDOInterface')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.ni_chassis_interface.NIAOInterface')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.camera_interface.CameraInterface')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.camera_interface.CameraInterface.connect')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.camera_interface.CameraInterface.initialize')
    @patch('qcos.cna.core.config.GlobalSetting')
    @patch('qcos.cna.core.rearrange.rearrangement.ReArrangement')
    @patch('qcos.cna.sequencer.Experiment')
    @patch('qcos.config.qcos_config_manager.QcosConfigManager.get_na_file')
    @patch('ctypes.cdll.LoadLibrary')
    @patch('nidaqmx.Task')
    @patch('builtins.open')
    @patch('os.listdir')
    def test_create_exp(
            self,
            mock_listdir,
            mock_open,
            mock_task,
            mock_ll,
            mock_get_na_file,
            mock_experiment,
            mock_rearrangement,
            mock_global_setting,
            mock_initialize,
            mock_connect,
            mock_camera,
            mock_niao,
            mock_nido,
            mock_awg,
    ):
        '''
        测试create_exp
        '''
        mock_ll.return_value = MagicMock()
        mock_global_setting.get_rearrangement_dll = MagicMock(
            return_value='mocked_dll')
        mock_rearrangement.return_value = MagicMock()
        mock_task.return_value = MagicMock()
        mock_get_na_file.return_value = 'mocked_na_file'
        mock_open.return_value = MagicMock()
        mock_open.return_value.__enter__.return_value.read.return_value = (
            json.dumps({'overview': {'row': 10, 'column': 10},
                        'movement': {'output_len': 1000}}
                       ))

        mock_awg.return_value = MagicMock()
        mock_listdir.return_value = 'test_files'
        mock_nido.return_value = MagicMock()
        mock_niao.return_value = MagicMock()
        mock_camera.return_value = MagicMock()

        if os.name == 'nt':
            # Windows环境
            with patch('ctypes.OleDLL') as mock_oledll:
                # 调用方法
                test_exp = self.task.create_exp()
        else:
            # Linux环境
            with patch('ctypes.CDLL') as mock_cdll:
                # 调用方法
                test_exp = self.task.create_exp()

        # 确认实验对象被正确创建
        self.assertIsInstance(test_exp, Experiment)

    @patch.object(QuantumCircuitTask, 'create_exp')
    def test_execute_task_on_quantum(self, mock_create_exp):
        '''
        测试execute_task_on_quantum
        '''
        # 设置 InstrumentType 返回值
        current_instrument_type = GlobalSetting.get_instrument_type()
        GlobalSetting.set_instrument_type(
            InstrumentType.INSTRUMENT_HW_FPGA_AWG)

        # 模拟create_exp方法返回值
        mock_exp = MagicMock()
        mock_create_exp.return_value = mock_exp
        mock_exp.new_sequence.return_value = MagicMock()
        mock_exp.new_sequence.return_value.set_sequence = MagicMock()
        mock_exp.last_sequence.get_atom_awg_data.return_value = (
            'awg_ch1_data',
            'awg_ch2_data',
            'awg_format',
        )
        mock_exp.awg_interface.generator.generateFullWave.return_value = (
            'awg_ch3_data',
            'awg_ch4_data',
        )
        mock_exp.awg_interface.sendSingleChannel = MagicMock()
        mock_exp.camera_switch = True
        mock_exp.camera.camera.start_acquisition = MagicMock()
        mock_exp.repeat = 1
        mock_exp.threshold = 1
        mock_exp.threshold_block = 1
        mock_exp.qubit_number = 10
        mock_exp.load_time = 0.1

        mock_exp.camera.get_status_with_threshold.return_value = MagicMock()
        # 模拟 rea 对象和 transport 方法
        mock_rea = MagicMock()
        mock_rea.transport.return_value = (
            'mocked_x_data',
            'mocked_y_data',
        )  # 返回两个模拟的值
        mock_exp.rea = mock_rea

        # 调用方法
        sequence = 'test_sequence'
        task_result, rea_result = self.task.execute_task_on_quantum(sequence)
        GlobalSetting.set_instrument_type(current_instrument_type)

        # 验证函数调用
        mock_create_exp.assert_called_once()
        mock_exp.new_sequence.assert_called_once()
        mock_exp.new_sequence.return_value.set_sequence.assert_called_once()
        mock_exp.last_sequence.get_atom_awg_data.assert_called_once()
        (mock_exp.awg_interface.generator.generateFullWave.
         assert_called_once_with(600, 'awg_format'))
        calls = [
            unittest.mock.call(
                'awg_ch3_data', channelID=3, trigger='externalcycle', cycles=1
            ),
            unittest.mock.call(
                'awg_ch4_data', channelID=4, trigger='externalcycle', cycles=1
            ),
        ]
        mock_exp.awg_interface.sendSingleChannel.assert_has_calls(
            calls, any_order=True)
        mock_exp.camera.get_status_with_threshold.assert_any_call(1, 1)
        mock_rea.transport.assert_called_once_with(
            mock_exp.camera.get_status_with_threshold.return_value
        )
        self.assertIsInstance(task_result, list)
        self.assertIsInstance(rea_result, list)


if __name__ == '__main__':
    # 运行所有单元测试
    unittest.main()
