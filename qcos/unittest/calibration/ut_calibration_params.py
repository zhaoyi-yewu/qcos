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

import json
import os
import time
import unittest
from unittest.mock import patch, MagicMock, mock_open
from qcos.calibration.calibration_params import (
    CalibrationParams, CalibrationParamsInteraction)
from qcos.\
    config.qcos_config_manager import \
    qcos_configer
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.awg_interface import AWGInterface
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.camera_interface import \
    CameraInterface
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.ni_chassis_interface import \
    NIAOInterface, NIDOInterface


class TestCalibrationParams(unittest.TestCase):
    '''
    CalibrationParams 类的单元测试
    '''

    def setUp(self):
        '''
        初始化测试环境
        '''
        self.calibration = CalibrationParams()

    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.awg_interface.AWGInterface')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.ni_chassis_interface.'
           'NIDOInterface')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.ni_chassis_interface.'
           'NIAOInterface')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.ni_chassis_interface.'
           'NIDOInterface.connect')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.ni_chassis_interface.'
           'NIAOInterface.connect')
    @patch('nidaqmx.Task')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.camera_interface.'
           'CameraInterface')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.camera_interface.'
           'CameraInterface.connect')
    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.camera_interface.'
           'CameraInterface.initialize')
    @patch('os.listdir')
    def test_hardware_instantiation(
            self, mock_listdir, mock_camera_initialize,
            mock_camera_connect, mock_camera, mock_task,
            mock_niao_connect, mock_nido_connect, mock_niao,
            mock_nido, mock_awg):
        '''
        测试 hardware_instantiation 方法
        '''
        # mock硬件类及函数
        mock_awg.return_value = MagicMock()
        mock_nido.return_value = MagicMock()
        mock_niao.return_value = MagicMock()
        mock_task.return_value = MagicMock()
        mock_camera.return_value = MagicMock()
        mock_listdir.return_value = 'test_files'

        if os.name == 'nt':
            # Windows环境
            with patch('ctypes.OleDLL') as mock_oledll:
                self.calibration.hardware_instantiation()
        else:
            # Linux环境
            with patch('ctypes.CDLL') as mock_cdll:
                self.calibration.hardware_instantiation()

        # 验证方法被成功调用
        mock_camera_connect.assert_called_once()
        mock_camera_initialize.assert_called_once()
        mock_niao_connect.assert_called_once()
        mock_nido_connect.assert_called_once()

    @patch('numpy.sin')
    @patch('os.mkdir')
    @patch('os.path.exists')
    @patch('numpy.linspace')
    @patch('qcos.cna.core.rearrange.generate_wave.generate_raman_wave')
    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('qcos.cna.core.rearrange.rearrangement.get_params')
    @patch('ctypes.cdll.LoadLibrary')
    @patch('qcos.cna.core.config.GlobalSetting')
    @patch('qcos.cna.core.rearrange.rearrangement.ReArrangement.transport')
    @patch('qcos.cna.core.rearrange.rearrangement.ReArrangement.set_target')
    @patch('qcos.cna.core.rearrange.rearrangement.ReArrangement')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('json.loads')
    def test_scan_parameter(
            self, mock_loads, mock_open, mock_rearrangement,
            mock_set_target, mock_transport, mock_global_setting,
            mock_load_library, mock_get_params, mock_info,
            mock_generate_raman_wave, mock_linspace, mock_exists,
            mock_mkdir, mock_sin):
        '''
        测试 scan_parameter 方法
        '''
        # 测试错误场景1
        qcos_configer.get_debug_mode = MagicMock(return_value=1)
        with self.assertRaises(RuntimeError):
            self.calibration.scan_parameter('rabi', 1, 1, 1, 1, 1, shots=1)
        # 测试错误场景2
        qcos_configer.get_debug_mode = MagicMock(return_value=0)
        self.calibration.hardware_instantiation = (
            MagicMock(side_effect=ValueError))
        with self.assertRaises(ConnectionError):
            self.calibration.scan_parameter('rabi', 1, 1, 1, 1, 1, shots=1)
        # 测试正确场景
        qcos_configer.get_debug_mode = MagicMock(return_value=0)
        self.calibration.hardware_instantiation = MagicMock()
        mock_loads.return_value = {
            'raman': {
                'c1_time': 0.0006,
                'c3_time': 1,
                'c3_start_time': 0.0001
            },
            'movement': {
                'arrange_amp': [1, 2]
            }
        }
        mock_rearrangement.return_value = MagicMock()
        mock_global_setting.get_rearrangement_dll = (
            MagicMock(return_value='mocked_dll'))
        mock_get_params.return_value = {
            'overview': {'row': 10, 'column': 10},
            'movement': {'output_len': 1000}
        }
        self.calibration.camera = MagicMock(spec=CameraInterface)
        self.calibration.camera.start_acquisition = MagicMock()
        self.calibration.awg = MagicMock(spec=AWGInterface)
        self.calibration.awg.sendSingleChannel = MagicMock()
        self.calibration.niao = MagicMock(spec=NIAOInterface)
        self.calibration.nido = MagicMock(spec=NIDOInterface)
        self.calibration.nido.send = MagicMock()
        self.calibration.niao.send = MagicMock()
        self.calibration.nido.start = MagicMock()
        self.calibration.niao.start = MagicMock()
        self.calibration.camera.capture_image = MagicMock()
        self.calibration.camera.get_status_with_threshold = (
            MagicMock(return_value=[1] * 100))
        self.calibration.awg.setArrangeWave = MagicMock()
        self.calibration.awg.startMultipChannel = MagicMock()
        self.calibration.awg.setRamanWave = MagicMock()
        self.calibration.niao.stop_operation = MagicMock()
        self.calibration.nido.stop_operation = MagicMock()
        self.calibration.camera.stop_operation = MagicMock()
        self.calibration.awg.load_queue_wave2_awg = MagicMock()

        # 调用 scan_parameter 方法
        self.calibration.scan_parameter('rabi', 1, 1, 1, 1, 1, shots=1)

        # 验证方法被成功调用
        mock_info.assert_called_with('参数扫描结束')
        self.calibration.niao.send_data.assert_called()
        self.calibration.niao.execute_operation.assert_called()
        self.calibration.camera.capture_image.assert_called()
        self.calibration.awg.setRamanWave.assert_called()
        self.calibration.camera.stop_operation.assert_called()

    def test_scan_raman_rabi(self):
        '''
        测试 scan_raman_rabi 方法
        '''
        self.calibration.scan_parameter = MagicMock()
        # 调用 scan_raman_rabi 方法
        self.calibration.scan_raman_rabi(1, 1, 1, 1, 1)
        # 验证方法被正确调用
        (self.calibration.scan_parameter.
         assert_called_once_with('rabi', 1, 1, 1, 1, 1))

    def test_scan_raman_ch1(self):
        '''
        测试 scan_raman_ch1 方法
        '''
        self.calibration.scan_parameter = MagicMock()
        # 调用 scan_raman_ch1 方法
        self.calibration.scan_raman_ch1(1, 1, 1, 1, 1)
        # 验证方法被正确调用
        (self.calibration.scan_parameter.
         assert_called_once_with('raman_ch1', 1, 1, 1, 1, 1))

    def test_scan_raman_ch2(self):
        '''
        测试 scan_raman_ch2 方法
        '''
        self.calibration.scan_parameter = MagicMock()
        # 调用 scan_raman_ch2 方法
        self.calibration.scan_raman_ch2(1, 1, 1, 1, 1)
        # 验证方法被正确调用
        (self.calibration.scan_parameter.
         assert_called_once_with('raman_ch2', 1, 1, 1, 1, 1))

    def test_scan_arrange_ch1(self):
        '''
        测试 scan_arrange_ch1 方法
        '''
        self.calibration.scan_parameter = MagicMock()
        # 调用 scan_arrange_ch1 方法
        self.calibration.scan_arrange_ch1(1, 1, 1, 1, 1, 1, 1)
        # 验证方法被正确调用
        (self.calibration.scan_parameter.
         assert_called_once_with('arrange_ch1', 1, 1, 1, 1, 1,
                                 row_up=1, row_down=1, col_left=1, col_right=1))

    def test_scan_arrange_ch2(self):
        '''
        测试 scan_arrange_ch2 方法
        '''
        self.calibration.scan_parameter = MagicMock()
        # 调用 scan_arrange_ch2 方法
        self.calibration.scan_arrange_ch2(1, 1, 1, 1, 1, 1, 1)
        # 验证方法被正确调用
        (self.calibration.scan_parameter.
         assert_called_once_with('arrange_ch2', 1, 1, 1, 1, 1,
                                 row_up=1, row_down=1, col_left=1, col_right=1))


