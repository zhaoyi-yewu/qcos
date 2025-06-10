import copy
from .gui.gui import get_box_list, set_value_by_input
import ipyvuetify as v
from ipywidgets.embed import embed_minimal_html
from IPython.display import display
import ipywidgets
import matplotlib.pyplot as plt
import numpy as np
from abc import ABC


def flex_column(widgets, class_="", **kwargs) -> v.Container:
    return v.Container(
        class_="d-flex flex-column " + class_, children=widgets, **kwargs
    )

class BasePulse(ABC):
    """
    脉冲抽象类

    Args:
        duration (int, optional): 持续时间. Defaults to 0.
        latency (int, optional): 延迟. Defaults to 0.
        pulse_type (_type_, optional): 脉冲类型. Defaults to None.
        label (_type_, optional): 标签. Defaults to None.
        para_table (_type_, optional): 参数字典，用以多比特脉冲参数设置. Defaults to None.
    """
    def __init__(self, duration = 0, latency=0, pulse_type = None, label = None, para_table = None) -> None:
        self.ion_index = None
        self.duration = duration
        self.latency = latency
        self.pulse_type = pulse_type
        self.label = label
        self.para_table = para_table
        self.on_flag = False
        self.v_plot_output = ipywidgets.Output(
            layout=ipywidgets.Layout(overflow="hidden")
        )
        
        self.attr_dict = {
            'pulse_type': {'disable': True}
        } 
    
    def on(self, ion_index):
        """
        脉冲作用的比特列表

        Args:
            ion_index (_type_): 作用比特，可为单个值或者列表
        """
        assert isinstance(ion_index, int) or isinstance(ion_index, list)
        #self.ion_index = ion_index
        if self.para_table:
            for ion in iter_int_or_tuple(ion_index):
                if self.para_table['data_per_ion'].get(ion) == None:
                    raise RuntimeError('ion index {} not existing in this advanced gate!'.format(ion))
        
        if self.on_flag == False:
            self.ion_index = ion_index
            self.on_flag = True
            #print(ion_index)
            return self
        else:
            another_gate = copy.copy(self)
            another_gate.ion_index = ion_index
            return another_gate
        
    def update_hardware(self):
        '''
        you should clarify the concrete hardware interface in the instantiation
        '''
        raise AssertionError("'"+self.label+".update_hardware' is not DEFINED.")

    def reset_hardware(self):
        raise AssertionError("'"+self.label+".reset_hardware' is not DEFINED.")
    
    
    def __get_widget(self):
        init_param = self.__dict__.copy()
        box_list = get_box_list(init_param, self.attr_dict, callback_func=self.set_params_from_gui)
        
        pulse_widget = v.Container(
            children=[
                flex_column(
                    [self.v_plot_output],
                    class_="p-0 m-0",
                    id="matplotlib_cntnr",
                ),],
            class_="ml-3 mt-0 pt-0",
            style_="width: 35%; max-width:1000px"
        )
        
        return v.Row(
            children=[
                v.Row(
                    children=box_list,
                    style_="max-width: 50%; align-content: flex-start;",
                ),
                pulse_widget
            ],
            class_="ml-3 mt-4",
        )
    
    def show(self):
        """
        脉冲可视化函数
        """
        display(self.__get_widget())
        self.pulse_refresh()
    
    def set_params_from_gui(self, change):
        """
        参数修改钩子函数
        """
        param_name = change["owner"].name
        param_val = change["owner"].num_value
        ori_val = getattr(self, param_name)
        setattr(self, param_name, param_val)
        if param_name in ['duration', 'amp', 'phase', 'freq'] and ori_val != param_val:
            self.pulse_refresh()
    
    def pulse_refresh(self):
        """
        可视化右侧脉冲图像刷新函数
        """
        self.v_plot_output.clear_output()
        if hasattr(self, 'plot_wave'):
            self.plot_wave()
    
    def snapshot(self):
        res = self.__dict__.copy()
        res.pop('v_plot_output')
        return res

    def __repr__(self) -> str:
        return f'{type(self).__name__}(target={self.ion_index}, type={self.pulse_type}, lable={self.label})'

    def save_as_html(self, title = None):
        if title is None: title = type(self).__name__
        #self.pulse_refresh()
        embed_minimal_html(f'{title}.html', views=[self.__get_widget()], title=title)
    
