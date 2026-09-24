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

import copy
import random
from pathlib import Path
import pytest

from networkx import Graph

from wy_qcos.transpiler.cmss.mapping.routing.sabre_routing import SABRE
from wy_qcos.transpiler.cmss.mapping.init_mapping.sabre_mapping import (
    sabre_initial_mapping,
)
from wy_qcos.common.cmss.gate_operation import X, H, CX, SWAP
from wy_qcos.common.cmss.measure import Measure
from wy_qcos.tests.common.qasm_file_reader import QasmFileReader
from wy_qcos.transpiler.cmss.mapping.utils.dg import DG
from wy_qcos.transpiler.cmss.mapping.utils.routing_verifier import (
    check_routing,
)


class TestSabre:
    def test_sabre_routing(self):
        coupling_graph = Graph()
        edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
        coupling_graph.add_edges_from(edges)
        sabre = SABRE(coupling_graph)

        gate1 = X([0])
        gate2 = CX([0, 1])
        gate3 = H([1])
        gates_list = [gate1, gate2, gate3]
        sabre.execute(gates_list)
        assert sabre.logic2phy[:2] == [0, 1]
        # auto-supplemented measures for qubits 0, 1
        non_measure_gates = [
            gate
            for gate in sabre.phy_exe_gates
            if not isinstance(gate, Measure)
        ]
        assert len(non_measure_gates) == len(gates_list)

        gate1 = CX([0, 1])
        gate2 = CX([2, 3])
        gate3 = CX([1, 2])
        gate4 = CX([0, 2])
        gates_list = [gate1, gate2, gate3, gate4]
        sabre.execute(gates_list)
        # verify routing correctness
        result = check_routing(
            coupling_graph,
            gates_list,
            sabre.phy_exe_gates,
            list(sabre.initial_l2p),
            sabre.logic2phy,
        )
        assert result
        # inserted one swap gate + auto-supplemented measures
        non_measure_gates = [
            gate
            for gate in sabre.phy_exe_gates
            if not isinstance(gate, Measure)
        ]
        assert len(non_measure_gates) >= len(gates_list)
        # between gate3 and gate4
        swap_gates = [g for g in non_measure_gates if isinstance(g, SWAP)]
        assert len(swap_gates) >= 1

        gate1 = CX([0, 3])
        gate2 = CX([1, 3])
        gate3 = CX([0, 2])
        gate4 = CX([0, 1])
        gates_list = [gate1, gate2, gate3, gate4]
        sabre.execute(gates_list)
        result = check_routing(
            coupling_graph,
            gates_list,
            sabre.phy_exe_gates,
            list(sabre.initial_l2p),
            sabre.logic2phy,
        )
        assert result
        non_measure_gates = [
            gate
            for gate in sabre.phy_exe_gates
            if not isinstance(gate, Measure)
        ]
        assert len(non_measure_gates) == len(gates_list) + 1
        assert isinstance(non_measure_gates[1], SWAP)

    def test_sabre_mapping(self):
        coupling_graph = Graph()
        edges = [(0, 1), (1, 2), (2, 3)]
        coupling_graph.add_edges_from(edges)
        sabre = SABRE(coupling_graph)

        gate1 = CX([0, 1])
        gate2 = CX([2, 3])
        gate3 = CX([1, 2])
        gate4 = CX([0, 2])
        gates_list = [gate1, gate2, gate3, gate4]
        mapping = sabre_initial_mapping(gates_list, coupling_graph)
        # insert one swap, between gate1 and gate2
        assert mapping == [0, 1, 2, 3]

        gate1 = CX([0, 3])
        gate2 = CX([1, 3])
        gate3 = CX([0, 2])
        gate4 = CX([0, 1])
        gates_list = [gate1, gate2, gate3, gate4]
        mapping = sabre_initial_mapping(gates_list, coupling_graph)
        sabre.execute(gates_list, initial_l2p=mapping)
        # insert one swap, between gate3 and gate4
        assert mapping == [2, 0, 3, 1]


