# -*- coding: utf-8 -*-
"""
Created on Wed Oct 13 22:22:04 2021

This module is last modified on 1/11/2021

@author: zhoux
"""
import networkx as nx
from networkx.algorithms import approximation as approx
from networkx import DiGraph
from qcos.transpiler.cmss.compiler import Gate, get_abs_tree, get_ir, create_gate
'''
gate is a tuple (gate_name, (qubits), (parameters))
supported gate_name:
    cx
    u3
    ...
'''

class DG(DiGraph):
    """量子任务拓扑分析并构建拓扑图
    """
    def __init__(self, ):
        super().__init__()
        self.qubit_to_node = [None] * 500
        self.num_gate_2q = 0
        self.num_gate_1q = 0
        self.node_count = 0
        self.num_q = None
    
    @property
    def num_gate(self):
        return self.num_gate_1q + self.num_gate_2q
        
    def get_shared_qubits(self, node1, node2):
        '''Get qubits which exist in both node1 and node2'''
        qubits = []
        for q in self.get_node_qubits(node1):
            if q in self.get_node_qubits(node2):
                qubits.append(q)
        return qubits
        
    def add_line(self, node_in, node_out, qubits=None, check=True):
        '''Connect two nodes using provided qubits'''
        qubits_share = self.get_shared_qubits(node_in, node_out)
        qubits_used = []
        for edge_c in self.out_edges(node_in):
            qubits_used.extend(self.get_edge_qubits(edge_c))
        for edge_c in self.in_edges(node_out):
            qubits_used.extend(self.get_edge_qubits(edge_c))
        qubits_share_new = []
        for q in qubits_share:
            if not q in qubits_used: qubits_share_new.append(q)
        qubits_share = qubits_share_new
        
        if qubits == None: qubits = qubits_share
        if check:
            for q in qubits:
                if not q in qubits_share:
                    print(self.nodes[node_in])
                    print(self.nodes[node_out])
                    print(qubits)
                    print(qubits_share)
                    raise()
        edge_add = (node_in, node_out)
        if edge_add in self.edges:
            for q in qubits:
                if not q in self.edges[edge_add]['qubits']:
                    self.edges[edge_add]['qubits'].append(q)
        else:
            self.add_edge(node_in, node_out, qubits=qubits)
    
    def add_gate(self, gate, add_edges=True):
        '''
        Attributes of a node:
            gates
            num_gate_1q
            num_gate_2q
            qubits
        '''
        # add node
        node_new = self.node_count
        self.node_count += 1
        self.add_node(node_new)
        self.nodes[node_new]['gates'] = [gate]
        self.nodes[node_new]['qubits'] = list(gate[1])
        self.nodes[node_new]['num_gate_1q'], self.nodes[node_new]['num_gate_2q'] = 0, 0
        if len(gate[1]) == 1:
            self.nodes[node_new]['num_gate_1q'] += 1
            self.num_gate_1q += 1
        if len(gate[1]) == 2:
            self.nodes[node_new]['num_gate_2q'] += 1
            self.num_gate_2q += 1
        if len(gate[1]) > 2: raise()
        if add_edges:
        # add edges
            for q in gate[1]:
                node_parent = self.qubit_to_node[q]
                if node_parent != None:
                    self.add_line(node_parent, node_new, [q])
                self.qubit_to_node[q] = node_new
        return node_new
            
    def get_node_num_q(self, node):
        return len(self.nodes[node]['qubits'])
    
    def get_node_num_2q_gates(self, node):
        return self.nodes[node]['num_gate_2q']
    
    def get_node_num_1q_gates(self, node):
        return self.nodes[node]['num_gate_1q']
    
    def get_node_gates(self, node):
        return self.nodes[node]['gates']
    
    def get_node_qubits(self, node):
        return self.nodes[node]['qubits']
    
    def get_node_depth(self, node):
        '''One SWAP takes 3 depth.'''
        qubit_depth = [0] * (max(self.get_node_qubits(node)) + 1)
        for name, qubits, _ in self.get_node_gates(node):
            current_ds = []
            for q in qubits:
                current_ds.append(qubit_depth[q])
            current_d = max(current_ds)
            if name == 'SWAP' or name == 'swap':
                current_d += 3
            else:
                current_d += 1
            for q in qubits:
                qubit_depth[q] = current_d
        return max(qubit_depth)
    
    def get_edge_qubits(self, edge):
        return self.edges[edge]['qubits']
    
    def set_edge_qubits(self, edge, qubits):
        self.edges[edge]['qubits'] = list(qubits)
    
    def add_gate_absorb(self, gate):
        '''Add a gate and absorb is if possible'''
        nodes_check = []
        for q in gate[1]:
            node_father = self.qubit_to_node[q]
            if not node_father in nodes_check and node_father != None:
                nodes_check.append(node_father)
        # add node
        new_node = self.add_gate(gate)
        # absorb
        for node_parent in nodes_check:
            if not self.check_absorbable(node_parent, new_node): continue
            new_node = self.cascade_node(new_node, node_parent)
        #self.check()
        return new_node
    
    def cascade_node(self, node1, node2):
        '''
        Combine two given nodes.
        Here we only update one node (node_in) and delete the other (node_out)
        instead of creating one node and deleting both.
        '''
        if not self.check_direct_dependency(node1, node2):
            if not self.check_parallel(node1, node2):
                raise()
        if (node1, node2) in self.edges:
            node_in, node_out = node1, node2
        else:
            if (node2, node1) in self.edges:
                node_in, node_out = node2, node1
            else:
                # we accept two nodes are parallel
                node_in, node_out = node1, node2
        # update attributes
        self.nodes[node_in]['gates'].extend(self.nodes[node_out]['gates'])
        for gate in self.nodes[node_out]['gates']:
            if len(gate[1]) == 1:
                self.nodes[node_in]['num_gate_1q'] += 1
            if len(gate[1]) == 2:
                self.nodes[node_in]['num_gate_2q'] += 1
            for q in gate[1]:
                if not q in self.nodes[node_in]['qubits']:
                    self.nodes[node_in]['qubits'].append(q)
        # delete node and add egdes
        for node in list(self.successors(node_out)):
            self.add_line(node_in, node, 
                          self.get_edge_qubits((node_out, node)),
                          check=False)
        for node in list(self.predecessors(node_out)):
            if node != node_in:
                self.add_line(node, node_in, 
                              self.get_edge_qubits((node, node_out)),
                              check=False)
        ## update qubit_to_node
        for q in self.get_node_qubits(node_out):
            if self.qubit_to_node[q] == node_out:
                self.qubit_to_node[q] = node_in
        self.remove_node(node_out)
        #self.check()
        return node_in
    
    
    def from_qasm_string(self, qasm_string, absorb=True):
        """从openqasm字符串构建拓扑"""
        abs_tree = get_abs_tree(qasm_string)
        qnum, ir = get_ir(abs_tree)
        self.num_q = qnum
        self.num_q_log = qnum
        return self.from_ir(ir, absorb=absorb)

    def from_ir(self, ir: list[Gate], absorb=True):
        measure_op = []
        for gate in ir:
            # 遍历QuantumCircuit中的门，添加入拓扑图中
            name = gate.name
            if name in ("barrier", "measure"): 
                if name == "measure": 
                    measure_op.append(gate)
                continue
            format_gate = (name, tuple(gate.targets), gate.arg_value)
            if absorb: 
                self.add_gate_absorb(format_gate)
            else:
                self.add_gate(format_gate)
            return measure_op

    def to_ir(self, add_barrier=False, decompose_swap=False):
        '''
        Convert the DG to a qiskit circuit.
        If decompose_swap is set to True, we will decompose each SWAP into 3 CNOTs.
        '''
        from .front_circuit import FrontCircuit
        # init circuits
        ag = nx.complete_graph(self.num_q)
        circuit = FrontCircuit(self, ag)
        ir = []
        # add qiskit gates one by one
        while circuit.num_remain_nodes > 0:
            front_nodes = circuit.front_layer
            if len(front_nodes) == 0:
                raise()
            for node in front_nodes:
                gates = self.get_node_gates(node)
                for gate in gates:
                    if decompose_swap and gate[0] == 'swap':
                        q0, q1 = gate[1]
                        ir.append(create_gate('cx', targets=[q0, q1], arg_value=gate[2]))
                        ir.append(create_gate('cx', targets=[q1, q0], arg_value=gate[2]))
                        ir.append(create_gate('cx', targets=[q0, q1], arg_value=gate[2]))
                    else:
                        ir.append(create_gate(gate[0], targets=list(gate[1]), arg_value=gate[2]))
                if add_barrier: ir.append(create_gate('sync', targets=list(range(self.num_q))))
            circuit.execute_front_layer()
        return ir
    
    def opt_node_gates(self, node):
        '''
        Use gate commutation and cancelling rules to reduce the # gates in one
        node.
        '''
        import sys
        sys.path.append("D:\\programs\\")

    def draw(self):
        '''Draw DG graph'''
        nx.draw(self, with_labels=1)
        
    def check_parallel(self, node1, node2):
        if approx.local_node_connectivity(self, node1, node2) == 0 and \
            approx.local_node_connectivity(self, node2, node1) == 0:
            return True
        else:
            return False
        
    def check_direct_dependency(self, node1, node2):
        '''
        We say node2 directly depends on node1 if 
            1) two nodes share at least one qubit;
            2) for each shared qubit, there can't be any nodes existing between 
            the two nodes;
            3) there can't be any path connecting node1 and node2 other than the
                edge in 1)
        If two node are directly dependent, these nodes can be absorbed or
        cascaded. Note that currently we won't accept node1 and node2 are 
        parallel, in that case, we will return False! One can use self.check_parallel
        to check the parallelism between nodes.
        '''
        # check condition 1
        if (node1, node2) in self.edges:
            node_in, node_out = node1, node2
        else:
            if (node2, node1) in self.edges:
                node_in, node_out = node2, node1
            else:
                return False
        # check condition 2
        ## it seems that condition 2 is covered in condition 3, hence I decide
        ## to annotate it.