class LaserPulse(BasePulse):
    """
    激光脉冲，该类脉冲仅需设置持续时间，其余参数如频率、幅值等都是预先调整设定好的

    Args:
        duration (_type_): 持续时间
        latency (int, optional): 延迟. Defaults to 0.
        pulse_type (_type_, optional): 脉冲类型. Defaults to None.
        label (_type_, optional): 标签. Defaults to None.
    """
    def __init__(self, 
                 duration, 
                 latency=0, 
                 pulse_type=None, 
                 label=None) -> None:
        super().__init__(duration=duration, latency=latency, pulse_type=pulse_type, label=label)
        
    def __repr__(self) -> str:
        return f'{type(self).__name__}(target={self.ion_index}, type={self.pulse_type}, lable={self.label}, duration={self.duration})'
        
class AWGPulse(BasePulse):
    """
    awg单比特脉冲
    
    Args:
        duration (_type_): 持续时间
        amp (float): 幅值
        freq (float): 频率
        phase (float): 初始相位
        latency (int, optional): 延迟. Defaults to 0.
        pulse_type (_type_, optional): 脉冲类型. Defaults to None.
        label (_type_, optional): 标签. Defaults to None.
        segment_number (int, optional): 分段数目. Defaults to -1.
        time_intervals (_type_, optional): 每个分段的时间. Defaults to None.
    
    为了实验的灵活性，我们允许AWG上的gate是分段函数，且每一个分段函数有多个频率成分。具体来说，分成如下两种情况: 
        1、gate不是分段函数，此时amp, freq, phase是三个实数(float)，或者三个tuple（每个tuple长度必须一样）
            即amp=1,freq=2,phase=3或者amp=(1,-1), freq=(2,2),phase=(3,-3)都是可以的。
            其中参数是tuple类型时，表示该函数有多个sin分量。例如: amp, freq, phase = (1,-1),(2,2),(3,-3)时，整体函数为:
            f(t) = 1*sin(2*t+3) - sin(2*t-3)
        2、gate是分段函数，则amp, freq, phase必须是三个长度等于segment_number的list。list内每一个元素同样可以是float或者tuple。例如:
            当segment_number == 4, time_intervals == [(0,9.33), (9.33,17.66), (17.66,28.53), (28.53,57.94)]时,
            amp = [1, (1,1), 3, (0.45,0.45,0.45)], freq = [0.2, (2.03,-2.03), 0.2, (0.2, 2.03, -2.03)],
            phase = [0.48, (0.308, -0.308), 0.086, (0.48,0.48,-0.48)]
            则: 
                    sin(0.2t+0.48)  当 t<9.33 
                    sin(2.03t+0.308) + sin(-2.03t-0.308)  当 9.33<=t<17.66
            f(t) =  3sin(0.2t+0.086)  当 17.66<=t<28.53 
                    0.45sin(0.2t+0.48) + 0.45sin(2.03t+0.48) + 0.45sin(-2.03t-0.48)  当 28.53<=t<57.94
        

    """
    def __init__(self, 
                 duration, 
                 amp: float, 
                 freq: float, 
                 phase: float,
                 latency = 0, 
                 pulse_type = None,  
                 label = None, 
                 segment_number = -1, 
                 time_intervals = None):

        super().__init__(duration = duration, 
                         latency = latency, 
                         pulse_type = pulse_type,
                         label =label)
        self.amp = amp
        self.freq = freq
        self.phase = phase
        self.segment_number = segment_number
        self.segment_flag = False
        self.time_intervals = None
        if segment_number > 0:
            self.segment_flag = True
            self.segment_number = segment_number
            self.time_intervals = time_intervals
            assert isinstance(self.time_intervals, list)
            for pair in self.time_intervals:
                assert len(pair) == 2
            assert len(self.time_intervals) == self.segment_number

    def parameter_list(self, segment_id = None):
        if segment_id == None:
            return {'amp':self.amp, 'freq':self.freq, 'phase':self.phase, 'duration':self.duration}
        else:
            return {'amp':self.amp[segment_id], 'freq':self.freq[segment_id], 'phase':self.phase[segment_id], 'duration':self.duration}
        
    def callable_test(self,func,t):
        if callable(func):
            result = func(t)
        else:
            result = func
        return result
    
    def func_generator(self,args):
        """
        波形数据生成函数 
        """
        if isinstance(args['amp'],tuple):
            assert len(args['amp']) == len(args['phase']) and len(args['amp']) == len(args['freq'])
            def func(t):
                func_list_temp = [self.callable_test(args['amp'][i], t)*np.sin(self.callable_test(2*np.pi*args['freq'][i], t)*t+self.callable_test(args['phase'][i], t)) for i in range(len(args['amp']))]
                return sum(func_list_temp)
        else:
            def func(t):
                try:
                    return self.callable_test(args['amp'], t)*np.sin(self.callable_test(2*np.pi*args['freq'], t)*t+self.callable_test(args['phase'], t))
                except TypeError:
                    print(args['amp'], args['freq'], args['phase'])
                    raise TypeError
        return func
    
    def plot_wave(self, save_fig = False, filename = ''):
        """
        波形可视化
        """
        if self.duration is not None and self.amp is not None and self.freq is not None and self.phase is not None:
            with self.v_plot_output:
                try:
                    t = np.linspace(0, self.duration, 1000)
                    func = self.func_generator(self.parameter_list())
                    y = func(t)
                    plt.plot(t, y)
                    if save_fig:
                        if filename == '': filename = f'{type(self).__name__}.png'
                        plt.savefig(filename)
                        plt.close()
                    else:
                        plt.show()
                except Exception as e:
                    print(f"plot pulse error: \n{str(e)}\n")
                    print("please adjust the paratemers' value\n")
                    print("make sure 'amp', 'phase' and 'freq' \nare the same type and has same length")
    
    def __repr__(self) -> str:
        return f'{type(self).__name__}(target={self.ion_index}, type={self.pulse_type}, lable={self.label}, duration={self.duration}, amp={self.amp}, freq={self.freq}, phase={self.phase})'
    
    def interactive_input(self):
        print(f'交互式定义脉冲序列参数\n\t[1]:持续时间\n\t[2]:幅值\n\t[3]:频率\n\t[4]:相位\n\t[q]:退出')
        while True:
            i = input("请选择操作:")
            if i == 'q':
                break
            elif i == '1':
                set_value_by_input(self, 'duration')
            elif i == '2':
                set_value_by_input(self, 'amp')
            elif i == '3':
                set_value_by_input(self, 'freq')
            elif i == '4':
                set_value_by_input(self, 'phase')
            else:
                print(f'仅支持以下操作\n\t[1]:持续时间\n\t[2]:幅值\n\t[3]:频率\n\t[4]:相位\n\t[q]:退出')

