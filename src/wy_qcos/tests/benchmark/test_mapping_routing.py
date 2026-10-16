#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from ..system_tests.job.driver.spinq.spinq_rpc.spinq_rpc_api_server import (
    load_config,
)
from wy_qcos.transpiler.cmss.mapping.init_mapping.sc_initial_mapping import (
    get_initial_mapping,
)
from wy_qcos.transpiler.cmss.mapping.routing.sabre_routing import SABRE
from wy_qcos.transpiler.cmss.mapping.utils.dg import DG
from wy_qcos.common.cmss.gate_operation import GateOperation
from wy_qcos.transpiler.cmss.mapping.utils.routing_verifier import (
    check_routing,
)

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
            config_file_path="./etc/qcos/conf.d/spinq_rpc.toml"
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

    def run_test(self, qasm):
        """Run one qasm test case."""
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
            # verify routing correctness
            res = check_routing(
                coulping_graph,
                ir,
                sabre.phy_exe_gates,
                initial_mapping,
                sabre.logic2phy,
            )
            assert res, "Routing verification failed"
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
        """Run all qasm test cases in directory.

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
