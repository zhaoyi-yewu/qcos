from .instrument_base import InstrumentBase
from .error import *
import matplotlib.pyplot as plt
import pickle
from ..gui.gui import get_box_list
import ipyvuetify as v
from IPython.display import display
from abc import abstractmethod
import pickle
from ..gui.gui import get_box_list
import ipyvuetify as v
from IPython.display import display
from ipywidgets.embed import embed_minimal_html

class HardwareBase(InstrumentBase):
    """
    硬件抽象类
    """
    def __init__(self, name: str, **kwargs) -> None:
        if hasattr(self, "connection") and hasattr(self.connection, "connect"):
            try:
                self.connection.connect()
            except Exception as e:
                raise DeveiceConnectionError(str(e))

        super().__init__(name, **kwargs)
    
    def close(self):
        """
        关闭硬件，并删除实例
        """
        if hasattr(self, "connection") and hasattr(self.connection, "close"):
            try:
                self.connection.close()
            except Exception as e:
                raise DeveiceCloseError(str(e))
        self.remove_instance(self)

    def save(self, path='./'):
        """
        保存硬件
        参数:
        path：硬件文件保存路径
        """
        save_path = f'{path}/{self.name}.pickle'
        with open(save_path, 'wb') as f:
            pickle.dump(self, f)

    def comm(self, send_data, **kwargs):
        """
        对外通信接口，集成了数据预处理、发送、接收及数据后处理
        """
        if hasattr(self, "preprocess"):
            send_data = self.preprocess(send_data, **kwargs)
        self.send(send_data, **kwargs)
        received_data = self.receive(**kwargs)
        if hasattr(self, "postprocess"):
            received_data = self.postprocess(received_data, **kwargs)
        return received_data

    def get_delay(self):
        """
        获取当前硬件的延迟
        """
        if hasattr(self, 'delay'): return self.delay
        return 0

    def delay_sync(self, insts = [], precision = 4):
        """
        对列表中的所有硬件做延时判断，求出若要同步列表中硬件与当前硬件，需要给当前硬件添加多少额外的延迟

        Args:
            insts (list, optional): 硬件列表. Defaults to [].
            precision (int, optional): 精度. Defaults to 4.
        """
        delay = self.get_delay()
        for inst in insts:
            delay = max(delay, inst.get_delay())
        return round(delay - self.get_delay(), precision)

    def __get_widget(self):
        init_param = self.snapshot()
        attr_dict = {}
        if hasattr(self, 'attr_dict'):
            attr_dict = self.attr_dict
        attr_dict['name'] = {'disable': True}
        box_list = get_box_list(init_param, attr_dict, self.set_params_from_gui)
        
        return v.Row(
            children=[
                v.Row(
                    children=box_list,
                    style_="max-width: 50%; align-content: flex-start;",
                ),
            ],
            class_="ml-3 mt-4",
        )
    
    def show(self):
        """
        参数可视化展示
        """
        display(self.__get_widget())
    
    def set_params_from_gui(self, change):
        param_name = change["owner"].name
        param_val = change["owner"].num_value
        setattr(self, param_name, param_val)
        
    def save_as_html(self, title = None):
        if title is None: title = self.name
        embed_minimal_html(f'{title}.html', views=[self.__get_widget()], title=title)

    @abstractmethod
    def send(self, send_data, **kwargs):
        """
        发送数据接口
        """
        pass

    @abstractmethod
    def receive(self, **kwargs):
        """
        接收数据接口
        """
        pass

    def preprocess(self, send_data, **kwargs):
        """
        数据预处理函数
        """
        pass

    def postprocess(self, received_data, **kwargs):
        """
        数据后处理函数
        """
        pass