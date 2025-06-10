import abc
import ctypes
from typing import Union


class EmccdCamera(abc.ABC):
    @staticmethod
    def from_path(dll_path, init_path='./') -> 'EmccdCamera':
        if dll_path == "<fake>":
            from .camera_fake import EmccdCameraFake
            return EmccdCameraFake()
        else:
            from .camera_dll import EmccdCameraByDll
            return EmccdCameraByDll.from_path(dll_path, init_path)

    # lifecycle

    def __init__(self):
        self.qubit = 1
        self.calibrate = 1
        self.i = 0
        self._initialize()

    def __del__(self):
        self._shutdown()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._shutdown()

    def shutdown(self):
        self._shutdown()

    @abc.abstractmethod
    def _initialize(self):
        pass

    @abc.abstractmethod
    def _shutdown(self):
        pass

    @abc.abstractmethod
    def set_temperature(self, temperature: int):
        pass

    @abc.abstractmethod
    def get_temperature(self) -> float:
        pass

    @abc.abstractmethod
    def set_acquisition_mode(self, mode):
        pass

    @abc.abstractmethod
    def set_exposure_time(self, time: float):
        pass

    # acquisition control

    @abc.abstractmethod
    def start_acquisition(self):
        pass

    @abc.abstractmethod
    def abort_acquisition(self):
        pass

    # data

    @abc.abstractmethod
    def get_acquired_data(self, size: int, buffer: Union[ctypes.POINTER, ctypes.Array]):
        pass

    @abc.abstractmethod
    def get_latest_image(self, size: int, buffer: Union[ctypes.POINTER, ctypes.Array]):
        pass
