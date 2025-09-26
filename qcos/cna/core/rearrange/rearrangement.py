import json
import numpy as np
import ctypes
from ..config import GlobalSetting

def get_params(qpu_file):
    params = {}
    with open(qpu_file, 'r') as f:
        params = json.loads(f.read())
    return params


class ReArrangementMocker():
    def __init__(self, qpu_file):
        self.qpu_file = qpu_file
        params = get_params(qpu_file)
        self.row = params['overview']['row']
        self.column = params['overview']['column']
        self.output_len = params['movement'].get('output_len', 1000)
        self.target = [0, 0]

    def transport(self, atom):
        return [], []

    def set_target(self, target):
        self.target = target


class ReArrangement():
    """原子重排
    Args:
        qpu_file: 硬件配置文件，里面包含重排所需参数，包括行列数、初始频率、间隔频率、操作时间等
    """

    def __init__(self, qpu_file):
        self.dll = ctypes.cdll.LoadLibrary(GlobalSetting.get_rearrangement_dll())
        self.qpu_file = qpu_file
        params = get_params(qpu_file)
        self.row = params['overview']['row']
        self.column = params['overview']['column']
        self.output_len = params['movement'].get('output_len', 1000)
        self.c_output = (ctypes.c_int * self.output_len)()
        self.target = [0, 0]
        # 先调用一遍dll进行预热
        self.transport([0] + [1] * (self.row * self.column - 1))

    def transport(self, atom):
        """_summary_

        Args:
            atom (list): 当前原子分布，包含row*column个数据，1代表当前位置有原子，0代表没有
            target (list): 目标点位坐标列表，长度为点位数*2，每两个数，代表一个坐标；如[0,0,1,2]代表两个点(0,0),(1,2)
        """
        assert len(atom) == self.row * self.column
        # 准备数据
        c_atom = (ctypes.c_int * len(atom))(*atom)
        c_target = (ctypes.c_int * len(self.target))(*self.target)
        for i in range(self.output_len): self.c_output[i] = -100
        # 重排
        self.dll._transport(self.row, self.column, c_atom, c_target, self.c_output, len(atom), len(self.target),
                            self.output_len)
        return self.get_arrange_opts()

    def get_arrange_opts(self):
        now_x, now_y = -1, -1
        x_opts = []
        y_opts = []
        i = 0
        while i < self.output_len:
            if self.c_output[i] == -100: break

            if self.c_output[i] == -1:
                # 当前移动操作结束，将原子放下
                x_opts.append(f"x_put_{now_x}")
                y_opts.append(f"y_put_{now_y}")
                now_x, now_y = -1, -1
                i += 1
            else:
                x, y = self.c_output[i], self.c_output[i + 1]
                if now_x == -1:
                    # 拿起原子
                    x_opts.append(f"x_grab_{x}")
                    y_opts.append(f"y_grab_{y}")
                else:
                    # 移动
                    if x != now_x:
                        x_opts.append(f"x_move_{now_x}_{x}")
                        y_opts.append(f"y_stable_{now_y}")
                    elif y != now_y:
                        x_opts.append(f"x_stable_{now_x}")
                        y_opts.append(f"y_move_{now_y}_{y}")
                now_x, now_y = x, y
                i += 2
        return x_opts, y_opts

    def set_target(self, target):
        self.target = target
