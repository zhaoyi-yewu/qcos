# -*- coding: utf-8 -*-
"""
Created on Fri Jul 23 16:04:46 2021

@author: zhoux
"""

legal_methods = {'naive', 'simulated_annealing', 'subgraph_isomorphism',
                 'Topgraph'}

def get_init_map(DG, AG, map_method='naive'):
    '''
    获取初始映射，提供4种方法：
        naive：顺序映射，直接将逻辑比特按顺序映射到物理比特上
        simulated_annealing
            启发式映射，基于模拟退火实现量子比特启发式分配，可参考《Quantum Circuit Transformation Based on Simulated Annealing and Heuristic Search》
        subgraph_isomorphism
            基于同构子图，实现量子比特精确分配（该方法不一定能得到解）
        Topgraph
            结合上面两种方法，对于线路拓扑图的前边部分（top graph）采用同构子图，可参考《Qubit Mapping Based on Subgraph Isomorphism and Filtered Depth-Limited Search》，实现时直接调用了该论文提供的开源库FiDLS
    Return
        map_list: represents a mapping in which indices and values stand for 
                  logical and physical qubits.
    '''
    if not map_method in legal_methods:
        raise(Exception("Unsupported method {} for initial mapping".format(map_method)))
    if map_method == 'naive':
        return list(range(len(AG)))
    if map_method == 'simulated_annealing':
        from .sa_mapping import InitialMapSimulatedAnnealingWeighted
        return InitialMapSimulatedAnnealingWeighted(DG, AG)
    if map_method == 'subgraph_isomorphism':
        from .subgraph_isomorphism_mapping import subgraph_isomorphism_mapping
        return subgraph_isomorphism_mapping(DG, AG)
    if map_method == 'Topgraph':
        from .FiDLS.inimap import _tau_bstg_
        cx_list = [] # 2-qubit gate list
        qubits_log = []
        for node in DG.nodes:
            qubits = DG.get_node_qubits(node)
            for q in qubits:
                if not q in qubits_log: qubits_log.append(q)
            if len(qubits) > 2: raise(Exception("We do not support gates with more than 3 qubits."))
            if len(qubits) == 1: continue
            cx_list.append(qubits)
        log_to_phy_dict = _tau_bstg_(cx_list, AG, anchor=False, stop=600)
        log_to_phy = list(AG.nodes)
        for q_log in log_to_phy_dict:
            q_phy = log_to_phy_dict[q_log]
            q_phy2 = log_to_phy[q_log]
            q_log2 = log_to_phy.index(q_phy)
            log_to_phy[q_log] = q_phy
            log_to_phy[q_log2] = q_phy2
        flag = False
        for cx in cx_list:
            if not (log_to_phy[cx[0]], log_to_phy[cx[1]]) in AG.edges:
                flag = True
                break
        if flag:
            #print('We use SA to futher optimise the initial mapping.')
            from .sa_mapping import InitialMapSimulatedAnnealingWeighted
            return InitialMapSimulatedAnnealingWeighted(DG, AG, start_map=log_to_phy)
        return log_to_phy