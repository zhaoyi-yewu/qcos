from .hardware_base import HardwareBase
import time
import socket
import re
from .error import *
import matplotlib.pyplot as plt
from .awg import GenerateDynamicC3C4


class AWGMocker(HardwareBase):
    """
    任意波形发生器

    Args:
        name (str): 设备名称
        awg_address (_type_, optional): 通信ip. Defaults to None.
    """

    def __init__(self, name: str, awgConfig=None, **kwargs) -> None:

        if awgConfig is None:
            raise DeveiceParameterError("awg需要config配置")
        addr_ip = awgConfig.get('addr_ip', '192.168.1.1')
        if not self.check_input(addr_ip):
            raise DeveiceConnectionError(
                "awg connect failed, The input is neither a valid IP address nor in the '/dev/xxx' format")
        self.channelList = awgConfig['channelList']
        self.samplingRateMHz = awgConfig.get('samplingRateMHz', 500)  # 采样频率，MHZ
        self.amp = awgConfig.get('amp', 0.5)  # 测试反馈说 (0.05 -> 100mV) awg最大只能输出 0.5  （也就是1V的 amp）
        super().__init__(name, **kwargs)
        self.generator = GenerateDynamicC3C4(awgFreMhz = self.samplingRateMHz, t0Us=1,t1Us=1,t2Us=1,t5Us=1)

    def check_input(self, input_str):
        # Check if the input is a valid IP address
        def is_valid_ip(ip_str):
            try:
                socket.inet_aton(ip_str)
                return True
            except socket.error:
                return False

        # Check if the input has the '/dev/xxx' format
        def is_dev_format(dev_str):
            pattern = r"^/dev/[\w-]+$"
            return bool(re.match(pattern, dev_str))

        if is_valid_ip(input_str):
            return True
        elif is_dev_format(input_str):
            return True
        else:
            return False

    def holding(self, channelList=None):
        # print("保持末端输出")
        if channelList is None:
            channelList = self.channelList
        pass

    def send(self, send_data, **kwargs):
        channelList = kwargs.get("channelList", self.channelList)
        print(channelList)
        nChannel = len(channelList)
        if len(send_data) != nChannel:
            raise Exception(
                f"dimsion of input data [{len(send_data)}] donot match number of channels [{len(channelList)}]")

    def receive(self, **kwargs):
        pass

    def sendSingleChannel(self,
                          wave: list,
                          channelID: int,
                          trigger: str = "external",
                          flush: bool = True,
                          cycles: int = 1,
                          amp: float = None,
                          **kw):
        pass

    def setQueueWaveIntoChannel(self,
                                channel: int,
                                qid: int,
                                trigger: str = "external",
                                flush: bool = True,
                                cycles: int = 1,
                                amp: float = None,
                                **kwargs):
        pass

    def setRamanWave(self, waves, **kwargs):
        channelList = kwargs.get("channelList", self.channelList)
        nChannel = len(channelList)
        if len(waves) != nChannel:
            raise Exception(f"dimsion of input data [{len(waves)}] donot match number of channels [{len(channelList)}]")

        amp = kwargs.get('amp', self.amp)

        pass

    def appendQueueWave(self, qid: int, dataFilePath: str):
        pass

    def setArrangeWave(self, waves, **kwargs):
        """重排波形发送

        Args:
            waves (_type_): 重排操作对应波形名称
        """
        channelList = kwargs.get("channelList", self.channelList)
        nChannel = len(channelList)
        if len(waves) != nChannel:
            raise Exception(f"dimsion of input data [{len(waves)}] donot match number of channels [{len(channelList)}]")

        amp = kwargs.get('amp', self.amp)
        pass

    def startMultipChannel(self, **kwargs):
        pass

    def receive(self, **kwargs):
        pass
