import json

import cv2
import numpy as np
import os
import shutil
import time
from qcos.cna.core.instrument.ni import NI
from qcos.cna.core.instrument.instrument_base import InstrumentBase
from qcos.cna.core.emccd.camera.TUCam import TUCAM_CAPTURE_MODES
from qcos.cna.core.emccd.camera.camera_dll import TucamDLL
from qcos.config.qcos_config_manager import qcos_configer
from qcos.log.qcos_log import QCOSLogger

qcos_logger = QCOSLogger()


def in_interval(a, l, r):
    if (a >= l) and (a <= r):
        return True
    else:
        return False


def search_light_blocks(bin_data):
    n, m = bin_data.shape
    flag_grid = np.zeros((n, m), dtype='int')
    light_blocks = []
    for i in range(n):
        for j in range(m):
            if (not flag_grid[i, j]) and bin_data[i, j]:
                queue = [(i, j)]
                l = 0
                flag_grid[i, j] = 1
                x, y = i, j
                while l < len(queue):
                    x, y = queue[l]
                    for dx in range(-1, 2):
                        for dy in range(-1, 2):
                            if (dx, dy) != (0, 0):
                                x2 = x + dx
                                y2 = y + dy
                                if in_interval(x2, 0, n - 1) and in_interval(y2, 0, m - 1):
                                    if (not flag_grid[x2, y2]) and bin_data[x2, y2]:
                                        queue.append((x2, y2))
                                        flag_grid[x2, y2] = 1
                    l += 1

                light_blocks.append(tuple(queue))
    return light_blocks


def find_qubits(data, threshold_block=12, threshold=None):
    """
    This function is used to find ions in a given image data.

    The function applies a median blur to the image and calculates a threshold for binarization.
    Then, it searches for light blocks in the binarized image, and checks each light block.
    If a block contains more than a certain number of bright pixels, it is considered an ion and its center and radius are calculated.

    Parameters:

    data: np.array
        The input image data as a numpy array. It should be either grayscale (single-channel) or BGR (three-channel).
        The data type of the image MUST be np.float32.

    threshold_block: int, optional
        The minimum number of bright pixels that should be present in a block for it to be considered an ion.
        It is used to differentiate between noise points and light spots in the image.
        The default value is 12, meaning any block with more than 12 bright pixels will be considered as an ion.

    Returns:

    circles: list of tuples
        Each tuple represents a detected ion, where the first two elements are the x and y coordinates of the ion's center,
        and the third element is the calculated radius of the ion.
    """
    n, m = data.shape
    if threshold is None:
        median = cv2.medianBlur(data, 5)
        median = np.array(median, dtype='int')
        n, m = median.shape
        median_1D = median.reshape(n * m)

        median_1D = np.sort(median_1D)

        valley, peak = median_1D[10], median_1D[-10]

        truncate_high = median_1D[np.where(median_1D > (valley + peak) / 2)]
        truncate_low = median_1D[np.where(median_1D <= (valley + peak) / 2)]

        hist_low, bins_low = np.histogram(a=truncate_low, bins=21)
        hist_high, bins_high = np.histogram(a=truncate_high, bins=21)

        max_index_low = np.argmax(hist_low)
        max_index_high = np.argmax(hist_high)
        max_low = (bins_low[max_index_low] + bins_low[max_index_low + 1]) / 2
        max_high = (bins_high[max_index_high] + bins_high[max_index_high + 1]) / 2
        threshold = (max_low + max_high) / 2
    # print("binaryzation threshold = ", threshold)
    # print(hist_high)
    # 得到threshold之后，做二值化处理(binarization)
    bin_data = np.zeros((n, m), dtype='int')
    bin_data[np.where(data > threshold)] = 1

    light_blocks = search_light_blocks(bin_data)

    circles = []
    for block in light_blocks:
        if len(block) > threshold_block:
            # we find a circle!
            sum_xy = np.sum(np.array(block), 0)
            avrg_x = sum_xy[0] / len(block)
            avrg_y = sum_xy[1] / len(block)
            r = 0
            for x, y in block:
                if (x - avrg_x) ** 2 + (y - avrg_y) ** 2 > r ** 2:
                    r = ((x - avrg_x) ** 2 + (y - avrg_y) ** 2) ** 0.5
            if r < min(n, m) / 3:
                circles.append((avrg_x, avrg_y, r))
    # print(len(circles))
    # print(circles)
    return adjust_position(circles)


def adjust_position(ion_list, axes=0, interval=10):
    """调整比特位置，

    Args:
        ion_list (_type_): 比特位置列表
        axes (int, optional): 将比特位置按axes排序，x为0， y为1
        interval (int, optional): 相邻两个坐标差，一般x轴相差10以上，y轴相差5以上
    """
    ion_list.sort(key=lambda e: e[axes])
    new_position_list = []
    l = 0
    ion_list.append([2048, 2048, 0])
    for i in range(1, len(ion_list)):
        if abs(ion_list[i][axes] - ion_list[l][axes]) > interval:
            tmp = ion_list[l:i]
            tmp.sort(key=lambda e: e[1 - axes])
            new_position_list += tmp
            l = i
    return np.array(new_position_list)