# =============================================================================
#         qubits_share = []
#         for q in self.get_node_qubits(node_out):
#             if q in self.get_node_qubits(node_in):
#                 qubits_share.append(q)
#         if len(qubits_share) == 0: raise()
#         for q in qubits_share:
#             if not q in self.edges[(node_in, node_out)]["qubits"]:
#                 return False
# =============================================================================
        # check condition 3
        if approx.local_node_connectivity(self, node_in, node_out) > 1:
            return False
        return True
    
    def check_absorbable(self, node1, node2):
        '''
        check if node1 and node2 can be obsorbed to each other
        node1 and node2 are absorbable if all qubits in node1 or node2 exist in
        node2 or node1 and they are directly dependent to each other.
        '''
        if len(self.get_node_qubits(node1)) > len(self.get_node_qubits(node2)):
            node_abs, node_org = node2, node1
        else:
            node_abs, node_org = node1, node2
        for q in self.get_node_qubits(node_abs):
            if not q in self.get_node_qubits(node_org): return False
        if not self.check_direct_dependency(node_org, node_abs):
            return False
        return True
    
    def check(self):
        '''Check whether current DG is legal.'''
        try:
            cycles = nx.find_cycle(self)
            print(cycles)
            raise()
        except:
            pass
        #self.qiskit_circuit(save_to_file=False)