class AWGMultiPulse(BasePulse):
    """
    多比特脉冲

    Args:
        latency (int, optional): 延迟. Defaults to 0.
        pulse_type (_type_, optional): 脉冲类型. Defaults to None.
        label (_type_, optional): 标签. Defaults to None.
        para_table (dict, optional): 参数字典. Defaults to {}.
    
    para_table是一个Python字典类型，具体描述如下: 
    {
        "ion_number" : (int)表示此纠缠门涉及到的离子数
        "segment_number" : (int)表示生成函数的分段数；当生成函数不是分段函数时，取值为1
        "time_intervals" : (list)，其结构与BasePulse的time_intervals相同
        "data_per_ion" : (list)，是一个长度为ion_number的list。list里面每一个元素都是一个字典。结构如下：
        {
            "amp" : 可以是float，tuple或者list（分两种情况讨论），意义同BasePulse.amp。但segment_number > 1时，必须是list类型
            "freq" : 意义同BasePulse.freq。
            "phase" : 意义同BasePulse.phase。
        }
    }
    """
    def __init__(self, latency=0, pulse_type = None, label = None, para_table = {}):

        super().__init__(latency = latency, 
                         pulse_type = pulse_type,
                         label =label,
                         para_table=para_table)
        
        if self.para_table != {}:
            self.__check_dict(self.para_table)
            self.ion_number = self.para_table['ion_number']
            #print(self.ion_number)
        
    def __check_dict(self, para_dic):
        """
        para_dic is a dict with following:
        'ion_number' : int
        'segment_number' : int
        'time_intervals' : list of tuples, like -- [(t1,t2),(t3,t4),(t5,t6),...]
        'data_per_ion' : dict of dicts, each dict contains three keys 'amp', 'freq', 'phase'
        """
        assert type(para_dic.get('ion_number')) == int
        assert type(para_dic.get('segment_number')) == int
        ion_number = para_dic['ion_number']
        seg_number = para_dic['segment_number']
        assert ion_number == len(para_dic['data_per_ion'])
        for (ion,ion_data) in para_dic['data_per_ion'].items():
            #print(ion,ion_data)
            if seg_number > 1:
                assert len(ion_data['amp']) == seg_number
                assert len(ion_data['freq']) == seg_number
                assert len(ion_data['phase']) == seg_number

    def set_parameter_table(self, para_dic):
        self.__check_dict(para_dic)
        self.para_table = para_dic
        self.ion_number = para_dic['ion_number']


