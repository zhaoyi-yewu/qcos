import networkx as nx
from collections import defaultdict
from qcos.transpiler.cmss.compiler import *
from copy import deepcopy


def get_qpu_configs(qpu_configs):
    """硬件参数解析，获取一个配置字典

    Args:
        qpu_configs (_type_): 硬件配置
    """
    if qpu_configs:
        validate_keys = [
            "qubits",
            "storage_area",
            "operate_area",
            "coupler_map",
            "readout_error",
            "coupler_error",
            "closest"
        ]
        for validate_key in validate_keys:
            if validate_key not in qpu_configs:
                break
            return qpu_configs

    # use default qpu_configs
    default_qpu_configs = {
        "qubits": 6,
        "storage_area": ["S27", "S28", "S29", "S35", "S36", "S37"],
        "operate_area": ["P27", "SP28", "SP29", "P35", "P36", "SP37"],
        "coupler_map": {
            "G0": ["P27", "P35"], "G1": ["P28", "P36"],
            "G2": ["P29", "P37"], "G3": ["P27", "P28"],
            "G4": ["P35", "P36"], "G5": ["P28", "P29"], "G6": ["P36", "P37"]
        },
        "readout_error": {
            "S27": 1.0,
            "S28": 2.0,
            "S35": 3.0,
            "S36": 4.0,
            "S29": 5.0,
            "S37": 6.0
        },
        "coupler_error": {
            "G0": 3.0,
            "G1": 3.0,
            "G2": 3.0,
            "G3": 3.0,
            "G4": 3.0,
            "G5": 3.0
        },
        "closest": {
            "P27": "S27",
            "P28": "S28",
            "P35": "S35",
            "P36": "S36",
            "P29": "S29",
            "P37": "S37"
        }
    }
    return default_qpu_configs


def get_dg(qasm, pos_num):
    """量子任务拓扑分析

    Args:
        qasm (_type_): openqasm2.0
    """

    # 低阶编译，得到基础门列表
    abs_tree = get_abs_tree(qasm)
    qnum, gates = get_ir(abs_tree)

    # 构建拓扑图
    dg = nx.DiGraph()
    dg.num_q = qnum
    dg.measure = []

    pre_nodes = defaultdict(lambda: -1)

    for idx, gate in enumerate(gates):

        if len(gate.targets) > pos_num:
            raise MemoryError(
                f"操作区仅能操作{qnum}个比特，{gate.name}执行需要{len(gate.targets)}，请调整程序或扩大操作区")

        if gate.name == 'measure':
            dg.measure.append(gate)
            continue
        if len(gate.targets) == 1:
            # 单比特门，同一比特上的连续单比特门合并（中性原子放到操作区后，可先把连续的单比特门执行完成）
            # 如该比特前面有执行两比特门，则从两比特门对应节点连一条有向线到该节点
            qubit = gate.targets[0]
            if pre_nodes[qubit] == -1:
                dg.add_node(idx, gate=[gate], qubits=gate.targets, type='single')
                pre_nodes[qubit] = idx
            else:
                node = pre_nodes[qubit]
                if len(gates[node].targets) == 1:
                    dg.nodes[node]['gate'].append(gate)
                else:
                    dg.add_node(idx, gate=[gate], qubits=gate.targets, type='single')
                    dg.add_edge(node, idx)
                    pre_nodes[qubit] = idx
        else:
            # 两比特门，前置节点包含其中某个比特，则连一条有向线
            dg.add_node(idx, gate=gate, qubits=gate.targets, type='multi')
            for qid in gate.targets:
                if pre_nodes[qid] != -1:
                    dg.add_edge(pre_nodes[qid], idx)
                pre_nodes[qid] = idx
    return dg


