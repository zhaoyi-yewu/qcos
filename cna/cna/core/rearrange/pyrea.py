import json
import numpy as np
import ctypes
from ..config import GlobalSetting

def get_params(qpu_file):
    params = {}
    with open(qpu_file, 'r') as f:
        params = json.loads(f.read())
    return params 

def get_path(path, grid):
    """从总移动路径生成具体的移动操作，主要是当有阻挡的原子时，需要将路径进行拆分

    Args:
        path (_type_): 总移动路径
        grid (_type_): 比特阵列，1代表该位置有原子

    Returns:
        res: 路径列表
        obstacle_cnt: 路径中有多少阻挡的原子
    """
    i = len(path) - 1
    res = []
    sub_path = []
    obstacle_cnt = 0
    while i >= 0:
        x, y = path[i]
        sub_path += [y, x]
        if grid[x][y] == 1:
            obstacle_cnt += 1
            res += sub_path[::-1]
            res.append(-1)
            sub_path = [y, x]
        i -= 1
    return res, obstacle_cnt
    
def mov(start_x, start_y, target_x, target_y, grid):
    """生成从起始位置到终止位置的移动路径

    Args:
        start_x (_type_): 起始x坐标
        start_y (_type_): 起始y坐标
        target_x (_type_): 终点x坐标
        target_y (_type_): 终点y坐标
        grid (_type_): 比特阵列，1代表该位置有原子
    """
    dx = np.sign(target_x - start_x)
    dy = np.sign(target_y - start_y)
    
    m, n = (target_x - start_x) * dx + 1, (target_y - start_y) * dy + 1
    path = []
    
    #通过动态规划找到最少阻挡原子的路径
    obstacle = [[0] * n for _ in range(m)]
    obstacle[0][0] = 0
    for i in range(1, m):
        obstacle[i][0] = obstacle[i-1][0] + grid[start_x + i * dx][start_y]
    for j in range(1, n):
        obstacle[0][j] = obstacle[0][j-1] + grid[start_x][start_y + j * dy]
    
    for i in range(1, m):
        for j in range(1, n):
            obstacle[i][j] = min(obstacle[i-1][j], obstacle[i][j-1]) + grid[start_x + i * dx][start_y + j * dy]
    i, j = m-1, n-1
    while i > 0 or j > 0:
        path.append((start_x + i * dx, start_y + j * dy))
        if i > 0 and obstacle[i][j] == obstacle[i-1][j] + grid[start_x + i * dx][start_y + j * dy]:
            i -= 1
        else:
            j -= 1
    path.append((start_x, start_y))
    return get_path(path[::-1], grid)
    
def HPFA(row, column, atom, target):
    """基于最少移动的启发式重排算法那

    Args:
        row (_type_): 阵列行数
        column (_type_): 阵列列数
        atom (_type_): 阵列中初始原子的分布
        target (_type_): 重排目标位置列表

    Returns:
        flag: 0：重排成功，1：失败
        output: 完整的重排路径
    """
    grid = [[0] * column for _ in range(row)]
    outside = set()
    for i, v in enumerate(atom):
        x, y = i // column, i % column
        grid[x][y] = v
        if v == 1:
            outside.add((x, y))
            
    inside = set()
    remain = set()
    n = len(target)
    for i in range(0, n, 2):
        x, y = target[i], target[i+1]
        inside.add((x, y))
        if (x, y) in outside:
            outside.remove((x, y))
        else:
            remain.add((x, y))
    
    if len(outside) < len(remain): return -1, []
    # 距离L从1开始遍历
    L = 1
    output = []
    while remain:
        tmp = remain.copy()
        # 遍历目标点位中所有还未有原子的点位
        for (x, y) in tmp:
            # 先选出所有满足距离L要求的可移动点位
            candidate = []
            for xx in range(max(0, x-L), min(x+L+1, row)):
                dy = L - abs(x - xx)
                yy = y - dy
                if yy >= 0 and (xx, yy) in outside and (xx, yy) not in inside:
                    candidate.append((xx, yy))   
                yy = y + dy
                if yy < column and (xx, yy) in outside and (xx, yy) not in inside:
                    candidate.append((xx, yy))
            # 选择阻挡原子最少的路径
            if candidate:
                obstacle_cnt = 100
                path = None
                start_x, start_y = -1, -1
                for (xx, yy) in candidate:
                    tmp_path, tmp_obstacle_cnt = mov(xx, yy, x, y, grid)
                    if tmp_obstacle_cnt < obstacle_cnt:
                        obstacle_cnt = tmp_obstacle_cnt
                        path = tmp_path
                        start_x = xx
                        start_y = yy
                    if obstacle_cnt == 1:
                        break
                output += path
                remain.remove((x, y))
                outside.remove((start_x, start_y))
                grid[x][y] = 1
                grid[start_x][start_y] = 0

        L += 1
    return 0, output
    
class PyRea():
    """原子重排
    Args:
        qpu_file: 硬件配置文件，里面包含重排所需参数，包括行列数、初始频率、间隔频率、操作时间等
    """
    
    def __init__(self, qpu_file):
        self.qpu_file = qpu_file
        params = get_params(qpu_file)
        self.row = params['overview']['row']
        self.column = params['overview']['column']
        self.target = [0, 0]
        
    def transport(self, atom):
        """_summary_

        Args:
            atom (list): 当前原子分布，包含row*column个数据，1代表当前位置有原子，0代表没有
            target (list): 目标点位坐标列表，长度为点位数*2，每两个数，代表一个坐标；如[0,0,1,2]代表两个点(0,0),(1,2)
        """
        assert len(atom) == self.row * self.column
        # 重排
        r, self.output = HPFA(self.row, self.column, atom, self.target)
        if r == -1: raise "rearrangement failed"
        return self.get_arrange_opts()
        
    def get_arrange_opts(self):
        now_x, now_y = -1, -1
        x_opts = []
        y_opts = []
        i = 0
        while i < len(self.output):
            if self.output[i] == -100: break
            
            if self.output[i] == -1:
                # 当前移动操作结束，将原子放下
                x_opts.append(f"x_put_{now_x}")
                y_opts.append(f"y_put_{now_y}")
                now_x, now_y = -1, -1
                i += 1
            else:
                x, y = self.output[i], self.output[i+1]
                if now_x == -1:
                    #拿起原子
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

    
    def mov_simulate(self, atom, output):
    
        mov_cnt = 0
        grab_cnt = 0

        now_x = now_y = -1
        i = 0
        sim_atom = np.reshape(atom.copy(), (self.row, self.column))
        while i < len(output):
            if output[i] == -100: break

            if output[i] == -1:
                sim_atom[now_x][now_y] = 1
                now_x = now_y = -1
                i += 1
            else:
                need_v = 0
                if now_x == -1:
                    need_v = 1
                    grab_cnt += 1
                else:
                    mov_cnt += 1
                now_x, now_y = output[i], output[i+1]
                if sim_atom[now_x][now_y] != need_v:
                    raise "move error"
                sim_atom[now_x][now_y] = 0
                i += 2
        return sim_atom, mov_cnt, grab_cnt
        