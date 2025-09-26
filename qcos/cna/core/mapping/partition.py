import json
import networkx as nx
from ..config import GlobalSetting


class Node:

    def __init__(self, qubits, left=None, right=None, ignore=False) -> None:
        """
        搜索树节点，也称作社区，每个节点包含一组量子比特

        Args:
            qubits (_type_): 节点包含的量子比特
            left (_type_, optional): 左子节点. Defaults to None.
            right (_type_, optional): 右子节点. Defaults to None.
            ignore (bool, optional): 是否忽略该节点. Defaults to False.
        """
        self.qubits = qubits
        self.left = left
        self.right = right
        self.ignore = ignore
        self.parent = None
        self.pos = -1


class HierarchyTree:
    """
    基于CDAP构建搜索树，参考《A New Qubits Mapping Mechanism for Multi- programming Quantum Computing》
    Args:
        qpu_file (_type_): 硬件配置文件，包含硬件拓扑信息
        w (float, optional): 错误率所占权重，越高表示越看中门和测量的保真度，为0表示只关心耦合情况. Defaults to 1.0.
    """

    def __init__(self, qpu_file, w=1.0) -> None:

        with open(qpu_file, 'r') as f:
            config = json.load(f)
        ag = nx.Graph()
        for k, e in config['overview']['coupler_map'].items():
            ag.add_edge(e[0], e[1], weight=1.0 - config['overview']['coupler_error'][k] / 100)

        for q in ag.nodes():
            ag.nodes[q]['weight'] = 1.0
            if q in config['overview']['readout_error']:
                ag.nodes[q]['weight'] = 1.0 - config['overview']['readout_error'][q] / 100

        self.G = ag
        self.m = len(ag.edges())
        self.w = w
        self.root = None
        self.all_qubits = config['overview']['qubits']

    def construct(self):
        """
        构建层次树，每次合并两个节点，直到最终只剩下一个节点
        """
        nodes = self.origin_node()
        while len(nodes) != 1:
            i, j = self.calc_F(nodes)
            # print(i, j)
            C = Node(nodes[i].qubits + nodes[j].qubits, left=nodes[i], right=nodes[j])
            C.left.parent = C
            C.left.pos = 0
            C.right.parent = C
            C.right.pos = 1
            # print(C.qubits)
            new_nodes = [C]
            for x in range(len(nodes)):
                if x == i or x == j: continue
                new_nodes.append(nodes[x])
            nodes = new_nodes
        self.root = nodes[0]

    def origin_node(self):
        """
        初始叶节点，每个比特/位置为一个叶节点
        """
        nodes = []
        for node in self.G.nodes():
            nodes.append(Node([node]))
        return nodes

    def visit(self, node):
        if node == None: return
        print(node.qubits)
        self.visit(node.left)
        self.visit(node.right)

    def get_all_leaf(self):
        """
        dfs获取所有的叶节点
        """
        leafs = []

        def dfs(node):
            if node == None: return
            if node.left == None and node.right == None:
                leafs.append(node)
            else:
                dfs(node.left)
                dfs(node.right)

        dfs(self.root)
        return leafs

    def average_fidelity(self, node):
        """
        当前节点的平均保真度，主要为节点包含比特的测量保真度和两比特门保真度

        Args:
            node (_type_): 节点
        """
        n = len(node.qubits)
        read_f = sum([self.G.nodes[q]['weight'] for q in node.qubits]) / n
        cx_f, en = 0.0, 0
        for i in range(n):
            for j in range(i):
                if self.G.has_edge(node.qubits[i], node.qubits[j]):
                    cx_f += self.G.edges[(node.qubits[i], node.qubits[j])]['weight']
                    en += 1
        if en > 0:
            cx_f /= en
        return read_f * cx_f

    def calc_Q(self, nodes):
        """
        衡量当前划分的指标

        Args:
            nodes (_type_): 当前划分下所有的节点
        """
        q = 0
        for node in nodes:
            if node.ignore == True: continue
            eii, ai = 0, 0
            for i in range(len(node.qubits)):
                for j in range(i):
                    if self.G.has_edge(node.qubits[i], node.qubits[j]): eii += 1
                ai += self.G.degree(node.qubits[i])
            ai - eii
            q += eii / self.m - (ai / self.m) ** 2
        return q

    def calc_EV(self, A, B):
        """
        计算两个节点间的平均两比特门保真度，以及平均测量保真度

        Args:
            A (_type_): 节点A
            B (_type_): 节点B
        """
        e = 0
        ecnt = 0
        v = 0
        qubits = set()
        for qa in A.qubits:
            for qb in B.qubits:
                if self.G.has_edge(qa, qb):
                    e += self.G.edges[(qa, qb)]['weight']
                    ecnt += 1
                    qubits.add(qa)
                    qubits.add(qb)
        for q in qubits: v += self.G.nodes[q]['weight']
        if e == 0 or v == 0: return 0
        return (e / ecnt) * (v / len(qubits)) * self.w

    def calc_F(self, nodes):
        """
        奖励函数，每次找奖励函数值最大的合并方案
        F = Qmerge - Qori + w * EV

        Args:
            nodes (_type_): 当前划分下所有节点
        """
        Q_origin = self.calc_Q(nodes)
        n = len(nodes)
        max_f = -1e8
        comb = (-1, -1)
        for i in range(n):
            A = nodes[i]
            A.ignore = True
            for j in range(i):
                B = nodes[j]
                B.ignore = True
                new_node = Node(A.qubits + B.qubits)
                nodes.append(new_node)
                Q_merged = self.calc_Q(nodes)
                f = Q_merged - Q_origin + self.calc_EV(A, B)
                # print(i, j, self.calc_EV(A, B))
                if f > max_f:
                    max_f = f
                    comb = (i, j)
                nodes.pop(-1)
                B.ignore = False
            A.ignore = False
        return comb