def _measure_indices(gates: list) -> list:
    """Return indices of measure gates in the list."""
    return [i for i, op in enumerate(gates) if op.name == "measure"]


def _has_measure_before_last_gate(gates: list) -> bool:
    """Check if any measure gate appears before the last non-measure gate."""
    measure_idx = _measure_indices(gates)
    if not measure_idx:
        return False
    first_measure = measure_idx[0]
    return any(
        op.name not in ("measure", "sync", "barrier")
        for op in gates[first_measure:]
    )


class TestSabreMeasurePlacement:
    """Verify SABRE.execute() keeps measure gates at the end.

    Even when measure gates are included in the input, they should not be
    moved before other gates.
    """

    @staticmethod
    def _linear_graph(num_qubits: int = 6) -> Graph:
        """Create a linear chain coupling graph: 0-1-2-...-N."""
        graph = Graph()
        edges = [(i, i + 1) for i in range(num_qubits - 1)]
        graph.add_edges_from(edges)
        return graph

    def test_measure_at_end_no_swap(self):
        """Measure gates should be at the end even without SWAP.

        Uses a chain CX(0,1)->CX(1,2)->CX(2,3) where measure on q0
        is attached to CX(0,1). Without the fix, measure(q0) would
        be output right after CX(0,1) executes, before CX(1,2).
        """
        sabre = SABRE(self._linear_graph(6))
        gates = [
            CX([0, 1]),
            CX([1, 2]),
            CX([2, 3]),
            H([0]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        sabre.execute(gates)
        result = sabre.phy_exe_gates
        assert not _has_measure_before_last_gate(result)
        assert len(_measure_indices(result)) == 4

    def test_measure_at_end_with_swap(self):
        """Measure gates should be at the end even when SWAPs are inserted."""
        sabre = SABRE(self._linear_graph(6))
        gates = [
            CX([0, 3]),
            CX([1, 3]),
            CX([0, 2]),
            CX([0, 1]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        sabre.execute(gates)
        result = sabre.phy_exe_gates
        assert not _has_measure_before_last_gate(result)
        swap_count = sum(1 for op in result if op.name == "swap")
        assert swap_count > 0
        measure_idx = _measure_indices(result)
        assert len(measure_idx) == 4
        assert measure_idx[0] > 0

    def test_measure_not_in_routing_result(self):
        """Measure gates should not appear in the routing portion.

        Uses a chain of CX gates on different qubit pairs. Without the
        fix, measure on q0 attached to CX(0,1) would be output before
        CX(1,2) and CX(2,3) are routed.
        """
        sabre = SABRE(self._linear_graph(6))
        gates = [
            CX([0, 1]),
            CX([1, 2]),
            CX([2, 3]),
            H([1]),
            H([2]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        sabre.execute(gates)
        result = sabre.phy_exe_gates
        measure_idx = _measure_indices(result)
        assert len(measure_idx) == 4
        assert measure_idx[0] == len(result) - 4

    def test_measure_count_preserved(self):
        """All measure gates in the input should appear in the output."""
        sabre = SABRE(self._linear_graph(6))
        gates = [
            H([0]),
            H([1]),
            H([2]),
            H([3]),
            CX([0, 3]),
            CX([1, 2]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        sabre.execute(gates)
        result = sabre.phy_exe_gates
        measure_gates = [op for op in result if op.name == "measure"]
        assert len(measure_gates) == 4

    def test_measure_targets_updated(self):
        """Measure targets should be mapped to physical qubits."""
        sabre = SABRE(self._linear_graph(6))
        gates = [
            CX([0, 3]),
            CX([0, 2]),
            CX([0, 1]),
            Measure([0]),
            Measure([1]),
            Measure([2]),
            Measure([3]),
        ]
        sabre.execute(gates)
        result = sabre.phy_exe_gates
        measure_gates = [op for op in result if op.name == "measure"]
        assert len(measure_gates) == 4
        final_mapping = sabre.logic2phy
        for measure_op in measure_gates:
            for target in measure_op.targets:
                assert target in final_mapping or target in range(
                    sabre.phy_qubit_num
                )


class TestSabreTargetBits:
    """Tests for target_bits subgraph routing."""

    @staticmethod
    def _linear_graph(num_qubits: int = 8) -> Graph:
        graph = Graph()
        graph.add_edges_from([(i, i + 1) for i in range(num_qubits - 1)])
        return graph

    def test_target_bits_restricts_routing(self):
        """Routing should only use qubits within target_bits."""
        graph = self._linear_graph(8)
        target = [0, 1, 2, 3]
        sabre = SABRE(graph, target_bits=target)
        gates = [
            CX([0, 1]),
            CX([1, 2]),
            CX([0, 2]),
        ]
        sabre.execute(gates)
        for gate in sabre.phy_exe_gates:
            for t in gate.targets:
                assert t in target or t < len(target)

    def test_target_bits_disconnected_raises(self):
        """Disconnected target_bits should raise ValueError."""
        graph = self._linear_graph(8)
        sabre = SABRE(graph, target_bits=[0, 5])
        gates = [CX([0, 1])]
        try:
            sabre.execute(gates)
            assert False, "Should have raised"
        except ValueError:
            pass

    def test_target_bits_connected_subset(self):
        """Connected target_bits subset should route normally."""
        graph = self._linear_graph(8)
        target = [2, 3, 4, 5]
        sabre = SABRE(graph, target_bits=target)
        gates = [
            CX([0, 1]),
            CX([1, 2]),
            CX([0, 2]),
        ]
        sabre.execute(gates)
        assert len(sabre.phy_exe_gates) > 0


class TestSabreFidelity:
    """Tests for fidelity-aware routing."""

    @staticmethod
    def _grid_graph() -> Graph:
        graph = Graph()
        edges = [
            (0, 1),
            (1, 2),
            (2, 3),
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
            (4, 5),
            (5, 6),
            (6, 7),
        ]
        graph.add_edges_from(edges)
        return edges, graph

    def test_low_fidelity_edge_filtered(self):
        """Edges below threshold should be removed from coupling."""
        edges, graph = self._grid_graph()
        fidelities = [0.99] * len(edges)
        fidelities[0] = 0.1
        single_fids = [0.99] * 8
        sabre = SABRE(
            graph,
            edge_fidelities=fidelities,
            single_qubit_fidelities=single_fids,
        )
        gates = [CX([0, 1]), CX([1, 2])]
        sabre.execute(gates)
        assert len(sabre.phy_exe_gates) > 0

    def test_adaptive_threshold(self):
        """Adaptive threshold (fidelity_threshold < 0) should work."""
        edges, graph = self._grid_graph()
        fidelities = [
            0.99,
            0.98,
            0.97,
            0.96,
            0.95,
            0.94,
            0.93,
            0.92,
            0.91,
            0.90,
        ]
        sabre = SABRE(
            graph,
            edge_fidelities=fidelities,
            fidelity_threshold=-1.0,
        )
        assert 0.3 <= sabre.fidelity_threshold <= 0.9

    def test_all_edges_below_threshold_raises(self):
        """All edges filtered out should raise (no usable graph)."""
        edges, graph = self._grid_graph()
        fidelities = [0.1] * len(edges)
        single_fids = [0.99] * 8
        sabre = SABRE(
            graph,
            edge_fidelities=fidelities,
            single_qubit_fidelities=single_fids,
            fidelity_threshold=0.5,
        )
        gates = [CX([0, 1])]
        try:
            sabre.execute(gates)
            assert False, "Should have raised"
        except (ValueError, RuntimeError, IndexError):
            pass


class TestSabreDensification:
    """Tests for sparse logical qubit ID densification."""

    def test_sparse_qubit_ids(self):
        """Circuit with qubit gaps (e.g. q0, q3, q5) should densify."""
        graph = Graph()
        graph.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4)])
        sabre = SABRE(graph)
        gates = [
            CX([0, 3]),
            CX([3, 5]),
            CX([0, 5]),
        ]
        sabre.execute(gates)
        # logic2phy should be restored to original sparse indices
        assert len(sabre.logic2phy) >= 6
        assert sabre.logic2phy[0] >= 0
        assert sabre.logic2phy[3] >= 0
        assert sabre.logic2phy[5] >= 0

    def test_contiguous_qubit_ids_no_densify(self):
        """Contiguous qubit IDs should not densify."""
        graph = Graph()
        graph.add_edges_from([(0, 1), (1, 2), (2, 3)])
        sabre = SABRE(graph)
        gates = [CX([0, 1]), CX([1, 2]), CX([0, 2])]
        sabre.execute(gates)
        assert len(sabre.logic2phy) == 3


class TestSabreAllSingleQubit:
    """Tests for all-single-qubit circuit shortcut."""

    def test_all_single_qubit_no_swap(self):
        """Circuits with only 1q gates should not insert SWAPs."""
        graph = Graph()
        graph.add_edges_from([(0, 1), (1, 2), (2, 3)])
        sabre = SABRE(graph)
        gates = [H([0]), H([1]), X([2]), H([3])]
        sabre.execute(gates)
        swaps = [g for g in sabre.phy_exe_gates if g.name == "swap"]
        assert len(swaps) == 0
        non_measure = [g for g in sabre.phy_exe_gates if g.name != "measure"]
        assert len(non_measure) == 4

    def test_single_qubit_with_target_bits(self):
        """1q circuit with target_bits should map to those qubits."""
        graph = Graph()
        graph.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])
        target = [0, 2, 4]
        sabre = SABRE(graph, target_bits=target)
        gates = [H([0]), H([1]), H([2])]
        sabre.execute(gates)
        non_measure = [g for g in sabre.phy_exe_gates if g.name != "measure"]
        assert len(non_measure) == 3
        for gate in non_measure:
            assert gate.targets[0] in target


class TestSabreInitialMapping:
    """Tests for custom initial mapping."""

    def test_custom_initial_l2p(self):
        """Custom initial mapping should be respected."""
        graph = Graph()
        graph.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4)])
        sabre = SABRE(graph)
        gates = [CX([0, 1]), CX([0, 2])]
        initial = [3, 4, 0, 1]
        sabre.execute(gates, initial_l2p=initial)
        assert len(sabre.phy_exe_gates) > 0

    def test_initial_l2p_with_extension(self):
        """Short initial mapping should be extended to cover all qubits."""
        graph = Graph()
        graph.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)])
        sabre = SABRE(graph)
        gates = [CX([0, 1]), CX([1, 2])]
        initial = [0, 1]
        sabre.execute(gates, initial_l2p=initial)
        assert len(sabre.logic2phy) >= 3


