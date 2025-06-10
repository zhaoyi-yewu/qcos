from .instrument_base import InstrumentBase
from enum import Enum
from abc import abstractmethod

class SimulatorType(Enum):
    #模拟器，类型未确定
    SIMULATOR_TYPE_NONE = 0
    #门电路模拟器
    SIMULATOR_TYPE_GATE = 1
    #脉冲模拟器
    SIMULATOR_TYPE_PULSE = 2

class SimulatorBase(InstrumentBase):
    """
    模拟器抽象类
    """
    _simulator_type:SimulatorType = SimulatorType.SIMULATOR_TYPE_NONE
    def __init__(self, name: str, sample_count, **kwargs) -> None:
        self.sample_count = sample_count
        super().__init__(name, **kwargs)

    def comm(self, data, **kwargs):
        """
        对外通信接口，集成了数据预处理、发送、接收及数据后处理
        """

        self.preprocess(data, **kwargs)
        result = self.start_simulation()
        return result

    @abstractmethod
    def start_simulation(self):
        """
        调用模拟器API进行模拟
        """
        pass

    @abstractmethod
    def preprocess(self, data, **kwargs):
        """
        数据预处理函数
        """
        pass