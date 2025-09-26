from qcos.cna import *

class TestMapping():
    
    task1_data = '''OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[5];
    creg c[5];
    x q[0];
    cx q[0], q[1];
    cx q[0], q[2];
    cx q[0], q[3];
    cx q[0], q[4];
    measure q->c;
    '''
    
    task2_data = '''OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[4];
    creg c[4];
    x q[0];
    cx q[0], q[1];
    cx q[0], q[2];
    cx q[0], q[3];
    measure q->c;
    '''

    task3_data = '''OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg c[2];
    x q[0];
    cx q[0], q[1];
    measure q->c;
    '''
    
    task4_data = '''OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[3];
    creg c[3];
    h q[0];
    cx q[1], q[0];
    h q[0];
    cx q[1], q[2];
    h q[1];
    h q[2];
    cx q[2], q[0];
    cx q[0], q[2];
    measure q->c;
    '''

    task5_data = '''OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[4];
    creg c[4];
    x q[0];
    x q[1];
    x q[2];
    x q[3];
    measure q->c;
    '''

    # 硬件参数解析和拓扑构建
    coupling_map = import_qpu_file("test/topo.json")['adjacency_list']
    ag = nx.Graph()
    ag.add_edges_from(coupling_map)
    
    ag.shortest_length = dict(nx.shortest_path_length(ag, source=None,
                                                            target=None,
                                                            weight=None,
                                                            method='dijkstra'))
    ag.shortest_length_weight = ag.shortest_length
    ag.shortest_path = nx.shortest_path(ag, source=None, target=None, 
                                                    weight=None, method='dijkstra')
    
    def test_merge(self):
        now_tasks = [Task(1, 1, 1, 3, self.task1_data, qubits=5), Task(2, 1, 1, 3, self.task2_data, qubits=4), Task(3, 1, 1, 3, self.task3_data, qubits=2)]
        tasks = find_tasks(now_tasks[0], now_tasks, 'test/na_file.json')
        assert len(tasks) == 1
        tasks = find_tasks(now_tasks[1], now_tasks, 'test/na_file.json')
        assert len(tasks) == 2
    
    def test_partition(self):
        tasks = [Task(2, 1, 1, 3, self.task2_data, qubits=4), Task(3, 1, 1, 3, self.task3_data, qubits=2)]
        _, blocks, _ = partition('test/na_file.json', tasks)
        assert len(blocks) == 2
        assert len(blocks[0]) == 4
        assert len(blocks[1]) == 2
    
    def test_params_deal(self):
        assert len(self.ag.nodes) == 14
        assert len(self.ag.edges) == 18
        
    def test_simulated_map(self):    
        # 量子任务拓扑构建
        dg = DG()
        measure_ops = dg.from_qasm_string(self.task1_data)
        # 启发式分配
        res = InitialMapSimulatedAnnealingWeighted(dg, self.ag)
        layout_dict = {}
        for i, v in enumerate(res):
            if i < 5:
                layout_dict[i] = v
                
        assert (layout_dict[0], layout_dict[1]) in self.ag.edges
        assert (layout_dict[0], layout_dict[2]) in self.ag.edges
        assert (layout_dict[0], layout_dict[3]) in self.ag.edges
        assert (layout_dict[0], layout_dict[4]) not in self.ag.edges
        
    def test_exact_map(self):
        dg = DG()
        measure_ops = dg.from_qasm_string(self.task2_data)
        # 精确分配
        res = subgraph_isomorphism_mapping(dg, self.ag)
        layout_dict = {}
        for i, v in enumerate(res):
            if i < 4:
                layout_dict[i] = v
        assert (layout_dict[0], layout_dict[1]) in self.ag.edges
        assert (layout_dict[0], layout_dict[2]) in self.ag.edges
        assert (layout_dict[0], layout_dict[3]) in self.ag.edges
        
    def test_na_based(self):
        est = NAEstimate()
        qpu_config = get_qpu_config("test/na_file.json")
        na = NARoute(qpu_config, self.task4_data)
        res_tmp = na.execute_with_order()
        assert len(res_tmp) == 18
        est.circuit = res_tmp
        assert est.estimate_fidelity() > 0.6
        assert est.estimate_time() == 10032
        res_tmp = na.execute_with_opt()
        assert len(res_tmp) == 15
        est.circuit = res_tmp
        assert est.estimate_fidelity() > 0.7
        assert est.estimate_time() == 8026

    def test_na_single(self):
        qpu_config = get_qpu_config("test/na_file.json")
        na = NASingleRoute(qpu_config, self.task5_data)
        res_tmp = na.execute_with_order()
        assert len(res_tmp) == 8

    def test_swap_based(self):
        mapped_ir, _, _, _ = mapping(self.task2_data, qpu_file='test/topo.json')
        assert len(mapped_ir) == 8
        est = SCEstimate()
        est.circuit = mapped_ir
        assert est.estimate_fidelity() > 0.9
        assert est.estimate_time() == 160

    def test_mov1(self):
        na = NARoute('test/na_file.json', self.task1_data)
        na.get_init_mapping()
        na.put(0, 'P69')
        na.put(1, 'P90')
        assert na.mov_to_neighbors('P69', 'P90')

    def test_mov2(self):
        na = NARoute('test/na_file.json', self.task1_data)
        na.get_init_mapping()
        na.put(0, 'P69')
        na.put(1, 'P70')
        na.put(2, 'P89')
        na.put(3, 'P90')
        assert na.mov_to_neighbors('P69', 'P90')

    def test_mov3(self):
        na = NARoute('test/na_file.json', self.task1_data)
        na.get_init_mapping()
        na.put(0, 'P69')
        na.put(1, 'P70')
        na.put(2, 'P89')
        na.put(3, 'P90')
        na.put(4, 'P110')
        assert na.mov_to_neighbors('P69', 'P90')

    def test_mov4(self):
        na = NARoute('test/na_file.json', self.task1_data)
        na.get_init_mapping()
        na.put(0, 'P69')
        na.put(1, 'P70')
        na.put(2, 'P89')
        na.put(3, 'P90')
        na.put(4, 'P110')
        na.locked.add('P70')
        na.locked.add('P89')
        assert na.mov_to_neighbors('P69', 'P90')

    def test_init_layout(self):
        initial_layout = {}
        for i in range(4): initial_layout[i] = i
        mapped_ir, _, _, _ = mapping(self.task2_data, qpu_file='test/topo.json', initial_layout=initial_layout)
        assert len(mapped_ir) == 14
