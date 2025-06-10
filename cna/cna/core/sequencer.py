from typing import Optional
from matplotlib import pyplot as plt
import copy
import numpy as np
from qcos.cna.core.pulse import *
import qcos.cna.core.data as cna_data
from qcos.cna.core.gui import scan_generator_pop
from pathlib import Path
import math
import time
from .config import GlobalSetting
from functools import partial
import json
from qcos.cna.core.instrument import *
import os
from qcos.cna.core.config import InstrumentType
from qcos.config.qcos_config_manager import qcos_configer

# 定义空序列，供doppler和pumping使用
empty = []

# all 在每次定义新的Experiment对象时都会对应改变为[0, 1, ..., ion_number-1]
# 比如: exp1 = Experiment(ion_number = 5, ...)时，all会自动变为[0,1,2,3,4]
all = []


def split_array(arr, n):
    remainder = len(arr) % n
    if remainder != 0:
        arr = arr[:-remainder]
    return arr.reshape(-1, n)


class ExpEncoder(json.JSONEncoder):
    """
    json编码器，用于做数据格式转换，以便可保存到文件中
    """

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, InstrumentBase):
            # print(obj)
            res = obj.snapshot()
            if 'attr_dict' in res: res.pop('attr_dict')
            return res
        elif isinstance(obj, Sequence):
            return obj.__dict__['input_list']
        elif isinstance(obj, BasePulse):
            return obj.snapshot()
        elif isinstance(obj, cna_data.DataDoc):
            return obj.__dict__
        else:
            print(obj)
            return json.JSONEncoder.default(self, obj)


