from .simulator_base import SimulatorBase
try:
    import pulser
    from pulser.devices import DigitalAnalogDevice
    from pulser_simulation import QutipEmulator
except:
    pass
from ..pulse import Raman
from ..pulse import MolmerSorensen
from ..pulse import Detection

PULSER_DURATION_UNIT = 4
class SimulatorPulser(SimulatorBase):
    """
    Pulser模拟器
    """
    def __init__(self, name: str, qnum: int, sample_count: int, **kwargs) -> None:       
        self.qnum = qnum
        self.reg = pulser.Register.square(qnum, spacing=4)
        self.seq = pulser.Sequence(self.reg, DigitalAnalogDevice)
        #声明DigitalAnalogDevice支持的两个信道，raman_local_channel 和 rydberg_local_channel
        self.seq.declare_channel("raman_local_channel", "raman_local")
        self.seq.declare_channel("rydberg_local_channel", "rydberg_local", initial_target=0)
        super().__init__(name, sample_count, **kwargs)

    def start_simulation(self):
        """
        启动模拟函数。
        将序列发送给模拟器进行模拟，并将模拟结果进行输出
        """
        #打印当前序列
        print(self.seq)
        print("=====send to simulator=====")
        # 创建模拟对象并且启动模拟，返回模拟结果给results.
        sim = QutipEmulator.from_sequence(self.seq)
        self.results = sim.run()
        print("=====receive results from simulator=====")
        #采样若干次，并打印运行结果。
        counts = self.results.sample_final_state(self.sample_count)
        return counts

    def add_raman(self, pulse:Raman, **kwargs):
        """
        添加Raman脉冲：
        将Raman脉冲添加至raman_local_channel。

        参数: 
        pulse：测控系统支持的脉冲
        返回值：无
        """
        if pulse.pulse_type != 'Raman':
            return
        self.seq.target(pulse.ion_index[0], "raman_local_channel")
        #模拟器支持的持续时间只能为4的倍数
        # raman pulser需要最短的时间是16ns
        if pulse.duration < 16:
            pulse.duration = 16
        if pulse.duration % PULSER_DURATION_UNIT != 0:
            pulse.duration += PULSER_DURATION_UNIT - pulse.duration % PULSER_DURATION_UNIT
        simple_pulse = pulser.Pulse.ConstantPulse(pulse.duration, pulse.amp, 0, pulse.phase)
        self.seq.add(simple_pulse, "raman_local_channel")

    def add_molmersorensen(self, pulse:MolmerSorensen, **kwargs):
        """
        添加MolmerSorensen脉冲：
        将MolmerSorensen脉冲添加至 rydberg_local_channel。

        参数: 
        pulse：测控系统支持的脉冲
        返回值：无
        """
        if pulse.pulse_type != 'MolmerSorensen':
            return
        assert pulse.ion_index != None
        time_segment_number = pulse.para_table['segment_number']
        for single_ion in pulse.ion_index:
            assert pulse.para_table['data_per_ion'][single_ion] != None
            self.seq.target_index(single_ion, "rydberg_local_channel")
            pulse_data = pulse.para_table['data_per_ion'][single_ion]
            for i in range(0, time_segment_number):
                duration = pulse.para_table['time_intervals'][i][1] - pulse.para_table['time_intervals'][i][0]
                #模拟器支持的持续时间只能为4的倍数
                if duration % PULSER_DURATION_UNIT != 0:
                    duration += PULSER_DURATION_UNIT - duration % PULSER_DURATION_UNIT
                simple_pulse = pulser.Pulse.ConstantPulse(duration, pulse_data['amp'][i][0], 0, pulse_data['phase'][i][0])
                self.seq.add(simple_pulse, "rydberg_local_channel")

    def measure(self, **kwargs):
        """
        测量函数
        参数: 无
        返回值：无
        """
        self.seq.measure(basis="ground-rydberg")

    def convert_pulses_to_pulse_seq(self, pulses):
        """
        将传入的脉冲转换为模拟器支持的脉冲
        参数: 
        pulse：测控系统支持的脉冲
        返回值：无
        """
        for pulse in pulses:
            if isinstance(pulse, Raman):
                self.add_raman(pulse)
            elif isinstance(pulse, MolmerSorensen):
                self.add_molmersorensen(pulse)
            elif isinstance(pulse, Detection):
                self.measure()
            elif isinstance(pulse, tuple):
                pass
            else:
                print('pulse type not supported')

    def preprocess(self, pulses, **kwargs):
        """
        预处理函数
        参数: 
        pulse：测控系统支持的脉冲
        返回值：无
        """
        self.convert_pulses_to_pulse_seq(pulses)
