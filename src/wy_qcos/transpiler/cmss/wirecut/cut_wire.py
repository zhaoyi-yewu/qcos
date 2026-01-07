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

import math
import time

from loguru import logger

from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.cmss.compiler.parser import Parser
from wy_qcos.transpiler.cmss.wirecut.cut import Cut
from wy_qcos.transpiler.cmss.wirecut.dag import DAG
from wy_qcos.transpiler.cmss.wirecut.dd import DD, reconstruct_prob_from_bins
from wy_qcos.transpiler.cmss.wirecut.greedy import GreedyModel
from wy_qcos.transpiler.cmss.wirecut.mip_model import MIPModel
from wy_qcos.transpiler.cmss.wirecut.prepare_data import Prepare_data
from wy_qcos.transpiler.cmss.wirecut.utils import (
    generate_subcircuits_for_execute,
)


class CutWire:
    """Circuit cutting class.

    Args:
        max_subcircuit_width (int): Max number of qubits allowed per subcircuit
        qasm (str): OpenQASM
        max_memory (int): Set the upper memory limit for the refactoring phase
        max_depth (int): Maximum recursion depth
        is_complete_reconstruction (bool): Whether a complete refactoring
        max_cuts (int): Maximum allowable number of cuts
    """

    def __init__(
        self,
        max_subcircuit_width,
        qasm,
        max_memory,
        max_depth: int = Constant.MAX_RERURSIVE_DEPTH,
        is_complete_reconstruction: bool = True,
        max_cuts: int = Constant.MAX_CIRCUIT_CUT,
    ):
        self.parser = Parser(qasm)
        self.dag = DAG(parser=self.parser)
        self.max_subcircuit_width = max_subcircuit_width
        self.max_cuts = max_cuts
        self.nvertex, self.edge_list = self.dag.knit_dag_to_graph()
        self.is_complete_reconstruction = is_complete_reconstruction
        logger.info(
            f"Number of vertices in the parsed DAG graph: {self.nvertex} ,"
            f"number of edges: {len(self.edge_list)}."
        )
        try:
            self.init_data()
        except ValueError as e:
            raise ValueError(f"Init data fail: {str(e)}.") from e
        self.subcircuits_dict = None
        self.max_memory = max_memory
        self.max_depth = max_depth

    def init_data(self):
        min_nsubcircuit = math.ceil(
            self.parser.nqubits / self.max_subcircuit_width
        )
        subcircuit = None
        start_time = time.time()
        for nsubcircuit in range(min_nsubcircuit, self.max_cuts + 2):
            tmp_start_time = time.time()
            # According to nvertex, determine the solution method for
            # circuit cutting schemes
            if self.nvertex >= 80:
                self.mip_model = GreedyModel(
                    nvertex=self.nvertex,
                    edges=self.edge_list,
                    nsubcircuit=nsubcircuit,
                    max_subcircuit_width=self.max_subcircuit_width,
                    max_cuts=self.max_cuts,
                )
            else:
                self.mip_model = MIPModel(
                    nvertex=self.nvertex,
                    edges=self.edge_list,
                    nsubcircuit=nsubcircuit,
                    max_subcircuit_width=self.max_subcircuit_width,
                    max_cuts=self.max_cuts,
                )
            _, cut_edges, subcircuit = self.mip_model.solve()
            tmp_end_time = time.time()
            logger.debug(
                f"Try to cut the circuit into {nsubcircuit} subcircuits, "
                f"time: {(tmp_end_time - tmp_start_time)} s."
            )
            if subcircuit is not None:
                self.num_cuts = len(cut_edges)
                break
        end_time = time.time()
        logger.debug(f"Circuit cutting time: {end_time - start_time} s.")
        if subcircuit is None:
            raise ValueError(
                "This circuit cannot be cut and reconfigured "
                "according to the given parameters."
            )
        result = self.dag.parse_subgraphs(subcircuit)
        self.cut = Cut(self.parser.quantum_circuit, result)
        self.subcircuits, qubit_allocation_map = self.cut.cut_circuit()

        start_time = time.time()
        self.prepare_data = Prepare_data(
            self.parser.quantum_circuit,
            self.subcircuits,
            qubit_allocation_map,
        )
        end_time = time.time()
        logger.debug(
            f"Generating variant subcircuits takes time: "
            f"{end_time - start_time} s."
        )

    def generate_all_variants_subcircuits(self):
        return generate_subcircuits_for_execute(self.prepare_data)