# 用于离子阱实验的主类，每次开始新的实验都应该创建一个Experiment实例。
# 例如：exp = Experiment(2, chapter_dict = FPGA_dict, port = 'COM3')
# 表示开始一次实验，此实验中离子数为2，FPGA对应的chapter表为FPGA_dict, 端口号为COM3
class Experiment:
    """
    实验类
    Args:
        qubit_number: 实验过程中用到的比特数
        chapter_dict: chapter字典
        fpga: 中控设备实例，debug模式可不传
        awg: awg实例，debug模式可不传
        nido: do板卡实例
        niao: ao板卡实例
        rea: 重排实例
        repeat: 运行shots数
        threshold:灰度阈值
        threshold_block:统计的像素点个数
        load_time:每个shot执行完后的等待时间

    """

    def __init__(self, qubit_number=-1, chapter_dict=None, fpga=None, awg=None, nido=None, niao=None,
                 camera=None, rea=None, repeat=100, threshold=100, threshold_block=3, load_time=1, **kwargs):
        self.qubit_number = qubit_number
        # self.rf_pick = rf_pick
        self.mode_frequency = np.random.random(qubit_number)
        # self.melt_status = melt_status
        # self.Lamb_Dicke_parameter = eta
        self.repeat = repeat
        self.ext_trig = 1
        # Different version of FPGA could have different bytes_returned. If FPGA doesn't work as expected, please check whether bytes_returned is correcly setted.
        self.awg_switch = False
        self.camera_switch = False
        self.threshold = threshold
        self.threshold_block = threshold_block
        self.state_flag = False
        self.awg_interface = None
        self.load_time = load_time

        self.__chapter_dict = None
        if chapter_dict is not None:
            self.__chapter_dict = self._prev_process_chapter(chapter_dict)
        else:
            print(
                'Warning! You did not specify the chapter data for this experiments, the FPGA utility will be deactivated.')

        # 一次实验可以创建多个Sequence，全部存储在seq_list里面
        self.seq_list = []
        self.last_sequence = Sequence(qubit_number=qubit_number, chapter_dict=self.__chapter_dict)
        global all
        all = []
        [all.append(i) for i in range(qubit_number)]
        self.all = list(range(qubit_number))

        assert (isinstance(qubit_number, int) and qubit_number >= 1)
        # assert(isinstance(melt_status, bool))

        # debug模式下：
        ### 假装PC连接了底层各类硬件，并且将“实验文件”保存至当前目录下的test_datafile_dir文件夹里
        # 实验模式下：
        ### 结束上一次实验的串口连接，并且为本次实验新建串口通讯
        ### 连接awg的以太网地址
        self.data = cna_data.DataDoc(disk_path=GlobalSetting.get_datapath())
        if GlobalSetting.get_instrument_type() == InstrumentType.INSTRUMENT_NONE:
            '''
            #self.data = cna_data.DataDoc(disk_path=r'test_datafile_dir',debug_mode=GlobalSetting.get_instrument_type())
            print("/********************\nCaution! You are using debug mode. \
This enables you to test some functions locally. But you cannot access the actual hardware in this mode.\n********************/")
            '''
            pass
        elif GlobalSetting.get_instrument_type() == InstrumentType.INSTRUMENT_HW_FPGA_AWG:
            # 可通过fpga或者ni板卡连接
            assert fpga != None or nido != None
            self.fpga = fpga
            self.nido = nido
            if self.nido != None:
                assert niao != None and camera != None
            self.niao = niao
            if awg != None:
                self.awg_switch = True
                self.awg_interface = awg
            if camera != None:
                self.camera_switch = True
                self.camera = camera
                print("""Camera is enabled.""")
            # 重排实例类
            if rea is not None:
                self.rea = rea
        else:
            pass

    def send_to_awg(self, sequence):
        """
        发送波形数据给awg，一般在类内部调用
        Args:
            sequence: 需要发送的序列
        """
        if sequence.awg_trigger == True and self.awg_interface != None:
            sequence.perform_sequence_awg()
            self.awg_interface.send(sequence.awg_data, loop=0)
            # time.sleep(1)

    ################################## TEMP ###############################################

    def update_chapter_dict(self, chapter_dict):
        """
        更新实验中的chapter字典
        Args:
            chapter_dict:新的chapter字典
        """
        self.__chapter_dict = self._prev_process_chapter(chapter_dict)

    # 在Experiment里创建一个新的Sequence实例
    def new_sequence(self):
        """
        创建一个新的序列，该序列添加在末尾
        """
        sampling_rate = qcos_configer.get_awg_sampling_rate()
        if self.awg_interface is not None:
            sampling_rate = self.awg_interface.samplingRateMHz
        row, column = qcos_configer.get_row_num(), qcos_configer.get_col_num()
        if hasattr(self, 'rea'):
            row, column = self.rea.row, self.rea.column
        seq = Sequence(qubit_number=self.qubit_number, chapter_dict=self.__chapter_dict, sampling_rate=sampling_rate,
                       row=row, column=column)
        self.seq_list.append(seq)
        self.last_sequence = seq
        return seq

    def _prev_process_chapter(self, chapter_dict):
        """
        chapter字典的格式处理，如去掉空格
        Args:
            chapter_dict: chapter字典
        """
        out_dict = {}
        for k, v in chapter_dict.items():
            st = v.replace(' ', '')
            chapter_data_list = []
            while st != '':
                lbracket_pos = st.find('[')
                rbracket_pos = st.find(']')
                if lbracket_pos == 0:
                    comma_pos = st.find(',')
                    assert comma_pos == 25
                    assert rbracket_pos > 26
                    sub_str_1 = st[1:25]
                    sub_str_2 = st[26:rbracket_pos]
                    chapter_data_list.append((sub_str_1, float(sub_str_2)))
                    st = st[rbracket_pos + 2:]
                else:
                    chapter_data_list.append(st[0:24])
                    st = st[25:]
            assert out_dict.get(k) == None
            out_dict[k] = chapter_data_list
        return out_dict

    def scan_generator(self, scan_list, ranges, sequence):
        """
        扫描函数生成器，用以生成扫描时需要的参数更新函数

        Args:
            scan_list: 脉冲标签列表
            ranges: 参数取值列表
            sequence: 扫描的序列
        """
        n = self.qubit_number
        # assert len(scan_list) == len(ranges)
        # Independently scan durations

        scan_ranges = ranges

        def update_value(key, value):
            if isinstance(scan_list, str):
                now_scan_list = [scan_list]
            for label in now_scan_list:
                if key == 'amp':
                    sequence.set_parameters(label=label, amp=value, batch_mode=True)
                elif key == 'phase':
                    sequence.set_parameters(label=label, phase=value, batch_mode=True)
                elif key == 'freq':
                    sequence.set_parameters(label=label, freq=value, batch_mode=True)
                elif key == 'duration':
                    sequence.set_parameters(label=label, duration=value, batch_mode=True)
                else:
                    sequence.set_user_defined_parameters(label=label, key=key, value=value)
            # sequence.update_hardwares(scan_list)
            sequence.regenerate_sequence()
            self.send_to_awg(sequence)
            # Run experiment
            raw_counts = self.run_once(sequence=sequence)[0]
            counts = sum(raw_counts) / self.repeat
            self.data.append_raw_data(value, raw_counts)
            return counts

        return scan_ranges, update_value

    def time_scan(self, scan_list, ranges, sequence=None, cycle=1, plot_flag=True, save_fig=False):
        """
        时间扫描函数
        Args:
            scan_list: 脉冲标签列表
            ranges: 参数取值列表
            sequence: 扫描的序列，默认为实验中的最后一个序列
            cycle: 需要扫描的次数.
            plot_flag: 是否需要实时显示扫描数据图.
        """
        self.scan('duration', scan_list=scan_list, ranges=ranges, sequence=sequence, cycle=cycle, plot_flag=plot_flag,
                  title="TimeScan", xtype="Duration", save_fig=save_fig)

    def freq_scan(self, scan_list, ranges, sequence=None, cycle=1, plot_flag=True, save_fig=False):
        """
        频率扫描函数，参数同上
        """
        self.scan('freq', scan_list=scan_list, ranges=ranges, sequence=sequence, cycle=cycle, plot_flag=plot_flag,
                  title="FreqScan", xtype="Frequency", save_fig=save_fig)

    def amp_scan(self, scan_list, ranges, sequence=None, cycle=1, plot_flag=True, save_fig=False):
        """
        幅度扫描函数，参数同上
        """
        self.scan('amp', scan_list=scan_list, ranges=ranges, sequence=sequence, cycle=cycle, plot_flag=plot_flag,
                  title="AmpScan", xtype="Amp", save_fig=save_fig)

    def phase_scan(self, scan_list, ranges, sequence=None, cycle=1, plot_flag=True, save_fig=False):
        """
        相位扫描函数，参数同上
        """
        self.scan('phase', scan_list=scan_list, ranges=ranges, sequence=sequence, cycle=cycle, plot_flag=plot_flag,
                  title="PhaseScan", xtype="Phase", save_fig=save_fig)

    def scan(self, key, scan_list, ranges, sequence=None, cycle=1, plot_flag=True, title=None, xtype=None,
             save_fig=False):
        """
        通用扫描函数
        Args:
            key: 扫描的变量名
            scan_list: 脉冲标签列表
            ranges: 参数取值列表
            sequence: 扫描的序列，默认为实验中的最后一个序列
            cycle: 需要扫描的次数.
            plot_flag: 是否需要实时显示扫描数据图.
            title: 扫描数据存储标签
            xtype: 扫描数据x轴标签
            save_fig: 是否保存图片
        """
        if sequence == None:
            sequence = self.last_sequence
        assert sequence != None
        self.data.title = title if title is not None else key
        self.data.reset_raw_data(xtype=xtype if xtype is not None else key)
        scan_ranges, update_value = self.scan_generator(scan_list, ranges, sequence)
        update_key = partial(update_value, key)
        if plot_flag:
            scan_generator_pop(func=update_key, scan_list=scan_ranges, title=key, cycle=cycle, dims=self.qubit_number,
                               plot_flag=plot_flag)
        else:
            for c in range(cycle):
                y = []
                for v in ranges:
                    y.append(update_key(v))
                y = np.array(y).T
                if save_fig:
                    self.save_scan_fig(ranges, y, key, f'{self.data.path_prefix}/{c + 1}.png')

        self.data.generate_json()
        return

    def interactive_scan(self, key, scan_list, ranges, sequence=None, cycle=1, title=None, xtype=None):
        """
        通用扫描函数
        Args:
            key: 扫描的变量名
            scan_list: 脉冲标签列表
            ranges: 参数取值列表
            sequence: 扫描的序列，默认为实验中的最后一个序列
            cycle: 需要扫描的次数.
            plot_flag: 是否需要实时显示扫描数据图.
            title: 扫描数据存储标签
            xtype: 扫描数据x轴标签
        """

        if sequence == None:
            sequence = self.last_sequence
        assert sequence != None
        self.data.title = title if title is not None else key
        self.data.reset_raw_data(xtype=xtype if xtype is not None else key)
        scan_ranges, update_value = self.scan_generator(scan_list, ranges, sequence)
        update_key = partial(update_value, key)

        all_y = []
        for c in range(cycle):
            y = []
            for v in ranges:
                y.append(update_key(v))
            y = np.array(y).T
            all_y.append(y)

        print(f'交互式扫描选项\n\t[1]:保存最终扫描结果\n\t[2]:保存扫描过程\n\t[3]:扫描累积数据均值\n\t[q]:退出')
        while True:
            i = input("请选择操作:")
            if i == 'q':
                break
            elif i == '1':
                path = f'{self.data.path_prefix}/{key}'
                if not os.path.exists(path):
                    os.makedirs(path)
                for c in range(cycle):
                    self.save_scan_fig(ranges, all_y[c], key, f'{path}/{c + 1}.png')
                print(f"最终结果已保存至{path}")
            elif i == '2':
                for c in range(cycle):
                    path = f'{self.data.path_prefix}/{key}-{c + 1}'
                    if not os.path.exists(path):
                        os.makedirs(path)
                    for i in range(1, len(ranges) + 1):
                        self.save_scan_fig(ranges, all_y[c], key, f'{path}/{i}.png', i)
                    print(f"第{c + 1}次扫描结果已保存至{path}")
            elif i == '3':
                path = f'{self.data.path_prefix}/{key}-ave'
                if not os.path.exists(path):
                    os.makedirs(path)
                for c in range(cycle):
                    self.save_scan_fig(ranges, sum(all_y[:c + 1]) / (c + 1), key, f'{path}/ave-{c + 1}.png')
                print(f"累积数据均值结果已保存至{path}")
            else:
                print(f'仅支持以下操作\n\t[1]:保存最终扫描结果\n\t[2]:保存扫描过程\n\t[3]:扫描累积数据均值\n\t[q]:退出')
        return

    def save_scan_fig(self, x, y, xlabel, filename, end=None):
        plt.figure()
        if end is None: end = len(x)
        if end != len(x):
            dx = x[1] - x[0]
            plt.xlim(x[0] - dx / 5, x[-1] + dx / 5)
        plt.xlabel(xlabel)
        for i, y_i in enumerate(y):
            plt.plot(x[:end], y_i[:end], label=f'Plot {i}', marker='o')
        plt.legend()
        plt.savefig(filename)
        plt.close()

    def print_sequence(self, size=(10, 4), sequence=None, remap_time=False, save_fig=False):
        """
        序列可视化展示
        Args:
            size (tuple, optional): 画布的大小. Defaults to (10, 4).
            sequence (_type_, optional): 需要可视化的序列， 默认为实验中的最后一个序列.
            remap_time (bool, optional): 是否需要对时间轴做缩放. Defaults to False.
            save_fig (bool): 是否保存图片
        """
        if sequence == None:
            sequence = self.last_sequence
        assert sequence != None
        # figure = plt.figure(figsize=size)
        plot_sequence(sequence.gate_sequence, remap_time=remap_time, auto_size=False, given_size=size)
        plt.tight_layout()
        if save_fig:
            plt.savefig(f"{self.data.path_prefix}sequence.png")
        else:
            plt.show()
        pass

    def save(self, name=None, path=None):
        """
        以json格式保存实验
        Args:
            name (_type_, optional): 文件名. Defaults to None.
            path (_type_, optional): 保存的路径. Defaults to None.
        """
        if name is None: name = 'exp' + time.strftime("-%H%M%S")
        if path is None: path = GlobalSetting.get_datapath()
        save_path = f'{path}/{name}.json'
        with open(save_path, 'w') as f:
            v = self.__dict__.copy()
            v.pop('last_sequence')
            if hasattr(self, 'camera'):
                v.pop('camera')
            f.write(json.dumps(v, cls=ExpEncoder))

    # hardware related functions

    def send_awg_data(self, sequence=None, print_flag=False):
        """
        发送波形数据给awg，一般在类外部调用
        Args:
            sequence (_type_, optional): 需要上传数据的序列，默认为实验中的最后一个序列.
            print_flag (bool, optional): 是否可视化展示波形数据. Defaults to False.
        """
        if sequence == None:
            sequence = self.last_sequence
        assert sequence != None
        sequence.perform_sequence_awg()
        if print_flag:
            fig, axs = plt.subplots(nrows=1, ncols=self.qubit_number, figsize=(27, 6))
            i = 0
            for ax in axs:
                ax.plot(sequence.awg_data[i])
                i += 1
            plt.show()
        if GlobalSetting.get_instrument_type() == InstrumentType.INSTRUMENT_HW_FPGA_AWG:
            if sequence.awg_trigger == True and self.awg_interface != None:
                self.awg_interface.send(sequence.awg_data, print_flag=print_flag)
            else:
                print("Caution! You are trying to send awg data while no awg interface defined. Check the ip address?")

    def run_once(self, sequence=None, **kwargs):
        """
        运行实验中的序列
        Args:
            sequence (_type_, optional): 需要运行的序列，默认为实验中的最后一个序列.
        """
        return self.run_once_pmt(sequence, **kwargs)

    def run_once_pmt(self, sequence=None, **kwargs):
        """
        运行实验中的序列，在debug模式下返回随机生成的数据，否则通过fpga接口进行硬件上的运行
        Args:
            sequence (_type_, optional): 需要运行的序列，默认为实验中的最后一个序列.
        """
        if sequence == None:
            sequence = self.last_sequence
        assert sequence != None
        # 如果处于实验模式下，将编码后的数据通过串口发送给FPGA，并读取FPGA的返回结果至result

        if GlobalSetting.get_instrument_type() == InstrumentType.INSTRUMENT_HW_FPGA_AWG:

            # 生成门的awg信号, 提前发送ch3，ch4的信号
            c1_time = kwargs.get('c1_time', 1200e-6) * 1e6
            ch1_data, ch2_data, awg_format = sequence.get_atom_awg_data()
            ch3_data, ch4_data = self.awg_interface.generator.generateFullWave(c1_time, awg_format)
            raman_channelList = kwargs.get('raman_channelList', [1, 2, 3, 4])
            self.awg_interface.sendSingleChannel(ch3_data, channelID=raman_channelList[2], trigger='externalcycle',
                                                 cycles=self.repeat)
            self.awg_interface.sendSingleChannel(ch4_data, channelID=raman_channelList[3], trigger='externalcycle',
                                                 cycles=self.repeat)

            # print(pulses)
            if self.camera_switch:
                self.camera.camera.start_acquisition()
            result = []
            rea_result = []
            if self.nido is not None:
                # 先上传do, ao信号
                self.niao.send([[]])
                self.nido.send([[]])
                rea_channelList = kwargs.get('rea_channelList', [1, 2])
                rea_amp = kwargs.get('rea_amp', 0.4)

                # 执行repeat次
                for _ in range(self.repeat):
                    # 控制信号任务启动
                    self.niao.start()
                    self.nido.start()
                    # 获取原子捕获照片
                    self.camera.capture_image()
                    # 进行原子重排
                    atom = self.camera.get_status_with_threshold(self.threshold, self.threshold_block)
                    x_data, y_data = self.rea.transport(atom)
                    # 发送awg信号
                    self.awg_interface.setArrangeWave([x_data, y_data], channelList=rea_channelList, amp=rea_amp)
                    self.awg_interface.startMultipChannel(channelList=rea_channelList)
                    # 获取原子重排后照片
                    self.camera.capture_image()
                    rea_result += self.camera.get_status_with_threshold(self.threshold, self.threshold_block)
                    self.awg_interface.setRamanWave([ch1_data, ch2_data], channelList=raman_channelList[:2])
                    self.awg_interface.startMultipChannel(channelList=raman_channelList[:2])
                    # 最后获取结果
                    self.camera.capture_image()
                    result += self.camera.get_status_with_threshold(self.threshold, self.threshold_block)
                    # 控制信号任务结束
                    self.niao.stop()
                    self.nido.stop()
                    time.sleep(self.load_time)
            else:
                ch1_data, ch2_data, awg_format = sequence.get_atom_awg_data()
                self.awg_interface.send([ch1_data, ch2_data], channelList=[1, 2])
                result = self.fpga.comm([], **self.__dict__)
                if self.camera_switch:
                    result = []
                    for _ in range(self.repeat):
                        result += self.camera.read_and_count()
                rea_result = result
            if self.camera_switch:
                self.camera.camera.abort_acquisition()

        # 如果处于debug模式下，则是直接生成相应长度的随机序列，存入result中
        else:
            result = np.zeros(self.qubit_number * self.repeat)
            rea_result = np.zeros(self.qubit_number * self.repeat)
            for i in range(self.repeat):
                for j in range(self.qubit_number):
                    result[i * self.qubit_number + j] = np.random.rand()
                    # result = np.random.rand(self.ion_number*self.repeat)
            time.sleep(0.005)
        return split_array(np.array(result), self.qubit_number), split_array(np.array(rea_result), self.qubit_number)

    def set_threshold(self, threshold, threshold_block=3):
        """亮态阈值设置
        Args:
            threshold (float): 灰度阈值
            threshold_block: 有效像素点个数
        """
        self.threshold = threshold
        self.threshold_block = threshold_block