def remove(node):
    ignore_node(node)
    removed_qubits = set(node.qubits)
    if node.parent:
        if node.pos == 0:
            node.parent.left = None
        else:
            node.parent.right = None
        while node.parent:
            qubits = set(node.parent.qubits)
            node.parent.qubits = list(qubits ^ removed_qubits)
            node = node.parent


def ignore_node(node):
    if node == None: return
    node.ignore = True
    ignore_node(node.left)
    ignore_node(node.right)


def get_block(ht, qnum):
    leafs = ht.get_all_leaf()
    candidates = set()
    for leaf in leafs:
        while leaf is not None:
            if not leaf.ignore and len(leaf.qubits) >= qnum:
                candidates.add(leaf)
                break
            leaf = leaf.parent
    if not candidates: return None
    best_node = None
    max_f = -10000

    for node in candidates:
        f = ht.average_fidelity(node)
        if f > max_f:
            best_node = node
            max_f = f
    remove(best_node)
    return best_node.qubits.copy()


def partition(qpu_file, tasks):
    """
    根据任务进行分区
    任务首先会以每个比特平均包含的两比特门为键进行排序
    然后按顺序在构建的搜索树中自底向上寻找，筛选出所有满足比特数条件的节点，根据节点的平均保真度选出最优节点，节点对应的分区即为划分为该任务的分区，将节点以及其子节点从搜索树中删除

    Args:
        qpu_file (_type_): 硬件配置文件，包含硬件拓扑信息
        tasks (_type_): 任务列表
    """
    density = []
    num_q = 0
    # 任务排序
    for i, task in enumerate(tasks):
        density.append((1, task.qubits, i))
        num_q += task.qubits
    density.sort(reverse=True)

    ht = HierarchyTree(qpu_file=qpu_file, w=1)
    all_qubits = ht.all_qubits if isinstance(ht.all_qubits, int) else len(ht.all_qubits)
    assert num_q <= all_qubits
    ht.construct()
    # ht.visit(ht.root)
    blocks = [[] for _ in range(len(tasks))]
    # 选择节点
    for _, qnum, i in density:
        blocks[i] = get_block(ht, qnum)
        if blocks[i] is None: raise MemoryError("can not get partition, please reduce the number of task")

    usage = num_q / all_qubits
    return ht.all_qubits, blocks, usage


def find_tasks(now_task, tasks, qpu_file):
    """可合并任务查找
    """

    hw_config = {'qubits': 8}
    with open(qpu_file, 'r') as f:
        hw_config = json.load(f)['overview']

    qubits = now_task.qubits
    merged_task = [now_task]
    for task in tasks:
        # 已完成任务跳过
        if task.status == 'Succeed': continue
        # 已失败任务跳过
        if task.status == 'Failed': continue
        # 系统任务跳过
        if task.user_id == 0: continue
        # 当前任务跳过
        if task.task_id == now_task.task_id: continue

        if task.qubits + qubits <= hw_config['qubits']:
            merged_task.append(task)
            qubits += task.qubits
    return merged_task