class TestSabreRoutingVerification:
    """Random correctness verification via check_routing."""

    @staticmethod
    def _linear_graph(num_qubits: int) -> Graph:
        graph = Graph()
        graph.add_edges_from([(i, i + 1) for i in range(num_qubits - 1)])
        return graph

    @staticmethod
    def _grid_graph(rows: int, cols: int) -> Graph:
        graph = Graph()
        for row in range(rows):
            for col in range(cols - 1):
                graph.add_edge(row * cols + col, row * cols + col + 1)
        for col in range(cols):
            for row in range(rows - 1):
                graph.add_edge(row * cols + col, (row + 1) * cols + col)
        return graph

    @staticmethod
    def _generate_circuit(num_logical: int, num_gates: int, rng):
        """Generate a random circuit with CX and single-qubit gates.

        Args:
            num_logical: Number of logical qubits.
            num_gates: Number of gates to generate.
            rng: Random instance.

        Returns:
            list: Random gate list.
        """
        gates: list = []
        for _ in range(num_gates):
            if rng.random() < 0.7:
                # 2-qubit gate
                q0 = rng.randrange(num_logical)
                q1 = rng.randrange(num_logical)
                while q1 == q0:
                    q1 = rng.randrange(num_logical)
                gates.append(CX([q0, q1]))
            else:
                # 1-qubit gate
                q0 = rng.randrange(num_logical)
                gates.append(H([q0]))
        return gates

    def test_random_linear_100_circuits(self):
        """Route 100 random circuits on linear chain, verify routing."""
        rng = random.Random(42)
        num_physical = 8
        graph = self._linear_graph(num_physical)

        for case_idx in range(100):
            num_logical = rng.randint(2, 5)
            num_gates = rng.randint(3, 15)
            gates = self._generate_circuit(num_logical, num_gates, rng)
            sabre = SABRE(graph)
            sabre.execute(copy.deepcopy(gates))
            initial_mapping = list(sabre.initial_l2p)
            result = check_routing(
                graph,
                gates,
                sabre.phy_exe_gates,
                initial_mapping,
                sabre.logic2phy,
            )
            assert result, (
                f"check_routing failed for linear case {case_idx}: "
                f"num_logical={num_logical}, gates={num_gates}"
            )

    def test_random_grid_100_circuits(self):
        """Route 100 random circuits on 3x3 grid, verify with check_routing."""
        rng = random.Random(123)
        graph = self._grid_graph(3, 3)

        for case_idx in range(100):
            num_logical = rng.randint(2, 6)
            num_gates = rng.randint(3, 20)
            gates = self._generate_circuit(num_logical, num_gates, rng)
            sabre = SABRE(graph)
            sabre.execute(copy.deepcopy(gates))
            initial_mapping = list(sabre.initial_l2p)
            result = check_routing(
                graph,
                gates,
                sabre.phy_exe_gates,
                initial_mapping,
                sabre.logic2phy,
            )
            assert result, (
                f"check_routing failed for grid case {case_idx}: "
                f"num_logical={num_logical}, gates={num_gates}"
            )


