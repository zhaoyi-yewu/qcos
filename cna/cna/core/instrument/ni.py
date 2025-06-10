from .hardware_base import HardwareBase
import time
import numpy as np
from .error import *
from .pcie_conn import *


class NI(HardwareBase):
    """
    中控设备

    Args:
        name (str): 设备名称
        dev (_type_, optional): 设备地址. Defaults to None.
        type：设备类型，0为DO，1为AO
    """
    
    def __init__(self, name: str, dev = None, type = 0, **kwargs) -> None:
        
        if dev == None: raise DeveiceParameterError(f"Please specify the device address for communication")
        self.__type = type
        self.params = kwargs.copy()
        self.rate = kwargs.get('rate', 1e6)
        self.delay_time = kwargs.get('delay_time', 0)
        self.delay_start = kwargs.get('delay_start', 0)

        # DO parameters
        self.do0_pgc_cooling_time = kwargs.get('do0_pgc_cooling_time', 0)
        self.do0_meas_cooling_time = kwargs.get('do0_meas_cooling_time', 0)
        self.do2_pgc_pump_time = kwargs.get('do2_pgc_pump_time', 0)
        self.do2_meas_pump_time = kwargs.get('do2_meas_pump_time', 0)

        # AO parameters
        self.ao1_pgc_cooling_detune = kwargs.get('ao1_pgc_cooling_detune', 3.2)
        self.ao1_meas_cooling_detune = kwargs.get('ao1_meas_cooling_detune', 3.2)
        self.ao1_meas_cooling_freq = kwargs.get('ao1_meas_cooling_freq', 6.4)
        self.ao3_pgc_pump_detune = kwargs.get('ao3_pgc_pump_detune', 3.4)
        self.ao3_meas_pump_detune = kwargs.get('ao3_meas_pump_detune', 4)
        self.ao4_pgc_comp_mag = kwargs.get('ao4_pgc_comp_mag', 1.277)
        self.ao5_pgc_comp_mag = kwargs.get('ao5_pgc_comp_mag', 1.261)
        self.ao6_pgc_comp_mag = kwargs.get('ao6_pgc_comp_mag', 1.325)
        self.ao7_raman_source_freq = kwargs.get('ao7_raman_source_freq', 1.325)
        self.ao8_pgc_pump_amp = kwargs.get('ao8_pgc_pump_amp', 5)
        self.ao8_meas_pump_amp = kwargs.get('ao8_meas_pump_amp', 5)
        self.ao9_pgc_cooling_amp = kwargs.get('ao9_pgc_cooling_amp', 5)

        if isinstance(dev, str):
            dev = [dev]
        if type == 0:
            self.connection = NIDO(dev, **kwargs)
        elif type == 1:
            self.connection = NIAO(dev, **kwargs)
        else:
            self.connection = NIMocker(dev, **kwargs)
        super().__init__(name, **kwargs)
        
    def send(self, send_data, **kwargs):
        print(f"send to {self.name}")
        data = self.get_package(send_data)
        self.connection.set_cfg(self.rate, len(data[0]))
        self.connection.write(data, **kwargs)
    
    def start(self):
        self.connection.run_task()
            
    def stop(self):
        self.connection.stop_task()
    
    def receive(self, **kwargs):
        print(f"receive from {self.name}")
        return self.connection.read(**kwargs)

    def get_package(self, send_data):
        """板卡数据集成
        """
        data = send_data
        if self.__type == 0:
            #data = self.ttl_package_generator(send_data)
            data = self.get_all_do()
        elif self.__type == 1:
            data = self.get_all_ao()
        else:
            data = []
            for signal in send_data:
                if self.__type == 2:
                    data.append(self.ttl_package_from_signal(signal))
                else:
                    data.append(self.ao_package_from_signal(signal))
            m = len(data[0])
            if not all([len(x) == m for x in data]): raise RuntimeError("各通道数据数量没对齐，请检查!")
        return data
    
    def ttl_package_generator(self, send_data, **kwargs):
        """对ttl信号数据进行格式解析和封装
        """
        data = []
        for (chapter, time) in send_data:
            ttl = int(chapter[:8], 2)
            data += [ttl] * int(np.ceil(time * self.rate / 1e6))
        return np.array(data, dtype=np.uint32)
    
    def ao_package_generator(self, time, sample_func = None):
        """模拟信号生成
        """
        if sample_func is None:
            sample_func = self.params.get('sample_func', np.sin)
        sample_num = int(np.round(time*self.rate / 1e6))
        sample_time = np.linspace(0, time, sample_num+1)
        return sample_func(sample_time)
    
    def set_sample_func(self, sample_func):
        self.params['sample_func'] = sample_func
    
    def get_all_do(self, unit = 1e-3):
        
        do_datas = [
            self.do0_kick_AOM_signal(),
            self.do1_shutter_signal(),
            self.do2_AOM_signal(),
            self.do3_shutter_signal(),
            self.do4_camera_signal(),
            self.do5_shutter_signal(),
            self.do6_AOM_signal(),
            self.do7_shutter_signal(),
            self.do8_wave_signal(),
            self.do9_shutter_signal(),
            self.do10_wave_signal(),
            self.do11_light_signal(),
            #self.do12_ao_start_signal(),
            self.do22_awg_start_signal(),
            self.do26_signal(),
            self.do27_signal(),
            self.do30_ao_start_signal()
        ]
    
        if self.delay_time != 0:
            for i in range(len(do_datas)):
                data = do_datas[i].tolist()
                idx = int(np.round(self.delay_start * self.rate * unit))
                v = data[idx]
                data = data[:idx] + [v] * int(np.round(self.delay_time * self.rate * unit)) + data[idx:]
                do_datas[i] = data
        return np.vstack(do_datas)

    def ttl_package_from_signal(self, signal, unit=1e-3):
        data = []
        for i, (t, s) in enumerate(signal):
            if i == len(signal) - 1:
                data.append(bool(s))
            else:
                time = signal[i+1][0] - t
                data += [bool(s)] * int(np.round(time * self.rate * unit))
        return np.array(data)

    def do0_kick_AOM_signal(self):
        signal = [(0, 0), (150, 1), (540 + self.do0_pgc_cooling_time, 0), (570, 1), (600 + self.do0_meas_cooling_time, 0), (650, 1), (670 + self.do0_pgc_cooling_time, 0),
                  (709, 1), (738, 0), (741, 1), (769, 0), (769.1, 1), (810, 0), (865, 0)]
        return self.ttl_package_from_signal(signal)
    
    def do1_shutter_signal(self):
        signal = [(0, 1), (710, 0), (800, 1), (865, 1)]
        return self.ttl_package_from_signal(signal)

    def do2_AOM_signal(self):
        signal = [(0, 0), (150, 1), (540 + self.do2_pgc_pump_time, 0), (570, 1), (600 + self.do2_meas_pump_time, 0), (650, 1), (670 + self.do2_pgc_pump_time, 0),
                  (709, 1), (739, 0), (740, 1), (810, 0), (865, 0)]
        return self.ttl_package_from_signal(signal)

    def do3_shutter_signal(self):
        signal = [(0, 1), (715, 0), (800, 1), (865, 1)]
        return self.ttl_package_from_signal(signal)

    def do4_camera_signal(self):
        signal = [(0, 0), (100, 1), (150, 0), (600, 1), (650, 0), (810, 1), (860, 0), (865, 0)]
        return self.ttl_package_from_signal(signal)

    def do5_shutter_signal(self):
        signal = [(0, 0), (732, 1), (747, 0), (865, 0)]
        return self.ttl_package_from_signal(signal)
    
    def do6_AOM_signal(self):
        signal = [(0, 1), (739, 0), (740.2, 1), (865, 1)]
        return self.ttl_package_from_signal(signal)

    def do7_shutter_signal(self):
        signal = [(0, 0), (729.5, 1), (740.5, 0), (865, 0)]
        return self.ttl_package_from_signal(signal)

    def do8_wave_signal(self):
        signal = [(0, 1), (865, 1)]
        return self.ttl_package_from_signal(signal)

    def do9_shutter_signal(self):
        signal = [(0, 0), (763, 1), (773, 0), (865, 0)]
        return self.ttl_package_from_signal(signal)
    
    def do10_wave_signal(self):
        signal = [(0, 0), (765.935, 1), (765.945, 0), (865, 0)]
        return self.ttl_package_from_signal(signal)

    def do11_light_signal(self):
        signal = [(0, 0), (861, 1), (862, 0), (865, 0)]
        return self.ttl_package_from_signal(signal)

    def do12_ao_start_signal(self):
        data = [True]
        data += [False] * int(np.round(865 * self.rate * 1e-3))
        return np.array(data)

    def do22_awg_start_signal(self):
        signal = [(0, 0), (764.93, 0), (764.93, 1), (764.934, 1), (764.934, 0), (865, 0)]
        return self.ttl_package_from_signal(signal)

    def do26_signal(self):
        signal = [(0, 1), (710, 1), (710, 0), (859, 0), (859, 1), (865, 1)]
        return self.ttl_package_from_signal(signal)
    
    def do27_signal(self):
        signal = [(0, 1), (766, 1), (766, 0), (766.016, 0), (766.016, 1), (865, 1)]
        return self.ttl_package_from_signal(signal)

    def do30_ao_start_signal(self):
        data = [True]
        data += [False] * int(np.round(865 * self.rate * 1e-3))
        return np.array(data)

    def get_all_ao(self, unit=1e-3):
        ao_datas = [
            self.ao0_MOT_signal(),
            self.ao1_fm_signal(),
            self.ao2_ta_signal(),
            self.ao3_signal(),
            self.ao4_signal(),
            self.ao5_signal(),
            self.ao6_signal(),
            self.ao7_signal(),
            self.ao8_signal(),
            self.ao9_signal(),
        ]
    
        if self.delay_time != 0:
            for i in range(len(ao_datas)):
                data = ao_datas[i].tolist()
                idx = int(np.round(self.delay_start * self.rate * unit))
                v = data[idx]
                data = data[:idx] + [v] * int(np.round(self.delay_time * self.rate * unit)) + data[idx:]
                ao_datas[i] = data
        return np.vstack(ao_datas)

    def ao_package_from_signal(self, signal, unit=1e-3):
        data = []
        for i, (t, s) in enumerate(signal):
            if i == len(signal) - 1:
                data.append(s)
            else:
                time = signal[i+1][0] - t
                if time == 0: continue
                data += np.linspace(s, signal[i+1][1], int(np.round(time * self.rate * unit))).tolist()

        return np.array(data)

    def ao0_MOT_signal(self):
        # signal = [(0, 4), (710, 4), (710, 5), (860, 5), (860, 0.8), (865, 0.8)]
        signal = [(0, 5), (100, 5), (150, 5), (180, 5), (600, 5), (710, 5), (810, 5), (860, 5), (860, 0.8), (865, 0.8)]
        return self.ao_package_from_signal(signal)
    
    def ao1_fm_signal(self):
        # signal = [(0, 4.3), (20, 4.3), (100, 3.2), (100, 4.3), (150, 4.3), (540, 4.3), (570, 3.2), (570, 4.3), (670, 4.3), (709, 3.2), (709, 4.3), (755, 4.3), (755, 6.4), (770, 6.4), (770, 4.3), (865, 4.3)]
        signal = [(0, 4.3), (20, 4.3), (100, self.ao1_pgc_cooling_detune), (100, self.ao1_meas_cooling_detune), (150, self.ao1_meas_cooling_detune), (150, 4.3), (540, 4.3), (570, self.ao1_pgc_cooling_detune),
                  (570, 4.3), (600, 4.3), (600, self.ao1_meas_cooling_detune), (650, self.ao1_meas_cooling_detune), (650, 4.3), (670, 4.3), (709, self.ao1_pgc_cooling_detune), (709, 4.3), (710, 4.3),
                  (755, 4.3), (755, self.ao1_meas_cooling_freq), (770, self.ao1_meas_cooling_freq), (770, 4.3), (810, 4.3), (810, self.ao1_meas_cooling_detune), (860, self.ao1_meas_cooling_detune), (860, 4.3), (865, 4.3)]
        return self.ao_package_from_signal(signal)
    
    def ao2_ta_signal(self):
        # signal = [(0, 5), (740.2, 5), (740.2, 4), (742.2, 1), (772.2, 1), (774.2, 4), (774.2, 5), (865, 5)]
        signal = [(0, 5), (740.2, 5), (740.2, 4), (742.2, 1), (772.2, 1), (774.2, 4), (774.2, 5), (865, 5)]
        return self.ao_package_from_signal(signal)

    def ao3_signal(self):
        signal = [(0, 6.3), (20, 6.3), (20, self.ao3_pgc_pump_detune), (100, self.ao3_pgc_pump_detune), (100, self.ao3_meas_pump_detune), (150, self.ao3_meas_pump_detune), (150, 6.3), (540, 6.3), (540, self.ao3_pgc_pump_detune), (570, self.ao3_pgc_pump_detune), (570, 6.3), 
                  (600, 6.3), (600, self.ao3_meas_pump_detune), (650, self.ao3_meas_pump_detune), (670, 4), (670, self.ao3_pgc_pump_detune), (709, self.ao3_pgc_pump_detune), (709, 4), (710, 4), (710, 6.3), (738, 6.3), (738, 4.1), (743, 4.1),
                  (743, 6.3), (810, 6.3), (810, self.ao3_meas_pump_detune), (860, self.ao3_meas_pump_detune), (860, 6.3), (865, 6.3)]
        return self.ao_package_from_signal(signal)

    def ao4_signal(self):
        signal = [(0, 1.262), (10, self.ao4_pgc_comp_mag), (80, self.ao4_pgc_comp_mag), (90, 1.262), (520, 1.262), (530, self.ao4_pgc_comp_mag), (570, self.ao4_pgc_comp_mag), 
                  (580, 1.262), (650, 1.262), (660, self.ao4_pgc_comp_mag), (709, self.ao4_pgc_comp_mag), (710, 1.262), (720, 1.262), (720, 1.252), (730, 1.243), (745, 1.243), 
                  (755, 1.252), (755, 1.262), (865, 1.262)]
        return self.ao_package_from_signal(signal)
    
    def ao5_signal(self):
        signal = [(0, 1.252), (10, self.ao5_pgc_comp_mag), (80, self.ao5_pgc_comp_mag), (90, 1.252), (520, 1.252), (530, self.ao5_pgc_comp_mag), (570, self.ao5_pgc_comp_mag), 
                  (580, 1.252), (650, 1.252), (660, self.ao5_pgc_comp_mag), (709, self.ao5_pgc_comp_mag), (710, 1.252), (720, 1.252), (720, 1.262), (730, 0.6), (785, 0.6), 
                  (795, 1.262), (795, 1.252), (865, 1.252)]
        return self.ao_package_from_signal(signal)
    
    def ao6_signal(self):
        signal = [(0, 1.325), (10, self.ao6_pgc_comp_mag), (80, self.ao6_pgc_comp_mag), (90, 1.325), (520, 1.325), (530, self.ao6_pgc_comp_mag), (570, self.ao6_pgc_comp_mag),
                  (580, 1.325), (650, 1.325), (660, self.ao6_pgc_comp_mag), (709, self.ao6_pgc_comp_mag), (710, 1.325), (720, 1.325), (720, 1.34), (730, 1.294), (745, 1.294),
                  (755, 1.34), (755, 1.325), (865, 1.325)]
        return self.ao_package_from_signal(signal)

    def ao7_signal(self):
        signal = [(0, self.ao7_raman_source_freq), (865, self.ao7_raman_source_freq)]
        return self.ao_package_from_signal(signal)

    def ao8_signal(self):
        signal = [(0, 5), (10, self.ao8_pgc_pump_amp), (80, self.ao8_pgc_pump_amp), (80, 5), (520, 5), (530, self.ao8_pgc_pump_amp), (570, self.ao8_pgc_pump_amp), (580, 5),
                  (650, 5), (660, self.ao8_pgc_pump_amp), (709, self.ao8_pgc_pump_amp), (710, 5), (755, 5), (755, self.ao8_meas_pump_amp), (770, self.ao8_meas_pump_amp),
                  (785, 5), (865, 5)]
        return self.ao_package_from_signal(signal)

    def ao9_signal(self):
        signal = [(0, 4.8), (10, self.ao9_pgc_cooling_amp), (80, self.ao9_pgc_cooling_amp), (80, 4.8), (520, 4.8), (530, self.ao9_pgc_cooling_amp), (570, self.ao9_pgc_cooling_amp),
                  (580, 4.8), (650, 4.8), (660, self.ao9_pgc_cooling_amp), (709, self.ao9_pgc_cooling_amp), (710, 4.8), (865, 4.8)]
        return self.ao_package_from_signal(signal)
