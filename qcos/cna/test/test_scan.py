from qcos.cna.core.sequencer import *
from qcos.cna.core.instrument import *
import os
    
class TestScan():
    test_chapter_dict = {
        'Doppler':'00000000 00000000 00000000', 
        'Doppler_Only':'00000000 00000000 00001111,[10000000 00000000 00000000, 1],[10000000 00000000 00010000,1]',
        'Pumping':  '01100000 11000000 00000000', 
        'Microwave': '10000000 00100000 00000000',
        'Detection':'01010000 10000000 00001111,[11000000 00000000 00000000, 1],[11000000 00000000 00010000,1]', 
        'Raman':  '11000000 10010000 00000000',
        'Zero': '11000000 10000000 00000000', 
        'Strong': '11111111 11111111 11111111', 
        'MolmerSorensen': '11000000 10010000 00000000',
    }
    try:
        fpga = InstrumentBase.find_instrument('fpga')
    except:
        fpga = FPGA('fpga', clock_period=5E-3, bytes_returned=12, port="COM5", test_time = 0.1)
        
    try:
        awg = InstrumentBase.find_instrument('awg')
    except:
        awgConfig = {
            'addr_ip': '192.168.1.1',
            'channelList': [1, 2, 3, 4]
        }
        awg = AWGMocker('awg', awgConfig=awgConfig)

    exp = Experiment(1, chapter_dict=test_chapter_dict, fpga=fpga, awg=awg, repeat=3)
    seqs = exp.new_sequence()
    seqs.set_sequence(
        awg_trigger(),
        Raman(duration=10, amp=0.1, freq=1.0, phase=0.,label='rm').on([0]),
    )

    def setup_method(self):
        GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_NONE)

    def teardown_method(self):
        GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_NONE)

    def test_scan_freq(self):
        freq_list = np.linspace(13485,13395,3)
        self.exp.freq_scan("rm", freq_list, plot_flag=False)
        assert os.path.exists(self.exp.data.DataFileName)
        
    def test_scan_time(self):
        time_list = np.linspace(10,20,3)
        self.exp.time_scan("rm", time_list, plot_flag=False)
        assert os.path.exists(self.exp.data.DataFileName)
    
    def test_scan_amp(self):
        amp_list = np.linspace(0.2,0.5,3)
        self.exp.amp_scan("rm", amp_list, plot_flag=False)
        assert os.path.exists(self.exp.data.DataFileName)
    
    def test_scan_phase(self):
        phase_list = np.linspace(0, np.pi/2,3)
        self.exp.phase_scan("rm", phase_list, plot_flag=False)
        assert os.path.exists(self.exp.data.DataFileName)
        
    def test_scan(self):
        scan_list = np.linspace(0, 1,3)
        self.seqs.labelled_pulse['rm'][0].user_param = 0.5
        self.exp.scan('user_param', "rm", scan_list, plot_flag=True)
        assert os.path.exists(self.exp.data.DataFileName)
        
    def test_scan_two_cycle(self):
        freq_list = np.linspace(13485,13395,3) #MHz
        self.exp.freq_scan("rm", freq_list, cycle=2, plot_flag=False)
        assert os.path.exists(self.exp.data.DataFileName)