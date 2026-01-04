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

from qcos.transpiler.cmss.circuit.collect_blocks import (
    BlockCollector,
    BlockSplitter,
)
from qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from qcos.transpiler.cmss.common.gate_operation import CX, Z, H, RZ
from qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit


class TestCollectBlocks:
    def test_collect_gates_from_dagcircuit_1(self):
        """Test collecting CX gates from DAGCircuits."""
        ir = [CX([0, 1]), CX([0, 2]), Z([0]), CX([0, 3]), CX([0, 4])]
        qc = QuantumCircuit.from_ir(ir)

        block_collector = BlockCollector(DAGCircuit.circuit_to_dag(qc))
        blocks = block_collector.collect_all_matching_blocks(
            lambda node: node.op.name == "cx",
            split_blocks=False,
            min_block_size=2,
        )

        # The middle z-gate leads to two blocks of size 2 each
        assert len(blocks) == 2
        assert len(blocks[0]) == 2
        assert len(blocks[1]) == 2

    def test_collect_gates_from_dagcircuit_2(self):
        """Test collecting both CX and Z gates from DAGCircuits."""
        ir = [CX([0, 1]), CX([0, 2]), Z([0]), CX([0, 3]), CX([0, 4])]
        qc = QuantumCircuit.from_ir(ir)

        block_collector = BlockCollector(DAGCircuit.circuit_to_dag(qc))
        blocks = block_collector.collect_all_matching_blocks(
            lambda node: node.op.name in ["cx", "z"],
            split_blocks=False,
            min_block_size=1,
        )

        # All of the gates are part of a single block
        assert len(blocks) == 1
        assert len(blocks[0]) == 5

    def test_collect_gates_from_dagcircuit_3(self):
        """Test collecting CX gates from DAGCircuits."""
        ir = [
            CX([0, 1]),
            CX([0, 2]),
            Z([0]),
            CX([1, 3]),
            CX([0, 3]),
            CX([0, 4]),
        ]
        qc = QuantumCircuit.from_ir(ir)

        block_collector = BlockCollector(DAGCircuit.circuit_to_dag(qc))
        blocks = block_collector.collect_all_matching_blocks(
            lambda node: node.op.name in ["cx"],
            split_blocks=False,
            min_block_size=1,
        )

        assert len(blocks) == 2

    def test_collect_gates_from_dagcircuit_4(self):
        """Test collecting CX, Rz, X gates from DAGCircuits."""
        ir = [
            H([0]),
            H([1]),
            H([2]),
            RZ([1], arg_value=[0.1]),
            RZ([2], arg_value=[0.2]),
            CX([1, 0]),
            RZ([0], arg_value=[0.3]),
            CX([1, 2]),
            CX([0, 1]),
            H([2]),
            CX([1, 2]),
            CX([0, 1]),
            RZ([1], arg_value=[0.4]),
            H([0]),
            H([1]),
        ]
        qc = QuantumCircuit.from_ir(ir)
        #      ┌───┐           ┌───┐┌─────────┐                  ┌───┐
        # q_0: ┤ H ├───────────┤ X ├┤ Rz(0.3) ├──■─────────■─────┤ H ├────────
        #      ├───┤┌─────────┐└─┬─┘└─────────┘┌─┴─┐     ┌─┴─┐┌──┴───┴──┐┌───┐
        # q_1: ┤ H ├┤ Rz(0.1) ├──■───────■─────┤ X ├──■──┤ X ├┤ Rz(0.4) ├┤ H ├
        #      ├───┤├─────────┤        ┌─┴─┐   ├───┤┌─┴─┐└───┘└─────────┘└───┘
        # q_2: ┤ H ├┤ Rz(0.2) ├────────┤ X ├───┤ H ├┤ X ├─────────────────────
        #      └───┘└─────────┘        └───┘   └───┘└───┘

        block_collector = BlockCollector(DAGCircuit.circuit_to_dag(qc))
        blocks = block_collector.collect_all_matching_blocks(
            lambda node: node.op.name in ["cx", "rz", "x"],
            split_blocks=False,
            min_block_size=1,
        )
        assert len(blocks) == 2
        assert len(blocks[0]) == 6
        assert len(blocks[1]) == 3

    def test_collect_and_split_gates_from_dagcircuit(self):
        """Test collecting and splitting blocks from DAGCircuit."""
        ir = [CX([0, 1]), CX([3, 5]), CX([2, 4]), CX([1, 0]), CX([5, 3])]
        qc = QuantumCircuit.from_ir(ir)

        block_collector = BlockCollector(DAGCircuit.circuit_to_dag(qc))
        blocks = block_collector.collect_all_matching_blocks(
            lambda node: True,
            split_blocks=False,
            min_block_size=1,
        )

        # All the gates are part of a single block
        assert len(blocks) == 1
        assert len(blocks[0]) == 5

        # Split the first block into sub-blocks over disjoint qubit sets
        # We should get 3 sub-blocks
        split_blocks = BlockSplitter().run(blocks[0])
        assert len(split_blocks) == 3
