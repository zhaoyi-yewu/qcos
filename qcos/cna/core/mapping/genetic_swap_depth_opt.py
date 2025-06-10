# -*- coding: utf-8 -*-
"""
Created on Tue Jul  5 13:34:26 2022

@author: zhoux

The genetic algorithm for optimizing the depth of a quantum circuit output by
a SWAP-based QCT algorithm. It usilizes the commutation rules between a SWAP and 
single- or CX gates.
"""
from copy import deepcopy
import numpy as np
from .cir_dg_swap_depth_opt import DGSwap, hybridization, hybridization2, hybridization3, hybridization4
import networkx as nx
import time

# parameters
num_species_default = 20 #10 or 20
init_mutation_time_default = 10 #10
mutation_rate_default = 0.85 #0.85
max_iter_default = 400 #200, 300
max_idle_times_default = 40 #50
flag_print = 0

class SolutionsPool():
    def __init__(self, dg_ori):
        self.pool = []
        self.dg_ori = dg_ori
        self.cost_ori = self.dg_ori.cost
        self.solution_best = (np.inf, None)
        self.log_cost_min, self.log_cost_ave, self.log_cost_max = None, None, None
        
    @property
    def best_dg(self):
        return self.solution_best[1]
    
    @property
    def best_cost(self):
        return self.solution_best[0]
        
    def get_ave_max_cost(self):
        cost_total = 0
        cost_max = -1*np.inf
        for cost, _ in self.pool:
            cost_total += cost
            if cost > cost_max: cost_max = cost
        return cost_total / len(self.pool) , cost_max
    
    def add_solution(self, dg, cost=None):
        if cost == None: cost = dg.cost
        self.pool.append((cost, dg))
# =============================================================================
#         if cost == self.solution_best[0]:
#             if dg.depth_ave > self.solution_best[1].depth_ave:
#                 self.solution_best = (cost, deepcopy(dg))
# =============================================================================
        if cost < self.solution_best[0]:
            self.solution_best = (cost, deepcopy(dg))
    
    def init_log(self):
        self.log_cost_min, self.log_cost_ave, self.log_cost_max = [], [], []
        cost_ave, cost_max = self.get_ave_max_cost()
        self.log_cost_min.append(self.solution_best[0])
        self.log_cost_ave.append(cost_ave)
        self.log_cost_max.append(cost_max)
        
    def update_log(self):
        if self.log_cost_min == None: raise()
        self.log_cost_min.append(self.solution_best[0])
        cost_ave, cost_max = self.get_ave_max_cost()
        self.log_cost_ave.append(cost_ave)
        self.log_cost_max.append(cost_max)
        if flag_print:
            print("{}: {} {} {}, ".format(str(len(self.log_cost_min)), 
                                          str(self.log_cost_min[-1]),
                                          str(self.log_cost_ave[-1]),
                                          str(self.log_cost_max[-1])),
                  end="")
        
    def worst_solution_index(self):
        if len(self.pool) < 1: raise()
        cost_worst, index_worst = 0, None
        for i, solution in enumerate(self.pool):
            if solution[0] > cost_worst:
                cost_worst, index_worst = solution[0], i
        return index_worst
    
    def pick_solution_random(self, flag_copy, num=1):
        picked = []
        for _ in range(num):
            index = np.random.randint(len(self.pool))
            if flag_copy:
                picked.append((self.pool[index][0],
                               deepcopy(self.pool[index][1])))
            else:
                picked.append(self.pool[index])
        return picked
        
    def delete_worst_solution(self):
        if len(self.pool) <= 1: raise()
        return self.pool.pop(self.worst_solution_index())
    
    def weed_out(self, survive_num):
        #if survive_num > len(self.pool): raise()
        while len(self.pool) > survive_num:
            self.delete_worst_solution()
            
    def weed_out2(self, survive_num, prob):
        '''Keep good solutions and bad solutions with a specific probability'''
        solutions_delete = []
        while len(self.pool) > survive_num:
            solutions_delete.append(self.delete_worst_solution())
        for cost, dg in solutions_delete:
            if np.random.rand() < prob:
                self.add_solution(dg, cost)
        
            
    def draw_best_solution(self):
        dg = self.solution_best[1]
        dg_copy = deepcopy(dg)
        dg_copy.remove_node(dg_copy.root)
        dg_copy.qiskit_circuit(save_to_file=1)
        
    def draw_log(self, title="Costs vs. Iterations", save_name=None):
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()  # a figure with a single Axes
        ax.plot([self.cost_ori]*len(self.log_cost_min), 
                label='cost_ori.', linestyle='--')
        ax.plot(self.log_cost_min, label='min')  # Plot some data on the axes.
        ax.plot(self.log_cost_ave, label='ave')  # Plot more data on the axes...
        ax.plot(self.log_cost_max, label='max')  # ... and some more.
        ax.set_xlabel('iteration')  # Add an x-label to the axes.
        ax.set_ylabel('cost')  # Add a y-label to the axes.
        ax.set_title(title)  # Add a title to the axes.
        ax.legend()  # Add a legend.
        
        if save_name[-5:] == '.qasm': save_name = save_name[:-5]
        save_name_new = ""
        for i in save_name: 
            if i == '.': continue
            if i == '/': 
                save_name_new += '_'
                continue
            save_name_new += i
        if save_name != None:
            plt.savefig(save_name_new)
        return fig, ax
    
