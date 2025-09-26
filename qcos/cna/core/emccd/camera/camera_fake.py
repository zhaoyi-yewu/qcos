import ctypes
from abc import update_abstractmethods
from typing import Union
import numpy as np

from .camera import EmccdCamera


class EmccdDllFake():

    def __init__(self) -> None:
        pass

    def SetNumberKinetics(self, num: int):
        pass

    def SetAccumulationCycleTime(self, time: float):
        pass

    def SetTriggerMode(self, mode: int):
        pass


class EmccdCameraFake(EmccdCamera):
    # lifecycle

    def __init__(self):
        """相机
        """
        super().__init__()
        self.w = self.h = 2048
        self.dll = EmccdDllFake()
        self.temperature = 0
        self.qubit = 200

    # temperature

    def set_temperature(self, temperature: float) -> None:
        self.temperature = temperature

    def get_temperature(self) -> float:
        return self.temperature

    # data
    def set_roi(self, w_off, h_off, w_v, h_v):
        self.w = w_v
        self.h = h_v

    def get_acquired_data(self, size: int, buffer: Union[ctypes.POINTER, ctypes.Array], img_name=None):
        self.get_latest_image(size, buffer)

    def get_latest_image(self, size: int, buffer: Union[ctypes.POINTER, ctypes.Array]):
        img = generate_img(self.qubit, self.calibrate, self.w, self.h)

        buffer = np.frombuffer(buffer, dtype=np.uint32).reshape((self.w, self.h))
        buffer[:, :] = img.astype(np.int32)
        self.i += 1


# implement all abstract methods

for abc_func_name in dir(EmccdCameraFake):
    if abc_func_name.startswith("__"):
        continue
    abc_func = getattr(EmccdCameraFake, abc_func_name)
    if not getattr(abc_func, '__isabstractmethod__', None):
        continue


    def _build_fake_func(name: str):
        def _fake_func(_, *args, **kwargs):
            args_str = (str(arg) for arg in args)
            kwargs_str = ((str(k) + '=' + str(v)) for k, v in kwargs.items())
            # print(f"{name}({','.join((*args_str, *kwargs_str))})")

        _fake_func.__name__ = name
        return _fake_func


    setattr(EmccdCameraFake, abc_func_name, _build_fake_func(abc_func_name))
update_abstractmethods(EmccdCameraFake)


# utils

def generate_img(num: int, calibrate: int, w, h) -> np.ndarray:
    """生成图片，最多包含16个比特

    Args:
        num (int): 比特数
        calibrate (int): 1表示校准阶段
    """
    img = np.zeros((w, h), dtype=np.uint32)
    r = 1
    xlist = list(range(30, 190, 16))
    ylist = list(range(30, 190, 8))
    for q in range(num):
        v = np.random.rand() > 0.5
        if calibrate == 1: v = True
        x = xlist[q // 20]
        y = ylist[q % 20]
        for i in range(x - r, x + r + 1):
            for j in range(y - r, y + r + 1):
                if (i - x) ** 2 + (j - y) ** 2 <= r ** 2:
                    if v:
                        img[i][j] = np.random.randint(128, 256)
                    else:
                        img[i][j] = 0
    return img