class Sequence:
    """
    序列类
    Args:
        qubit_number (int, optional): 序列中用到的比特数. Defaults to 5.
        chapter_dict (_type_, optional): chapter字典，用以生成控制信号. Defaults to None.
        sampling_rate (int, optional): awg采样率，用以生成波形数据. Defaults to 500.
    """

    def __init__(self, qubit_number=64, chapter_dict=None, sampling_rate=500,
                 add_sync=False, row=8, column=8):
        self.awg_sampling_rate = sampling_rate  # unit: MHz /default: 500 MHz
        self.awg_trigger = False
        self.awg_trigger_time = -1  # awg_trigger打开的时间
        self.current_time = 0  # 表示上一个门结束的时间
        self.input_list = []
        self.set_para_flag = False
        self.gate_sequence = []
        self.qubit_number = qubit_number  # total qubits
        self.time_stamp = [0 for i in range(self.qubit_number)]
        # self.gate_list = []
        self.gate_list_per_ion = [[] for i in range(qubit_number)]
        self.labelled_pulse = {}
        self.awg_data = None
        self.real_chapter_dict = chapter_dict
        self.add_sync = add_sync
        # 中性原子阵列大小
        self.row = row
        self.column = column

    def set_parameters(self, label=None, duration=None, amp=None, freq=None, phase=None, batch_mode=True,
                       regenerate_sequence=True):
        """
        修改脉冲的参数，主要针对脉冲的四个基础参数：持续时间、幅度、频率、初始相位

        Args:
            label (list, optional): 需要修改的脉冲的标签
            duration (_type_, optional): 脉冲持续时间. Defaults to None.
            amp (_type_, optional): 脉冲幅度. Defaults to None.
            freq (_type_, optional): 脉冲频率. Defaults to None.
            phase (_type_, optional): 脉冲初始相位. Defaults to None.
            batch_mode (bool, optional): 是否批量修改. Defaults to True.
            regenerate_sequence (bool, optional): 修改完后是否重新做分析，如修改完持续时间后需要重新做时序分析. Defaults to True.

        batch_mode = True时程序会无条件将相同的参数赋值给每一个pulse，如
        set_parameters(label='rx0', duration=100, amp = (10,20))
        set_parameters(label='rx0', duration=100, amp = (10,20), batch_mode = True)
        表示将所有label为'rx0'的gate的duration设为100，amp设为(10,20)

        batch_mode == False的情况主要是用于同时对多个相同标签的gate的参数赋值，如
        set_parameters(label='raman', amp=(300,200), batch_mode = False)
        要求本序列中有两个脉冲为raman标签，认为用户是想把amp=300和amp=200分别赋值给这两个脉冲

        list用于描述分段函数（即一个脉冲分为多个时间段）
        """
        assert label != None

        if self.labelled_pulse.get(label) == None:
            raise KeyError(f'sequence has no pulse named {label}')

        self.set_para_flag = True

        gate_category = -1
        for gate in self.labelled_pulse[label]:
            if isinstance(gate, AWGMultiPulse):
                # 专用于多离子纠缠的AdvancePulse
                assert gate_category in {-1, 2}
                gate_category = 2
            else:
                # 用于单离子的BasePulse
                assert gate_category in {-1, 1}
                gate_category = 1

        if gate_category == 1:
            all_paras = [duration, amp, freq, phase]
            num = len(self.labelled_pulse[label])
            para_names = ['duration', 'amp', 'freq', 'phase']
            if num > 1:
                if batch_mode == False:
                    for idx, para in enumerate(all_paras):
                        if para != None:
                            try:
                                assert type(para) == tuple
                                assert len(para) == num
                            except Exception as e:
                                print(
                                    "Error during setting parameters! The shape of \'{}\' does not match the number of pulses {}".format(
                                        para_names[i], num))
                                raise e

            for i in range(4):
                para = all_paras[i]
                if para != None:
                    if batch_mode == False:
                        if type(para) != tuple:
                            para = [para for j in range(num)]
                        # print('i, para: ',i, para)
                        # print(num)
                        assert len(para) == num
                        for j in range(num):
                            if para[j] != None:
                                if not hasattr(self.labelled_pulse[label][j], para_names[i]):
                                    raise RuntimeError(f'pulse {label} has no attribute "{para_names[i]}"')
                                setattr(self.labelled_pulse[label][j], para_names[i], copy.copy(para[j]))
                    else:  # batch_mode : allocate identical parameters to all pulses
                        for j in range(num):
                            if not hasattr(self.labelled_pulse[label][j], para_names[i]):
                                raise RuntimeError(f'pulse {label} has no attribute "{para_names[i]}"')
                            setattr(self.labelled_pulse[label][j], para_names[i], copy.copy(para))

        if regenerate_sequence == True:
            self.regenerate_sequence()
            self.set_para_flag = False

    def set_user_defined_parameters(self, label, key, value):
        """
        脉冲中用户自定义参数的修改，此函数只能将相同的参数赋值给每一个标签为label的脉冲

        Args:
            label (_type_): 脉冲标签
            key (_type_): 参数名称
            value (_type_): 需要修改的值
        """
        if self.labelled_pulse.get(label) == None:
            raise KeyError(f'sequence has no pulse named {label}')
        for i in range(len(self.labelled_pulse[label])):
            if not hasattr(self.labelled_pulse[label][i], key):
                raise KeyError(f'pulse has no attribute named {key}')
            setattr(self.labelled_pulse[label][i], key, value)

    def __add_gate(self, gate):
        """
        脉冲时序分析
        根据脉冲的作用比特、延迟，以及ASAP，求出脉冲的起始时间
        根据脉冲的起始时间以及持续时间计算出结束时间，并更新作用比特对应的时间，以便对后续脉冲进行分析

        Args:
            gate (_type_): 需要分析的脉冲
        """
        if self.real_chapter_dict is not None:
            gate.chapter_data = self.real_chapter_dict[gate.pulse_type]

        if isinstance(gate, (LaserPulse, AWGPulse)):
            ion = gate.ion_index

            assert ion is not None
            tn = gate.duration
            tl = gate.latency
            if gate.label is not None:
                if self.labelled_pulse.get(gate.label) is not None:
                    self.labelled_pulse[gate.label].append(gate)
                else:
                    self.labelled_pulse[gate.label] = [gate]

            if isinstance(ion, int):
                self.gate_sequence.append((ion, self.time_stamp[ion] + tl, tn, gate.pulse_type, gate))
                self.time_stamp[ion] += tn + tl
                self.current_time = self.time_stamp[ion]
                if isinstance(gate, AWGPulse):
                    assert self.awg_trigger is True
                    self.gate_list_per_ion[ion].append((self.time_stamp[ion] - tn, tn, gate))
            else:
                tmax = -1
                if ion == empty:
                    ion = all
                for single_ion in ion:
                    tmax = max(tmax, self.time_stamp[single_ion])
                self.gate_sequence.append((ion, tmax + tl, tn, gate.pulse_type, gate))
                for single_ion in ion:
                    self.time_stamp[single_ion] = tmax + tn + tl
                    if isinstance(gate, AWGPulse):
                        assert self.awg_trigger is True
                        self.gate_list_per_ion[single_ion].append((self.time_stamp[single_ion] - tn, tn, gate))
                self.current_time = tmax + tn + tl
        else:
            assert isinstance(gate, AWGMultiPulse)
            assert gate.ion_index != None
            para_dict = gate.para_table
            tl = gate.latency
            tmax = -1
            time_segment_number = para_dict['segment_number']
            # gate duration即为分段函数最后一段的结束时间
            tn = para_dict['time_intervals'][time_segment_number - 1][1]
            # print(gate.ion_index, gate.pulse_type)
            for single_ion in iter_int_or_tuple(gate.ion_index):
                assert para_dict['data_per_ion'][single_ion] != None
                tmax = max(tmax, self.time_stamp[single_ion])
            # gate.ion_index里必须有离子，即必须on在至少一个离子上tmax才不等于-1
            try:
                assert tmax != -1
            except AssertionError as e:
                print('Error! This {} gate is not performed on any ions.'.format(gate.pulse_type))
                raise e

            self.gate_sequence.append((gate.ion_index, tmax + tl, tn, gate.pulse_type, gate))

            for single_ion in iter_int_or_tuple(gate.ion_index):
                self.time_stamp[single_ion] = tmax + tn + tl
                self.gate_list_per_ion[single_ion].append((self.time_stamp[single_ion] - tn, tn, gate))

    def add_gates(self, *args):
        """
        添加操作接口，args可以为list/tuple形式的操作序列，调用inner_add_gates进行操作分析并添加脉冲
        这些操作将被添加到原序列的末尾
        """
        self.input_list.extend(list(args))
        self.inner_add_gates(args)

    def inner_add_gates(self, args):
        """
        操作分析及添加脉冲的入口函数，args可以为list/tuple形式的操作序列
        主要分3类：
            sync：同步操作
            awg_trigger：awg打开
            BasePulse：脉冲操作
        Args:
            args (_type_): 脉冲序列
        """
        gate_num = len(args)
        for item in args:
            for pulse in iter_gate_or_tuple_or_list(item):
                if isinstance(pulse, BasePulse):
                    if self.add_sync:
                        tmax = max(self.time_stamp)
                        self.time_stamp = [tmax] * self.qubit_number
                    self.__add_gate(pulse)
                elif isinstance(pulse, tuple):
                    tmax = -1
                    if pulse[0] == 'sync':
                        for single_ion in pulse[1]:
                            tmax = max(tmax, self.time_stamp[single_ion])
                        for single_ion in pulse[1]:
                            self.time_stamp[single_ion] = tmax
                        self.current_time = tmax
                    elif pulse[0] == 'awg_trigger':
                        assert self.awg_trigger == False
                        self.awg_trigger = True
                        self.awg_trigger_time = self.current_time + pulse[1]
                    else:
                        print('Error in pulse sequence, exception type not permitted')
                        raise Exception()
                    # self.gate_list.append()
                else:
                    pass

    def set_sequence(self, *args):
        """
        序列设置接口，args可以为list/tuple形式的操作序列
        这些操作将覆盖原序列
        """
        self.clear(make_sure=True)
        self.input_list = list(args)
        self.inner_add_gates(args)

    def reformat_sequence(self):
        """
        序列格式化接口
        start_point、end_point字典以脉冲的起始、结束时间点为key，value为一个三元组(sequence_index, gate_object, ion_index)
        time_index：包含所有不同的起始、结束点
        """
        seq = self.gate_sequence
        time_index = set()

        for pulse in seq:
            time_index.add(pulse[1])
            time_index.add(pulse[1] + pulse[2])
        time_index = list(time_index)
        time_index.sort()
        # print(time_index)
        start_point = {}
        end_point = {}
        label_time = {}
        end_branch_positions = set()
        for idx, pulse_item in enumerate(seq):
            lt = pulse_item[1]
            rt = pulse_item[1] + pulse_item[2]
            pulse = pulse_item[4]
            if start_point.get(lt) != None:
                start_point[lt].append((idx, pulse_item[3], pulse_item[0], pulse_item[4]))
            else:
                start_point[lt] = [(idx, pulse_item[3], pulse_item[0], pulse_item[4])]
            if end_point.get(rt) != None:
                end_point[rt].append((idx, pulse_item[3], pulse_item[0], pulse_item[4]))
            else:
                end_point[rt] = [(idx, pulse_item[3], pulse_item[0], pulse_item[4])]
            if pulse.label != None:
                label_time[pulse.label] = lt
            # if isinstance(pulse, End) or isinstance(pulse, EndBranch):
            #    end_branch_positions.add(lt)

        return time_index, start_point, end_point  # , branch_point, end_branch_positions

    def callable_test(self, func, t):
        if callable(func):
            result = func(t)
        else:
            result = func
        return result

    def func_generator(self, args):
        """
        波形数据生成函数，参数可能为
            单个值：直接根据值计算出对应的波形数据
            元组：求每个分量对应的波形数据，并将所有分量相加
            关于时间t的函数：先求出t时刻对应的值，并根据值计算出对应的波形数据

        Args:
            args (_type_): 脉冲参数字典
        """
        if isinstance(args['amp'], tuple):

            def func(t):
                func_list_temp = [self.callable_test(args['amp'][i], t) * np.sin(
                    self.callable_test(2 * np.pi * args['freq'][i], t) * t + self.callable_test(args['phase'][i], t))
                                  for i in range(len(args['amp']))]
                return sum(func_list_temp)
        # for i in range(len(args['amp'])):
        #     print(args['amp'][i])
        #     def func_temp(t):
        #         return self.callable_test(args['amp'][i], t)*np.sin(self.callable_test(2*np.pi*args['freq'][i], t)*t+self.callable_test(args['phase'][i], t))
        #     func_list_temp = func_list_temp + [func_temp]
        # def func(t):
        #     result = 0
        #     for i in range(len(func_list_temp)):
        #         result = result + func_list_temp[i](t)
        #     return result

        else:
            def func(t):
                try:
                    return self.callable_test(args['amp'], t) * np.sin(
                        self.callable_test(2 * np.pi * args['freq'], t) * t + self.callable_test(args['phase'], t))
                except TypeError:
                    print(args['amp'], args['freq'], args['phase'])
                    raise TypeError
                    # pass

        return func

    def func_list_generator(self):
        """
        获取脉冲波形数据生成函数以及对应的时间列表

        脉冲不分段：直接调用func_generator得到波形生成函数
        脉冲分段，对每个时间分段做分析
        """

        func_list = []
        t_list = []
        for ion_id, gate_list in enumerate(self.gate_list_per_ion):
            # gate_list_per_ion存下每个离子对应的gate_list，list中每个元素都是一个三元组(start_time, duration, gate)
            # 其中gate是的一个BasePulse对象或AdvancePulse对象
            func_list_single_ion = []
            t_list_single_ion = []

            # print(func_list_single_ion)

            for gate_tuple in gate_list:
                # print(gate_tuple[0],gate_tuple[1],gate_tuple[2])
                # (start_time, end_time, gate_object)
                # 用list表示分段函数
                if isinstance(gate_tuple[2], AWGPulse):
                    if isinstance(gate_tuple[2].amp, (list, tuple)) and len(gate_tuple[2].amp) == gate_tuple[2].segment_number:
                        for idx in range(len(gate_tuple[2].time_intervals)):
                            args = gate_tuple[2].parameter_list(idx)
                            try:
                                assert args['amp'] != None
                                assert args['freq'] != None
                                assert args['phase'] != None
                            except AssertionError as e:
                                print(
                                    'Error in generating function, some parameters of a gate on ion {} are None.'.format(
                                        gate_tuple[2].ion_index))
                                raise e
                            lt, rt = gate_tuple[2].time_intervals[idx]
                            if rt <= gate_tuple[2].duration:
                                t_list_single_ion.append((gate_tuple[0] + lt, gate_tuple[0] + rt))
                                func_list_single_ion = func_list_single_ion + [
                                    self.func_generator(gate_tuple[2].parameter_list(idx))]
                            elif lt <= gate_tuple[2].duration:
                                t_list_single_ion.append((gate_tuple[0] + lt, gate_tuple[0] + gate_tuple[2].duration))
                                func_list_single_ion = func_list_single_ion + [
                                    self.func_generator(gate_tuple[2].parameter_list(idx))]
                    else:
                        args = gate_tuple[2].parameter_list()
                        try:
                            assert args['amp'] != None
                            assert args['freq'] != None
                            assert args['phase'] != None
                        except AssertionError as e:
                            print('Error in generating function, some parameters of a gate on ion {} are None.'.format(
                                gate_tuple[2].ion_index))
                            raise e
                        # print('ion {}:'.format(idx) , gate_tuple[2].parameter_list())
                        func_list_single_ion = func_list_single_ion + [
                            self.func_generator(gate_tuple[2].parameter_list())]
                        t_list_single_ion.append((gate_tuple[0], gate_tuple[0] + gate_tuple[1]))
                else:
                    gate = gate_tuple[2]
                    assert isinstance(gate, AWGMultiPulse)
                    time_segment_number = gate.para_table['segment_number']
                    single_ion_data_dict = gate.para_table['data_per_ion'][ion_id]
                    for i in range(time_segment_number):
                        lt, rt = gate.para_table['time_intervals'][i]
                        temp_dict = {
                            'amp': single_ion_data_dict['amp'][i],
                            'freq': single_ion_data_dict['freq'][i],
                            'phase': single_ion_data_dict['phase'][i]
                        }
                        t_list_single_ion.append((gate_tuple[0] + lt, gate_tuple[0] + rt))
                        func_list_single_ion = func_list_single_ion + [self.func_generator(temp_dict)]

            func_list.append(func_list_single_ion)
            t_list.append(t_list_single_ion)

        return (func_list, t_list)

    def generator_awg_waveform(self):
        """
        awg波形数据生成
        首先调用func_list_generator获取波形数据生成函数以及对应时间列表
        再根据采样频率，获取采样的时间点
        最终根据采样时间点及波形生成函数获取每个采样点的波形数据
        """
        func_list, t_list = self.func_list_generator()
        data_list = []
        ion_id = 0
        for ion_f_list, ion_t_list in zip(func_list, t_list):
            # start = ion_t_list[0]
            # data_temp = []
            # print(ion_id)
            tlist_temp = []
            flist_temp = np.array([])
            # 当前离子编号是ion_id, 下面的i是第i段函数
            for i in range(len(ion_t_list)):
                lt, rt = ion_t_list[i]
                t_temp_for_compute = np.arange(lt - self.awg_trigger_time, rt - self.awg_trigger_time,
                                               1 / self.awg_sampling_rate)
                # print('ion,lt,rt,t_temp:', ion_id,lt,rt,len(t_temp_for_compute))
                tlist_temp.append((lt, rt))
                if i > 0:
                    if lt > tlist_temp[-2][1]:
                        num_zeroes = round((lt - tlist_temp[-2][1]) * self.awg_sampling_rate)
                        # print(lt - tlist_temp[-2][1])
                        # print('padding zeroes: ion_id, i, duration ,num_zero_points', ion_id, i ,lt - tlist_temp[-2][1] ,num_zeroes)
                        if num_zeroes % 10 != 0:
                            # print(tlist_temp[-2][1],lt,num_zeroes)
                            pass
                        zero_padd = np.zeros(num_zeroes)
                        flist_temp = np.append(flist_temp, zero_padd)
                elif (lt > self.awg_trigger_time):  # i==0
                    num_zeroes = round((lt - self.awg_trigger_time) * self.awg_sampling_rate)
                    zero_padd = np.zeros(num_zeroes)
                    flist_temp = np.append(flist_temp, zero_padd)
                    # awg数据点从trigger之后才开始
                try:
                    flist_temp = np.append(flist_temp, ion_f_list[i](t_temp_for_compute))
                    # print(ion_f_list[i](t_temp_for_compute)[0:5])
                    # print('ion, data points: ', ion_id, len(flist_temp))
                except TypeError as e:
                    print(lt, rt)
                    print(e)
                    raise e
                # start = ion_t_list[i+1]
            flist_temp = np.array(flist_temp)
            data_list.append((tlist_temp, flist_temp))
            ion_id += 1
        return data_list

    def regenerate_sequence(self):
        """
        序列重分析
        """
        args = tuple(self.input_list)
        self.clear(make_sure=True)
        self.inner_add_gates(args)
        self.set_para_flag = False

    def perform_sequence_awg(self):
        """
        对波形数据做对齐（补0），使每个通道的数据长度保证一致
        """
        # generate the awg waveform data according to pulse waveform function

        _temp_awg_data = self.generator_awg_waveform()

        max_awg_data_len = 0
        for i in range(len(_temp_awg_data)):
            if len(_temp_awg_data[i][1]) > max_awg_data_len:
                max_awg_data_len = len(_temp_awg_data[i][1])
        # print(max_awg_data_len)
        self.awg_data = []
        for i in range(len(_temp_awg_data)):
            temp_data = np.pad(_temp_awg_data[i][1], (0, max_awg_data_len - len(_temp_awg_data[i][1])))
            self.awg_data.append(temp_data)
        self.awg_data = np.array(self.awg_data)  ## This is what we need to send to the awg

    def get_atom_awg_data(self):
        """生成awg的Ch1,Ch2通道需要的波形名，并生成每个比特上raman光的信息，以便后续生成Ch3，Ch4通道数据
        """
        qubits_list = []
        awg_format = []
        all_gate_time = []
        ch1_data = []
        ch2_data = []
        for gate_tuple in self.gate_sequence:
            pulse = gate_tuple[4]
            if not isinstance(pulse, Raman): continue
            k = gate_tuple[0]
            if not isinstance(gate_tuple[0], int):
                k = gate_tuple[0][0]
            if k not in qubits_list:
                qubits_list.append(k)
                awg_format.append([])
                all_gate_time.append(0)
                x, y = k // self.column, k % self.column
                ch1_data.append(f'raman_x_{x}')
                ch2_data.append(f'raman_y_{y}')
            idx = qubits_list.index(k)
            all_gate_time[idx] += gate_tuple[2]
            ch4_open = False
            if pulse.phase > 0: ch4_open = True
            awg_format[idx].append((ch4_open, gate_tuple[2]))
        # 注意，当脉冲数量过大时，需要调整ch1,ch2通道的波形长度，重新生成波形文件，并加载到awg的RAM
        return ch1_data, ch2_data, awg_format

    def clear(self, make_sure=False):
        """
        清除原序列
        """
        if make_sure == False:
            print("This operation will delete the sequence in current object, if you confirm \
                    to do that please set the argument \'make_sure\' to be True.")
        else:
            self.gate_sequence = []
            # del(self.gate_time)
            self.time_stamp = [0 for i in range(self.qubit_number)]
            # self.gate_list = []
            # gate_list_per_ion存下每个离子对应的gate_list，list中每个元素都是一个三元组(start_time, duration, gate)
            # 其中gate是BasePulse的一个实例
            self.gate_list_per_ion = [[] for i in range(self.qubit_number)]
            self.awg_trigger = False
            self.awg_trigger_time = -1
            self.current_time = 0
            self.labelled_pulse = {}