class NASingleRoute():

    def __init__(self, qasm, qpu_configs={}, **kwargs):

        self.qpu_config = get_qpu_configs(qpu_configs)
        self.storage_area = self.qpu_config['storage_area']
        self.operate_area = self.qpu_config['operate_area']
        self.ag = nx.Graph()
        for k, (a, b) in self.qpu_config['coupler_map'].items():
            if (a not in self.operate_area) or (b not in self.operate_area): continue
            self.ag.add_edge(a, b)
        self.ag.shortest_length = dict(nx.shortest_path_length(self.ag, source=None,
                                                               target=None,
                                                               weight=None,
                                                               method='dijkstra'))

        abs_tree = get_abs_tree(qasm)
        qnum, gates = get_ir(abs_tree)
        self.gates = gates
        self.qnum = qnum
        assert len(self.storage_area) >= self.qnum
        err_dict = {}
        for k, v in self.qpu_config['readout_error'].items():
            if k in self.storage_area:
                err_dict[k] = v
        sq = sorted(err_dict.items(), key=lambda e: e[1])[:self.qnum]
        self.mapping = dict([(a, b[0]) for a, b in zip(range(self.qnum), sq)])
        self.qids = [int(q[0][1:]) for q in sq]

    def execute_with_order(self):
        """
        按比特执行门，将比特上所有单比特门执行完后，再执行下一个比特的门
        """
        gates_on_qubit = {}
        measure = []
        for gate in self.gates:
            assert len(gate.targets) == 1
            gate.targets = [int(self.mapping[int(q)][1:]) for q in gate.targets]
            if gate.name == 'measure':
                measure.append(gate)
                continue
            if gate.targets[0] not in gates_on_qubit:
                gates_on_qubit[gate.targets[0]] = []
            gates_on_qubit[gate.targets[0]].append(gate)

        gates = []
        for q in gates_on_qubit:
            gates += gates_on_qubit[q]
            # gates.append(create_gate('sync', self.qids))
        gates += measure
        return gates