def genetic_opt(index, qasm, ag, 
                draw=False, test_mode=False):
    '''
    Genetic algorithm for opt. the circuit depth using SWAP based communation 
    rules.
    '''
    if test_mode:
        # set parameters for testing
        num_species = 10 #10 or 20
        init_mutation_time = 10 #10
        mutation_rate = 0.85 #0.85
        max_iter = 20 #200, 300
        max_idle_times = 20 #50
    else:
        num_species = num_species_default 
        init_mutation_time = init_mutation_time_default 
        mutation_rate = mutation_rate_default 
        max_iter = max_iter_default 
        max_idle_times = max_idle_times_default 
    if isinstance(qasm, str):
        dg_ori = DGSwap(ag)
        dg_ori.from_qasm(qasm)
        dg_ori.num_q = len(ag)
    else:
        dg_ori = qasm
    dg_baseline = deepcopy(dg_ori)
    #nx.draw(dg_ori, with_labels=1)
    evolution_count = 0
    
    # check depth
    from qiskit.converters import circuit_to_dag, dag_to_circuit
    from qiskit.transpiler.passes import Decompose
    from qiskit.circuit.library.standard_gates.swap import SwapGate
    #dg_ori_copy = deepcopy(dg_ori)
    #dg_ori_copy.remove_node(dg_ori_copy.root)
    cir_qiskit = dg_ori.qiskit_circuit()
    dag_qiskit = circuit_to_dag(cir_qiskit)
    de_pass = Decompose(gate=SwapGate)
    dag_qiskit = de_pass.run(dag_qiskit)
    cir_qiskit = dag_to_circuit(dag_qiskit)
    
    # init species
    t_start = time.time()
    solutions_pool = SolutionsPool(dg_ori)
    for _ in range(num_species * 3):
        dg_new = deepcopy(dg_ori)
        evolution_count += dg_new.random_mutation(init_mutation_time)
        solutions_pool.add_solution(dg_new)
    solutions_pool.weed_out(num_species)
    solutions_pool.init_log()
    best_cost = solutions_pool.best_cost
    # # of times for continuous iterations that can't find any better solution
    count = 0 
    # iteration
    for _ in range(max_iter):
        # generate new solutions
        count += 1
        for species_i in range(num_species):
            if species_i <= mutation_rate * num_species:
                # mutation
                solutions = solutions_pool.pick_solution_random(flag_copy=True,
                                                                num=1)
                cost, dg_new = solutions[0]
                evolution_count += dg_new.random_mutation2()
            else:
                # hybridization
                solutions = solutions_pool.pick_solution_random(flag_copy=False,
                                                                num=2)
                dg1, dg2 = solutions[0][1], solutions[1][1]
                if np.random.rand() < 0.5:
                    dg_new = hybridization4(dg1, dg2, dg_ori)
                else:
                    dg_new = hybridization4(dg1, dg2, dg_ori)
                evolution_count += 1
            solutions_pool.add_solution(dg_new)
        # select best soultions
        solutions_pool.update_log()
        solutions_pool.weed_out(num_species)
        #solutions_pool.weed_out2(num_species, prob=1-np.exp(-0.01*count))
        current_cost = solutions_pool.best_cost
        if current_cost < best_cost:
            best_cost, count = current_cost, 0
        if count > max_idle_times: break
    
    #eq = equivalence_checking(dg_ori, solutions_pool.solution_best[1], ag)
    #if not eq: raise()
    
    # draw log
    if draw:
        fig, ax = solutions_pool.draw_log(title=str(qasm), save_name=str(qasm))
    # compare with a stochastic baseline algorithm
# =============================================================================
#     dg_comp = deepcopy(dg_ori)
#     dg_comp.random_mutation3(evolution_count)
#     print('Cost for stochastic baseline is', dg_comp.cost)
# =============================================================================
    if test_mode:
        score = solutions_pool.best_dg.get_score()
        return index, None, None, score, time.time()-t_start
    return index, solutions_pool.best_dg.cost, dg_ori.cost, solutions_pool.best_dg, time.time()-t_start

