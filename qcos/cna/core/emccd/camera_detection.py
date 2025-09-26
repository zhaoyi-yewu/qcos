import time
import matplotlib.pyplot as plt
import numpy as np
import ctypes
from .camera import (
    create_uint32_buffer,
    EmccdCamera,
)
from copy import deepcopy
import cv2


class CameraDetection:
    def __init__(self, dll_path="<fake>", init_path='./'):
        self.camera = EmccdCamera.from_path(dll_path, init_path)
        self.current_image = None  # Initialize current_image attribute
        # self.current_images = []
        self.buffer = None
        self.buffer_data_mode = None
        self.ion_position_list = None
        self.img_num = 1

    def set_acquisition_mode(self, mode):
        """Set acquisition mode and related settings."""
        self.camera.dll.SetTriggerMode(mode)

    def set_roi(self, w_off, h_off, w_v, h_v):
        self.img_w = w_v
        self.img_h = h_v
        self.img_size = self.img_w * self.img_h
        self.camera.set_roi(w_off, h_off, w_v, h_v)

    def set_exposure_time(self, exposuretime):
        """Set the exposure time."""
        self.camera.set_exposure_time(exposuretime)

    def capture_image(self, img_num=None):
        """获取一张图片，保存至current_image中."""
        if self.buffer is None or ctypes.sizeof(self.buffer) < self.img_size * ctypes.sizeof(ctypes.c_uint32):
            self.buffer = create_uint32_buffer(self.img_size)

        self.camera.get_acquired_data(self.img_size, self.buffer, img_num)
        images = np.frombuffer(self.buffer, dtype=np.uint32).reshape((-1, self.img_h, self.img_w))
        self.current_image = images[0]

    def read_and_count(self, threshold_block=3, img_path=None):
        """
        针对mocker的比特状态读取，返回当前比特的平均光子数，可通过阈值来判断处于亮态还是暗态
        """
        img = self.current_image
        if img_path is not None:
            img = cv2.imread(img_path, flags=0)
        counts = []
        for x, y, ion_size in self.ion_position_list:
            ion_image = img[
                        int(max(0, x - ion_size)): int(x + ion_size) + 1,
                        int(max(0, y - ion_size)): int(y + ion_size) + 1,
                        ]
            f2 = ion_image.flatten().tolist()
            f2.sort(reverse=True)
            f2 = f2[:threshold_block]
            v = sum(f2) / len(f2)
            counts.append(v)
        return counts

    def get_status_with_threshold(self, threshold: float, threshold_block=3, img_path=None):
        """根据阈值获取当前图片中比特的状态

        Args:
            threshold (float): 亮态阈值
        """
        img = self.current_image
        if img_path is not None:
            img = cv2.imread(img_path, flags=0)
        results = []
        for x, y, ion_size in self.ion_position_list:
            ion_image = img[
                        int(max(0, x - ion_size)): int(x + ion_size) + 1,
                        int(max(0, y - ion_size)): int(y + ion_size) + 1,
                        ]
            f2 = ion_image.flatten().tolist()
            f2.sort(reverse=True)
            f2 = f2[:threshold_block]
            v = sum(f2) / len(f2)
            results.append(1 if v > threshold else 0)
        return results

    def measure_with_threshold(self, threshold: float):
        """根据阈值获取最终的量子态0， 1

        Args:
            threshold (float): 亮态阈值
        """
        counts = self.read_and_count()
        result = [1 if v > threshold else 0 for v in counts]
        return result

    def plot_images(self, images):
        """Plot images"""
        plt.clf()
        for i, image in enumerate(images, start=1):
            plt.figure()
            plt.imshow(image)

    def save_images(self, images, folder):
        """Plot and save images to the specified folder."""
        for i, image in enumerate(images, start=1):
            cv2.imwrite(folder + f"measure{i}.png", image.astype(np.uint8))

    def save_with_box(self, res, image, path):
        new_img = image.copy()
        new_img = new_img.astype(np.uint8)
        new_img = cv2.cvtColor(new_img, cv2.COLOR_GRAY2BGR)
        cnt = 0
        for i, v in enumerate(res):
            if v == 1:
                y, x, r = self.ion_position_list[i]
                a, b = (int(max(0, x - r)), int(max(0, y - r))), (int(x + r), int(y + r))
                cv2.rectangle(new_img, a, b, (0, 255, 0), 2)
                cnt += 1
        cv2.imwrite(path, new_img)
