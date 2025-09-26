from qcos.cna.core.instrument.fpga import FPGA
from qcos.cna.core.instrument.awg import AWG
from qcos.cna.core.instrument.awgmocker import AWGMocker
from qcos.cna.core.instrument.error import *
from qcos.cna.core.sequencer import *
from qcos.cna.core.instrument.instrument_base import InstrumentBase
import pickle

class TestHardware():
    
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
    
    awgConfig = {
        'addr_ip': '192.168.1.1',
        'channelList': [1,2,3,4]
    }

    def test_hardware_define(self):
        try:
            fpga = FPGA('test_fpga', bytes_returned=12, test_time = 0)
        except DeveiceParameterError as e:
            assert e.code == 404
            assert e.msg == 'Please specify the serial port for communication'
            
        try:
            awg = AWGMocker('test_awg', awgConfig=self.awgConfig)
        except DeveiceConnectionError as e:
            assert e.code == 402
            assert e.msg == "awg connect failed, The input is neither a valid IP address nor in the '/dev/xxx' format"
    
            
    def test_redefine(self):
        try:
            fpga = InstrumentBase.find_instrument('fpga')
        except:
            fpga = FPGA('fpga', clock_period=5E-3, bytes_returned=12, port="COM5", test_time = 0.1)
            
        try: 
            fpga = FPGA('fpga', clock_period=5E-3, bytes_returned=12, port="COM5", test_time = 0.1)
        except DeveiceDefineError as e:
            assert e.code == 401
            assert e.msg == "Another instrument has the name: fpga"
        fpga.close()
    
    def test_fpga(self):
        
        try:
            fpga = InstrumentBase.find_instrument('fpga')
        except:
            fpga = FPGA('fpga', clock_period=5E-3, bytes_returned=12, port="COM5", test_time = 0.1)
        
        assert fpga != None
        send_data = [['00000000 11000000 00000000', 10],
                    ['11000000 11000000 00000000', 10],
                    ['11000000 10000000 00000000', 10],
                    ['01010000 00000000 00001111', 100],
                    ['11000000 00000000 00000000', 1.0],
                    ['11000000 00000000 00010000', 1.0]
        ]
        res = fpga.comm(send_data, repeat = 10)
        assert len(res) == 10
        assert isinstance(res[0], np.float64)
        fpga.show()
        fpga.save_as_html("fpga.html")

    def test_awg(self):
        try:
            awg = AWGMocker('awg_error')
        except DeveiceParameterError as e:
            assert 'config' in str(e)

        awgConfig = {
            'channelList': [1, 2, 3, 4],
            'addr_ip': '192.1.'
        }
        try:
            awg = AWGMocker('awg_error', awgConfig=awgConfig)
        except DeveiceConnectionError as e:
            assert 'valid IP' in str(e)

        try:
            awg = InstrumentBase.find_instrument('awg')
        except:
            awg = AWGMocker('test_awg', awgConfig=self.awgConfig)

        assert awg != None
        send_data = np.array([1, 2, 3])
        res = awg.send([send_data], channelList=[1])
        assert res == None

    def test_access(self):
        try:
            InstrumentBase.find_instrument('fpga1')
        except DeveiceAccessError as e:
            assert e.code == 405
            assert e.msg == "Instrument with name fpga1 does not exist"

        ff = FPGA('test_fpga', clock_period=5E-3, bytes_returned=12, port="COM5", test_time=0.1)
        assert ff != None
        ff1 = InstrumentBase.find_instrument('test_fpga')
        assert ff1.name == 'test_fpga'

    def test_save(self):
        fpga = FPGA('test_fpga2', clock_period=5E-3, bytes_returned=12, port="COM5", test_time=0.1)
        assert fpga != None
        fpga.save()
        with open("./test_fpga2.pickle", "rb") as file:
            fpga2 = pickle.load(file)
            assert fpga2.name == 'test_fpga2'

    def test_ni_do(self):
        ni = NI('test_nido', dev=['test'], type=2, rate=1e4)
        do_signal = [(0, 0), (0.5, 1), (1, 1)]
        do_data = ni.ttl_package_from_signal(do_signal)
        assert len(do_data) == 11
        assert do_data[-1] == 1
        assert do_data[0] == 0
        assert do_data[5] == 1
        ni.send([do_signal])
        data = ni.get_all_do()
        assert len(data) == 16
        assert len(data[0]) == 8651

    def test_ni_ao(self):
        ni = NI('test_niao', dev=['test'], type=3, rate=1e4)
        ao_signal = [(0, 1), (1, 10)]
        ao_data = ni.ao_package_from_signal(ao_signal)
        assert len(ao_data) == 11
        assert ao_data[0] == 1.0
        assert ao_data[-1] == 10.0
        ni.send([ao_signal])
        data = ni.get_all_ao()
        assert len(data) == 7
        assert len(data[0]) == 8651

    def test_awg_send_data(self):
        try:
            awg = InstrumentBase.find_instrument('awg')
        except:
            awg = AWGMocker('test_awg', awgConfig=self.awgConfig)

        try:
            awg.setRamanWave([1])
        except Exception as e:
            print(e)
            assert 'donot match number of channels' in str(e)

        awg.setRamanWave([[1], [2]], channelList=[1, 2])
        awg.startMultipChannel(channelList=[1, 2])
        try:
            awg.setArrangeWave([1])
        except Exception as e:
            assert 'donot match number of channels' in str(e)
        awg.setArrangeWave([[1], [2]], channelList=[1, 2])
        awg.holding([1, 2])
        try:
            awg.send([1])
        except Exception as e:
            assert 'donot match number of channels' in str(e)

    def test_delay(self):
        awg1 = AWGMocker('awg1', awgConfig=self.awgConfig, delay=0.1)
        awg2 = AWGMocker('awg2', awgConfig=self.awgConfig, delay=0.2)
        awg3 = AWGMocker('awg3', awgConfig=self.awgConfig, delay=0.3)
        # 需要同步的设备列表
        sync_ins = [awg1, awg2, awg3]
        # 计算要达到同步，发送给每个awg的信号需要延迟多久
        assert awg1.delay_sync(sync_ins) == 0.2
        assert awg2.delay_sync(sync_ins) == 0.1
        assert awg3.delay_sync(sync_ins) == 0
