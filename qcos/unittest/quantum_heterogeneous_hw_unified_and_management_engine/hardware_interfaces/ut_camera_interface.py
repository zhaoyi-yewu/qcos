#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Longfei Tian at 2024-11
# ------------------------


import unittest
import os
import numpy as np
from unittest.mock import patch, MagicMock, Mock
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.camera_interface import \
    CameraInterface
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    control_systems.camera_control_system import \
    CameraControlSystem
from qcos.config.qcos_config_manager import qcos_configer
from qcos.cna.core.emccd.camera.TUCam import \
    (TUFRM_FORMATS, TUCAM_FRAME, TUCAM_TRIGGER_EXP,
     TUCAM_TRIGGER_ATTR, TUCAM_TRIGGER_EDGE)
from qcos.log.qcos_log import QCOSLogger

qcos_logger = QCOSLogger()


class TestCameraInterface(unittest.TestCase):
    '''
    Camera接口测试
    '''
    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('qcos.config.qcos_config_manager.qcos_configer.get_camera_dll_path',
           return_value='<path_to_dll>')
    def setUp(self, mock_get_camera_dll_path, mock_logger):
        if os.name == 'nt':
            # Windows环境
            with patch('ctypes.OleDLL') as mock_oledll:
                mock_oledll.return_value = MagicMock()
                # 创建CameraInterface实例
                self.camera = CameraInterface()
        else:
            # Linux环境
            with patch('ctypes.CDLL') as mock_cdll:
                mock_cdll.return_value = MagicMock()
                # 创建CameraInterface实例
                self.camera = CameraInterface()

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch('qcos.cna.core.emccd.camera.TUCam.TUCAM_INIT')
    @patch('qcos.cna.core.emccd.camera.TUCam.TUCAM_OPEN')
    def test_init(self, mock_cam_open, mock_cam_init, mock_logger):
        # 测试初始化SDK环境参数和打开相机参数
        self.camera.cam_int = mock_cam_init.return_value
        self.camera.cam_open = mock_cam_open.return_value
        # 验证初始化是否成功
        self.assertIsNone(self.camera.connection)
        self.assertEqual(
            self.camera.status, 'Disconnected')
        # 验证是否正确设置相机SDK路径及相关参数
        self.assertEqual(
            self.camera.sdk_path,
            qcos_configer.get_camera_init_path())
        self.assertIsNone(self.camera.frame)
        self.assertIsNone(self.camera.buffer)
        self.assertEqual(self.camera.image_idx, 0)
        self.assertIsNone(self.camera.current_image)
        self.assertEqual(self.camera.total_width, 2048)
        self.assertEqual(self.camera.total_height, 2048)
        self.assertEqual(
            self.camera.width_offset,
            qcos_configer.get_width_offset())
        self.assertEqual(
            self.camera.height_offset,
            qcos_configer.get_height_offset())
        self.assertEqual(self.camera.roi_width, qcos_configer.get_roi_width())
        self.assertEqual(
            self.camera.roi_height,
            qcos_configer.get_roi_height())
        self.assertEqual(
            self.camera.image_size,
            qcos_configer.get_roi_width() *
            qcos_configer.get_roi_height())
        self.assertEqual(
            self.camera.threshold_block,
            qcos_configer.get_measure_threshold_block())
        self.assertEqual(
            self.camera.threshold,
            qcos_configer.get_measure_threshold())

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    @patch.object(CameraInterface, 'set_acquisition_mode')
    @patch.object(CameraInterface, 'set_roi')
    @patch('cv2.imread')
    @patch('qcos.cna.core.emccd.functions.auto_detection.find_qubits')
    @patch('numpy.array')
    def test_initialize(
            self,
            mock_array,
            mock_find_qubits,
            mock_imread,
            mock_set_roi,
            mock_set_acquisition_mode,
            mock_logger):
        '''
        测试初始化相机接口
        '''
        # 模拟方法中所用函数的返回值
        mock_imread.return_value = np.zeros((100, 100))
        mock_array.return_value = np.array([10, 10, 10])
        # 调用 initialize 方法
        self.camera.initialize()
        # 验证 initialize 是否被正确调用
        mock_set_acquisition_mode.assert_called_once()
        mock_set_roi.assert_called_once_with(
            self.camera.width_offset,
            self.camera.height_offset,
            self.camera.roi_width,
            self.camera.roi_height)
        mock_imread.assert_called_once_with(
            qcos_configer.get_calib_img_path(), flags=0)
        self.assertEqual(
            self.camera.qubit_position_list,
            mock_array.return_value)
        mock_logger.assert_called_once_with('Initialized Camera interface')

    '''
    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_connect_success(self, mock_logger):
        #测试相机连接成功流程
        # 模拟方法中函数的返回值
        self.camera.cam_int.uiCamCount = 1
        self.camera.cam_open.hIdxTUCam = 1
        # 调用 connect 方法
        self.camera.connect(0)

        # 验证 connect 方法成功连接相机
        self.assertEqual(self.camera.status, 'Connected')
        mock_logger.assert_called_once_with('Successfully connected to camera')
    '''

    @patch('qcos.log.qcos_log.QCOSLogger.error')
    def test_connect_failure(self, mock_logger):
        '''
        测试相机连接失败流程
        '''
        # 测试未物理连接相机场景
        self.camera.cam_int.uiCamCount = 0
        self.assertRaisesRegex(
            ConnectionError,
            'There is 0 camera, can not find camera 0',
            self.camera.connect)

        # 测试相机打开失败场景
        self.camera.cam_int.uiCamCount = 1
        self.assertRaisesRegex(
            ConnectionError,
            'Open the camera failure!',
            self.camera.connect)

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_disconnect(self, mock_logger):
        '''
        测试断开相机连接
        '''
        # 模拟方法中函数的返回值
        self.camera.cam_open.hIdxTUCam = 1
        self.camera.connection = Mock(spec=CameraControlSystem)
        # 调用 disconnect 方法
        self.camera.disconnect()

        # 验证 disconnect 成功断开相机
        self.assertEqual(self.camera.status, 'Disconnected')
        mock_logger.assert_called_once_with('Disconnected from camera')

    def test_adjust_position(self):
        '''
        测试调整比特位置
        '''
        position_list = [(10, 10, 1)]
        result = self.camera.adjust_position(position_list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result, np.ndarray)

    def test_find_qubits_with_threshold(self):
        '''
        测试获取某一个轴上的所有坐标，阈值无需生成
        '''
        image_data = np.float32(np.zeros((100, 100)))
        self.camera.find_qubits(image_data)
        self.assertIsNotNone(self.camera.threshold)

    def test_find_qubits_without_threshold(self):
        '''
        测试获取某一个轴上的所有坐标，阈值为空，需要生成
        '''
        image_data = np.float32(np.zeros((100, 100)))
        self.camera.threshold = None

        self.camera.adjust_position = Mock()
        self.camera.adjust_position.return_value = np.array([])

        # 调用方法
        result = self.camera.find_qubits(image_data)
        # 验证结果
        self.assertIsNotNone(self.camera.threshold)
        self.assertIsInstance(result, np.ndarray)
        self.camera.adjust_position.assert_called_once_with([])

    def test_capture_image(self):
        '''
        测试相机获取图片
        '''
        # 测试相机未连接场景
        self.camera.connection = Mock(spec=CameraControlSystem)
        self.camera.connection.verify_camera_connection.side_effect = [
            False, True]
        self.assertRaisesRegex(
            ConnectionError,
            'Camera is not connected',
            self.camera.get_acquired_data)

        # 测试相机已连接场景
        self.camera.get_acquired_data = Mock(return_value=Mock)

        # 调用 capture_image 方法
        self.camera.capture_image()

        # 验证 capture_image 被成功调用
        self.camera.get_acquired_data.assert_called_once()

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_execute_operation(self, mock_logger):
        '''
        测试初始化相机，进行相机获取
        '''
        # 测试相机未连接场景
        self.camera.connection = Mock(spec=CameraControlSystem)
        self.camera.connection.verify_camera_connection.side_effect = [
            False, True]
        self.assertRaisesRegex(
            ConnectionError,
            'Camera is not connected',
            self.camera.get_acquired_data)

        # 测试相机已连接场景
        self.camera.cam_open.hIdxTUCam = 1
        self.camera.frame = None
        self.camera.attr_trigger = TUCAM_TRIGGER_ATTR()
        # 调用 execute_operation 方法
        self.camera.execute_operation()

        # 验证 execute_operation 方法被成功调用
        self.assertIsNotNone(self.camera.frame)
        mock_logger.assert_called_once_with('Start camera acquisition')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_stop_operation(self, mock_logger):
        '''
        测试停止相机获取，释放相机缓存
        '''
        # 测试相机未连接场景
        self.camera.connection = Mock(spec=CameraControlSystem)
        self.camera.connection.verify_camera_connection.side_effect = [
            False, True]
        self.assertRaisesRegex(
            ConnectionError,
            'Camera is not connected',
            self.camera.get_acquired_data)

        # 测试相机已连接场景
        self.camera.cam_open.hIdxTUCam = 1
        # 调用 stop_operation 方法
        self.camera.stop_operation()

        # 验证 execute_operation 方法被成功调用
        mock_logger.assert_called_once_with('Stop camera acquisition')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_set_acquisition_mode(self, mock_logger):
        '''
        测试设置图像获取模式及其他相关设置
        '''
        # 调用 set_acquisition_mode 方法
        self.camera.set_acquisition_mode(1)

        # 验证 set_acquisition_mode 被成功调用
        self.assertEqual(
            self.camera.attr_trigger.nExpMode,
            TUCAM_TRIGGER_EXP.TUCTE_EXPTM.value)
        self.assertEqual(
            self.camera.attr_trigger.nEdgeMode,
            TUCAM_TRIGGER_EDGE.TUCTD_RISING.value)
        self.assertEqual(self.camera.attr_trigger.nBufFrames, 1)
        mock_logger.assert_called_once_with('Successfully set parameters')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_set_roi(self, mock_logger):
        '''
        测试设置图像获取的ROI区域
        '''
        # 设置ROI参数
        roi_width = 2048
        roi_height = 2048
        # 调用 set_roi 方法
        self.camera.set_roi(0, 0, roi_width, roi_height)

        # 验证 set_roi 是否被成功调用
        self.assertEqual(self.camera.roi_width, roi_width)
        self.assertEqual(self.camera.roi_height, roi_height)
        self.camera.cam_dll.TUCAM_Cap_SetROI.assert_called()
        mock_logger.assert_called_once_with('Successfully set roi')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_set_exposure_time(self, mock_logger):
        '''
        测试设置相机的曝光时间
        '''
        # 设置曝光时间
        exposure_time = 50
        # 调用 set_exposure_time 方法
        self.camera.set_exposure_time(exposure_time)

        # 验证 set_exposure_time 是否被成功调用
        self.camera.cam_dll.TUCAM_Prop_SetValue.assert_called_once()
        mock_logger.assert_called_once_with(
            f'Successfully set exposure time: {exposure_time}')

    @patch('qcos.log.qcos_log.QCOSLogger.info')
    def test_set_temperature(self, mock_logger):
        '''
        测试设置相机的温度
        '''
        # 设置相机温度
        temperature = 50
        # 调用 set_temperature 方法
        self.camera.set_temperature(temperature)

        # 验证 set_temperature 是否被成功调用
        self.camera.cam_dll.TUCAM_Prop_SetValue.assert_called_once()
        mock_logger.assert_called_once_with(
            f'Successfully set temperature: {temperature}')

    @patch('cv2.imread')
    def test_get_status_with_threshold(self, mock_imread):
        '''
        测试根据阈值获取当亲图片中比特的状态
        '''
        # 模拟方法中函数䣌返回
        mock_imread.return_value = np.zeros((100, 100))
        self.camera.qubit_position_list = [(2, 2, 1)]
        # 调用 get_status_with_threshold 方法
        result = self.camera.get_status_with_threshold(
            threshold=100, threshold_block=3, img_path='mock_image_path')

        # 验证 get_status_with_threshold 方法被成功调用
        self.assertEqual(len(result), 1)

    @patch('cv2.imread')
    def test_get_acquired_data(self, mock_imread):
        '''
        测试获取图像并保持功能
        '''
        # 测试相机未连接场景
        self.camera.connection = Mock(spec=CameraControlSystem)
        self.camera.connection.verify_camera_connection.side_effect = [
            False, True]
        self.assertRaisesRegex(
            ConnectionError,
            'Camera is not connected',
            self.camera.get_acquired_data)

        # 测试相机已连接场景
        cam_frformat = TUFRM_FORMATS
        cam_frame = TUCAM_FRAME()
        cam_frame.pBuffer = 0
        cam_frame.ucFormatGet = cam_frformat.TUFRM_FMT_USUAl.value
        cam_frame.uiRsdSize = 1
        self.camera.frame = cam_frame
        self.camera.cam_dll.TUCAM_Buf_WaitForFrame.return_value = True
        # 调用 get_acquired_data 方法
        self.camera.get_acquired_data()

        # 验证 get_acquired_data 方法被成功调用
        self.camera.cam_dll.TUCAM_File_SaveImage.assert_called_once()
        mock_imread.assert_called_once_with(
            f'./image{self.camera.image_idx}.png', flags=0)

    def test_get_exposure_time(self):
        '''
        测试获取相机曝光时间
        '''
        # 调用 get_exposure_time 方法
        self.camera.get_exposure_time()
        # 验证 get_exposure_time 被成功调用
        self.camera.cam_dll.TUCAM_Prop_GetValue.assert_called_once()

    def test_get_temperature(self):
        '''
        测试获取相机温度
        '''
        # 调用 get_temperature 方法
        self.camera.get_temperature()
        # 验证 get_temperature 被成功调用
        self.camera.cam_dll.TUCAM_Prop_GetValue.assert_called_once()

    def test_get_status(self):
        '''
        测试获取相机连接状态
        '''
        self.camera.cam_open.hIdxTUCam = 0
        # 调用 get_temperature 方法
        result = self.camera.get_status()
        # 判断 get_status 被成功调用
        self.assertFalse(result)

    def test_other_func(self):
        '''
        测试暂未用到的接口
        '''
        # 调用相关函数
        self.camera.calibrate()
        self.camera.send_data('mock_data')
        self.camera.receive_data()


if __name__ == '__main__':
    unittest.main()
