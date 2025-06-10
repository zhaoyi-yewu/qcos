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
import json

import numpy as np
import cv2
import os
import ctypes
from typing import Any, Dict, List
from qcos.cna.core.emccd.camera.TUCam import \
    (TUCAM_INIT, TUCAM_OPEN, TUCAM_CAPTURE_MODES,
     TUFRM_FORMATS, TUCAM_IDPROP, TUCAM_FRAME,
     TUCAM_TRIGGER_EXP, TUCAM_TRIGGER_ATTR, TUCAM_TRIGGER_EDGE,
     TUCAM_ROI_ATTR, TUCAM_IDCROI,
     TUCAM_PROP_ATTR, TUCAM_FILE_SAVE, TUIMG_FORMATS)
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    hardware_interfaces.quantum_hardware_interface import \
    QuantumHardwareInterface
from qcos.\
    quantum_heterogeneous_hw_unified_and_management_engine.\
    control_systems.camera_control_system import \
    CameraControlSystem
from qcos.config.qcos_config_manager import qcos_configer
from qcos.log.qcos_log import QCOSLogger

qcos_logger = QCOSLogger()


class CameraInterface(QuantumHardwareInterface):
    '''
    相机接口类
    '''

    def __init__(self):
        '''
        初始化相机接口
        '''
        self.connection = None
        self.status = 'Disconnected'

        # 相机动态链接库解析
        if os.name == 'nt':
            # Windows环境
            self.cam_dll = ctypes.OleDLL(qcos_configer.get_camera_dll_path())
        else:
            # Linux环境
            self.cam_dll = ctypes.CDLL(qcos_configer.get_camera_dll_path())
        # 相机SDK路径
        self.sdk_path = qcos_configer.get_camera_init_path()
        # 初始化SDK环境参数
        self.cam_int = TUCAM_INIT(0, self.sdk_path.encode('utf-8'))
        # 打开相机参数
        self.cam_open = TUCAM_OPEN(0, 0)
        # 初始化帧采集和控制相机
        self.cam_dll.TUCAM_Api_Init(ctypes.pointer(self.cam_int))
        self.frame = None
        self.buffer = None
        self.image_idx = 0
        self.current_image = None
        # 相机触发属性，包括触发模式、曝光模式等
        self.attr_trigger = None
        self.qubit_position_list = None
        self.total_width = qcos_configer.get_total_width()
        self.total_height = qcos_configer.get_total_height()
        self.width_offset = qcos_configer.get_width_offset()
        self.height_offset = qcos_configer.get_height_offset()
        self.roi_width = qcos_configer.get_roi_width()
        self.roi_height = qcos_configer.get_roi_height()
        self.image_size = self.roi_width * self.roi_height
        self.threshold_block = qcos_configer.get_measure_threshold_block()
        self.threshold = qcos_configer.get_measure_threshold()

    def initialize(self):
        '''
        初始化相机接口
        '''
        # 设置相机获取模式为标准模式
        self.set_acquisition_mode(
            TUCAM_CAPTURE_MODES.TUCCM_TRIGGER_STANDARD.value)
        # 设置相机成像的ROI区域
        self.set_roi(
            self.width_offset, self.height_offset,
            self.roi_width, self.roi_height)
        calib_image = cv2.imread(qcos_configer.get_calib_img_path(), flags=0)
        # 原子位置解析结果，包含(x, y, radius)
        self.qubit_position_list = np.array(self.find_qubits(calib_image))
        # 记录初始化信息
        qcos_logger.info('Initialized Camera interface')

    def connect(self, cam_idx: int = 0):
        '''
        连接相机

        参数:
        cam_idx (int): 用于与真实相机匹配
        '''
        # 未物理连接相机时，uiCamCount为0; 正常连接相机时，uiCamCount为1
        if cam_idx >= self.cam_int.uiCamCount:
            raise ConnectionError(
                f'There is {self.cam_int.uiCamCount} '
                f'camera, can not find camera {cam_idx}')
        self.cam_open = TUCAM_OPEN(cam_idx, 0)
        # 打开相机，让相机处于工作模式
        self.cam_dll.TUCAM_Dev_Open(ctypes.pointer(self.cam_open))
        if self.cam_open.hIdxTUCam == 0:
            qcos_logger.error('Failed to open camera')
            raise ConnectionError('Open the camera failure!')
        # 初始化相机控制系统
        self.connection = CameraControlSystem('camera')
        self.connection.connect()
        if self.connection.verify_camera_connection(self.cam_open.hIdxTUCam):
            self.status = 'Connected'
            qcos_logger.info('Successfully connected to camera')
        else:
            qcos_logger.error('Failed to verify camera')
            raise ConnectionError('Failed to verify camera')

    def disconnect(self):
        '''
        断开相机连接
        '''
        if self.connection.verify_camera_connection(self.cam_open.hIdxTUCam):
            # 获取已打开相机的句柄
            cam_idx = ctypes.c_int64(self.cam_open.hIdxTUCam)
            # 关闭相机
            self.cam_dll.TUCAM_Dev_Close(cam_idx)
            self.connection.disconnect()
        self.status = 'Disconnected'
        qcos_logger.info('Disconnected from camera')

    def adjust_position(self, position_list, axes=0, interval=10):
        '''
        调整比特位置

        参数:
            position_list (_type_): 比特位置列表
            axes (int, optional): 将比特位置按指定排序的轴axes排序，x轴为0， y轴为1
            interval (int, optional): 相邻两个坐标差，一般x轴相差10以上，y轴相差5以上
        返回：
            np.array(new_position_list)(np.ndarray): 调整后的量子比特位置列表
        '''
        position_list.sort(key=lambda e: e[axes])
        new_position_list = []
        # 当前组起始索引
        start_index = 0
        # 末尾添加最后一个组的结束标志
        position_list.append([2048, 2048, 0])
        for i in range(1, len(position_list)):
            if abs(position_list[i][axes] -
                   position_list[start_index][axes]) > interval:
                tmp = position_list[start_index:i]
                tmp.sort(key=lambda e: e[1 - axes])
                new_position_list += tmp
                start_index = i
        # 返回调整后的量子比特位置列表
        return np.array(new_position_list)

    def find_qubits(self, img_data):
        '''
        在给定的图像数据中寻找离子
        对图像应用中值模糊，然后，在二值化图像中搜索光斑块，
        如果一个块包含的亮像素超过某个特定数量，则被认为是一个离子，计算其中心和半径

        参数:
            img_data（np.array）：图像的数据，数据类型必须是np.float32
        返回:
            circles (list): 元组列表，每个元组代表一个检测到的离子，
            元组元素是离子中心的x和y坐标，以及离子半径
        '''
        row, col = img_data.shape
        if self.threshold is None:
            # 中值模糊
            median = cv2.medianBlur(img_data, 5)
            median = np.array(median, dtype='int')
            row, col = median.shape

            # 图像数据展平并排序
            median_1d = median.reshape(row * col)
            median_1d = np.sort(median_1d)

            # 分割直方图
            min_value, max_value = median_1d[10], median_1d[-10]
            higher = median_1d[np.where(median_1d >
                                        (min_value + max_value) / 2)]
            lower = median_1d[np.where(median_1d <=
                                       (min_value + max_value) / 2)]

            # 计算直方图寻找峰值，并计算峰值的中心
            hist_high, bins_high = np.histogram(a=higher, bins=21)
            hist_low, bins_low = np.histogram(a=lower, bins=21)
            max_index_high = np.argmax(hist_high)
            max_index_low = np.argmax(hist_low)
            max_low = (bins_low[max_index_low]
                       + bins_low[max_index_low + 1]) / 2
            max_high = (bins_high[max_index_high]
                        + bins_high[max_index_high + 1]) / 2
            self.threshold = (max_low + max_high) / 2

        # 得到threshold之后，做二值化处理
        bin_data = np.zeros((row, col), dtype='int')
        bin_data[np.where(img_data > self.threshold)] = 1

        # 在二值化图像数据中搜索并识别出亮块
        bin_data_row, bin_data_col = bin_data.shape
        # 标记已访问
        visited_flag = np.zeros(
            shape=(
                bin_data_row,
                bin_data_col),
            dtype='int')
        # 存储检测到的亮块
        light_blocks = []
        for i in range(bin_data_row):
            for j in range(bin_data_col):
                if (not visited_flag[i, j]) and bin_data[i, j]:
                    queue = [(i, j)]
                    l = 0
                    visited_flag[i, j] = 1
                    x, y = i, j
                    while l < len(queue):
                        x, y = queue[l]
                        # 检查当前像素点周围的8个像素点
                        for dx in range(-1, 2):
                            for dy in range(-1, 2):
                                if (dx, dy) != (0, 0):
                                    # 相邻像素点
                                    x2 = x + dx
                                    y2 = y + dy
                                    if (0 <= x2 < bin_data_row and
                                            0 <= y2 < bin_data_col):
                                        if ((not visited_flag[x2, y2])
                                                and bin_data[x2, y2]):
                                            queue.append((x2, y2))
                                            visited_flag[x2, y2] = 1
                        l += 1
                    light_blocks.append(tuple(queue))

        circles = []
        for block in light_blocks:
            if len(block) > self.threshold_block:
                # find a circle!
                sum_xy = np.sum(np.array(block), 0)
                # 圆心
                avrg_x = sum_xy[0] / len(block)
                avrg_y = sum_xy[1] / len(block)
                # 半径
                r = 0
                for x, y in block:
                    if (x - avrg_x) ** 2 + (y - avrg_y) ** 2 > r ** 2:
                        r = ((x - avrg_x) ** 2 + (y - avrg_y) ** 2) ** 0.5
                if r < min(row, col) / 3:
                    circles.append((avrg_x, avrg_y, r))

        return self.adjust_position(circles)

    def capture_image(self, img_name=None):
        '''
        获取一张图像，保存到current_image中

        参数:
        img_name (str): 图像保存路径
        '''
        if not self.connection.verify_camera_connection(
                self.cam_open.hIdxTUCam):
            self.status = 'Disconnected'
            qcos_logger.error('Camera is not connected')
            raise ConnectionError('Camera is not connected')
        # 获取一张图像
        self.get_acquired_data(img_name)
        self.image_idx += 1

    def execute_operation(self):
        '''
        初始化相机，开始相机获取
        '''
        if not self.connection.verify_camera_connection(
                self.cam_open.hIdxTUCam):
            self.status = 'Disconnected'
            qcos_logger.error('Camera is not connected')
            raise ConnectionError('Camera is not connected')
        self.image_idx = 0
        if self.frame is None:
            # 设置图像帧的参数
            cam_frformat = TUFRM_FORMATS
            cam_frame = TUCAM_FRAME()
            cam_frame.pBuffer = 0
            cam_frame.ucFormatGet = cam_frformat.TUFRM_FMT_USUAl.value
            cam_frame.uiRsdSize = 1
            self.frame = cam_frame
        # 获取已打开相机的句柄
        cam_idx = ctypes.c_int64(self.cam_open.hIdxTUCam)
        attr_trigger = self.attr_trigger
        # 获取触发的属性
        self.cam_dll.TUCAM_Cap_GetTrigger(
            cam_idx, ctypes.pointer(attr_trigger))
        # 分配内存空间
        self.cam_dll.TUCAM_Buf_Alloc(cam_idx, ctypes.pointer(self.frame))
        # 开始捕获图像数据
        self.cam_dll.TUCAM_Cap_Start(cam_idx, attr_trigger.nTgrMode)
        qcos_logger.info('Start camera acquisition')

    def stop_operation(self):
        '''
        停止相机获取，释放相机缓存
        '''
        if not self.connection.verify_camera_connection(
                self.cam_open.hIdxTUCam):
            self.status = 'Disconnected'
            qcos_logger.error('Camera is not connected')
            raise ConnectionError('Camera is not connected')
        # 获取已打开相机的句柄
        cam_idx = ctypes.c_int64(self.cam_open.hIdxTUCam)
        # 中断等待捕获图像数据
        self.cam_dll.TUCAM_Buf_AbortWait(cam_idx)
        # 停止图像数据捕获
        self.cam_dll.TUCAM_Cap_Stop(cam_idx)
        # 释放相机缓存
        self.cam_dll.TUCAM_Buf_Release(cam_idx)
        qcos_logger.info('Stop camera acquisition')

    def set_acquisition_mode(self, mode):
        '''
        设置图像获取模式及其他相关设置

        参数:
        mode (Any): 图像获取模式
        '''
        cam_idx = ctypes.c_int64(self.cam_open.hIdxTUCam)
        attr_trigger = TUCAM_TRIGGER_ATTR()
        # 获取并修改触发属性
        self.cam_dll.TUCAM_Cap_GetTrigger(
            cam_idx, ctypes.pointer(attr_trigger))
        attr_trigger.nTgrMode = ctypes.c_int32(mode)
        attr_trigger.nExpMode = (
            TUCAM_TRIGGER_EXP.TUCTE_EXPTM.value)  # 以设置的曝光时间作为曝光时间
        attr_trigger.nEdgeMode = TUCAM_TRIGGER_EDGE.TUCTD_RISING.value  # 上升沿触发
        attr_trigger.nBufFrames = 1
        # 设置修改后的触发属性
        self.cam_dll.TUCAM_Cap_SetTrigger(cam_idx, attr_trigger)
        self.attr_trigger = attr_trigger
        qcos_logger.info('Successfully set parameters')

    def set_roi(
            self, width_offset, height_offset, roi_width, roi_height):
        '''
        设置图像获取的ROI区域

        参数:
        width_offset (int): ROI区域左上角的w值
        height_offset (int): ROI区域左上角的h值
        roi_width (int): ROI区域的w值
        roi_height (int): ROI区域的h值
        '''
        self.roi_width = roi_width
        self.roi_height = roi_height
        self.image_size = self.roi_width * self.roi_height
        # roi_width 和 roi_height 必须为4的倍数
        cam_idx = ctypes.c_int64(self.cam_open.hIdxTUCam)
        cam_roi = TUCAM_ROI_ATTR()
        cam_roi.bEnable = 1
        cam_roi.idCalc = TUCAM_IDCROI.TUIDCR_WBALANCE.value
        cam_roi.nHOffset = ctypes.c_int32(width_offset)
        cam_roi.nVOffset = ctypes.c_int32(height_offset)
        cam_roi.nWidth = ctypes.c_int32(roi_width)
        cam_roi.nHeight = ctypes.c_int32(roi_width)
        self.cam_dll.TUCAM_Cap_SetROI(cam_idx, cam_roi)
        qcos_logger.info('Successfully set roi')

    def set_exposure_time(self, exposure_time):
        '''
        设置相机曝光时间

        参数:
        exposure_time (float): 曝光时间，单位为ms
        '''
        cam_idx = ctypes.c_int64(self.cam_open.hIdxTUCam)
        cam_prop = TUCAM_PROP_ATTR()
        cam_prop.idProp = TUCAM_IDPROP.TUIDP_EXPOSURETM.value
        cam_prop.nIdxChn = 0
        self.cam_dll.TUCAM_Prop_SetValue(
            cam_idx, cam_prop.idProp, ctypes.c_double(exposure_time), 0)
        qcos_logger.info(f'Successfully set exposure time: {exposure_time}')

    def set_temperature(self, temperature):
        '''
        设置相机温度

        参数:
        temperature (float): 相机温度，单位为°
        '''
        cam_idx = ctypes.c_int64(self.cam_open.hIdxTUCam)
        cam_prop = TUCAM_PROP_ATTR()
        cam_prop.idProp = TUCAM_IDPROP.TUIDP_TEMPERATURE.value
        cam_prop.nIdxChn = 0
        self.cam_dll.TUCAM_Prop_SetValue(
            cam_idx, cam_prop.idProp, ctypes.c_double(temperature), 0)
        qcos_logger.info(f'Successfully set temperature: {temperature}')

    def get_status_with_threshold(
            self, threshold: float, threshold_block=3, img_path=None):
        '''
        根据阈值获取当前图片中比特的状态

        参数:
        threshold (float): 灰度阈值
        threshold_block (int): 像素数阈值
        img_name (str): 图像路径
        '''
        image = self.current_image
        if img_path is not None:
            image = cv2.imread(img_path, flags=0)
        results = []
        # 解析图像中原子位置的灰度并与阈值判断以得到原子测量结果
        for x, y, size in self.qubit_position_list:
            qubit_image = image[
                int(max(0, x - size)): int(x + size) + 1,
                int(max(0, y - size)): int(y + size) + 1]
            greyness = qubit_image.flatten().tolist()
            greyness.sort(reverse=True)
            greyness = greyness[:threshold_block]
            average_grey = sum(greyness) / len(greyness)
            results.append(1 if average_grey > threshold else 0)
        return results

    def get_acquired_data(self, img_name=None):
        '''
        获取图像并保存

        参数:
        img_name (str): 图像保存路径
        '''
        if not self.connection.verify_camera_connection(
                self.cam_open.hIdxTUCam):
            self.status = 'Disconnected'
            qcos_logger.error('Camera is not connected')
            raise ConnectionError('Camera is not connected')
        try:
            if img_name is None:
                img_name = f'./image{self.image_idx}'
            cam_idx = ctypes.c_int64(self.cam_open.hIdxTUCam)
            cam_frame = self.frame
            # 等待捕获图像数据，等待时间为100s
            self.cam_dll.TUCAM_Buf_WaitForFrame(
                cam_idx, ctypes.pointer(cam_frame), 100000)
            # 保存图片到本地
            cam_file_save = TUCAM_FILE_SAVE()
            cam_file_save.pFrame = ctypes.pointer(cam_frame)
            cam_format = TUIMG_FORMATS
            cam_file_save.nSaveFmt = ctypes.c_int32(
                cam_format.TUFMT_PNG.value)
            cam_file_save.pstrSavePath = ctypes.c_char_p(
                img_name.encode('utf-8'))
            self.cam_dll.TUCAM_File_SaveImage(cam_idx, cam_file_save)
            self.current_image = cv2.imread(f'{img_name}.png', flags=0)
            qcos_logger.info(f'Save the image data success, '
                             f'the path is {img_name}')
        except BaseException:
            qcos_logger.error('Image capture failed')
            raise RuntimeError('Image capture failed')

    def get_exposure_time(self) -> float:
        '''
        获取相机曝光时间

        返回:
        float: 曝光时间，单位为ms
        '''
        cam_idx = ctypes.c_int64(self.cam_open.hIdxTUCam)
        exposure_time = ctypes.c_double(0)
        self.cam_dll.TUCAM_Prop_GetValue(
            cam_idx, TUCAM_IDPROP.TUIDP_EXPOSURETM.value,
            ctypes.pointer(exposure_time), 0)
        return exposure_time

    def get_temperature(self) -> float:
        '''
        获取相机温度

        返回:
        float: 相机温度，单位为°
        '''
        cam_idx = ctypes.c_int64(self.cam_open.hIdxTUCam)
        temperature = ctypes.c_double(0)
        self.cam_dll.TUCAM_Prop_GetValue(
            cam_idx, TUCAM_IDPROP.TUIDP_TEMPERATURE.value,
            ctypes.pointer(temperature), 0)
        return temperature

    def get_status(self) -> bool:
        '''
        获取相机连接状态

        返回:
        bool: 相机连接状态信息
        '''
        if self.cam_open.hIdxTUCam == 0:
            self.status = 'Disconnected'
            return False
        return True

    def calibrate(self):
        '''
        校准硬件
        '''
        pass

    def send_data(self, data: Any):
        '''
        发送数据

        参数:
        data (Any): 要发送的数据
        '''
        pass

    def receive_data(self) -> Any:
        '''
        接收数据

        返回:
        Any: 接收到的数据
        '''
        pass
