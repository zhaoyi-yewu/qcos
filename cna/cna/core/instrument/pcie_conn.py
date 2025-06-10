from abc import abstractmethod, ABC
class PCIEConnect(ABC):
    
    def __init__(self, dev, **kwargs) -> None:
        self.dev = dev
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    @abstractmethod
    def connect(self):
        pass 
    
    @abstractmethod
    def read(self):
        pass 
    
    @abstractmethod
    def write(self):
        pass 


class SimplePCIE(PCIEConnect):
    
    def connect(self):
        from pypcie import Device
        self.device = Device(self.dev)
        self.effective_bar = []
        for idx, bar in enumerate(self.device.bar):
            if bar is not None:
                self.effective_bar.append(idx)
        if len(self.effective_bar) == 0: raise "no effective bar"
        self.bar_id = self.effective_bar[0]
    
    def set_bar_id(self, id: int):
        self.bar_id = id
    
    def read(self, **kwargs):
        offset = kwargs.get('offset', 0x1000)
        return self.device.bar[self.bar_id].read(offset)
    
    def write(self, data, **kwargs):
        offset = kwargs.get('offset', 0x1000)
        self.device.bar[self.bar_id].write(offset, data)

class NIDO(PCIEConnect):
    """数字信号输出
    Args:
        rate：采样率，满足ttl信号间隔，具体由硬件决定
        num_samples：每个通道发送的ttl信号数目
    """
    def connect(self):
        import nidaqmx
        from nidaqmx.constants import LineGrouping
        self.task = nidaqmx.Task()
        for dev_str in self.dev:
            self.task.do_channels.add_do_chan(dev_str, line_grouping = LineGrouping.CHAN_PER_LINE)
        # self.rate = getattr(self, 'rate', 1e6)
        #self.num_samples = getattr(self, 'num_samples', 1)

    def set_cfg(self, rate, samps_per_chan):
        from nidaqmx.constants import AcquisitionType
        self.task.timing.cfg_samp_clk_timing(rate=rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=samps_per_chan)

    def write(self, data):
        self.task.write(data, auto_start = False)

    def read(self):
        raise RuntimeError("there are no input channels in this task to which data can be read.")

    def run_task(self):
        self.task.start()

    def stop_task(self):
        self.task.wait_until_done()
        self.task.stop()

    def close(self):
        if hasattr(self, 'task'):
            try:
                self.task.close()
            except:
                pass

class NIAO(PCIEConnect):
    """模拟信号输出。对于模拟信号，提前写入数据，等待通过trigger触发

    Args:
        min_v：电压最小值
        max_v：电压最大值
        rate：采样率
        trigger_source：触发源，连接PXIe-6536的引脚
    """
    def connect(self):
        import nidaqmx
        self.task = nidaqmx.Task()
        min_v = getattr(self, 'min_val', -10.0)
        max_v = getattr(self, 'max_val', 10.0)
        for dev_str in self.dev:
            self.task.ao_channels.add_ao_voltage_chan(dev_str, min_val=min_v, max_val=max_v)
        # self.rate = getattr(self, 'rate', 1e6)
        #self.num_samples = getattr(self, 'num_samples', 1)
        # self.task.timing.cfg_samp_clk_timing(rate=self.rate, sample_mode=AcquisitionType.FINITE)
        # trigger_source = getattr(self, 'trigger_source', '/DEV1/PXI_Trig0')
        # self.task.triggers.start_trigger.cfg_dig_edge_start_trig(trigger_source=trigger_source)

    def set_cfg(self, rate, samps_per_chan):
        from nidaqmx.constants import AcquisitionType
        self.task.timing.cfg_samp_clk_timing(rate=rate, sample_mode=AcquisitionType.FINITE, samps_per_chan=samps_per_chan)

    def write(self, data):
        self.task.write(data, auto_start=False)

    def run_task(self):
        self.task.start()

    def stop_task(self):
        self.task.wait_until_done(timeout = 10)
        self.task.stop()

    def read(self):
        raise RuntimeError("there are no input channels in this task to which data can be read.")

    def close(self):
        if hasattr(self, 'task'):
            try:
                self.task.close()
            except:
                pass


class NIMocker(PCIEConnect):
    """模拟信号输出。对于模拟信号，提前写入数据，等待通过trigger触发

    Args:
        min_v：电压最小值
        max_v：电压最大值
        rate：采样率
        trigger_source：触发源，连接PXIe-6536的引脚
    """

    def connect(self):
        pass

    def set_cfg(self, rate, samps_per_chan):
        pass

    def write(self, data):
        if len(data) != len(self.dev):
            raise RuntimeError(f"数据数量与通道数不对齐，{len(self.dev)}个通道，{len(data)}个数据包")
        print("数据发送成功")

    def run_task(self):
        pass

    def stop_task(self):
        pass

    def read(self):
        raise RuntimeError("there are no input channels in this task to which data can be read.")

    def close(self):
        pass
