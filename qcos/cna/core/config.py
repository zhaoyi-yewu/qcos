from enum import Enum
import socket
from qcos.cna.core.instrument.error import DeveiceParameterError
import re


class InstrumentType(Enum):
    # 不使用任何硬件或者模拟器
    INSTRUMENT_NONE = 0
    # 使用硬件FPGA和AWG
    INSTRUMENT_HW_FPGA_AWG = 1
    # 使用PULSER 模拟器
    INSTRUMENT_SIMULATOR_PULSER = 2


class GlobalSetting:
    """
    全局参数
        __debug_mode：调试模式
        __datapath：数据存储路径
        __log：日志路径
        __fusion： 是否聚合
        __fusion_thread：聚合任务阈值
        __decomposition_rule：门分解规则
    """
    __debug_mode: bool = False
    # __debug_mode: bool = True
    __ser = None
    __datapath = '../test_data/'
    __log = '../test_data/log.txt'
    __fusion: bool = False
    __fusion_thread = 2
    __decomposition_rule = {}
    __instrument_type: InstrumentType = InstrumentType.INSTRUMENT_NONE
    __task_manager = None
    __awg_dll = r"C:\Program Files\Keysight\SD1\shared\SD1core"
    __rearrangement_dll = "./test.dll"

    @classmethod
    def get_ser(cls):
        return cls.__ser

    @classmethod
    def get_debug_mode(cls):
        return cls.__debug_mode

    @classmethod
    def get_log(cls):
        return cls.__log

    @classmethod
    def get_fusion(cls):
        return cls.__fusion

    @classmethod
    def get_fusion_thread(cls):
        return cls.__fusion_thread

    @classmethod
    def get_datapath(cls):
        return cls.__datapath

    @classmethod
    def get_decomposition_rule(cls):
        return cls.__decomposition_rule

    @classmethod
    def set_ser(cls, ser):
        cls.__ser = ser

    @classmethod
    def set_debug_mode(cls, mode: bool):
        cls.__debug_mode = mode

    @classmethod
    def set_log(cls, path):
        cls.__log = path

    @classmethod
    def set_datapath(cls, datapath):
        cls.__datapath = datapath

    @classmethod
    def set_fusion(cls, fusion: bool):
        cls.__fusion = fusion

    @classmethod
    def set_fusion_thread(cls, thread):
        cls.__fusion_thread = thread

    @classmethod
    def set_decomposition_rule(cls, decomposition_rule):
        cls.__decomposition_rule = decomposition_rule

    @classmethod
    def get_instrument_type(cls):
        return cls.__instrument_type

    @classmethod
    def set_instrument_type(cls, instrument_type):
        cls.__instrument_type = instrument_type

    @classmethod
    def get_awg_dll(cls):
        return cls.__awg_dll

    @classmethod
    def set_awg_dll(cls, awg_dll):
        cls.__awg_dll = awg_dll

    @classmethod
    def get_task_manager(cls):
        return cls.__task_manager

    @classmethod
    def set_task_manager(cls, task_manager):
        cls.__task_manager = task_manager

    @classmethod
    def get_rearrangement_dll(cls):
        return cls.__rearrangement_dll

    @classmethod
    def set_rearrangement_dll(cls, dll):
        cls.__rearrangement_dll = dll