class TestCalibrationParamsInteraction(unittest.IsolatedAsyncioTestCase):
    '''
    CalibrationParamsInteraction 类的单元测试
    '''

    def setUp(self):
        '''
        初始化测试环境
        '''
        self.calibration_interaction = CalibrationParamsInteraction()
        self.calibration_interaction.calibration = (
            MagicMock(spec=CalibrationParams))
        self.calibration_interaction.calibration_app.testing = True
        self.app = self.calibration_interaction.calibration_app.test_client()

    def test_fetch_params(self):
        '''
        测试 fetch_params 方法
        '''
        # 测试错误场景1
        self.calibration_interaction.deal_request()
        response_data = self.app.post('/v1/auto_calibration')
        self.assertEqual(response_data.get_json(), {'code': 1})

        # 测试错误场景2
        response_data = self.app.post('/v1/auto_calibration', json={})
        self.assertEqual(response_data.get_json(), {'code': 1})

        # 测试正确场景
        data = {
            'data': {
                'type': 'rabi',
                'parameters': {
                    'atom_row': 1,
                    'atom_col': 1,
                    'init_val': 1,
                    'step': 1,
                    'step_num': 1,
                    'row_up': 1,
                    'row_down': 1,
                    'col_left': 1,
                    'col_right': 1
                }
            }
        }
        self.calibration_interaction.execute_calibration = MagicMock()
        response_data = self.app.post('/v1/auto_calibration', json=data)
        self.assertEqual(response_data.get_json(), {'code': 0})

    def test_feedback_result(self):
        '''
        测试 feedback_result 方法
        '''
        # 测试场景1：当前没有校准任务
        self.calibration_interaction.current_type = None
        self.calibration_interaction.deal_request()
        response_data = self.app.get('/v1/auto_calibration?type=rabi')
        ideal_data = {
            'code': 0,
            'data': {
                'status': 'ready'
            }
        }
        self.assertEqual(response_data.get_json(), ideal_data)

        # 测试场景2：校准任务出错
        self.calibration_interaction.current_type = 'rabi'
        self.calibration_interaction.message = 'error'
        response_data = self.app.get('/v1/auto_calibration?type=rabi')
        ideal_data = {
            'code': 1,
            'data': {
                'status': 'fail',
                'res': [],
                'message': self.calibration_interaction.message
            }
        }
        self.assertEqual(response_data.get_json(), ideal_data)

        # 测试场景3：校准任务进行中
        self.calibration_interaction.current_type = 'rabi'
        self.calibration_interaction.message = None
        res = [
            {
                'result': 'test_result1'
            }
        ]
        self.calibration_interaction.deal_data = MagicMock(return_value=res)
        self.calibration_interaction.step_num = 2
        response_data = self.app.get('/v1/auto_calibration?type=rabi')
        ideal_data = {
            'code': 0,
            'data': {
                'status': 'running',
                'res': res
            }
        }
        self.assertEqual(response_data.get_json(), ideal_data)

        # 测试场景4：校准任务完成
        self.calibration_interaction.current_type = 'rabi'
        self.calibration_interaction.message = None
        res = [
            {
                'result': 'test_result2'
            }
        ]
        self.calibration_interaction.deal_data = MagicMock(return_value=res)
        self.calibration_interaction.step_num = 1
        response_data = self.app.get('/v1/auto_calibration?type=rabi')
        ideal_data = {
            'code': 0,
            'data': {
                'status': 'complete',
                'res': res
            }
        }
        self.assertEqual(response_data.get_json(), ideal_data)

    def test_abort_calibration(self):
        '''
        测试 abort_calibration 方法
        '''
        self.calibration_interaction.calibration.allow_run = True
        self.calibration_interaction.deal_request()
        response_data = self.app.post('/v1/auto_calibration/abort')
        ideal_data = {
            'code': 0
        }
        self.assertEqual(response_data.get_json(), ideal_data)
        self.assertEqual(
            self.calibration_interaction.calibration.
            allow_run, False)

    @patch('qcos.quantum_heterogeneous_hw_unified_and_management_engine.'
           'hardware_interfaces.awg_interface.AWGInterface')
    @patch('os.listdir')
    @patch('numpy.sin')
    @patch('os.mkdir')
    @patch('os.path.exists')
    @patch('numpy.linspace')
    def test_update_params(
            self, mock_linspace, mock_exists,
            mock_mkdir, mock_sin, mock_listdir, mock_awg):
        '''
        测试 update_params 方法
        '''
        qcos_configer.get_debug_mode = MagicMock(return_value=1)
        # 测试错误场景1
        self.calibration_interaction.deal_request()
        response_data = self.app.post('/v1/auto_calibration/submit')
        self.assertEqual(response_data.get_json(), {'code': 1})

        # 测试错误场景2
        response_data = self.app.post('/v1/auto_calibration/submit', json={})
        self.assertEqual(response_data.get_json(), {'code': 1})

        # 测试正确场景
        mock_awg.load_queue_wave2_awg = MagicMock
        load_data = {
            'overview': {
                'row': 10,
                'column': 10,
                'awgSamplingRate': 500
            },
            'raman': {
                'init_freq_x': 50,
                'init_freq_y': 50,
                'inter_freq_x': 10,
                'inter_freq_y': 10,
                'c1_time': 0.0006,
                'c3_time': 1,
                'c3_start_time': 0.0001
            },
            'movement': {
                'init_freq_x': 50,
                'init_freq_y': 50,
                'inter_freq_x': 10,
                'inter_freq_y': 10,
                'grab_time': 0.0005,
                'mov_time': 0.002
            }
        }
        origin_data = json.dumps(load_data)
        with (patch('builtins.open', mock_open(read_data=origin_data))
              as mock_file):
            mock_file.write = MagicMock()
            # 测试更新 rabi 参数
            data = {
                'type': 'rabi',
                'data': 1
            }
            response_data = self.app.post('/v1/auto_calibration/submit',
                                          json=data)
            self.assertEqual(response_data.get_json(), {'code': 0})

            # 测试更新 raman_ch1 参数
            data = {
                'type': 'raman_ch1',
                'data': 1
            }
            response_data = self.app.post('/v1/auto_calibration/submit',
                                          json=data)
            self.assertEqual(response_data.get_json(), {'code': 0})

            # 测试更新 raman_ch2 参数
            data = {
                'type': 'raman_ch2',
                'data': 1
            }
            response_data = self.app.post('/v1/auto_calibration/submit',
                                          json=data)
            self.assertEqual(response_data.get_json(), {'code': 0})

            # 测试更新 arrange_ch1 参数
            data = {
                'type': 'arrange_ch1',
                'data': 1
            }
            response_data = self.app.post('/v1/auto_calibration/submit',
                                          json=data)
            self.assertEqual(response_data.get_json(), {'code': 0})

            # 测试更新 arrange_ch2 参数
            data = {
                'type': 'arrange_ch2',
                'data': 1
            }
            response_data = self.app.post('/v1/auto_calibration/submit',
                                          json=data)
            self.assertEqual(response_data.get_json(), {'code': 0})

    def test_feedback_current_value(self):
        '''
        测试 feedback_current_value 方法
        '''
        # 测试错误场景
        self.calibration_interaction.deal_request()
        response_data = self.app.get('/v1/auto_calibration/current_value')
        ideal_data = {
            'code': 1
        }
        self.assertEqual(response_data.get_json(), ideal_data)

        # 测试正确场景
        load_data = {
            'raman': {
                'init_freq_x': 50,
                'init_freq_y': 50,
                'c3_time': 50
            },
            'movement': {
                'init_freq_x': 50,
                'init_freq_y': 50
            }
        }
        origin_data = json.dumps(load_data)
        with patch('builtins.open', mock_open(read_data=origin_data)):
            rabi_data = self.app.get('/v1/auto_calibration/'
                                     'current_value?type=rabi')
            raman_ch1_data = self.app.get('/v1/auto_calibration/'
                                          'current_value?type=raman_ch1')
            raman_ch2_data = self.app.get('/v1/auto_calibration/'
                                          'current_value?type=raman_ch2')
            arrange_ch1_data = self.app.get('/v1/auto_calibration/'
                                            'current_value?type=arrange_ch1')
            arrange_ch2_data = self.app.get('/v1/auto_calibration/'
                                            'current_value?type=arrange_ch2')
            ideal_data = {
                'code': 0,
                'data': 50
            }
            self.assertEqual(rabi_data.get_json(), ideal_data)
            self.assertEqual(raman_ch1_data.get_json(), ideal_data)
            self.assertEqual(raman_ch2_data.get_json(), ideal_data)
            self.assertEqual(arrange_ch1_data.get_json(), ideal_data)
            self.assertEqual(arrange_ch2_data.get_json(), ideal_data)

    @patch('time.time')
    async def test_execute_calibration(self, mock_time):
        '''
        测试 execute_calibration 方法
        '''
        mock_time.return_value = '20250401'
        # 测试扫描 rabi 参数
        self.calibration_interaction.calibration.scan_raman_rabi = MagicMock()
        await (self.calibration_interaction.
               execute_calibration('rabi', 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        (self.calibration_interaction.calibration.scan_raman_rabi.
         assert_called_once_with(
             1, 1, 1, 1, 1, shots=1, log_name='rabi_20250401.log'))

        # 测试扫描 raman_ch1 参数
        self.calibration_interaction.calibration.scan_raman_ch1 = MagicMock()
        await (self.calibration_interaction.
               execute_calibration('raman_ch1', 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        (self.calibration_interaction.calibration.
         scan_raman_ch1.assert_called_once_with(
             1, 1, 1, 1, 1, shots=1, log_name='raman_ch1_20250401.log'))

        # 测试扫描 raman_ch2 参数
        self.calibration_interaction.calibration.scan_raman_ch2 = MagicMock()
        await (self.calibration_interaction.
               execute_calibration('raman_ch2', 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        (self.calibration_interaction.calibration.scan_raman_ch2.
         assert_called_once_with(
             1, 1, 1, 1, 1, shots=1, log_name='raman_ch2_20250401.log'))

        # 测试扫描 arrange_ch1 参数
        self.calibration_interaction.calibration.scan_arrange_ch1 = MagicMock()
        await (self.calibration_interaction.
               execute_calibration('arrange_ch1', 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        (self.calibration_interaction.calibration.scan_arrange_ch1.
         assert_called_once_with(
             1, 1, 1, 1, 1, 1, 1, shots=1, log_name='arrange_ch1_20250401.log'))

        # 测试扫描 arrange_ch2 参数
        self.calibration_interaction.calibration.scan_arrange_ch2 = MagicMock()
        await (self.calibration_interaction.
               execute_calibration('arrange_ch2', 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        (self.calibration_interaction.calibration.scan_arrange_ch2.
         assert_called_once_with(
             1, 1, 1, 1, 1, 1, 1, shots=1, log_name='arrange_ch2_20250401.log'))

        # 测试错误场景
        await (self.calibration_interaction.
               execute_calibration('test_type', 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))
        self.assertEqual(
            self.calibration_interaction.message,
            '参数校准时出现错误：传入参数有误')

    def test_deal_data(self):
        '''
        测试 deal_data 方法
        '''
        # 测试错误场景
        self.calibration_interaction.current_file = None
        result = self.calibration_interaction.deal_data()
        self.assertEqual(result, [])

        # 测试正确场景
        with patch(
                'builtins.open', mock_open(
                    read_data='scan_value=1, '
                              'rea_qubit_res=1, raman_qubit_res=1')):
            self.calibration_interaction.current_file = 'test.log'
            result = self.calibration_interaction.deal_data()
            ideal_res = [{
                'scan_value': 1,
                'rea_qubit_res': 1,
                'raman_qubit_res': 1
            }]
            self.assertEqual(result, ideal_res)


if __name__ == '__main__':
    unittest.main()
