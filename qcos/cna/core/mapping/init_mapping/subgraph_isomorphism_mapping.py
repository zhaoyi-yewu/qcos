# -*- coding: utf-8 -*-
"""
Created on Thu Sep  1 02:01:56 2022

@author: zhoux
"""
from networkx import DiGraph, Graph
from networkx.algorithms import isomorphism

def subgraph_isomorphism_mapping(dg, ag):
    """基于同构子图的量子比特精确分配

    Args:
        dg: 量子线路拓扑
        ag: 硬件拓扑
    """
    # 从量子线路拓扑中构建量子比特的拓扑图（比特间做两比特门，则连一条线）
    # subgraph = DiGraph()
    subgraph = Graph()
    for node in dg.nodes:
        qubits = dg.get_node_qubits(node)
        if len(qubits) > 2: raise()
        if len(qubits) == 1: continue
        for q in qubits:
            if not q in subgraph:
                subgraph.add_node(q)
        subgraph.add_edge(qubits[0], qubits[1])
    # 同构子图查找
    GM = isomorphism.GraphMatcher(ag, subgraph)
    phy_to_log = None
    log_to_phy = None
    # 若找到同构子图则返回对应映射关系，否则返回None
    if GM.subgraph_is_isomorphic():
        log_to_phy = list(range(len(ag)))
        phy_to_log = GM.mapping
        for q_phy in phy_to_log:
            q_log = phy_to_log[q_phy]
            q_phy2 = log_to_phy[q_log]
            q_log2 = log_to_phy.index(q_phy)
            log_to_phy[q_log] = q_phy
            log_to_phy[q_log2] = q_phy2
    return log_to_phy
    
    
if __name__ == '__main__':
    import networkx as nx
    G1 = nx.DiGraph()
    G2 = nx.DiGraph()
    nx.add_path(G1, [1, 2, 3, 4])
    nx.add_path(G2, [10, 20, 30, ])
    GM = isomorphism.GraphMatcher(G1, G2)
    print(GM.subgraph_is_isomorphic())
    print(GM.mapping)