def get_position(positions, axes, interval):
    """获取某一个轴上的所有坐标

    Args:
        positions (_type_): 比特位置列表
        axes (_type_): 坐标轴，0为x, 1为y
        interval (_type_): 相邻两个坐标差，一般x轴相差10以上，y轴相差5以上
    """
    position_list = positions.copy()
    position_list = adjust_position(position_list, axes=axes, interval=interval)
    p_list = []
    v, cnt = 0, 0
    for i in range(len(position_list) - 1):
        v += position_list[i][axes]
        cnt += 1
        if abs(position_list[i + 1][axes] - position_list[i][axes]) > interval:
            p_list.append(v / cnt)
            cnt = 0
            v = 0
    p_list.append(v / cnt)
    return p_list


def get_all_qubits_png(src_img_path=None, calib_img_path=qcos_configer.get_calib_img_path(),
                       threshold_block=qcos_configer.get_measure_threshold_block(),
                       threshold=qcos_configer.get_measure_threshold(), x_interval=10, y_interval=10):
    """从多张原子图片拼出完整的原子阵列

    Args:
        src_img_path (_type_): 图片路径
        calib_img_path (_type_): 需要保存的完整阵列图片位置
        threshold_block (int): 判断量子比特的有效像素点个数
        threshold (int): 量子比特状态的亮态阈值
        x_interval (int): 相邻量子比特的x轴差值
        y_interval (int): 相邻量子比特的y轴差值
    """

    # 拼接图片
    roi_width = qcos_configer.get_roi_width()
    roi_height = qcos_configer.get_roi_height()
    img_data = np.zeros((roi_width, roi_height))
    cnt = np.zeros((roi_width, roi_height))
    if not src_img_path:
        try:
            get_multiple_img()
        except Exception as e:
            qcos_logger.error(f"原子成像获取失败：{e}")
            return
        src_img_path = './image'
    for file in os.listdir(src_img_path):
        img = cv2.imread(f"{src_img_path}/{file}", flags=0)
        cnt += np.where(img > 80, 1, 0)
        img_data += np.where(img > 80, img, 0)
    for i in range(roi_width):
        for j in range(roi_height):
            if cnt[i][j] > 0:
                img_data[i][j] //= cnt[i][j]
    # 识别比特点位
    try:
        position_list = find_qubits(img_data, threshold_block=threshold_block, threshold=threshold).tolist()
        if len(position_list) != qcos_configer.get_qubit_number():
            # 寻找x坐标
            x_list = get_position(position_list, 0, x_interval)
            # 寻找y坐标
            y_list = get_position(position_list, 1, y_interval)
            qubit = [[0, 0, 151, 0, 0],
                     [0, 155, 243, 238, 113],
                     [0, 202, 249, 249, 139],
                     [0, 109, 198, 202, 125],
                     [0, 0, 94, 0, 0]]
            x_list.sort()
            y_list.sort()
            # 补齐比特
            q_index = 0
            for x in x_list:
                for y in y_list:
                    if abs(position_list[q_index][0] - x) > x_interval or abs(position_list[q_index][1] - y) > y_interval:
                        img_data[int(x - 2):int(x + 3), int(y - 2):int(y + 3)] = qubit
                    else:
                        q_index += 1
    except Exception as e:
        qcos_logger.error(f"原子阵列图像生成失败：{e}")
    else:
        cv2.imwrite(calib_img_path, img_data)
        qcos_logger.debug(f"原子阵列图像已保存在{calib_img_path}下")


def get_multiple_img(repeat: int = 30, img_path: str = './image'):
    """
    多次装载采集多张原子图像以用于拼出完整的原子阵列

    Args:
        repeat (int): 采集原子图像数量
        img_path (str): 图像保存目录
    """

    # 初始化相机
    camera = TucamDLL(qcos_configer.get_camera_dll_path())
    camera.OpenCamera(0)
    # 设置相机采集的ROI区域
    width_off = qcos_configer.get_width_offset()
    height_off = qcos_configer.get_height_offset()
    width = qcos_configer.get_roi_width()
    height = qcos_configer.get_roi_height()
    camera.SetROI(width_off, height_off, width, height)
    # 设置相机的捕获模式
    camera.SetTriggerMode(mode=TUCAM_CAPTURE_MODES.TUCCM_TRIGGER_STANDARD.value)
    # 开始相机获取
    camera.StartAcquisition()

    # 初始化NI
    try:
        nido = InstrumentBase.find_instrument('nido')
    except:
        nido = NI('nido', dev=qcos_configer.get_ni_do_address(), type=0, rate=qcos_configer.get_ni_do_rate())
    try:
        niao = InstrumentBase.find_instrument('niao')
    except:
        niao = NI('niao', dev=qcos_configer.get_ni_ao_address(), type=1, rate=qcos_configer.get_ni_ao_rate(),
                  num_samples=1, trigger_source=qcos_configer.get_ni_ao_trigger_source())

    if os.path.exists(img_path):
        shutil.rmtree(img_path)
    os.makedirs(img_path)
    if nido is not None:
        # 先上传do, ao信号
        niao.send([[]])
        nido.send([[]])
        # 执行repeat次
        for i in range(repeat):
            # 控制信号任务启动
            niao.start()
            nido.start()
            # 获取原子捕获照片
            camera.GetAcquiredData(img_name=os.path.join(img_path, f'image{i}'))
            # 控制信号任务结束
            niao.stop()
            nido.stop()
            time.sleep(2)
    else:
        raise RuntimeError("NI板卡设备异常，无法触发采集原子图像")


if __name__ == "__main__":
    # 自动获取多张原子成像并拼成完整的原子阵列图像，默认保存在配置文件中指定的calib_img_path路径下
    get_all_qubits_png()
