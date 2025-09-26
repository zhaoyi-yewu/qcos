from qcos.cna import *
import numpy as np

# 测试序列处理
class TestSeq:
    
    test_chapter_dict = {
        'Doppler':'00000000 00000000 00000000', 
        'Doppler_Only':'00000000 00000000 00001111,[10000000 00000000 00000000, 1],[10000000 00000000 00010000,1]',
        'Pumping':  '01100000 11000000 00000000', 
        'Microwave': '10000000 00100000 00000000',
        'Detection':'01010000 10000000 00001111,[11000000 00000000 00000000, 1],[11000000 00000000 00010000,1]', 
        'Raman':  '11000000 00000000 00000000',
        'Zero': '11000000 10000000 00000000', 
        'Strong': '11111111 11111111 11111111', 
        'MolmerSorensen': '11000000 10010000 00000000',
    }
    
    param_dict = {
        'ion_number' : 2,
        'segment_number' : 3,
        'time_intervals' : [(0,17.33),(17.33, 45.66),(45.66, 87.99)],
        'data_per_ion' : {
            #第一个比特的参数表
            0 : {
                'amp': [(0.45,0.45), (0.42,0.42),(0.23,0.23)], 
                'freq': [(4+2.03,4-2.03),(4+2.03,4-2.03),(4+2.03,4-2.03)],
                'phase': [(0.48,-0.48),(0.308,-0.308),(0.086,-0.086)]
            },
            #第一个比特的参数表
            1 : {
                'amp': [(0.42,0.42),(0.23,0.23),(0.45,0.45,0.10)], 
                'freq': [(4+2.03,4-2.03),(4+2.03,4-2.03),(4+2.03,4-2.03,2.03)],
                'phase': [(0.308,-0.308),(0.086,-0.086),(-0.086,0.086,0.086)]
            }
        }
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
    exp = Experiment(2, chapter_dict=test_chapter_dict, fpga=fpga, awg=awg)
    seqs = exp.new_sequence()
    raman1 = Raman(10, amp=0.5, freq=1, phase=0, label='raman1').on(0)
    raman2 = Raman(10, amp=0.5, freq=1, phase=0, label='raman2').on(1)
    ms = MolmerSorensen(para_table=param_dict).on([0,1])
    
    def setup_method(self):
        pass
    
    def teardown_method(self):
        pass
        
    #脉冲类测试
    def test_pulse(self):
        parameters = self.raman1.parameter_list()
        assert parameters['amp'] == 0.5
        assert parameters['freq'] == 1
        assert parameters['phase'] == 0
        assert parameters['duration'] == 10
        # 实例化两比特脉冲，作用在第0,1个比特上
        assert self.ms.qubit_number == 2
        param_dict = copy.copy(self.param_dict)
        param_dict["time_intervals"] = [(0, 30)]
        self.ms.set_parameter_table(param_dict)
        assert self.ms.para_table["time_intervals"] == [(0, 30)]
        # 脉冲定义界面
        self.raman1.show()
        
    #序列类测试
    def test_seq(self):
        # 脉冲序列输入
        self.seqs.add_gates(
            awg_trigger(),
            Raman(10, amp=0.5, freq=1, phase=0, label='raman1').on(0),
            Raman(20, amp=0.5, freq=1, phase=0, label='raman2').on(1),
            sync([0, 1]), # 同步
            Raman(10, amp=0.5, freq=1, phase=0, label='raman1').on(0),
            Raman(10, amp=0.5, freq=1, phase=0, label='raman2').on(1),
            MolmerSorensen(para_table=self.param_dict).on([0,1]),
            Detection(10).on([0, 1])
        )
        assert len(self.seqs.input_list) == 8
        assert len(self.seqs.gate_sequence) == 6
        # 时序分析
        gates = self.seqs.gate_list_per_ion
        s, t, g = gates[0][0]
        assert s == 0 and t == 10
        assert g.label == 'raman1'
        # 时序同步
        s1, _, _ = gates[0][1]
        s2, _, _ = gates[1][1]
        assert s1 == s2
        # 序列chapter处理验证
        assert self.seqs.gate_sequence[0][4].chapter_data == ['110000000000000000000000']
        # 模拟信号参数处理测试，参数修改
        self.seqs.set_parameters('raman1', duration=15)
        assert self.seqs.gate_sequence[0][4].duration == 15 and self.seqs.gate_sequence[2][4].duration == 15
        self.seqs.set_parameters('raman2', batch_mode=False, amp=(0.2, 0.4), duration=(15, 20), freq=(2, 3), phase=(0, np.pi/2))        
        assert self.seqs.gate_sequence[1][4].duration == 15 and self.seqs.gate_sequence[3][4].freq == 3
        time_index, start_point, end_point = self.seqs.reformat_sequence()
        assert len(time_index) == 6
        
    #实验类测试
    def test_exp(self):
        # 实验类初始化是否正确
        assert self.exp.qubit_number == 2
        # 序列可视化
        self.exp.print_sequence()
        # 运行测试
        self.exp.send_awg_data(print_flag=True)
        res, _ = self.exp.run_once()
        assert res.shape == (100, 2)
        self.exp.save()
        
    #波形数据生成测试
    def test_wave_data(self):
        
        # 单一波形
        args = {
                "amp" : 0.3,
                "freq" : 1,
                "phase" : 0,
            }
        fc = self.seqs.func_generator(args)
        t = np.linspace(0, 1, 100)
        pulse_data = fc(t)
        assert len(pulse_data) == 100
        assert pulse_data[10] == 0.3 * np.sin(2*np.pi*t[10])
        # 多个波形叠加
        args = {
            "amp" : (0.3, 0.5),
            "freq" : (1, 2),
            "phase" : (0, np.pi),
        }
        fc = self.seqs.func_generator(args)
        t = np.linspace(0, 1, 100)
        pulse_data = fc(t)
        assert len(pulse_data) == 100
        assert pulse_data[10] == 0.3 * np.sin(2*np.pi*t[10]) + 0.5 * np.sin(2*np.pi*2*t[10] + np.pi)
        # 分段函数波形生成
        self.seqs.set_sequence(
            awg_trigger(),
            MolmerSorensen(para_table=self.param_dict).on([0,1])
        )
        awg_data = self.seqs.generator_awg_waveform()
        assert len(awg_data) == 2
        assert len(awg_data[0][0]) == 3

    # raman数据生成
    def test_raman_data(self):
        # 脉冲序列输入
        seqs = self.exp.new_sequence()
        seqs.add_sync = True
        seqs.set_sequence(
            awg_trigger(),
            Raman(10, amp=0.5, freq=1, phase=0, label='raman1').on([0]),
            Raman(20, amp=0.5, freq=1, phase=0, label='raman2').on([1]),
        )
        ch1, ch2, awg_format = seqs.get_atom_awg_data()
        print(ch1, ch2, awg_format)
        assert len(ch1) == 2
        assert ch1[0] == 'raman_x_0'
        assert len(ch2) == 2
        assert ch2[1] == 'raman_y_1'
        assert len(awg_format) == 2
        assert len(awg_format[0]) == 1
        assert len(awg_format[0][0]) == 2

    def test_raman_seg(self):
        ram = Raman(10, amp=(0.5, 1), freq=(1, 2), phase=(0, 0), segment_number=2, time_intervals=[(0, 5), (5, 10)])
        assert ram.segment_flag
        ram.plot_wave(save_fig=True, filename='ram.png')
        ram.on(1)
        ram.on(0)
        d = ram.snapshot()
        assert d['duration'] == 10
        ram.save_as_html('ram.html')
        self.seqs.set_sequence(
            awg_trigger(),
            ram
        )
        data_list = self.seqs.generator_awg_waveform()
        assert len(data_list) == 2

    def test_raman_type_err(self):
        ram = Raman(10, amp='s', freq=1, phase=0)
        try:
            ram.plot_wave()
        except:
            pass

    def test_hw_exp(self):
        GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_HW_FPGA_AWG)
        Exp_chapter_dict = {
            'Raman': '11000000 00000000 00000000',
            'Detection': '01010000 00000000 00001111',
        }
        camera_ins = get_camera_mocker()

        try:
            awg = InstrumentBase.find_instrument('hw_awg_test')
        except:
            awgConfig = {
                "product": "M3201A",
                "serialNumber": "MY63400261",
                "channelList": [1, 2, 3, 4],
                "samplingRateMHz": 5,
                "amp": 0.5
            }
            awg = AWGMocker("hw_awg_test", awgConfig=awgConfig)
        try:
            nido = InstrumentBase.find_instrument('nido')
        except:
            nido = NI("nido", dev=['test'], type=2, rate=100)
        try:
            niao = InstrumentBase.find_instrument('niao')
        except:
            niao = NI("niao", dev=["test"], type=3, rate=100, num_samples=1, trigger_source='trigger_source')
        rea = ReArrangementMocker(qpu_file = 'test/na_file.json')
        a, b, c, d = [3, 5, 9, 11]
        target = []
        for i in range(a, b):
            for j in range(c, d):
                target += [i, j]
        rea.target = target
        test_exp = Experiment(200, chapter_dict=Exp_chapter_dict, repeat=3, awg=awg, nido=nido, niao=niao,
                              camera=camera_ins, rea=rea, load_time=0)
        test_exp.set_threshold(100, 3)
        test_exp_seq = test_exp.new_sequence()
        test_exp_seq.set_sequence(
            awg_trigger(),
            Raman(10, amp=0.5, freq=1, phase=0, label='raman1').on(0),
        )
        res, rea_res = test_exp.run_once(c1_time=10)
        assert len(res) == 3 and len(res[0]) == 200
        assert len(rea_res) == 3 and len(rea_res[0]) == 200
        GlobalSetting.set_instrument_type(InstrumentType.INSTRUMENT_NONE)