def sync(ion_index):
    # synchronize all ions in ion_index, aligning their timing
    if type(ion_index) == int:
        ion_index = [ion_index]
    return ('sync', ion_index)

#awg_trigger函数用于打开awg开关，latency参数表示距离上一个输入波形结束时的延时
def awg_trigger(latency = 0, ion_index = None):
    # turn on the awg trigger, latency is the time distance with previous pulse
    if type(ion_index) == int:
        ion_index = [ion_index]
    return ('awg_trigger', latency, ion_index)


def iter_int_or_tuple(item):
    try:
        for sub_item in item:
            yield sub_item
    except TypeError:
        yield item

class Doppler(LaserPulse):
    """
    doppler脉冲，用以初始化
    """
    hardware_amp, hardware_freq, hardware_phase = None, None, None
    def __init__(self, duration, latency = 0, label = "Doppler"):      
        super().__init__(duration, latency, 'Doppler', label)
        #self.hardware = labbrick_doppler
    
    def update_hardware(self):
        #print("Update Doppler with ", "amp:", self.amp, "freq:", self.freq, "duration: ", self.duration,str(time()))
        #labbrick_370_lock_EOM.freq_update(self.freq)
        pass
        
    def reset_hardware(self):
        #labbrick_doppler.freq_update(165)
        pass

class Detection(LaserPulse):
    """
    测量脉冲，用以量子态测量
    """
    hardware_amp, hardware_freq, hardware_phase = None, None, None
    def __init__(self, duration, latency = 0, label = "Detection"):      
        super().__init__(duration, latency, 'Detection', label)
        #self.hardware = labbrick_doppler
    
    def update_hardware(self):
        pass
        
    def reset_hardware(self):
        pass

            
class Raman(AWGPulse):
    """
    拉曼脉冲，用以操作量子比特，实现单比特门操作
    """
    def __init__(self, duration, amp = None, freq = None, phase = None, latency = 0, label = "Raman", segment_number=-1, time_intervals=None):
        super().__init__(duration, amp, freq, phase, latency=latency, pulse_type='Raman', label=label, segment_number=segment_number, time_intervals=time_intervals)

    def update_hardware(self):
        pass

    def reset_hardware(self):
        pass

class MolmerSorensen(AWGMultiPulse):
    """
    MS脉冲，用以实现多比特门
    """
    def __init__(self, latency=0, label = 'MolmerSorensen', para_table = {}):
        super().__init__(latency=latency, para_table=para_table, pulse_type = 'MolmerSorensen', label = label)
        
    def update_hardware(self):
        pass

    def reset_hardware(self):
        pass
