# -*- coding: utf-8 -*-
"""
Created on Fri Aug 26 22:09:40 2022

@author: zhoux
"""

# =============================================================================
# edges = []
# flag_odd = True
# for i in range(11):
#     flag_odd = not flag_odd
#     if i == 0: continue
#     for j in range(6):
#         index = 6 * i + j
#         edges.append((index-6, index))
#         if j == 0 and flag_odd:
#             continue
#         if j == 5 and not flag_odd:
#             continue
#         if flag_odd:
#             edges.append((index-7, index))
#             continue
#         if not flag_odd:
#             edges.append((index-5, index))
#             continue
# =============================================================================

import networkx as nx
edges = [(0, 6), (1, 7), (0, 7), (2, 8), (1, 8), (3, 9), (2, 9), (4, 10), 
         (3, 10), (5, 11), (4, 11), (6, 12), (7, 12), (7, 13), (8, 13), 
         (8, 14), (9, 14), (9, 15), (10, 15), (10, 16), (11, 16), (11, 17), 
         (12, 18), (13, 19), (12, 19), (14, 20), (13, 20), (15, 21), (14, 21), 
         (16, 22), (15, 22), (17, 23), (16, 23), (18, 24), (19, 24), (19, 25), 
         (20, 25), (20, 26), (21, 26), (21, 27), (22, 27), (22, 28), (23, 28), 
         (23, 29), (24, 30), (25, 31), (24, 31), (26, 32), (25, 32), (27, 33), 
         (26, 33), (28, 34), (27, 34), (29, 35), (28, 35), (30, 36), (31, 36), 
         (31, 37), (32, 37), (32, 38), (33, 38), (33, 39), (34, 39), (34, 40), 
         (35, 40), (35, 41), (36, 42), (37, 43), (36, 43), (38, 44), (37, 44), 
         (39, 45), (38, 45), (40, 46), (39, 46), (41, 47), (40, 47), (42, 48), 
         (43, 48), (43, 49), (44, 49), (44, 50), (45, 50), (45, 51), (46, 51), 
         (46, 52), (47, 52), (47, 53), (48, 54), (49, 55), (48, 55), (50, 56), 
         (49, 56), (51, 57), (50, 57), (52, 58), (51, 58), (53, 59), (52, 59), 
         (54, 60), (55, 60), (55, 61), (56, 61), (56, 62), (57, 62), (57, 63), 
         (58, 63), (58, 64), (59, 64), (59, 65)]

def get_ag(disable_qubits=[]):
    ag = nx.Graph()
    qubits = list(range(66))
    for q in qubits:
        if not q in disable_qubits:
            ag.add_node(q)
    for edge in edges:
        flag = True
        for q in disable_qubits:
            if q in edge:
                flag = False
                break
        if flag: ag.add_edge(edge[0], edge[1])
    return ag

def get_ag_3X3():
    ag = nx.Graph()
    qubits = list(range(9))
    ag.add_nodes_from(qubits)
    edge = []
    length = 3
    width = 3
    for raw in range(width-1):
        for col in range(length-1):
            current_v = col + raw*length
            edge.append((current_v, current_v + 1))
            edge.append((current_v, current_v + length))
    for raw in range(width-1):
        current_v = (length - 1) + raw*length
        edge.append((current_v, current_v + length))
    for col in range(length-1):
        current_v = col + (width - 1)*length
        edge.append((current_v, current_v + 1))
    ag.add_edges_from(edge)
    return ag
    