class NARoute():
    """中性原子路由

    Args:
        storage_area：存储区位置
        operate_area：操作区位置
        ag：操作区的拓扑图，节点为每个位置，两个位置间可以做两比特门，则连一条边
        qpu_configs: 硬件配置信息
        qasm: openqasm2.0
    """

    def __init__(self, qasm, qpu_configs={}, **kwargs):

        self.qpu_config = get_qpu_configs(qpu_configs)
        self.storage_area = self.qpu_config['storage_area']
        self.operate_area = self.qpu_config['operate_area']
        self.ag = nx.Graph()
        for k, (a, b) in self.qpu_config['coupler_map'].items():
            if (a not in self.operate_area) or (b not in self.operate_area): continue
            self.ag.add_edge(a, b)
        self.ag.shortest_length = dict(nx.shortest_path_length(self.ag, source=None,
                                                               target=None,
                                                               weight=None,
                                                               method='dijkstra'))
        self.qasm = qasm
        self.all_qubits = self.qpu_config['qubits']

    def get_init_mapping(self):
        """比特初始映射及映射表构建

            dg：量子线路拓扑
            dg_opt：dg的深拷贝，用以将处理后的节点删除，并寻找新的可执行节点
            mapping：比特所处存储区位置（目前比特与存储区一一对应，方便维护）
            oloc：比特对应的操作区位置，若不在操作区则为-1
            oqloc：操作区中的比特，若不存在则为-1
            ohas：操作区包含的所有比特
            locked：锁定的量子比特（这些比特不能再移动位置）
            res：最终映射后的指令集列表
        """
        self.dg = get_dg(self.qasm, len(self.operate_area))
        self.qnum = self.dg.num_q
        assert len(self.storage_area) >= self.qnum
        self.pre_node = None
        self.dg_opt = deepcopy(self.dg)
        err_dict = {}
        for k, v in self.qpu_config['readout_error'].items():
            if k in self.storage_area:
                err_dict[k] = v
        sq = sorted(err_dict.items(), key=lambda e: e[1])[:self.qnum]
        self.mapping = dict([(a, b[0]) for a, b in zip(range(self.qnum), sq)])
        # self.sloc = dict([(a, b) for a, b in zip(range(self.qnum), self.storage_area[:self.qnum])])
        # self.sqloc = dict([(a, b) for a, b in zip(self.storage_area[:self.qnum], range(self.qnum))])
        self.oloc = dict([(a, -1) for a in range(self.qnum)])
        self.oqloc = dict([(a, -1) for a in self.operate_area])
        self.ohas = set()
        self.locked = set()
        self.res = []

    def get_front_layer(self):
        """获取当前可执行的节点，节点可执行的条件是入度为0
        """
        front_layer = set()
        for node in self.dg_opt.nodes():
            if self.dg_opt.in_degree[node] == 0:
                front_layer.add(node)
        return front_layer

    def find_pos(self, dis):
        """在操作区中寻找可放置比特的位置，若不存在，则为-1

        Args:
            dis (int): 与现有的比特间的距离至少为dis
        """
        disable_pos = set()
        for o in self.ohas:
            # 将操作区中已有比特以及与该比特距离小于dis的比特全部排除
            disable_pos.add(o)
            for nxt in self.ag.shortest_length[o]:
                if self.ag.shortest_length[o][nxt] < dis: disable_pos.add(nxt)
        for o in self.operate_area:
            if o not in disable_pos: return o
        return -1

    def back(self, o):
        """将比特移到操作区，并更新映射表
        Args:
            o：操作区位置
        """
        q = self.oqloc[o]
        self.res.append(MOV(targets=[q], arg_value=[o, self.mapping[q]], type=-2))  # f"back {self.oqloc[o]} {o}"
        self.oloc[q] = -1
        self.oqloc[o] = -1
        self.ohas.remove(o)

    def put(self, q, o):
        """将比特移到存储区，并更新映射表
        Args:
            q：需要操作的比特
            o：操作区位置
        """
        self.res.append(MOV(targets=[q], arg_value=[self.mapping[q], o], type=-3))  # f"put {q} {o}")
        self.oloc[q] = o
        self.oqloc[o] = q
        self.ohas.add(o)

    def mov(self, o1, o2):
        """将比特从存取区的某一位置移到另一位置，并更新映射表
        Args:
            o1：操作区起始位置
            o2：操作区目标位置
        """
        q = self.oqloc[o1]
        self.res.append(MOV(targets=[q], arg_value=[o1, o2], type=-4))  # f"mov {self.oqloc[o1]} {o2}")
        self.oloc[q] = o2
        self.oqloc[o1] = -1
        self.oqloc[o2] = q
        self.ohas.remove(o1)
        self.ohas.add(o2)

    def pre_back(self, nodes):
        """将操作区中不属于当前可执行门的比特移回存储区

        Args:
            nodes (List): 当前可执行门列表
        """
        all_q = set()
        for node in nodes:
            qubits = self.dg.nodes[node]['qubits']
            for q in qubits:
                all_q.add(q)
        ohas = self.ohas.copy()
        for o in ohas:
            if self.oqloc[o] not in all_q:
                self.back(o)

    def get_empty_neighbor(self, p):
        """获取操作区某一位置的相邻空位置

        Args:
            p: 操作区位置
        """
        n = set(self.ag.neighbors(p))
        n -= (n & self.ohas)
        if len(n) > 0:
            return list(n)[0]
        return -1

    def get_unlocked_neighbor(self, p):
        """获取操作区某一位置的相邻非上锁位置
        Args:
            p: 操作区位置
        """
        for nxt in self.ag.neighbors(p):
            if nxt not in self.locked:
                return nxt
        return -1

    def mov_to_neighbors(self, p1, p2):
        """将比特1和比特2移到相邻位置，前提为两个比特均已在操作区

        Args:
            p1：比特1当前所在的操作区位置
            p2：比特2当前所在的操作区位置
        """
        # 如果直接相邻，则无需操作，直接返回
        if p2 in self.ag.neighbors(p1): return True
        # 找操作区p1的相邻空位置，若存在则将比特2移到该位置
        d = self.get_empty_neighbor(p1)
        if d != -1:
            self.mov(p2, d)
            self.locked.add(p1)
            self.locked.add(d)
            return True
        # 找操作区p2的相邻空位置，若存在则将比特1移到该位置
        d = self.get_empty_neighbor(p2)
        if d != -1:
            self.mov(p1, d)
            self.locked.add(p2)
            self.locked.add(d)
            return True
        # 找操作区p1的相邻非上锁位置，若存在则将比特2放到该位置，原位置的比特移回存储区
        d = self.get_unlocked_neighbor(p1)
        if d != -1:
            self.back(d)
            self.mov(p2, d)
            self.locked.add(p1)
            self.locked.add(d)
            return True
        # 找操作区p2的相邻非上锁位置，若存在则将比特1交换到该位置，原位置的比特移回存储区
        d = self.get_unlocked_neighbor(p2)
        if d != -1:
            self.back(d)
            self.mov(p2, d)
            self.locked.add(p2)
            self.locked.add(d)
            return True
        return False

    def put_to_neighbors1(self, p1, q):
        """将q放到p1的相邻位置，前提为q在存储区

        Args:
            p1：比特1当前所在的操作区位置
            q：需要移动的比特
        """
        # 找操作区p1的相邻空位置，若存在则将q移到该位置
        d = self.get_empty_neighbor(p1)
        if d != -1:
            self.put(q, d)
            self.locked.add(p1)
            self.locked.add(d)
            return True
        return False

    def put_to_neighbors2(self, q1, q2):
        """将比特q1，q2放到相邻位置，前提为q1，q2均在存储区

        Args:
            q1, q2：比特
        """
        # 从硬件拓扑图中找到一条边，该边的两个节点都还未放入比特
        for a, b in self.ag.edges():
            if a not in self.ohas and b not in self.ohas:
                self.put(q1, a)
                self.put(q2, b)
                self.locked.add(a)
                self.locked.add(b)
                return True
        return False

    def execute_multi_nodes(self, nodes):
        """执行两比特门

        Args:
            nodes (List): 所有当前可执行的两比特门对应的节点
        """
        # 重置锁定比特，通过mov_multi_nodes先将可同时执行的两比特门对应的比特位置调整好（放到相邻的位置）
        self.locked = set()
        remain = self.mov_multi_nodes(nodes)
        for node in remain:
            # 不能执行的两比特门，对应比特需要放回存储区
            for q in self.dg.nodes[node]['qubits']:
                if self.oloc[q] != -1:
                    self.back(self.oloc[q])
        for node in nodes:
            if node in remain: continue
            self.pre_node = node
            self.res.append(self.dg.nodes[node]['gate'])
            self.dg_opt.remove_node(node)

    def mov_multi_nodes(self, nodes):
        """两比特门执行前，将比特先放置在操作区合适的位置

        Args:
            nodes (List): 所有当前可执行的两比特门对应的节点
        """
        # 先将其余的量子比特移回存储区
        self.pre_back(nodes)
        remain = []
        for node in nodes:
            # 每个两比特门判断当前两个比特的位置是否符合要求
            qubits = self.dg.nodes[node]['qubits']
            p1, p2 = self.oloc[qubits[0]], self.oloc[qubits[1]]
            if p1 != -1 and p2 != -1:
                # 均在操作区
                if not self.mov_to_neighbors(p1, p2): remain.append(node)
            elif p1 != -1 and p2 == -1:
                # 一个在操作区，一个在存储区
                if not self.put_to_neighbors1(p1, qubits[1]): remain.append(node)
            elif p1 == -1 and p2 != -1:
                if not self.put_to_neighbors1(p2, qubits[0]): remain.append(node)
            else:
                # 都在存储区
                if not self.put_to_neighbors2(qubits[0], qubits[1]): remain.append(node)
        return remain

    def execute_single_node(self, node):
        """执行单比特门

        Args:
            node: 当前可执行的单比特门对应的节点
        """
        # 先将其余的量子比特移回存储区
        self.pre_back([node])
        q = self.dg.nodes[node]['qubits'][0]
        p = self.oloc[q]
        if p == -1:
            # 如果比特在存储区，先将比特移入操作区
            dis = 3
            while dis > 0 and p == -1:
                p = self.find_pos(dis)
                dis -= 1
            # 单比特门必定可以找到位置
            # if p == -1: raise LookupError("操作区没有剩余的位置放置比特")
            self.put(q, p)
        self.pre_node = node
        self.res += self.dg.nodes[node]['gate']
        self.dg_opt.remove_node(node)

    def overlap(self, nd1, nd2):
        """判断两个单比特节点包含的门列表是否满足nd2为nd1的后缀
            若nd2为nd1的后缀，则在执行nd1的所有单比特门时，可在适当位置将nd2的比特放入操作区，后续单比特门可一起执行
            如nd1比特为Q1，包含[H, X], nd2比特为Q2包含[X]
                一般执行顺序为：PUT Q1; H Q1; X Q1; BACK Q1; PUT Q2; X Q2
                优化顺序：PUT Q1; H Q1; PUT Q2; X Q1 Q2;
        Args:
            nd1: 节点1
            nd2: 节点2
        """
        gt1 = self.dg.nodes[nd1]['gate']
        gt2 = self.dg.nodes[nd2]['gate']
        if len(gt1) < len(gt2): return False
        l = 0
        for i in range(len(gt1) - len(gt2), len(gt1)):
            if gt1[i].name != gt2[l].name: return False
            l += 1
        return True

    def add_put(self, res, opt):
        """将overlap中的put操作放入对应的位置

        Args:
            res: 当前的指令集列表
            opt: put操作
        """
        q = opt.targets[0]
        i = len(res) - 1
        while i >= 0:
            # print("add put: ", res[i])
            if not isinstance(res[i], MOV): break
            t = res[i]
            if t.type == -2 and t.targets[0] == q:
                # 若有直接相邻的back操作，且作用在同一比特上，可消除
                op = t.arg_value[0]
                p = self.oloc[q]
                self.ohas.remove(p)
                self.ohas.add(op)
                self.oqloc[p] = -1
                self.oqloc[op] = q
                self.oloc[q] = op
                return res[:i] + res[i + 1:]
            i -= 1
        res.append(opt)
        return res

    def adjust_pos(self, pos, posq):
        """调整put操作的位置，调用add_put，放入合适的位置
        Args:
            pos: 所有的put操作
            posq: 操作对应的比特
        """
        if pos == []: return
        n = len(pos)
        res = self.res[-n:]
        self.res = self.res[:-n]
        new_res = []
        pre = 0
        targets = self.res[-1].targets.copy()
        # 安装放入位置排序，位置小的先放入，放入后，后续所有门的目标量子比特都需更新
        for p, r, q in sorted(zip(pos, res, posq)):
            if p == pre:
                new_res = self.add_put(new_res, r)
                targets.append(q)
            else:
                if pre > 0:
                    for gate in self.res[pre:p]:
                        if not isinstance(gate, MOV):
                            gate.targets = targets.copy()
                new_res += self.res[pre:p]
                # new_res.append(r)
                new_res = self.add_put(new_res, r)
                targets.append(q)
            pre = p

        for gate in self.res[pre:]:
            if not isinstance(gate, MOV):
                gate.targets = targets.copy()

        new_res += self.res[pre:]
        self.res = new_res

    def execute_single_node_opt(self):
        """执行单比特门，通过overlap进行优化
        """
        pos = []
        posq = []
        front_layer = self.front_layer.copy()
        for node in front_layer:
            if self.dg.nodes[node]['type'] == 'single':
                if self.overlap(self.pre_node, node):
                    q = self.dg.nodes[node]['qubits'][0]
                    p = self.find_pos(1)
                    if p != -1:
                        # 如果能找到空的位置，则移到操作区一起执行
                        self.put(q, p)
                        pos.append(-1 * len(self.dg.nodes[node]['gate']))
                        posq.append(q)
                        self.dg_opt.remove_node(node)
                        self.front_layer.remove(node)
        self.adjust_pos(pos, posq)

    def get_max_common(self):
        """从当前可执行节点中找可执行的节点
        """
        multi_qubits = set()
        multi_nodes = []
        comm = 0
        execute_node = None
        for node in self.front_layer:
            qubits = self.dg.nodes[node]['qubits']
            # 如果为单比特门，优先选择比特已在操作区，且可执行的门的列表最长
            if self.dg.nodes[node]['type'] == 'single':
                if comm > 1: continue
                if qubits[0] not in self.ohas and comm == 1: continue

                if qubits[0] in self.ohas: comm = 1

                if execute_node is not None and len(self.dg.nodes[execute_node]['gate']) >= len(
                        self.dg.nodes[node]['gate']):
                    continue
                execute_node = node
            else:
                # 如果为两比特门，添加到可执行列表中（两比特门默认均为CX，可一起执行）
                multi_qubits.update(set(qubits))
                comm = max(comm, len(multi_qubits & self.ohas))
                multi_nodes.append(node)
        if comm <= 1:
            if execute_node is not None: return 1, execute_node
        return 2, multi_nodes

    def execute_with_order(self):
        """按顺序执行门，不进行优化
        """
        self.get_init_mapping()
        for node in self.dg.nodes():
            if self.dg.nodes[node]['type'] == 'single':
                self.execute_single_node(node)
            else:
                self.execute_multi_nodes([node])
        return self.res

    def execute_with_opt(self):
        """按拓扑序执行门，进行简单的优化
        """
        self.get_init_mapping()
        self.front_layer = self.get_front_layer()
        t = 0
        while self.front_layer:
            # 若前一个执行的为单比特节点，可从当前可执行节点中找所有的单比特节点，进行overlap优化
            if self.pre_node is not None and self.dg.nodes[self.pre_node]['type'] == 'single':
                self.execute_single_node_opt()
                self.front_layer = self.get_front_layer()

            if self.front_layer:
                i, node = self.get_max_common()
                if i == 1:
                    self.execute_single_node(node)
                else:
                    self.execute_multi_nodes(node)

            self.front_layer = self.get_front_layer()
            t += 1

        return self.res

    def printinfo(self):
        for opt in self.res:
            print(opt)
