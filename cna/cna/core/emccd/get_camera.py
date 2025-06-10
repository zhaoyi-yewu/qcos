from .camera_detection import CameraDetection
import numpy as np
from .functions.auto_detection import find_qubits
from .camera.buffer import create_uint32_buffer
from .camera.TUCam import TUCAM_CAPTURE_MODES
import cv2 as cv


def get_camera_mocker(**kwargs):
    """初始化一个相机，确定比特位置
    """
    camera_detection = CameraDetection()
    exposure_time = kwargs.get('exposure_time', 50)
    camera_detection.set_exposure_time(exposure_time)
    camera_detection.set_acquisition_mode(TUCAM_CAPTURE_MODES.TUCCM_TRIGGER_SOFTWARE.value)
    w_off = kwargs.get('w_off', 912)
    h_off = kwargs.get('h_off', 864)
    w_v = kwargs.get('w_v', 232)
    h_v = kwargs.get('h_v', 232)
    camera_detection.set_roi(w_off, h_off, w_v, h_v)
    camera_detection.capture_image()
    data = np.float32(camera_detection.current_image)
    threshold_block = kwargs.get('threshold_block', 3)
    threshold = kwargs.get('threshold', 100)
    camera_detction.ion_position_list = np.array(find_qubits(data, threshold_block=threshold_block, threshold=threshold))
    camera_detection.camera.calibrate = 0
    return camera_detection


def get_real_camera(dll_path, init_path, calib_img_path, **kwargs):
    """初始化一个真实相机
    Args:
        dll_path: dll文件路径
        init_path: 相机初始化文件所在目录
        calib_img_path: 校准图片的路径
    """
    camera_detection = CameraDetection(dll_path=dll_path, init_path=init_path)
    # exposure_time = kwargs.get('exposure_time', 50)
    # camera_detection.set_exposure_time(exposure_time) #ms
    camera_detection.set_acquisition_mode(TUCAM_CAPTURE_MODES.TUCCM_TRIGGER_STANDARD.value)
    w_off = kwargs.get('w_off', 912)
    h_off = kwargs.get('h_off', 875)
    w_v = kwargs.get('w_v', 232)
    h_v = kwargs.get('h_v', 232)
    camera_detection.set_roi(w_off, h_off, w_v, h_v)
    img = cv.imread(calib_img_path, flags=0)
    threshold_block = kwargs.get('threshold_block', 3)
    threshold = kwargs.get('threshold', 100)
    camera_detection.ion_position_list = np.array(find_qubits(img, threshold_block=threshold_block, threshold=threshold))
    return camera_detection
