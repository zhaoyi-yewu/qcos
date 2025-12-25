#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------
import networkx as nx
import numpy as np
from networkx import DiGraph

from qcos.transpiler.cmss.mapping.utils.dg_swap_opt import DGSwap
from qcos.transpiler.cmss.mapping.utils.front_circuit import FrontCircuit


score_decay_rate_size = 0.7  # default 0.7 for IBM Q20, J-P
score_decay_rate_depth = 0.85
display_state = 0  # whether we print the internal states during search process
log_data = 0  # transcribe relevant data for figuring?

"""
default select_mode specifies the mode for evaluation during selection
"""
_select_mode_ = ["KS", 15]

"""
mode for Back Propagation
['globalscore_depth', [score_decay_rate, depth_threshold]]
recommended value:
    Q20: ['globalscore', [score_decay_rate]]
    J_P: ['globalscore', [score_decay_rate]]
"""
_mode_BP = ["globalscore", None]

"""
mode for decision
    ['global_score']:
        only consider global score
"""
_mode_decision = ["global_score"]

"""mode for simulation"""
_mode_sim = ["fix_cx_num", [500, 30]]

MCTree_key_words = [
    "select_mode",
    "mode_BP",
    "mode_decision",
    "objective",
    "score_layer",
    "use_prune",
    "use_hash",
    "init_mapping",
]

depth_cx = 1