class AwgSetting:
    """
    硬件设备AWG的配置

    参数
        __sampling_rate: 采样频率
        __delay： 延迟
        __test_time：测试时间
        __awg_address：IP 地址
    """
    __sampling_rate: int = 625
    __delay: int = 0
    __test_time: float = 0.5
    __awg_address: str = '192.168.1.1'

    @classmethod
    def get_sampling_rate(cls):
        """
        获取采样频率

        参数：无
        返回值：采样频率
        """
        return cls.__sampling_rate

    @classmethod
    def set_sampling_rate(cls, sampling_rate):
        """
        设置采样频率，如果采样频率为负数，抛出异常

        参数：采样频率
        返回值：无
        """
        if sampling_rate < 0:
            raise DeveiceParameterError(f"invalid sampling_rate value: {sampling_rate}")
        cls.__sampling_rate = sampling_rate

    @classmethod
    def get_delay(cls):
        """
        获取硬件延迟

        参数：无
        返回值：硬件延迟
        """
        return cls.__delay

    @classmethod
    def set_delay(cls, delay):
        """
        设置硬件延迟，如果延迟为负数，抛出异常

        参数：硬件延迟
        返回值：无
        """
        if delay < 0:
            raise DeveiceParameterError(f"invalid delay value: {delay}")
        cls.__delay = delay

    @classmethod
    def get_test_time(cls):
        """
        获取测试时间

        参数：无
        返回值：测试时间
        """
        return cls.__test_time

    @classmethod
    def set_test_time(cls, test_time):
        """
        设置测试时间，如果时间为负数，抛出异常

        参数：测试时间
        返回值：无
        """
        if test_time < 0:
            raise DeveiceParameterError(f"invalid test_time value: {test_time}")
        cls.__test_time = test_time

    @classmethod
    def get_awg_address(cls):
        """
        获取AWG IP地址

        参数：无
        返回值：IP地址
    """
        return cls.__awg_address

    @classmethod
    def is_valid_ip(cls, ip_address):
        """
        校验IP地址是否合法

        参数：IP地址
        返回值：True or False
        """
        try:
            socket.inet_aton(ip_address)
            return True
        except socket.error:
            return False

    @classmethod
    def set_awg_address(cls, awg_address):
        """
        设置IP地址，如果IP地址不合法，抛出异常

        参数：IP地址
        返回值：无
        """
        if not cls.is_valid_ip(awg_address):
            raise DeveiceParameterError(f"invalid awg_address: {awg_address}")
        cls.__awg_address = awg_address


class FpgaSetting:
    """
    硬件设备FPGA的配置

    参数
        __port: 端口
        __clock_period： 时钟周期
        __test_time：测试时间
        __bytes_returned：返回数据字节数
    """
    __port: str = "COM5"
    __clock_period: int = 1E06
    __test_time: float = 0.5
    __bytes_returned: int = 12

    @classmethod
    def get_port(cls):
        """
        获取端口号

        参数：无
        返回值：端口号
        """
        return cls.__port

    @classmethod
    def match_str(self, port):
        pattern = r'^(COM|com)\d+$'
        return bool(re.match(pattern, port))

    @classmethod
    def set_port(cls, port: str):
        """
        设置端口号

        参数：端口号
        返回值：无
        """
        if not cls.match_str(port):
            raise DeveiceParameterError(f"invalid port value: {port}")

        cls.__port = port

    @classmethod
    def get_clock_period(cls):
        """
        获取时钟周期

        参数：无
        返回值：时钟周期
        """
        return cls.__clock_period

    @classmethod
    def set_clock_period(cls, clock_period):
        """
        设置时钟周期，如果时钟周期为负数，抛出异常

        参数：时钟周期
        返回值：无
        """
        if clock_period < 0:
            raise DeveiceParameterError(f"invalid clock_period value: {clock_period}")
        cls.__clock_period = clock_period

    @classmethod
    def get_test_time(cls):
        """
        获取测试时间

        参数：无
        返回值：测试时间
        """
        return cls.__test_time

    @classmethod
    def set_test_time(cls, test_time):
        """
        设置测试时间，如果时间为负数，抛出异常

        参数：测试时间
        返回值：无
        """
        if test_time < 0:
            raise DeveiceParameterError(f"invalid test_time value: {test_time}")
        cls.__test_time = test_time

    @classmethod
    def get_bytes_returned(cls):
        """
        获取返回字节数

        参数：无
        返回值：返回字节数
        """
        return cls.__bytes_returned

    @classmethod
    def set_bytes_returned(cls, bytes_returned):
        """
        设置返回字节数，如果字节数为负数，抛出异常

        参数：返回字节数
        返回值：无
        """
        if bytes_returned < 0:
            raise DeveiceParameterError(f"invalid bytes_returned value: {bytes_returned}")
        cls.__bytes_returned = bytes_returned
