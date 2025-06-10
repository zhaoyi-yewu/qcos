import ctypes
import os
import typing
from .TUCam import *
from .camera import EmccdCamera
import numpy as np
import cv2 as cv


class TucamDLL():

    def __init__(self, dll_path, init_path='./'):
        self.dll = ctypes.OleDLL(dll_path)
        self.Path = init_path
        self.TUCAMINIT = TUCAM_INIT(0, self.Path.encode('utf-8'))
        self.TUCAMOPEN = TUCAM_OPEN(0, 0)
        self.dll.TUCAM_Api_Init(pointer(self.TUCAMINIT))
        self.frame = None
        print(self.TUCAMINIT.uiCamCount)
        print(self.TUCAMINIT.pstrConfigPath)
        print('Connect %d camera' % self.TUCAMINIT.uiCamCount)

    def OpenCamera(self, Idx):

        if Idx >= self.TUCAMINIT.uiCamCount:
            raise ConnectionError(f"There is {self.TUCAMINIT.uiCamCount} camera, can not find camera {Idx}")

        self.TUCAMOPEN = TUCAM_OPEN(Idx, 0)

        self.dll.TUCAM_Dev_Open(pointer(self.TUCAMOPEN))

        if 0 == self.TUCAMOPEN.hIdxTUCam:
            raise ConnectionError('Open the camera failure!')
        else:
            print('Open the camera success!')

    def CloseCamera(self):
        if 0 != self.TUCAMOPEN.hIdxTUCam:
            hIdxTUCam = c_int64(self.TUCAMOPEN.hIdxTUCam)
            self.dll.TUCAM_Dev_Close(hIdxTUCam)
        print('Close the camera success')

    def SetTemperature(self, temp):
        hIdxTUCam = c_int64(self.TUCAMOPEN.hIdxTUCam)
        m_prop = TUCAM_PROP_ATTR()
        m_prop.idProp = TUCAM_IDPROP.TUIDP_TEMPERATURE.value
        m_prop.nIdxChn = 0
        self.dll.TUCAM_Prop_SetValue(hIdxTUCam, m_prop.idProp, c_double(temp), 0)
        print("PropID=", m_prop.idProp, "Set default value ", temp)
        print("Set Temperature success")

    def GetTemperature(self):
        hIdxTUCam = c_int64(self.TUCAMOPEN.hIdxTUCam)
        value = c_double(0)
        self.dll.TUCAM_Prop_GetValue(hIdxTUCam, TUCAM_IDPROP.TUIDP_TEMPERATURE.value, pointer(value), 0)
        return value

    def SetExposureTime(self, time):
        hIdxTUCam = c_int64(self.TUCAMOPEN.hIdxTUCam)
        m_prop = TUCAM_PROP_ATTR()
        m_prop.idProp = TUCAM_IDPROP.TUIDP_EXPOSURETM.value
        m_prop.nIdxChn = 0
        self.dll.TUCAM_Prop_SetValue(hIdxTUCam, m_prop.idProp, c_double(time), 0)
        print("PropID=", m_prop.idProp, "Set default value ", time)
        print("Set Exposure Time success")

    def GetExposureTime(self):
        hIdxTUCam = c_int64(self.TUCAMOPEN.hIdxTUCam)
        value = c_double(0)
        self.dll.TUCAM_Prop_GetValue(hIdxTUCam, TUCAM_IDPROP.TUIDP_EXPOSURETM.value, pointer(value), 0)
        return value

    def SetTriggerMode(self, mode):
        hIdxTUCam = c_int64(self.TUCAMOPEN.hIdxTUCam)
        m_tgr = TUCAM_TRIGGER_ATTR()
        self.dll.TUCAM_Cap_GetTrigger(hIdxTUCam, pointer(m_tgr))
        m_tgr.nTgrMode = c_int32(mode)
        m_tgr.nExpMode = TUCAM_TRIGGER_EXP.TUCTE_EXPTM.value  # 以设置的曝光时间作为曝光时间
        m_tgr.nEdgeMode = TUCAM_TRIGGER_EDGE.TUCTD_RISING.value  # 上升沿触发
        m_tgr.nBufFrames = 1
        self.dll.TUCAM_Cap_SetTrigger(hIdxTUCam, m_tgr)
        self.m_tgr = m_tgr
        print("Set mode success")

    def SetROI(self, w_off, h_off, w_v, h_v):
        # w_v 和 h_v 不能随便设置，必须为4的倍数
        hIdxTUCam = c_int64(self.TUCAMOPEN.hIdxTUCam)
        roi = TUCAM_ROI_ATTR()
        roi.bEnable = 1
        roi.idCalc = TUCAM_IDCROI.TUIDCR_WBALANCE.value
        roi.nHOffset = c_int32(w_off)
        roi.nVOffset = c_int32(h_off)
        roi.nWidth = c_int32(w_v)
        roi.nHeight = c_int32(h_v)
        self.dll.TUCAM_Cap_SetROI(hIdxTUCam, roi)
        print("Set roi success")

    def StartAcquisition(self):
        if self.frame is None:
            m_frformat = TUFRM_FORMATS
            m_frame = TUCAM_FRAME()
            m_frame.pBuffer = 0
            m_frame.ucFormatGet = m_frformat.TUFRM_FMT_USUAl.value
            m_frame.uiRsdSize = 1
            self.frame = m_frame

        hIdxTUCam = c_int64(self.TUCAMOPEN.hIdxTUCam)
        m_tgr = self.m_tgr  # TUCAM_TRIGGER_ATTR()
        self.dll.TUCAM_Cap_GetTrigger(hIdxTUCam, pointer(m_tgr))
        self.dll.TUCAM_Buf_Alloc(hIdxTUCam, pointer(self.frame))
        self.dll.TUCAM_Cap_Start(hIdxTUCam, m_tgr.nTgrMode)
        print("StartAcquisition success")

    def GetAcquiredData(self, img_name):
        # example: [./test]    不能有后缀格式
        hIdxTUCam = c_int64(self.TUCAMOPEN.hIdxTUCam)
        m_frame = self.frame
        try:
            # self.dll.TUCAM_Cap_DoSoftwareTrigger(hIdxTUCam)
            result = self.dll.TUCAM_Buf_WaitForFrame(hIdxTUCam, pointer(m_frame), 100000)
            print(
                "Grab the software trigger frame success, width:%d, height:%#d, channel:%#d, elembytes:%#d, image size:%#d" % (
                m_frame.usWidth, m_frame.usHeight, m_frame.ucChannels,
                m_frame.ucElemBytes, m_frame.uiImgSize))
            # 保存图片到本地
            m_fs = TUCAM_FILE_SAVE()
            m_fs.pFrame = pointer(m_frame)
            m_format = TUIMG_FORMATS
            m_fs.nSaveFmt = c_int32(m_format.TUFMT_PNG.value)
            m_fs.pstrSavePath = c_char_p(img_name.encode('utf-8'))
            print("saving image...")
            code = self.dll.TUCAM_File_SaveImage(hIdxTUCam, m_fs)
            print('Save the image data success, the path is %#s' % img_name)
        except Exception as e:
            print(str(e))
            print('Grab the software trigger frame failure')

    def AbortAcquisition(self):
        hIdxTUCam = c_int64(self.TUCAMOPEN.hIdxTUCam)
        self.dll.TUCAM_Buf_AbortWait(hIdxTUCam)
        self.dll.TUCAM_Cap_Stop(hIdxTUCam)
        self.dll.TUCAM_Buf_Release(hIdxTUCam)


