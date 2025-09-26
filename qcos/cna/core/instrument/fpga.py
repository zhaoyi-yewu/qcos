from .hardware_base import HardwareBase
import time
import numpy as np
from .error import *

class FPGA(HardwareBase):
    """
    中控设备

    Args:
        name (str): 设备名称
        port (str): 通信串口. Defaults to None.
    """
    
    def __init__(self, name: str, port = None, **kwargs) -> None:
        
        if port == None: raise DeveiceParameterError(f"Please specify the serial port for communication")
        self.port = port
        self.clock_period = kwargs.get('clock_period', 1E06) #时钟周期
        self.bytes_returned = kwargs.get('bytes_returned', 12) #返回数据字节数
        self.test_time = kwargs.get('test_time', 0.5)
        
        super().__init__(name, **kwargs)
        
    def send(self, send_data, **kwargs):
        # print("=====send to fpga=====")
        time.sleep(self.test_time)
    
    def receive(self, **kwargs):
        time.sleep(self.test_time)
        # print("=====receive from fpga=====")
    
    def preprocess(self, send_data, **kwargs):
        """
        数据预处理函数，将脉冲对应的控制信号按格式打包
        """
        repeat = kwargs.get('repeat', 100)
        ext_trig = kwargs.get('ext_trig', 1)
        
        pulses = self.pre_binary(send_data, self.clock_period)
        packets = [self.packets_generator(pulses, ext_trig, repeat), int(repeat*self.bytes_returned)]
        return packets

    def postprocess(self, received_data, **kwargs):
        repeat = kwargs.get('repeat', 1)
        ion_number = kwargs.get('ion_number', 1)
        res = np.zeros(ion_number * repeat)
        channel = kwargs.get('channel', list(range(ion_number)))
        active_channel = kwargs.get('active_channel', channel)
        idx = [channel.index(c) for c in active_channel]
        for i in range(repeat):
            for j in idx:
                res[i*ion_number + j] = np.random.rand() * 256
        return res
    
    
    def timestamp(self, duration, clock_period):
        # convert duration to a 40 bit binary string
        N = int(duration/clock_period-1)
        return self.timestamp_generator(N)

    def timestamp_generator(self, N):
        W = 40 
        # convert number N to a W-bit binary timestap
        T = (W-N)&(2**W-1)
        T = '{0:040b}'.format(T)
        Res = ''
        for i in range(W):
            j = (int(T[W-1-i:W],2) < i)|(int(T[W-1-i:W],2) >= (1<<i) + i)
            Res = str(int(j)) + Res
        return Res

    def chapter_padding(self, chapter):
        return chapter[0][:18]+'{0:08b}'.format(0) + ' '+chapter[0][18:]
    
    def pre_binary(self, pulses, clock_period):
        # change [chapter, duration] to binary strings
        duration_list = [] 
        for element in pulses:
            duration_list = duration_list + [[self.chapter_padding(element[0]),self.timestamp(element[1], clock_period)]]
        return duration_list

    def packets_generator(self, pulses, ext_trig, repeat):
        start_packet = '100' + str(int(ext_trig)) + '{0:052b}'.format(0) + '{0:024b}'.format(int(repeat))
        pulse_packates = [start_packet]
        i = 0
        time_packets_length = len(pulses)+3
        # convert pulses to timestamp
        for element in pulses:
            packet = '010'
            packet = packet + '{0:05b}'.format(0) + element[1] + element[0].replace(' ','')
            pulse_packates = pulse_packates + [packet]
            i += 1
        # padding the time packet
        if time_packets_length < 15:
            for i in range(15 - time_packets_length):
                packet = '010'
                packet = packet + '{0:05b}'.format(0) + self.timestamp_generator(1-1) + '{0:032b}'.format(0)
                pulse_packates = pulse_packates + [packet]
        elif time_packets_length%5 != 0 and time_packets_length >= 15:
            for i in range(5 - time_packets_length%5):
                packet = '010'
                packet = packet + '{0:05b}'.format(0) + self.timestamp_generator(1-1) + '{0:032b}'.format(0)
                pulse_packates = pulse_packates + [packet]
        # generate end packets
        end_packets_3 = '010' + '{0:05b}'.format(0) + self.timestamp_generator(8-1) + '{0:032b}'.format(0)
        end_packets_2 = '010' + '{0:05b}'.format(0) + self.timestamp_generator(2-1) + '{0:032b}'.format(0)
        end_packets_1 = '011' + '{0:05b}'.format(0) + self.timestamp_generator(1-1) + '{0:032b}'.format(0)
        pulse_packates = pulse_packates + [end_packets_3, end_packets_2, end_packets_1]
        pulse_packates_hex = ''
        for packet in pulse_packates:
            pulse_packates_hex = pulse_packates_hex + hex(int(packet,2))[2:] + ' '
        # end_packet = 
        return pulse_packates_hex