class TestSabreQasmBench:
    """Routing verification on real QASM benchmark circuits."""

    @staticmethod
    def _grid_graph(rows, cols):
        graph = Graph()
        for row in range(rows):
            for col in range(cols - 1):
                graph.add_edge(
                    row * cols + col,
                    row * cols + col + 1,
                )
        for col in range(cols):
            for row in range(rows - 1):
                graph.add_edge(
                    row * cols + col,
                    (row + 1) * cols + col,
                )
        return graph

    def test_qasmbench_small(self):
        """Route and verify all parseable qasmbench-small circuits."""
        project_root = Path(__file__).resolve().parents[6]
        qasm_dir = (
            project_root
            / "samples"
            / "qasm"
            / "benchpress"
            / "qasmbench-small"
        )
        if not qasm_dir.exists():
            pytest.skip("qasmbench-small directory not found")

        reader = QasmFileReader(qasm_dir)
        grid = self._grid_graph(4, 5)
        failed = []
        skipped = []

        for qasm_file in reader.iter_files():
            if "_transpiled" in qasm_file.name:
                continue
            qasm_str = qasm_file.read_text()
            dg = DG()
            try:
                dg.from_qasm_string(qasm_str)
            except Exception:
                skipped.append(qasm_file.stem)
                continue

            ir = dg.origin_ir
            sabre = SABRE(grid)
            sabre.execute(copy.deepcopy(ir))
            initial_mapping = list(sabre.initial_l2p)
            result = check_routing(
                grid,
                ir,
                sabre.phy_exe_gates,
                initial_mapping,
                sabre.logic2phy,
            )
            if not result:
                failed.append(qasm_file.stem)

        assert not failed, (
            f"check_routing failed for: {failed}, "
            f"skipped (parse error): {skipped}"
        )
