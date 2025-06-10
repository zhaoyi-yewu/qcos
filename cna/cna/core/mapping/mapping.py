# -*- coding: utf-8 -*-
"""
Created on Tue Mar 21 11:35:00 2023

Modified on Oct 19

@author: zhoux

The programs for finding initial mappings are based on:
    @article{zhou2020quantum,
      title={Quantum circuit transformation based on simulated annealing and heuristic search},
      author={Zhou, Xiangzhen and Li, Sanjiang and Feng, Yuan},
      journal={IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems},
      volume={39},
      number={12},
      pages={4683--4694},
      year={2020},
      publisher={IEEE}
    }
    
    @article{li2020qubit,
      title={Qubit mapping based on subgraph isomorphism and filtered depth-limited search},
      author={Li, Sanjiang and Zhou, Xiangzhen and Feng, Yuan},
      journal={IEEE Transactions on Computers},
      volume={70},
      number={11},
      pages={1777--1788},
      year={2020},
      publisher={IEEE}
      }
    
The programs for qubit routing are based on:
    @inproceedings{zhou2020monte,
      title={A monte carlo tree search framework for quantum circuit transformation},
      author={Zhou, Xiangzhen and Feng, Yuan and Li, Sanjiang},
      booktitle={Proceedings of the 39th International Conference on Computer-Aided Design},
      pages={1--7},
      year={2020}
    }
    
    @article{zhou2022quantum,
      title={Quantum Circuit Transformation: A Monte Carlo Tree Search Framework},
      author={Zhou, Xiangzhen and Feng, Yuan and Li, Sanjiang},
      journal={ACM Transactions on Design Automation of Electronic Systems (TODAES)},
      year={2022},
      publisher={ACM New York, NY}
    }
"""
from .cir_dg import DG
import networkx as nx
import numpy as np
from .monte_carlo_tree import MCTree
from .init_mapping.get_init_map import get_init_map
#from .genetic_swap_depth_opt import genetic_opt

# simulated_annealing, subgraph_isomorphism naive, Topgraph
method_init_mapping = 'Topgraph'

#print('We use {} mapping!'.format(method_init_mapping))

def layout_dict_to_list(layout_dict):
    num_q_log = max(list(layout_dict.keys())) + 1
    layout_list = [-1] * num_q_log
    for key in layout_dict.keys():
        layout_list[key] = layout_dict[key]
    return layout_list

def layout_list_to_dict(layout_list):
    layout_dict = {}
    for i, v in enumerate(layout_list):
        layout_dict[i] = v
    return layout_dict

def layout_dict_reverse(layout_dict):
    layout_dict_r = {v:k for k, v in layout_dict.items()}
    return layout_dict_r

def import_qpu_file(qpu_config, disable_qubits=[]):
    """硬件参数解析，获取一个包含耦合列表的字典

    Args:
        qpu_config: 硬件配置文件或字典
        disable_qubits: 不可用比特列表. Defaults to [].
    """
    qpu_config_dice = {}
    if isinstance(qpu_config, str):
        import json
        with open(qpu_config, 'r') as f:
            config = json.load(f)
        coupler_map = config['overview']['coupler_map']
    else:
        coupler_map = qpu_config['overview']['coupler_map']
    adjacency_list = []
    for Q1, Q2 in coupler_map.values():
        q1 = int(Q1[1:])
        q2 = int(Q2[1:])
        if Q1 in disable_qubits or Q2 in disable_qubits: continue
        adjacency_list.append([q1, q2])
    qpu_config_dice['adjacency_list'] = adjacency_list
    return qpu_config_dice