class EmccdCameraByDll(EmccdCamera):
    @classmethod
    def from_path(cls, dll_path, init_path='./'):
        dll = TucamDLL(dll_path, init_path)
        return EmccdCameraByDll(dll)

    def __init__(self, dll):
        # noinspection PyTypeChecker
        self._dll = dll
        self.w = self.h = 2048
        self.i = 0
        super().__init__()

    @property
    def dll(self):
        return self._dll

    # lifecycle

    def _initialize(self):
        self._dll.OpenCamera(0)

    def _shutdown(self):
        self._dll.CloseCamera()

    # temperature

    def set_temperature(self, temperature: int):
        self._dll.SetTemperature(temperature)

    def get_temperature(self) -> float:
        return self._dll.GetTemperature()

    def set_acquisition_mode(self):
        pass

    def set_exposure_time(self, time: float):
        self._dll.SetExposureTime(time)

    def set_roi(self, w_off, h_off, w_v, h_v):
        self._dll.SetROI(w_off, h_off, w_v, h_v)
        self.w = w_v
        self.h = h_v

    # acquisition control

    def start_acquisition(self):
        self.i = 0
        self._dll.StartAcquisition()

    def abort_acquisition(self):
        self._dll.AbortAcquisition()

    def get_acquired_data(self, size: int, buffer: typing.Union[ctypes.POINTER, ctypes.Array], img_name=None):
        try:
            if img_name is None:
                img_name = f'./image{self.i}'
            self._dll.GetAcquiredData(img_name)
            img = cv.imread(f'{img_name}.png', flags=0)
            buffer = np.frombuffer(buffer, dtype=np.uint32).reshape((self.w, self.h))
            buffer[:, :] = img.astype(np.int32)
            self.i += 1
        except:
            raise RuntimeError("获取图像失败")

    def get_latest_image(self, size: int, buffer: typing.Union[ctypes.POINTER, ctypes.Array]):
        pass