def plot_sequence(sequence, remap_time=True, ax: Optional[plt.Axes] = None, auto_size=False, given_size=None):
    """
    序列可视化

    Args:
        sequence (_type_): 需要可视化的序列
        remap_time (bool, optional): 是否需要对时间轴做缩放. Defaults to True.
        ax (Optional[plt.Axes], optional): 画布区域. Defaults to None.
        auto_size (bool, optional): 是否自动调整大小. Defaults to False.
        given_size (_type_, optional): 画布大小. Defaults to None.

    对于数据很多的图，如果想看清的话需要手动设置图片大小: plt.plot(figsize=(n,m))
    autosize == True时图片会自动设置长度，用于显示很长的sequence
    """

    new_sequence = []
    for gate_tuple in sequence:
        new_sequence.append(
            (gate_tuple[0], round(gate_tuple[1], 1), round(gate_tuple[2], 1), gate_tuple[3], gate_tuple[4]))

    sequence = new_sequence

    moments_org2rmp, moments_rmp2org = remap_to_indices(
        moment
        for (_, start_time, duration, _, _) in sequence
        for moment in (start_time, start_time + duration)
    )

    # print(moments_org2rmp, moments_rmp2org)
    xlen = len(moments_rmp2org)
    if auto_size == True:
        plt.figure(figsize=(int(xlen * 1.5), 5))
    elif given_size != None:
        plt.figure(figsize=given_size)

    sequence = tuple(sequence)
    ax = plt.gca() if ax is None else ax

    line1, line2 = None, None

    ion_org2rmp, ion_rmp2org = remap_to_indices(
        ion
        for (ions, start_time, duration, _, _) in sequence
        for ion in iter_int_or_tuple(ions)
    )

    for ions, start_time, duration, pulse_type, pulse_instance in sequence:
        # start_time = round(start_time, 3)
        ions = sorted(list(iter_int_or_tuple(ions)))

        if remap_time:
            remapped_start_moment = moments_org2rmp[start_time]
            remapped_end_moment = moments_org2rmp[start_time + duration]
        else:
            remapped_start_moment = start_time
            remapped_end_moment = start_time + duration

        polygon_xy = []
        for ion in ions:
            remapped_ion = ion_org2rmp[ion]

            l = remapped_start_moment
            r = remapped_end_moment
            w = r - l
            h = 4 / 5
            cx = (l + r) / 2
            cy = remapped_ion

            rect = plt.Rectangle((l, cy - h / 2), w, h,
                                 facecolor='white', edgecolor='black', linewidth=3,
                                 zorder=2.5)
            if isinstance(pulse_instance, (AWGPulse, AWGMultiPulse)):
                rect = plt.Rectangle((l, cy - h / 2), w, h,
                                     facecolor='white', edgecolor='blue', linewidth=3,
                                     zorder=2.5)
                line2 = rect
            else:
                line1 = rect

            ax.add_patch(rect)

            text = plt.Text(cx, cy, pulse_type,
                            verticalalignment='center', horizontalalignment='center',
                            wrap=True, color='black',
                            zorder=2.5)
            ax.add_artist(text)

            polygon_xy.append((cx, cy))

        if len(ions) > 1:
            polygon = plt.Polygon(polygon_xy, closed=False,
                                  edgecolor='black', linewidth=3,
                                  zorder=2.4)
            ax.add_patch(polygon)

    ax.set_xlabel("time")

    if remap_time:
        padding_x = 3 / 5
        ax.set_xlim(0 - padding_x, len(moments_rmp2org) - 1 + padding_x)
    else:
        padding_x = (max(moments_rmp2org) - min(moments_rmp2org)) / 20
        ax.set_xlim(min(moments_rmp2org) - padding_x, max(moments_rmp2org) + padding_x)

    ax.grid(axis='x', color='grey', ls='--')
    if remap_time:
        ax.set_xticks(range(len(moments_rmp2org)))
    else:
        ax.set_xticks(moments_rmp2org)
    ax.set_xticklabels(moments_rmp2org)

    ax.set_ylabel("qubit")

    padding_y = 3 / 5
    ax.set_ylim(len(ion_rmp2org) - 1 + padding_y, -padding_y)
    ax.grid(axis='y', color='black')
    ax.set_yticks(range(len(ion_rmp2org)))
    ax.set_yticklabels(ion_rmp2org)

    ax.set_frame_on(False)

    # ax.legend(['fpga--black','awg--blue','1','1','1','1','1','1'])
    # box = ax.get_position()
    # ax.set_position([box.x0, box.y0, box.width, box.height*0.8])
    if line1 != None and line2 != None:
        ax.legend((line1, line2), ('fpga', 'awg'), loc='upper left', bbox_to_anchor=(0, 1.15), ncol=3)
    elif line1 != None:
        ax.legend([line1], ['fpga'], loc='upper left', bbox_to_anchor=(0, 1.15), ncol=3)
    elif line2 != None:
        ax.legend([line2], ['awg'], loc='upper left', bbox_to_anchor=(0, 1.15), ncol=3)


def remap_to_indices(items, key=None):
    items_set = set(items)
    items_sorted = sorted(items_set, key=key)
    moments_dict = {t: i for i, t in enumerate(items_sorted)}

    org2rmp = moments_dict
    rmp2org = items_sorted
    return org2rmp, rmp2org


def iter_int_or_tuple(item):
    try:
        for sub_item in item:
            yield sub_item
    except TypeError:
        yield item


def iter_gate_or_tuple_or_list(item):
    if isinstance(item, list):
        for sub_item in item:
            yield (sub_item)
    else:
        yield item
