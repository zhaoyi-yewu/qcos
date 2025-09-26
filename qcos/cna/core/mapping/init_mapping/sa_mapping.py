# -*- coding: utf-8 -*-
"""
Created on Fri Jul 23 15:03:29 2021

@author: zhoux
"""
import numpy as np
from ..front_circuit import FrontCircuit
from networkx import DiGraph
import matplotlib.pyplot as plt

def CalCostMatrixWeighted(cost_m, current_sol, shortest_length_G, qubits_log):
    """估算当前映射下，线路中需要插入swap的成本

    Args:
        cost_m: 成本矩阵
        current_sol: 当前映射 
        shortest_length_G: 最短路径字典 
        qubits_log: 逻辑比特列表（仅包含需要做两比特门的比特）
    """
    cost_total = 0
    for q1_log in qubits_log:
        for q2_log in qubits_log:
            q1_phy, q2_phy = current_sol[q1_log], current_sol[q2_log]
            num_swap = shortest_length_G[q1_phy][q2_phy] - 1
            cost_total += num_swap * cost_m[q1_log][q2_log]
    return cost_total

def InitialCostMatrixWeighted(DG, AG, add_weight=False):
    """初始化成本矩阵

    Args:
        DG: 线路拓扑
        AG: 硬件拓扑
        add_weight (bool, optional): 忽略连续作用在同两个比特上的两比特门. Defaults to False.
    """
    num_q, qubits_log = len(AG), set()
    cost_m = np.zeros((num_q, num_q))
    cir = FrontCircuit(DG, AG)
    num_CX = len(DG.nodes())
    num_CX_current = num_CX
    weight = 1
    while len(cir.front_layer) != 0:
        # 权重随着剩余门数减少而减小，放大前面的两比特的重要性
        weight = num_CX_current / num_CX # linear decayed weight
        current_nodes = cir.front_layer
        num_CX_current -= len(current_nodes)
        for node in current_nodes:
            # 遍历两比特门，增加门作用的两个比特的成本
            op = DG.nodes[node]['qubits']
            if len(op) == 1: continue
            if len(op) > 2: raise()
            if add_weight == True:
                flag = 1
                '''if comment the following, we ignore the successive CX'''
                if DG.out_degree(node) == 1:
                    qubits = op
                    op_next = DG.nodes[list(DG.successors(node))[0]]['qubits']
                    qubits_next = op_next
                    if qubits[0] == qubits_next[0] and qubits[1] == qubits_next[1]:
                        flag = 0
                    if qubits[0] == qubits_next[1] and qubits[1] == qubits_next[0]:
                        flag = 0 
                
                DG.nodes[node]['weight'] = weight * flag
            qubits = op
            qubits_log.add(qubits[0]), qubits_log.add(qubits[1])
            if add_weight == True:
                cost_m[qubits[0]][qubits[1]] += DG.nodes[node]['weight']
            else:
                cost_m[qubits[0]][qubits[1]] += weight
            #cost_m[qubits[1][1]][qubits[0][1]] += weight
        cir.execute_front_layer()
    return cost_m, qubits_log

def initpara():
    '''Initialize parameters for simulated annealing'''
    alpha = 0.95 #0.98
    t = (1,100)#(1,100)
    markovlen = 70 #100
    return alpha,t,markovlen

def InitialMapSimulatedAnnealingWeighted(DG,
                                         AG,
                                         start_map=None,
                                         convergence=False,):
    '''
    基于模拟退火的量子比特启发式分配
    This function is modified from "https://blog.csdn.net/qq_34798326/article/details/79013338"
    
    Return
        solutionbest: represents a mapping in which indices and values stand
                      for logical and physical qubits.
    '''
    # 计算硬件耦合结构中，任意两个比特间的最短路径
    shortest_length_G = AG.shortest_length_weight
    #num_q = len(AG.nodes()) # num of physical qubits
    if convergence == True:
        temp = []
        solution = []
        solution_best = []
    # 初始映射
    if start_map == None: start_map = list(AG.nodes)
    if len(start_map) != len(AG.nodes()):
        '''
        if logical qubits is less than physical, we extend logical qubit to
        ensure the completeness and delete added qubits at the end of the
        algorithm
        '''
        for v in AG.nodes():
            if not v in start_map: start_map.append(v)
    '''gen cost matrix and involved logical qubits'''
    # 初始化加权的成本矩阵
    cost_m, qubits_log = InitialCostMatrixWeighted(DG, AG, True)
    qubits_log = tuple(qubits_log)
    '''Simulated Annealing'''
    solutionnew = start_map
    num = len(start_map)
    #valuenew = np.max(num)
    solutioncurrent = solutionnew.copy()
    valuecurrent = np.inf  #np.max这样的源代码可能同样是因为版本问题被当做函数不能正确使用，应取一个较大值作为初始值
    
    #print(valuecurrent)
    
    solutionbest = solutionnew.copy()
    valuebest = np.inf #np.max
    alpha,t2,markovlen = initpara()
    t = t2[1]#temperature
    result = [] #记录迭代过程中的最优解
    
    while t > t2[0]:
        for i in np.arange(markovlen):
            # 选择两个比特
            q_log1 = np.random.choice(qubits_log)
            q_phy1 = solutionnew[q_log1]
            q_phy2 = np.random.choice(list(AG.neighbors(q_phy1)))
            q_log2 = solutionnew.index(q_phy2)
            # 交换，重新计算成本
            solutionnew[q_log1],solutionnew[q_log2] = solutionnew[q_log2],solutionnew[q_log1] 
            valuenew = CalCostMatrixWeighted(cost_m, solutionnew,
                                             shortest_length_G, qubits_log)
           # print (valuenew)
            if valuenew < valuecurrent: #接受该解
                #更新solutioncurrent 和solutionbest
                valuecurrent = valuenew
                solutioncurrent = solutionnew.copy()
                #renew best solution
                if valuenew < valuebest:
                    valuebest = valuenew
                    solutionbest = solutionnew.copy()
            else:#按一定的概率接受该解
                if np.random.rand() < np.exp(-(valuenew-valuecurrent)/t):
                    valuecurrent = valuenew
                    solutioncurrent = solutionnew.copy()
                else:
                    solutionnew = solutioncurrent.copy()

            if convergence == True:
                temp.append(t)
                solution.append(valuecurrent)
                solution_best.append(valuebest)
        
        t = alpha*t
        #print(valuebest)
        result.append(valuebest)
    '''draw convergence graph'''
    if convergence == True:
        figure_fig = plt.figure()
        plt.grid()
        plt.xlabel('Times of Iteration')
        plt.ylabel('Cost of States')
        plt.plot(solution)
        plt.plot(solution_best)
        figure_fig.savefig('simulated annealing convergence.eps', format='eps', dpi=1000)
        
    return solutionbest