def mapping(qasm_str, qpu_file, disable_qubits = [], initial_layout=None, objective='size',
              seed=None, use_post_opt=False,):
    """
    基于swap门的映射接口
    该接口通过搜索从虚拟量子位到物理量子位的映射和交换策略来传输qasm字符串，以便qasm描述的电路可以安装到coupling_map描述的硬件中，同时减少电路深度。
    该方法基于蒙特卡罗搜索，可参考《Quantum Circuit Transformation: A Monte Carlo Tree Search Framework》
    Parameters
    ----------
    qasm : string
        qasm string
    coupling_map:
        can be either 
            a list [(phy_q_i, phy_q_i), ...] in which (phy_q_i, phy_q_i)
            indicates that the physical qubits i and j are coupled 
        or
            a nx.Graph object the nodes and edges in which represent respectively
            the corresponding physical qubits and their connectivities.
    initial_layout : dict, optional
        Initial position of virtual qubits on physical qubits.
        If given, this is the initial state in search of virtual to physical qubit mapping
        e.g.:
            {0:4, 1:1, 2:5, 3:2, 4:0, 5:3}
        The default is None.
    objective:
        size: min. # of added swaps
        depth: min. depth
        no_swap: try best to find an initial mapping requiring no swaps; raise 
        an error if fail
    seed : integer, optional
        Set random seed for the stochastic part of the tranpiler 
        The default is None.
    use_post_opt: we provide a genetic alg. which utilizes exchange rules for
        swaps to futher min. depth.

    Returns
    -------
    qasm_transpiled : string
        qasm string after transpilation
    layout : dict
        mapping from virtual to physical qubit
        e.g.:
            {0:1, 1:2, 2:3, 3:4, 4:0}
    swap_mapping : dict
        mapping from initial physical qubit to final physical qubit after a series of swaps
        e.g.:
            {0:1, 1:2, 2:3, 3:4, 4:0}
    mapping_virtual_to_final:
        mapping from virtual to final physical qubit
            
    raised:
        TranspileError:
           if graph specified by coupling map is disconnected

    """
    
    qpu_config_dice = import_qpu_file(qpu_file, disable_qubits=disable_qubits)
    coupling_map = qpu_config_dice['adjacency_list']
    
    if seed != None: np.random.seed(seed)
    # check coupling_map
    if isinstance(coupling_map, list):
        qubits = []
        for edge in coupling_map:
            qubits.extend(edge)
            if not isinstance(edge[0], int) or not isinstance(edge[1], int):
                raise(Exception('Coupling_map can only contain int'))
        # After some testing, we believe the following constraint is not necessary any more.
        #if not 0 in qubits:
        #    raise(Exception('Indices of physical qubits must start from 0.'))
        # generate AG
        ag = nx.Graph()
        ag.add_edges_from(coupling_map)
    elif isinstance(coupling_map, nx.Graph):
        ag = coupling_map
    else:
        raise(Exception(f"Unsupported coupling map type {coupling_map}."))
    if not nx.is_connected(ag):
        raise(Exception("The coupling map is disconnected."))
    # parameters for MCT search process
    selec_times = 50 # recommend:50 for realistic circuits
    select_mode = ['KS', 15]
    use_prune = 1
    use_hash = 1
    # init objective
    score_layer = 5
    # generate dependency graph
    dg = DG()
    measure_ops = dg.from_qasm_string(qasm_str)
    num_q_vir = dg.num_q
    ag.shortest_length = dict(nx.shortest_path_length(ag, source=None,
                                                           target=None,
                                                           weight=None,
                                                           method='dijkstra'))
    ag.shortest_length_weight = ag.shortest_length
    ag.shortest_path = nx.shortest_path(ag, source=None, target=None, 
                                             weight=None, method='dijkstra')
    '''
    if disable_qubits == []:
        if dg.num_q == 5:
            initial_layout = {
                0: 11,
                1: 10,
                2: 12,
                3: 3,
                4: 2
            }
        if dg.num_q == 4:
            initial_layout = {
                0: 11,
                1: 10,
                2: 12,
                3: 3
            }
        if dg.num_q == 2:
            initial_layout = {
                0: 11,
                1: 10
            }
    '''
    
    # initial mapping
    if initial_layout != None:
        if objective == 'no_swap':
            raise(Exception("initial_layout should not be set when the objective is no_swap."))
        init_map = layout_dict_to_list(initial_layout)
        # extend init_map and initial_layout to all physical qubits
        for i in ag:
            if len(ag) == len(init_map): break
            if not i in init_map:
                init_map.append(i)
                initial_layout[len(init_map)-1] = i
        # check if all physical qubits exist in ag
        for _, q in initial_layout.items():
            if not q in ag.nodes:
                print(f"Physical qubit {q} in the given initial mapping does not exist in QPU. Therefore we will ignore this mapping.")
                initial_layout = None
                break
    if initial_layout == None:
        init_map = get_init_map(dg, ag, method_init_mapping)
        initial_layout = layout_list_to_dict(init_map)
    # init search tree
    search_tree = MCTree(ag, dg,
                         objective=objective,
                         select_mode=select_mode,
                         score_layer=score_layer,
                         use_prune=use_prune,
                         use_hash=use_hash,
                         init_mapping=init_map,)
    # MCT search process
    while search_tree.nodes[search_tree.root_node]['num_remain_gates'] > 0:
        #for _ in range(selec_times):
        while search_tree.selec_count < selec_times:
            # selection
            exp_node, _ = search_tree.selection()
            # EXP
            search_tree.expansion(exp_node)
        # decision
        search_tree.decision()
    dg_qct = search_tree.to_dg()
    dg_qct.num_q = max(list(ag.nodes)) + 1
    #if use_post_opt:
    #    _, _, _, dg_qct, _ = genetic_opt(0, dg_qct, ag)
    #qasm_transpiled = dg_qct.to_qasm_str()
    mapped_ir = dg_qct.to_ir(decompose_swap=True)
    # get swap mapping
    swaps = search_tree.get_swaps()
    print(f"添加swap门: {len(swaps)}")
    swap_mapping = list(range(max(list(ag.nodes)) + 1))
    for swap in swaps:
        t0, t1 = swap_mapping[swap[0]], swap_mapping[swap[1]]
        swap_mapping[swap[0]], swap_mapping[swap[1]] = t1, t0
    swap_mapping = layout_dict_reverse(layout_list_to_dict(swap_mapping))
    mapping_virtual_to_final = {i:swap_mapping[initial_layout[i]] for i in range(len(ag))}
    # delete redundant qubits
    for q in list(initial_layout.keys()):
        if q >= num_q_vir: 
            initial_layout.pop(q)
            mapping_virtual_to_final.pop(q)
    for gate in measure_ops:
        gate.targets = [mapping_virtual_to_final[q] for q in gate.targets]
        mapped_ir.append(gate)
    return mapped_ir, initial_layout, swap_mapping, mapping_virtual_to_final


