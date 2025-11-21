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

import time
from pathlib import Path

from networkx import Graph
from tabulate import tabulate

from qcos.transpiler.cmss.mapping.initial_mapping.sc_initial_mapping import (
    get_initial_mapping,
)
from qcos.transpiler.cmss.mapping.routing.sabre_routing import SABRE
from qcos.transpiler.cmss.mapping.utils.dg import DG
from qcos.tests.system_tests.job.driver.spinq.spinq_api_server import (
    load_config,
)
from qcos.transpiler.cmss.common.gate_operation import GateOperation
from qcos.transpiler.cmss.mapping.utils.front_circuit import FrontCircuit
from qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit


initial_methods = [
    "naive",
    "simulated_annealing",
    # "subgraph_isomorphism",
    "topgraph",
    "sabre",
]


class TestMappingRouting:
    def __init__(self) -> None:
        # TODO lwc: test different coupling
        self.coupling_graph = self.get_coupling_graph()

    def get_coupling_graph(self):
        """Load coupling graph from config file."""
        _, _, coupling_list, _ = load_config(
            path="./etc/qcos/conf.d/spinq_rpc.toml"
        )
        if coupling_list is None:
            raise ValueError("Coupling list is None")
        # duplicate edges
        coupling_list = coupling_list[::2]

        coupling_graph = Graph()
        coupling_graph.add_edges_from(coupling_list)
        return coupling_graph

    def get_qasm_test_cases(self, path: str):
        """Read qasm test cases from a folder."""
        try:
            folder_path = Path(path)
        except FileNotFoundError as e:
            raise e
        files = folder_path.glob("*.qasm")
        return files

    def counts_swaps(self, ir: list[GateOperation]):
        """Count the number of swap gates in the ir."""
        num = 0
        for gate in ir:
            if gate.name == "swap":
                num += 1
        return num

    def check_routing(
        self,
        ir: list,
        phy_gates: list[GateOperation],
        mapping: list[int],
    ):
        """
        Simulate the routing process to verify if the result is feasible.

        Args:
            ir (list[GateOperation]): gates list of logic gates.
            phy_gates (list[GateOperation]): gates list of physical gates.
            mapping (list[int]): dynamic mapping list, will be updated by swap.

        Returns:
            bool: True if the result is feasible, False otherwise.
        """
        coupling_graph = self.coupling_graph

        j = 0
        dg = DG()
        circ = QuantumCircuit()
        circ.append_operations(ir)
        dg.from_ir(circ, absorb=False)
        front_circ = FrontCircuit(dg, coupling_graph)
        front_layer = front_circ.front_layer

        while len(front_layer) > 0 and j < len(phy_gates):
            # find all front layer cx gates
            while True:
                flag = 0
                for node in front_layer:
                    targets = dg.nodes[node]["qubits"]
                    if len(targets) == 1:
                        front_circ.execute_gate(node)
                        flag = 1
                # front layer remain only 2-qubit gates
                if flag == 0:
                    break

            # find the next 2-qubit gate in phy_gates
            while j < len(phy_gates) and len(phy_gates[j].targets) == 1:
                j += 1
            if j == len(phy_gates):
                break

            # update the mapping list
            while phy_gates[j].name == "swap":
                u, v = phy_gates[j].targets
                if u in mapping and v in mapping:
                    u_idx, v_idx = mapping.index(u), mapping.index(v)
                    mapping[u_idx], mapping[v_idx] = (
                        mapping[v_idx],
                        mapping[u_idx],
                    )
                elif u in mapping:
                    u_idx = mapping.index(u)
                    mapping[u_idx] = v
                elif v in mapping:
                    v_idx = mapping.index(v)
                    mapping[v_idx] = u
                else:
                    raise ValueError("swap error")
                j += 1

            # the qubits of the physical gate (actual result of the mapping)
            u_phy2, v_phy2 = phy_gates[j].targets
            # check having edge between the logic cx gate
            flag = 0
            for gate_node in list(front_layer):
                # the logic qubits of current cx gate
                u_logic, v_logic = dg.nodes[gate_node]["qubits"]
                # the physical qubits under current mapping
                u_phy, v_phy = mapping[u_logic], mapping[v_logic]
                if u_phy == u_phy2 and v_phy == v_phy2:
                    assert coupling_graph.has_edge(u_phy, v_phy)
                    front_circ.execute_gate(gate_node)
                    flag = 1
                    j += 1
                    break
            # no gate in front layer can be executed
            if flag == 0:
                return False
        return True

    def run_test(self, qasm):
        """run one qasm test case"""
        dg = DG()
        dg.from_qasm_string(qasm)
        ir = dg.origin_ir
        coulping_graph = self.coupling_graph

        # mapping time for all algorithms
        all_mapping_time = []
        # mapping+routing time for all algorithms
        all_total_time = []
        # swap counts for all algorithms
        all_swap_counts = []

        for method in initial_methods:
            start = time.time()
            # run initial mapping
            initial_mapping = get_initial_mapping(
                dg, coulping_graph, method=method
            )
            if initial_mapping is None:
                # subgraph isomorphism failed
                all_mapping_time.append(None)
                all_total_time.append(None)
                all_swap_counts.append(None)
                continue
            time1 = time.time()
            # run routing
            sabre = SABRE(coulping_graph)
            sabre.execute(ir, initial_mapping)
            time2 = time.time()
            # compute time and swap count
            initial_time = time1 - start
            totol_time = time2 - start
            swap_num = self.counts_swaps(sabre.phy_exe_gates)
            # simulate the routing process
            res = self.check_routing(ir, sabre.phy_exe_gates, initial_mapping)
            assert res
            # save results
            all_mapping_time.append(initial_time)
            all_total_time.append(totol_time)
            all_swap_counts.append(swap_num)

        return (
            dg.num_q,
            len(ir),
            all_mapping_time,
            all_total_time,
            all_swap_counts,
        )

    def run_tests(self, path: str):
        """run all qasm test cases in directory.

        Args:
            path (str): directory of qasm test cases.
        """
        # two-dimensional lists, every list represents a single test case
        mapping_time = []
        total_time = []
        swap_counts = []
        qasm_names = []

        files = self.get_qasm_test_cases(path)
        for file in files:
            with file.open("r") as f:
                qasm_names.append(file.name)
                qasm = f.read()
                # data for one qasm testcase
                num_q, num_gates, mapping_time_, total_time_, swap_counts_ = (
                    self.run_test(qasm)
                )
                # show qasm info
                mapping_time_ = [num_q, num_gates] + mapping_time_
                total_time_ = [num_q, num_gates] + total_time_
                swap_counts_ = [num_q, num_gates] + swap_counts_
                # save results
                mapping_time.append(mapping_time_)
                total_time.append(total_time_)
                swap_counts.append(swap_counts_)

        # print results in table
        header1 = ["width", "size"] + initial_methods
        header2 = ["width", "size"] + [
            alg + "+sabre" for alg in initial_methods
        ]

        # calculate average
        qasm_names.append("average")
        # [None, None] is position for width and size
        avg_mapping_time = [None, None]
        avg_total_time = [None, None]
        avg_swap_counts = [None, None]
        for i in range(2, len(mapping_time[0])):
            avg_mapping_time.append(
                sum(mapping_time[j][i] for j in range(len(mapping_time)))
                / len(mapping_time)
            )
            avg_total_time.append(
                sum(total_time[j][i] for j in range(len(total_time)))
                / len(total_time)
            )
            avg_swap_counts.append(
                sum(swap_counts[j][i] for j in range(len(swap_counts)))
                / len(swap_counts)
            )
        mapping_time.append(avg_mapping_time)
        total_time.append(avg_total_time)
        swap_counts.append(avg_swap_counts)

        print("compare times of mapping algorithms")
        print(
            tabulate(
                mapping_time,
                headers=header1,
                showindex=qasm_names,
                tablefmt="grid",
            )
        )
        print("\ncompare times of mapping+routing algorithms")
        print(
            tabulate(
                total_time,
                headers=header2,
                showindex=qasm_names,
                tablefmt="grid",
            )
        )
        print("\ncompare swap count of mapping+routing algorithms")
        print(
            tabulate(
                swap_counts,
                headers=header2,
                showindex=qasm_names,
                tablefmt="grid",
            )
        )