class MCTree(DiGraph):
    """蒙特卡洛树.

    Args:
        AG: 硬件拓扑
        DG: 量子线路拓扑
        shortest_length_AG: 硬件上任意两个点间的最短距离
        shortest_path_AG: 硬件上任意两个点间的最短路径
        select_mode: 选择策略（默认 KS 方法）
        mode_BP: 反向传播方式（目前支持 globalscore）
        mode_decision: 子节点选择依据（默认 global_score）
        objective: 优化目标（size 或 depth）
        root_node: 根节点
    """

    def __init__(self, AG, DG, **args):
        """Initialize MCTree.

        swap_combination is a list of swaps to be considered
        T: ratio for node evaluation
        node_count: index for newly added node.
        """
        super().__init__()
        # check key words
        for i in args:
            if i not in MCTree_key_words:
                raise ValueError(f"Unsupported keyword {i}")
        # set parameters
        # self.use_remote = use_remote
        self.node_count = 0
        self.AG = AG
        # self.num_q_phy = len(AG)
        # the max. index of physical qubits + 1
        self.num_q_phy = max(list(AG.nodes)) + 1
        self.num_q_log = DG.num_q_log
        self.DG = DG
        self.shortest_length_AG = self.AG.shortest_length
        self.shortest_path_AG = self.AG.shortest_path
        self.max_length = nx.diameter(AG)
        self.fallback_value = self.max_length * 2
        self.fallback_count = 0
        self.selec_count = 0
        self.score_layer = args["score_layer"]
        if "select_mode" in args:
            self.select_mode = args["select_mode"]
        else:
            self.select_mode = _select_mode_.copy()
        if "mode_BP" in args:
            self.mode_BP = args["mode_BP"]
        else:
            self.mode_BP = _mode_BP.copy()
        if "use_prune" in args:
            self.use_prune = args["use_prune"]
        if "mode_decision" in args:
            self.mode_decision = args["mode_decision"]
        else:
            self.mode_decision = _mode_decision.copy()
        if "init_mapping" in args:
            self.init_mapping = args["init_mapping"]
        else:
            raise ValueError("init_mapping is required")
        self.objective = args["objective"]
        self.use_hash = args["use_hash"]
        if self.objective == "depth":
            self.opt_depth = True
        elif self.objective == "size":
            self.opt_depth = False
        elif self.objective == "no_swap":
            self.opt_depth = False
        else:
            raise ValueError(f"Unsupported objective {self.objective}.")
        # used to store some data for future analysis
        self.log = {
            "score": [],
            "visit": [],
            "swap_vs_cx": [],
            "num_remain_cx": [],
        }
        # initialize the first node
        self.root_node = self.add_node_mcts(father_node=None)
        self.init_node = self.root_node
        # init functions
        if self.objective == "depth":
            self.pick_best_son = self.pick_best_son_depth
            self.decay = score_decay_rate_depth
        if self.objective == "size":
            self.pick_best_son = self.pick_best_son_size
            self.decay = score_decay_rate_size

    def add_node_mcts(
        self, father_node, added_swap=None, remote_exe_node=None
    ):
        """Add a node to mct.

        visited_time: how many times this node has been visited
        added_swap: list like [(in1, in2),...]
        added_remote: remote CNOTs added
        swap_decay: deacy parameter for added SWAP, this is only uesful for
                    modified globalscore BP mode
        num_remain_gates: number of unexecuted CNOT gates in logical circuit
        local_score: local score
        global_score: global score considering all its son nodes, the initial
                      value is its (local) score
        sim_score: simulation score
        return: generated node number.
        """
        if father_node is None:
            # root node
            cir = FrontCircuit(self.DG, self.AG)
            # use naive mapping for the root node
            exe_gates = cir.assign_mapping_from_list(self.init_mapping)
            num_add_gates_new = 0
            remote_cxs = None
            if self.objective == "no_swap" and cir.num_remain_nodes > 0:
                raise ValueError("Fail to find a mapping requiring no swaps.")
        else:
            cir = self.nodes[father_node]["circuit"].copy()
            exe_gates = None
            num_add_gates_new = None
            remote_cxs = None
            if added_swap is not None:
                remote_cxs = None
                exe_gates = cir.swap(added_swap)
                num_add_gates_new = (
                    self.nodes[father_node]["num_add_gates"] + 3
                )
            if remote_exe_node is not None:
                remote_cxs, exe_gates = cir.execute_gate_remote(
                    remote_exe_node
                )
                num_add_gates_new = (
                    self.nodes[father_node]["num_add_gates"]
                    + len(remote_cxs)
                    - 1
                )
            if exe_gates is None or num_add_gates_new is None:
                raise ValueError(
                    "Either added_swap or remote_exe_node must be provided"
                )
        # add node and edge
        # add 'new' node and its edge
        self.add_nodes_from(["new"])
        if father_node is not None:
            self.add_edge(father_node, "new")
        # update parapeters
        # pylint: disable=invalid-sequence-index
        self.nodes["new"]["circuit"] = cir
        self.nodes["new"]["num_add_gates"] = (
            int(num_add_gates_new)
            if not isinstance(num_add_gates_new, int)
            else num_add_gates_new
        )
        self.nodes["new"]["father_node"] = father_node
        self.nodes["new"]["local_score"] = (
            int(len(exe_gates))
            if not isinstance(len(exe_gates), int)
            else len(exe_gates)
        )
        if remote_exe_node is not None:
            self.nodes["new"]["local_score"] += 1
        self.nodes["new"]["global_score"] = (
            int(self.nodes["new"]["local_score"])
            if not isinstance(self.nodes["new"]["local_score"], int)
            else self.nodes["new"]["local_score"]
        )
        self.nodes["new"]["added_swap"] = added_swap
        self.nodes["new"]["added_remote"] = remote_cxs
        self.nodes["new"]["remote_node"] = remote_exe_node
        self.nodes["new"]["executed_gates"] = exe_gates
        self.nodes["new"]["visited_time"] = 0
        # Ensure num_remain_gates is an int
        self.nodes["new"]["num_remain_gates"] = int(cir.num_remain_nodes)
        # pylint: enable=invalid-sequence-index
        # add depth once
        self.add_depth("new")
        # check already exist?
        if self.use_hash:
            new_node = hash(cir)
        else:
            new_node = self.node_count
        if new_node in self.nodes:
            # already exist
            # compare
            if self.node_cost("new") < self.node_cost(new_node):
                # the new node is better
                # print('replace')
                old_father = self.nodes[new_node]["father_node"]
                old_children = list(self.succ[new_node])
                old_global = (
                    self.nodes[new_node]["global_score"]
                    - self.nodes[new_node]["local_score"]
                )
                self.remove_node(new_node)
                # relabel node
                nx.relabel_nodes(self, {"new": new_node}, copy=False)
                # add back the original out edges and global score
                for child in old_children:
                    self.add_edge(new_node, child)
                self.nodes[new_node]["global_score"] = (
                    old_global + self.nodes[new_node]["local_score"]
                )
                self._delete_false_leaf(old_father)
                self.selec_count += min(self.nodes[new_node]["local_score"], 1)
            else:
                # the old one is better, hence wo won't create new node
                self.remove_node("new")
                return None
        else:
            # new node
            self.node_count += 1
            nx.relabel_nodes(self, {"new": new_node}, copy=False)
            self.selec_count += min(self.nodes[new_node]["local_score"], 1)
        return new_node

    def get_father(self, node):
        return self.nodes[node]["father_node"]

    def get_circuit(self, node):
        return self.nodes[node]["circuit"]

    def get_num_exe_gates(self, node):
        num_gates = len(self.nodes[node]["executed_gates"])
        if self.nodes[node]["remote_node"] is not None:
            num_gates += 1
        return num_gates

    def node_cost_from_father(self, father_node, added_swap, added_cxs):
        if father_node is None:
            return 0
        if self.opt_depth:
            depth_phy_qubits = self.nodes[father_node]["depth_phy_qubits"]
            depth = None
            if added_swap is not None:
                q_phy0, q_phy1 = added_swap
                depth = (
                    max(depth_phy_qubits[q_phy0], depth_phy_qubits[q_phy1])
                    + 3 * depth_cx
                )
            if added_cxs is not None:
                depth_phy_qubits = depth_phy_qubits.copy()
                for q_phy0, q_phy1 in added_cxs:
                    max_depth = (
                        max(depth_phy_qubits[q_phy0], depth_phy_qubits[q_phy1])
                        + depth_cx
                    )
                    depth_phy_qubits[q_phy0] = max_depth
                    depth_phy_qubits[q_phy1] = max_depth
                depth = np.max(depth_phy_qubits)
            if depth is None:
                return self.nodes[father_node]["depth"]
            return max(self.nodes[father_node]["depth"], depth)
        else:
            if added_swap is not None:
                return self.nodes[father_node]["num_add_gates"] + 3
            if added_cxs is not None:
                return (
                    self.nodes[father_node]["num_add_gates"]
                    + len(added_cxs)
                    - 1
                )
            return 0

    def node_cost(self, node):
        if self.opt_depth:
            return self.nodes[node]["depth"]
        else:
            return self.nodes[node]["num_add_gates"]

    def add_depth(self, node):
        """Add depth information to a new node.

        This should be revoked after or at the end of the add_node method.

        variables added:
            depth_phy_qubits -> a list in which the index corresponds to the
                                physical qubits and value the depth
            depth_add -> add depht corresponding to the current physical
                         circuit brougnt by insertinf SWAP gate
        """
        log_to_phy = self.nodes[node]["circuit"].log_to_phy
        father_node = self.nodes[node]["father_node"]
        # add_depth
        if father_node is None:
            # root node
            depth_add = 0
            depth_phy_qubits = np.zeros(self.num_q_phy)
        else:
            depth_phy_qubits_pre = self.nodes[father_node]["depth_phy_qubits"]
            depth_phy_qubits = np.array(depth_phy_qubits_pre)
            depth_after = np.max(depth_phy_qubits)
            # consider added SWAP
            swap = self.nodes[node]["added_swap"]
            if swap is not None:
                # ensure indices are ints to satisfy static checkers
                q_phy0, q_phy1 = int(swap[0]), int(swap[1])
                depth0, depth1 = (
                    depth_phy_qubits[q_phy0],
                    depth_phy_qubits[q_phy1],
                )
                max_depth = max((depth0, depth1)) + 3 * depth_cx
                depth_phy_qubits[q_phy0] = max_depth
                depth_phy_qubits[q_phy1] = max_depth
                depth_after = np.max(depth_phy_qubits)
            # consider remote CNOTs
            added_cxs = self.nodes[node]["added_remote"]
            remote_node = self.nodes[node]["remote_node"]
            if added_cxs is not None:
                gates = self.DG.nodes[remote_node]["gates"]
                for name, qubits, p in gates:
                    if len(qubits) == 2:
                        # add remote cxs
                        for q_phy0, q_phy1 in added_cxs[:-1]:
                            # we will exclude the last CNOT
                            q_phy0, q_phy1 = int(q_phy0), int(q_phy1)
                            max_depth = (
                                max(
                                    depth_phy_qubits[q_phy0],
                                    depth_phy_qubits[q_phy1],
                                )
                                + depth_cx
                            )
                            depth_phy_qubits[q_phy0] = max_depth
                            depth_phy_qubits[q_phy1] = max_depth
                        depth_after = np.max(depth_phy_qubits)
                        # add back the last cx
                        q_phy0, q_phy1 = (
                            int(added_cxs[-1][0]),
                            int(added_cxs[-1][1]),
                        )
                        max_depth = (
                            max(
                                depth_phy_qubits[q_phy0],
                                depth_phy_qubits[q_phy1],
                            )
                            + depth_cx
                        )
                        depth_phy_qubits[q_phy0] = max_depth
                        depth_phy_qubits[q_phy1] = max_depth
                    if len(qubits) == 1:
                        # add single-qubit gates
                        q_phy = int(log_to_phy[qubits[0]])
                        depth_phy_qubits[q_phy] += 1
            # depth increasement brought by the SWAP or remote gates
            depth_add = max(depth_after - np.max(depth_phy_qubits_pre), 0)
            # print(depth_add)
        # consider newly executed CX gates and the single-qubit gates right
        # after each CX gate
        new_exe_nodes_DG = self.nodes[node]["executed_gates"]
        for node_DG in new_exe_nodes_DG:
            for _, qubits, _ in self.DG.nodes[node_DG]["gates"]:
                num_q = len(qubits)
                if num_q == 1:
                    q_phy = int(log_to_phy[qubits[0]])
                    depth_phy_qubits[q_phy] += 1
                if num_q == 2:
                    q_phy0 = int(log_to_phy[qubits[0]])
                    q_phy1 = int(log_to_phy[qubits[1]])
                    depth0, depth1 = (
                        depth_phy_qubits[q_phy0],
                        depth_phy_qubits[q_phy1],
                    )
                    depth_after = max((depth0, depth1)) + depth_cx
                    depth_phy_qubits[q_phy0] = depth_after
                    depth_phy_qubits[q_phy1] = depth_after
        # Add relevant varibles
        self.nodes[node]["depth_phy_qubits"] = depth_phy_qubits
        self.nodes[node]["depth_add"] = depth_add
        self.nodes[node]["depth"] = np.max(depth_phy_qubits)

    def expand_node_via_swap(self, node, swap):
        added_node = self.add_node_mcts(node, added_swap=swap)
        return added_node

    def expand_node_via_remote(self, node):
        """Expand a node via reomte CNOTs."""
        # expand via remote cnot
        cir = self.nodes[node]["circuit"]
        front_nodes = cir.front_layer
        log_to_phy = cir.log_to_phy
        added_nodes = []
        # find cnot with length 1
        for exe_node in front_nodes:
            if self.DG.nodes[exe_node]["num_gate_2q"] != 1:
                continue
            qubits_log = self.DG.nodes[exe_node]["qubits"]
            qubits_phy = (
                int(log_to_phy[qubits_log[0]]),
                int(log_to_phy[qubits_log[1]]),
            )
            if self.shortest_length_AG[qubits_phy[0]][qubits_phy[1]] == 2:
                # add remote cnot
                added_node = self.add_node_mcts(
                    node, added_swap=None, remote_exe_node=exe_node
                )
                if added_node is not None:
                    added_nodes.append(added_node)
        return added_nodes

    def expansion(self, node):
        """Expand a node via all non-trivival swaps and do backpropagation."""
        if self.out_degree[node] != 0:
            raise ValueError("Expanded node already has son nodes.")

        if self.nodes[node]["num_remain_gates"] == 0:
            # we can't expand finished node
            # add selection count
            self.selec_count += 1
            return []

        swaps, swap_scores, swap_scores_front = self.nodes[node][
            "circuit"
        ].pertinent_swaps(score_layer=self.score_layer)

        # pruning threshold for exp.
        if self.use_prune:
            # recommend this strategy for random circuits
            # score_thre = np.median(swap_scores)
            score_thre = min(0, np.median(swap_scores))
        else:
            score_thre = -1 * np.inf

        added_nodes = []
        for swap, h_score, h_score_front in zip(
            swaps, swap_scores, swap_scores_front
        ):
            if h_score < score_thre and h_score_front <= 0:
                continue
            add_node = self.expand_node_via_swap(node, swap)
            if add_node is None:
                continue
            added_nodes.append(add_node)
            if self.score_layer == 0:
                continue
            # re: 0.7 for realistic circuits
            h_score *= self.decay
            self.nodes[add_node]["h_score"] = h_score
            self.nodes[add_node]["global_score"] += h_score
            self.nodes[add_node]["local_score"] += h_score
            # self.back_propagation(add_node)

        # BP
        # check if no nodes opened because of all its sons have already existed
        if self.out_degree(node) > 0:
            best_son, best_socre = self.pick_best_son(node, ["decision"])
            if best_son is not None:
                self.back_propagation(best_son)
        else:
            # check if no nodes opened because of all its sons have already
            # existed
            self._delete_false_leaf(node)

        return added_nodes

    def get_son_attributes(self, node, args):
        """Get attributes and sons from all sons of node."""
        sons = []
        num_attr = len(args)
        num_son = self.out_degree(node)
        res = []
        for _ in range(num_attr):
            res.append(np.empty([num_son]))
        pos_son = -1
        for son in self.successors(node):
            pos_son += 1
            sons.append(son)
            for pos_arg in range(num_attr):
                new_value = self.nodes[son][args[pos_arg]]
                if new_value is None:
                    # self.PrintSonNodesArgs(node, args)
                    raise ValueError("Value None")
                # 修复 W0632：元组解包加长度判断
                if (
                    isinstance(new_value, (tuple, list))
                    and len(new_value) < num_son
                ):
                    raise ValueError(
                        f"Unbalanced tuple unpacking: {new_value}"
                    )
                res[pos_arg][pos_son] = new_value
        return sons, res

    def pick_best_son_size(self, node, method):
        """This is a subfunction for selection section."""
        if method[0] == "KS":
            # Kocsis and Szepesvári method
            C = method[1]  # this is the parameter for values calculating
            args = ["global_score", "visited_time"]
            sons, res = self.get_son_attributes(node, args)
            # defensive checks to avoid unbalanced unpacking (W0632)
            if not isinstance(res, (list, tuple)) or len(res) < 2:
                raise ValueError("Unexpected get_son_attributes result (KS)")
            # pylint: disable=unbalanced-tuple-unpacking
            scores, visit = res
            # pylint: enable=unbalanced-tuple-unpacking
            if not (
                isinstance(scores, (list, tuple, np.ndarray))
                and isinstance(visit, (list, tuple, np.ndarray))
            ):
                raise ValueError("Invalid res types from get_son_attributes")
            if len(scores) != len(visit) or len(scores) != len(sons):
                raise ValueError("Unbalanced result lengths (KS)")

            sum_visit = max(np.sum(visit), 1)
            # two methods for cal values, comment one and keep one
            sqrt_term = np.sqrt(np.log(sum_visit) / (visit + 0.001))
            values = scores + C * sqrt_term

            picked_index = np.argmax(values)
            picked_node = sons[picked_index]
            return picked_node, values[picked_index]

        if method[0] == "decision":
            args = ["global_score"]
            sons, res = self.get_son_attributes(node, args)
            # expect res to be a sequence with one element: scores
            if not isinstance(res, (list, tuple)) or len(res) < 1:
                raise ValueError("Unexpected result (decision)")
            scores = res[0]
            if len(scores) != len(sons):
                raise ValueError("Unbalanced lengths (decision)")
            # if all son nodes' global score are 0
            # if np.max(scores) == 0 and np.min(scores) == 0:
            # print('WARNING: all scores of candidates are 0!')
            #    return None, 0
            picked_index = np.argmax(scores)
            picked_node = sons[picked_index]
            return picked_node, scores[picked_index]

        raise ValueError(f"Unsupported method {method}")

    def pick_best_son_depth(self, node, method):
        """This is a subfunction for selection section for depth opt."""
        if method[0] == "KS":
            # Kocsis and Szepesvári method from WIKI
            C = method[1]  # this is the parameter for values calculating
            args = ["global_score", "visited_time", "depth_add"]
            sons, res = self.get_son_attributes(node, args)
            # pylint: disable=unbalanced-tuple-unpacking
            scores, visit, depths_add = res
            # pylint: enable=unbalanced-tuple-unpacking
            scores = scores * np.power(score_decay_rate_depth, depths_add)

            sum_visit = max(np.sum(visit), 1)
            # two methods for cal values, comment one and keep one
            sqrt_term = np.sqrt(np.log(sum_visit) / (visit + 0.001))
            values = scores + C * sqrt_term

            picked_index = np.argmax(values)
            picked_node = sons[picked_index]
            return picked_node, values[picked_index]

        if method[0] == "decision":
            args = ["global_score", "depth_add"]
            sons, res = self.get_son_attributes(node, args)
            # pylint: disable=unbalanced-tuple-unpacking
            scores, depths_add = res
            # pylint: enable=unbalanced-tuple-unpacking
            # 修复 W0632：元组解包加长度判断
            if isinstance(scores, (tuple, list)) and isinstance(
                depths_add, (tuple, list)
            ):
                if len(scores) != len(depths_add):
                    raise ValueError("Unbalanced scores vs depths_add")
            scores = scores * np.power(score_decay_rate_depth, depths_add)
            # if all son nodes' global score are 0
            # if np.max(scores) == 0 and np.min(scores) == 0:
            # print('WARNING: all scores of candidates are 0!')
            #    return None, 0
            picked_index = np.argmax(scores)
            picked_node = sons[picked_index]
            return picked_node, scores[picked_index]

        raise ValueError(f"Unsupported method {method}")

    def back_propagation(self, start_node, mode_BP=None):
        """反向传播，更新父节点的分数.

        renew a variable reversely
        start_node: is the node the the original value extracted from,
                    note that the first backpropagated node is its father node
        value: Propagated value
        arg_name: the name (string) of this variable
        mode(string):
            'globalscore' ->
                when going to a new node, we compare new_value (global score of
                its son node)*args[0] + score (of current new node) with old
                global score varible, if the former is larger than the latter,
                then we update the global score of this new node.
        """
        flag = True
        if mode_BP is None:
            mode_BP = self.mode_BP
        if mode_BP[0] == "globalscore":
            dicount = self.decay
            new_value = self.nodes[start_node]["global_score"]
            current_node = self.nodes[start_node]["father_node"]
            if self.opt_depth:
                dicount = np.power(
                    self.decay, self.nodes[start_node]["depth_add"]
                )
            while flag and current_node != self.root_node:
                # calculate decay rate for propagated score
                old_value = self.nodes[current_node]["global_score"]
                new_value = new_value * dicount
                new_value = self.nodes[current_node]["local_score"] + new_value
                if new_value > old_value:
                    self.nodes[current_node]["global_score"] = new_value
                    if self.opt_depth:
                        dicount = np.power(
                            self.decay, self.nodes[current_node]["depth_add"]
                        )
                    current_node = self.nodes[current_node]["father_node"]
                else:
                    flag = False
            return

        raise ValueError(f"Unsupported BP method {mode_BP}")

    def selection(self):
        """我们从根节点选择子节点到叶节点，然后扩展叶节点并反向传播扩展节点的最佳分数."""
        current_node = self.root_node
        search_depth = 0
        # proceed until find leaf node
        while self.out_degree[current_node] != 0:
            search_depth += 1
            current_node, current_score = self.pick_best_son(
                current_node, self.select_mode
            )
            # judge whether wo should ban the expanded nodes from simulation
            # update total visited time
            self.nodes[current_node]["visited_time"] += 1

        return current_node, search_depth

    def delete_nodes(self, nodes):
        """Delete nodes and all its successors."""
        for node in nodes:
            # delete
            T_succ = nx.dfs_tree(self, node)
            self.remove_nodes_from(T_succ.nodes)

    def _delete_false_leaf(self, node):
        # check if no nodes opened because of all its sons have already existed
        # we call a node with no child after expansion a false leaf
        if node not in self.nodes:
            return
        current_node = node
        while self.out_degree(current_node) == 0:
            father = self.nodes[current_node]["father_node"]
            self.remove_node(current_node)
            current_node = father

    def fallback(self):
        print("Fallback!")
        start_node = self.root_node
        deleted_node = None
        # find the initial node for fallback
        while (
            self.nodes[start_node]["local_score"] == 0
            and start_node != self.init_node
        ):
            deleted_node = start_node
            start_node = self.nodes[start_node]["father_node"]
        # self.nodes[start_node]['circuit'].print_front_layer()
        # extract swaps list
        executable_vertex = self.nodes[start_node]["circuit"].front_layer
        log_to_phy = self.nodes[start_node]["circuit"].log_to_phy
        min_CX_dis = 1000
        chosen_CX_phy = None
        for v in executable_vertex:
            CX = self.DG.nodes[v]["qubits"]
            CX_phy = (int(log_to_phy[CX[0]]), int(log_to_phy[CX[1]]))
            currant_CX_dis = self.shortest_length_AG[CX_phy[0]][CX_phy[1]]
            if currant_CX_dis < min_CX_dis:
                min_CX_dis = currant_CX_dis
                chosen_CX_phy = CX_phy
        if chosen_CX_phy is None:
            raise ValueError("No executable vertex found")
        path = self.shortest_path_AG[chosen_CX_phy[0]][chosen_CX_phy[1]].copy()
        # num_swap = int(np.ceil(min_CX_dis/2))
        num_swap = int(min_CX_dis - 1)
        # set new root node and delete redunant nodes
        self.root_node = start_node
        if deleted_node is not None:
            self.delete_nodes([deleted_node])
        # add swaps
        flag = True
        for i in range(num_swap):
            if flag:
                added_swap = path.pop(0), path[0]
            else:
                added_swap = path.pop(), path[-1]
            flag = not flag
            added_node = self.expand_node_via_swap(self.root_node, added_swap)
            self.root_node = added_node
        if self.nodes[self.root_node]["local_score"] == 0:
            # if the newly added node still can't execute any CX, there is sth
            # wrong with the fallback procedure
            raise ValueError("Fallback error!")

    def decision(self, mode_decision=None):
        """选择一个叶子节点，删除其父节点的所有其他叶子节点."""
        # self.nodes[self.root_node]['circuit'].print_front_layer_qubits()
        # self.print_son_attrs(self.root_node,
        #                     ['added_swap', 'local_score', 'global_score'])
        if mode_decision is None:
            mode_decision = self.mode_decision
        father_node = self.root_node
        best_son = None
        if mode_decision[0] == "global_score":
            best_son, socre = self.pick_best_son(father_node, ["decision"])
        # if we can't find a son node,
        # do not update root node
        if best_son is None:
            return self.root_node
        # init selection count
        self.selec_count = 0
        # delete residual nodes
        deleted_nodes = list(self.successors(father_node))
        deleted_nodes.remove(best_son)
        self.delete_nodes(deleted_nodes)
        # self.nodes[father_node]['son_nodes'] = [best_son]
        # update fallback count
        if self.nodes[best_son]["local_score"] == 0:
            self.fallback_count += 1
        else:
            self.fallback_count = 0
        if self.fallback_count >= self.fallback_value:
            # raise()
            self.fallback()
            self.fallback_count = 0
            return self.root_node
        # update root node
        self.root_node = best_son
        # print('Chosen next node is %d \n' %best_son)
        if display_state:
            print(
                f"\r{self.nodes[self.root_node]['num_remain_gates']} "
                f"gates unfinished",
                end="",
            )
            # print('added swap info')
            # self.nodes[self.root_node]['circuit'].print_front_layer_len()
            # self.nodes[self.root_node]['circuit'].print_front_layer_qubits()
            # print()
        return self.root_node

    # Simulation phase of the MCTS algorithm.
    def sim_function(self, gate0, gate1, *args):
        if len(args) == 2:
            mapping, times_sim = args
            return self._sim_function_size(gate0, gate1, mapping, times_sim)
        elif len(args) == 5:
            (
                single_gate0,
                single_gate1,
                depth_phy_qubits,
                mapping,
                times_sim,
            ) = args
            return self._sim_function_depth(
                gate0,
                gate1,
                single_gate0,
                single_gate1,
                depth_phy_qubits,
                mapping,
                times_sim,
            )
        else:
            raise ValueError("Invalid arguments for sim_function")

    # Simulation method targeting size.
    def _sim_function_size(self, gate0, gate1, mapping, times_sim):
        num_swaps = 0
        current_gate_idx = 0
        num_gates = len(gate0)
        edges = list(self.AG.edges)

        while current_gate_idx < num_gates and num_swaps < times_sim:
            # Execute executable gates
            while current_gate_idx < num_gates:
                u = mapping[gate0[current_gate_idx]]
                v = mapping[gate1[current_gate_idx]]
                if self.shortest_length_AG[u][v] == 1:
                    current_gate_idx += 1
                else:
                    break

            if current_gate_idx >= num_gates:
                break

            # Greedy strategy: select SWAP reducing sum of distances
            best_swap = None
            min_dist_sum = float("inf")

            current_locs0 = [mapping[g] for g in gate0[current_gate_idx:]]
            current_locs1 = [mapping[g] for g in gate1[current_gate_idx:]]

            current_dist_sum = 0
            for u, v in zip(current_locs0, current_locs1):
                current_dist_sum += self.shortest_length_AG[u][v]

            min_dist_sum = current_dist_sum
            found_better = False

            for p, q in edges:
                temp_dist_sum = current_dist_sum
                affected = False

                # Calculate new distance sum for this swap
                for i in range(len(current_locs0)):
                    u = current_locs0[i]
                    v = current_locs1[i]

                    if u != p and u != q and v != p and v != q:
                        continue

                    affected = True
                    old_dist = self.shortest_length_AG[u][v]

                    new_u = u
                    if u == p:
                        new_u = q
                    elif u == q:
                        new_u = p

                    new_v = v
                    if v == p:
                        new_v = q
                    elif v == q:
                        new_v = p

                    new_dist = self.shortest_length_AG[new_u][new_v]
                    temp_dist_sum = temp_dist_sum - old_dist + new_dist

                if affected and temp_dist_sum < min_dist_sum:
                    min_dist_sum = temp_dist_sum
                    best_swap = (p, q)
                    found_better = True

            if not found_better:
                # Fallback: Swap on shortest path of the first gate
                u = mapping[gate0[current_gate_idx]]
                v = mapping[gate1[current_gate_idx]]
                path = self.shortest_path_AG[u][v]
                if len(path) > 1:
                    best_swap = (u, path[1])
                else:
                    break

            # Perform swap
            p, q = best_swap
            for i in range(len(mapping)):
                if mapping[i] == p:
                    mapping[i] = q
                elif mapping[i] == q:
                    mapping[i] = p

            num_swaps += 1

        return num_swaps

    def _sim_function_depth(
        self,
        gate0,
        gate1,
        single_gate0,
        single_gate1,
        depth_phy_qubits,
        mapping,
        times_sim,
    ):
        num_swaps = self._sim_function_size(gate0, gate1, mapping, times_sim)
        # Assuming sequential swaps for depth calculation in simulation
        num_depth_swap = num_swaps
        return None, num_depth_swap, num_swaps

    def simulation(self, sim_node, mode_sim=None):
        """Simulation and BP the simulation score.

        Different modes for simulation
        mode_sim = ['name', arg_list]
            name:

                fix_cx_num ->
                do simulation executing fixed number of CNOT gates.
                arg_list = [simulation_times, num_CX_gates]
        """
        if sim_node == self.root_node:
            return None
        if mode_sim is None:
            mode_sim = self.mode_sim

        if mode_sim[0] == "fix_cx_num" and self.objective == "size":
            # this is the number of CNOT to be executed
            num_exe_cx = mode_sim[1][1]
            times_sim = mode_sim[1][0]  # how many times
            cir = self.nodes[sim_node]["circuit"]
            gate0, gate1 = cir.get_future_cx_fix_num(num_exe_cx)
            if len(gate0) < num_exe_cx:
                return None
            # because the obtained qubits are physical, we only need naive
            # mapping
            mapping = list(range(self.num_q_phy))
            num_swap_sim = self.sim_function(gate0, gate1, mapping, times_sim)
            # convert the # swaps to simulation score
            sim_score = len(gate0) * np.power(self.decay, num_swap_sim / 2)
            # we backpropagate the simulation score
            new_value = self.nodes[sim_node]["local_score"] + sim_score
            if new_value > self.nodes[sim_node]["global_score"]:
                self.nodes[sim_node]["global_score"] = new_value
                self.back_propagation(sim_node)
            return None

        if mode_sim[0] == "fix_cx_num" and self.objective == "depth":
            decay_BP_depth = 0.85
            # this is the number of CNOT to be executed
            num_exe_cx = mode_sim[1][1]
            times_sim = mode_sim[1][0]  # how many times
            cir = self.nodes[sim_node]["circuit"]
            gate0, gate1, single_gate0, single_gate1 = (
                cir.get_future_cx_fix_num_with_single(num_exe_cx)
            )
            depth_phy_qubits = list(self.nodes[sim_node]["depth_phy_qubits"])
            # we abandon the simulation with only 1 gate
            # do we really need to do this?
            if len(gate0) < num_exe_cx:
                return None
            # gen map list for simulation
            # because the obtained qubits are physical, we only need naive
            # mapping
            mapping = list(range(self.num_q_phy))
            res_sim = self.sim_function(
                gate0,
                gate1,
                single_gate0,
                single_gate1,
                depth_phy_qubits,
                mapping,
                times_sim,
            )
            _, num_depth_swap, num_swap_sim = res_sim
            num_gates = len(gate0)
            num_depth_swap = num_depth_swap * 2
            h_score = num_gates * np.power(
                decay_BP_depth ** (num_depth_swap / num_swap_sim),
                num_swap_sim / 2,
            )
            # we backpropagation heuristic score
            new_value = self.nodes[sim_node]["local_score"] + h_score
            if new_value > self.nodes[sim_node]["global_score"]:
                self.nodes[sim_node]["global_score"] = new_value
                self.back_propagation(sim_node)
            return True

        raise ValueError(f"Unsupported simultation method {mode_sim}")

    def get_swaps(self):
        node = self.init_node
        swaps = []
        while self.out_degree(node) > 0:
            if self.out_degree(node) > 1:
                raise ValueError("Multiple successors found")
            node = list(self.successors(node))[0]
            swaps.append(self.nodes[node]["added_swap"])
        return swaps

    def to_dg(self):
        dg = DGSwap(self.AG)
        node = self.init_node
        while True:
            if self.out_degree(node) > 1:
                raise ValueError("Multiple successors found")
            swap = self.nodes[node]["added_swap"]
            # remote_cnots = self.nodes[node]['added_remote']
            nodes_dg = self.nodes[node]["executed_gates"]
            log_to_phy = self.get_circuit(node).log_to_phy
            # add swap gates
            if swap is not None:
                dg.add_gate(("swap", tuple(swap), []))
            # add transformed gates
            for node_dg in nodes_dg:
                gates = self.DG.nodes[node_dg]["gates"]
                for name, qubits_log, p in gates:
                    qubits_phy = [log_to_phy[q] for q in qubits_log]
                    dg.add_gate((name, tuple(qubits_phy), p))
            if self.out_degree(node) == 0:
                break
            node = list(self.successors(node))[0]

        # extract SWAP gates in the DG
        swap_nodes = []
        for node in dg.nodes:
            if node == dg.root:
                continue
            name = dg.get_node_gates(node)[0][0]
            if name == "swap":
                swap_nodes.append(node)
        dg.swap_nodes = tuple(swap_nodes)
        # add depth information to each edge
        dg.add_depth_to_all_edges()
        return dg

    def print_node_attrs(self, node, names):
        print(f"  node {node}")
        for name in names:
            print(f"    {name} is {self.nodes[node][name]}")

    def print_son_attrs(self, father_node, names_son, names_father=[]):
        if not isinstance(names_son, list) and not isinstance(
            names_son, tuple
        ):
            raise ValueError(
                f"names argument must be list or tuple, but it is "
                f"{type(names_son)}"
            )
        if not isinstance(names_father, list) and not isinstance(
            names_father, tuple
        ):
            raise ValueError(
                f"names argument must be list or tuple, but it is "
                f"{type(names_father)}"
            )
        print(f"father node is {father_node}")
        sons = self.succ[father_node]
        for name in names_father:
            print(f"    {name} is {self.nodes[father_node][name]}")
        print(f"all son nodes of {father_node}")
        for son in sons:
            self.print_node_attrs(son, names_son)