def generate_all_variant_subcircuits_for_execute(
    max_subcircuit_width,
    qasm,
    max_memory,
    max_depth: int = Constant.MAX_RERURSIVE_DEPTH,
    is_complete_reconstruction: bool = True,
    max_cuts: int = Constant.MAX_CIRCUIT_CUT,
):
    """Generate all variant subcircuits.

    Args:
        max_subcircuit_width (int): Maximum width of subcircuit.
        qasm (str): The openQASM representation of a quantum circuit.
        max_memory (int): Memory upper limit set during the refactoring phase.
        max_depth (int): Maximum recursion depth
        is_complete_reconstruction (bool): Whether a complete refactoring.
        max_cuts (int): Maximum cutting value.

    Returns:
        All variant subcircuits of serialization and cut_wire instance.
    """
    cut_wire = CutWire(
        max_subcircuit_width=max_subcircuit_width,
        qasm=qasm,
        max_memory=max_memory,
        max_depth=max_depth,
        is_complete_reconstruction=is_complete_reconstruction,
        max_cuts=max_cuts,
    )
    origin_subcircuits = cut_wire.subcircuits
    subcircuits_dict = cut_wire.generate_all_variants_subcircuits()
    cut_wire.subcircuits_dict = subcircuits_dict
    subcircuits = simple_subcircuit_dict(subcircuits_dict)
    logger.info(f"Generated {len(subcircuits)} subcircuits")
    return (
        origin_subcircuits,
        simple_subcircuit_dict(subcircuits_dict),
        cut_wire,
    )


def simple_subcircuit_dict(subcircuits_dict):
    """Generate simple subcircuits.

    Args:
        subcircuits_dict (dict): subcircuits dict

    Returns:
        list: variant subcircuits
    """
    variant_subcircuits = []
    for _, subcircuit in subcircuits_dict.items():
        for _, variant_circuit in subcircuit.items():
            variant_subcircuits.append(variant_circuit)
    return variant_subcircuits


def reconstruct_probability_distribution_wire_cut(
    wirecut,
    results_for_execute,
    is_complete_reconstruction,
):
    """Reconstruct the probability distribution.

    Args:
        wirecut:  wirecut instance object
        results_for_execute: Execution results of the seed variation circuit
        is_complete_reconstruction: Whether to perform complete reconstruction

    Returns:
        counts: Circuit sampling results.
        probability_distribution: Probability distribution.
    """
    all_results_dict = {}
    subcircuits_for_execute = wirecut.subcircuits_dict
    cnt = 0
    for (
        subcircuit_index,
        subcircuit_variants,
    ) in subcircuits_for_execute.items():
        results_dict_for_one_subcircuit = {}
        for config, _ in subcircuit_variants.items():
            result = results_for_execute[cnt]
            results_dict_for_one_subcircuit[config] = result
            cnt += 1
        all_results_dict[subcircuit_index] = results_dict_for_one_subcircuit
    dd = DD(
        topo_subcircuits=wirecut.prepare_data.topo_subcircuits,
        prepare_data=wirecut.prepare_data,
        results_from_hardware=all_results_dict,
        max_memory=wirecut.max_memory,
        max_depths=wirecut.max_depth,
    )
    dd.dd()
    probability_distribution, sparse_prob_list = reconstruct_prob_from_bins(
        subcircuit_out_qubits=wirecut.prepare_data.origin_qubit_order,
        dd_bins=dd.dd_bins,
        max_memory=wirecut.max_memory,
        is_complete_reconstruction=is_complete_reconstruction,
    )

    return probability_distribution, sparse_prob_list
