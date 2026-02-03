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
import pytest
import numpy as np
from unittest.mock import patch

from wy_qcos.transpiler.cmss.optimizer.clifford_rz_optimization import (
    CliffordRzOptimization,
)
from wy_qcos.transpiler.cmss.common.gate_operation import (
    RZ,
    X,
    H,
    CX,
    S,
    SDG,
    T,
    Z,
)
from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.common.errors import CircuitException
from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.circuit.utils import RandomCircuitGen, is_equal
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.optimizer.gate_optimizer import optimize
from wy_qcos.tests.unit_tests.transpiler.comm import validate_optimize_result
from wy_qcos.transpiler.common.utils import logger


class TestCliffordRzOptimization:
    def test_reduce_hadamard_gates(self):
        opt = CliffordRzOptimization()

        ir = [H([0]), S([0]), H([0])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(dag)
        assert ret == 1
        counts = dag.count_ops()
        assert counts.get("h", 0) == 1
        assert counts.get("s", 0) == 0
        assert counts.get("sdg", 0) == 2
        validate_optimize_result(init_ir, dag)

        ir = [H([0]), SDG([0]), H([0])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(dag)
        assert ret == 1
        counts = dag.count_ops()
        assert counts.get("h", 0) == 1
        assert counts.get("s", 0) == 2
        assert counts.get("sdg", 0) == 0
        validate_optimize_result(init_ir, dag)

        ir = [H([0]), H([1]), CX([0, 1]), H([0]), H([1])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(dag)
        assert ret == 4
        counts = dag.count_ops()
        assert counts.get("h", 0) == 0
        assert counts["cx"] == 1
        validate_optimize_result(init_ir, dag)

        ir = [H([1]), H([2]), CX([1, 2]), H([1]), H([2])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(dag)
        assert ret == 4
        nodes = list(dag.topological_op_nodes())
        assert len(nodes) == 1
        assert nodes[0].op.name == "cx"
        assert nodes[0].op.targets == [2, 1]
        validate_optimize_result(init_ir, dag)

        ir = [H([1]), H([2]), CX([2, 1]), H([1]), H([2])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(dag)
        assert ret == 4
        nodes = list(dag.topological_op_nodes())
        assert len(nodes) == 1
        assert nodes[0].op.name == "cx"
        assert nodes[0].op.targets == [1, 2]
        validate_optimize_result(init_ir, dag)

        ir = [H([1]), S([1]), CX([0, 1]), SDG([1]), H([1])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(dag)
        assert ret == 2
        validate_optimize_result(init_ir, dag)

        ir = [H([1]), SDG([1]), CX([0, 1]), S([1]), H([1])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(dag)
        assert ret == 2
        validate_optimize_result(init_ir, dag)

        ir = [
            H([0]),
            SDG([0]),
            H([0]),
            H([1]),
            H([2]),
            CX([2, 1]),
            H([1]),
            H([2]),
        ]
        #      ┌───┐┌─────┐┌───┐
        # q_0: ┤ H ├┤ Sdg ├┤ H ├
        #      ├───┤└┬───┬┘├───┤
        # q_1: ┤ H ├─┤ X ├─┤ H ├
        #      ├───┤ └─┬─┘ ├───┤
        # q_2: ┤ H ├───■───┤ H ├
        #      └───┘       └───┘
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(
            copy.deepcopy(dag), basis_gates={"h", "sdg", "s", "cx"}
        )
        assert ret == 5
        validate_optimize_result(init_ir, dag)

        ret = opt.reduce_hadamard_gates(
            copy.deepcopy(dag), basis_gates={"sdg", "s", "cx"}
        )
        assert ret == 0
        validate_optimize_result(init_ir, dag)

        ret = opt.reduce_hadamard_gates(
            copy.deepcopy(dag), basis_gates={"h", "cx"}
        )
        assert ret == 4
        validate_optimize_result(init_ir, dag)

        ret = opt.reduce_hadamard_gates(
            copy.deepcopy(dag), basis_gates={"h", "sdg", "s"}
        )
        assert ret == 1
        validate_optimize_result(init_ir, dag)

    def test_cancel_single_qubit_gates(self):
        opt = CliffordRzOptimization()
        # test1
        ir = [
            RZ([1], arg_value=[0.1]),
            RZ([1], arg_value=[0.1]),
            H([1]),
            CX([0, 1]),
            H([1]),
            RZ([1], arg_value=[0.1]),
        ]
        init_ir = copy.deepcopy(ir)
        # q_0: ─────────────────────────────■──────────────────
        #      ┌─────────┐┌─────────┐┌───┐┌─┴─┐┌───┐┌─────────┐
        # q_1: ┤ Rz(0.1) ├┤ Rz(0.1) ├┤ H ├┤ X ├┤ H ├┤ Rz(0.1) ├
        #      └─────────┘└─────────┘└───┘└───┘└───┘└─────────┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 2
        validate_optimize_result(init_ir, dag)

        # test2
        ir = [
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
        ]
        init_ir = copy.deepcopy(ir)
        # q_0: ─────────────■───────────────■─────────────
        #      ┌─────────┐┌─┴─┐┌─────────┐┌─┴─┐┌─────────┐
        # q_1: ┤ Rz(0.2) ├┤ X ├┤ Rz(0.2) ├┤ X ├┤ Rz(0.2) ├
        #      └─────────┘└───┘└─────────┘└───┘└─────────┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1
        validate_optimize_result(init_ir, dag)

        # test3
        ir = [RZ([0], arg_value=[0.3]), CX([0, 1]), RZ([0], arg_value=[0.3])]
        init_ir = copy.deepcopy(ir)
        #      ┌─────────┐     ┌─────────┐
        # q_0: ┤ Rz(0.3) ├──■──┤ Rz(0.3) ├
        #      └─────────┘┌─┴─┐└─────────┘
        # q_1: ───────────┤ X ├───────────
        #                 └───┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1
        validate_optimize_result(init_ir, dag)

        # test4
        ir = [
            RZ([0], arg_value=[0.1]),
            CX([1, 0]),
            CX([0, 2]),
            CX([1, 0]),
            RZ([0], arg_value=[0.1]),
        ]
        init_ir = copy.deepcopy(ir)
        #      ┌─────────┐┌───┐     ┌───┐┌─────────┐
        # q_0: ┤ Rz(0.1) ├┤ X ├──■──┤ X ├┤ Rz(0.1) ├
        #      └─────────┘└─┬─┘  │  └─┬─┘└─────────┘
        # q_1: ─────────────■────┼────■─────────────
        #                      ┌─┴─┐
        # q_2: ────────────────┤ X ├────────────────
        #                      └───┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1
        validate_optimize_result(init_ir, dag)

        # test5
        ir = [
            RZ([0], arg_value=[0.1]),
            H([0]),
            X([0]),
            H([0]),
            RZ([0], arg_value=[0.2]),
        ]
        init_ir = copy.deepcopy(ir)
        #    ┌─────────┐┌───┐┌───┐┌───┐┌─────────┐
        # q: ┤ Rz(0.1) ├┤ H ├┤ X ├┤ H ├┤ Rz(0.2) ├
        #    └─────────┘└───┘└───┘└───┘└─────────┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1
        validate_optimize_result(init_ir, dag)

        # test6
        ir = [
            RZ([1], arg_value=[0.1]),
            # ---
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            # ---
            H([1]),
            CX([0, 1]),
            H([1]),
            # ---
            RZ([1], arg_value=[0.2]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1
        validate_optimize_result(init_ir, dag)

        # test7
        ir = [
            RZ([1], arg_value=[0.1]),
            # ---
            H([1]),
            CX([0, 1]),
            H([1]),
            # ---
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            # ---
            RZ([1], arg_value=[0.2]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1
        validate_optimize_result(init_ir, dag)

        # test8
        ir = [
            RZ([1], arg_value=[0.1]),
            # ---
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            # ---
            CX([1, 2]),
            # ---
            RZ([1], arg_value=[0.2]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1
        validate_optimize_result(init_ir, dag)

        # test9
        ir = [
            RZ([1], arg_value=[0.1]),
            # ---
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            # ---
            CX([2, 1]),
            RZ([1], arg_value=[0.2]),
            CX([2, 1]),
            # ---
            RZ([1], arg_value=[0.2]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1
        validate_optimize_result(init_ir, dag)

        # test10
        ir = [
            RZ([1], arg_value=[0.1]),
            # ---
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            # ---
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            # ---
            RZ([1], arg_value=[0.2]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1
        validate_optimize_result(init_ir, dag)

        # test11
        ir = [
            RZ([2], arg_value=[0.1]),
            # ---
            CX([1, 2]),
            RZ([2], arg_value=[0.2]),
            CX([1, 2]),
            # ---
            CX([0, 2]),
            RZ([2], arg_value=[0.2]),
            CX([0, 2]),
            # ---
            RZ([2], arg_value=[0.2]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1
        validate_optimize_result(init_ir, dag)

        # test with basis_gates
        ir = [
            RZ([1], arg_value=[0.1]),
            # ---
            H([1]),
            CX([0, 1]),
            H([1]),
            # ---
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            # ---
            RZ([1], arg_value=[0.2]),
        ]
        # q_0: ──────────────────■─────────■───────────────■─────────────
        #      ┌─────────┐┌───┐┌─┴─┐┌───┐┌─┴─┐┌─────────┐┌─┴─┐┌─────────┐
        # q_1: ┤ Rz(0.1) ├┤ H ├┤ X ├┤ H ├┤ X ├┤ Rz(0.2) ├┤ X ├┤ Rz(0.2) ├
        #      └─────────┘└───┘└───┘└───┘└───┘└─────────┘└───┘└─────────┘
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        # will not be optimized, because the first template will be ignored
        cnt = opt.cancel_single_qubit_gates(dag, basis_gates={"cx", "rz"})
        assert cnt == 0
        validate_optimize_result(init_ir, dag)

    def test_cancel_two_qubit_gates(self):
        opt = CliffordRzOptimization()
        # test for control qubit template
        # test1
        ir = [CX([0, 1]), CX([0, 2]), CX([0, 1])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2
        validate_optimize_result(init_ir, dag, num_qubits1=3, num_qubits2=3)

        # test2
        ir = [CX([0, 1]), RZ([0], arg_value=[0.1]), CX([0, 1])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2
        validate_optimize_result(init_ir, dag, num_qubits1=2, num_qubits2=2)

        # test for target qubit template
        # test1
        ir = [CX([0, 2]), CX([1, 2]), CX([0, 2])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2
        validate_optimize_result(init_ir, dag, num_qubits1=3, num_qubits2=3)

        # test2
        ir = [CX([0, 1]), H([1]), CX([1, 2]), H([1]), CX([0, 1])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2
        validate_optimize_result(init_ir, dag)

        # test3
        ir = [CX([0, 1]), X([1]), CX([0, 1])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2
        validate_optimize_result(init_ir, dag)

        # test for combine templates
        # test1
        ir = [
            CX([0, 1]),
            # ---template1
            CX([0, 2]),
            # ---end
            CX([0, 1]),
            CX([0, 1]),
            # ---template2
            H([1]),
            CX([1, 2]),
            H([1]),
            # ---end
            CX([0, 1]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 4
        validate_optimize_result(init_ir, dag)

        # test2
        ir = [
            CX([0, 1]),
            # ---t1
            RZ([0], arg_value=[0.1]),
            # ---end
            CX([0, 1]),
            CX([0, 2]),
            # ---t2
            CX([1, 2]),
            # ---end
            CX([0, 2]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 4
        validate_optimize_result(init_ir, dag)

        # test3
        ir = [
            CX([0, 1]),
            # ---
            CX([0, 2]),
            RZ([0], arg_value=[0.1]),
            CX([0, 3]),
            # ---
            CX([0, 1]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2
        validate_optimize_result(init_ir, dag)

        # test4
        ir = [
            CX([0, 1]),
            # ---
            RZ([0], arg_value=[0.1]),
            RZ([0], arg_value=[0.1]),
            RZ([0], arg_value=[0.1]),
            # ---
            CX([0, 1]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2
        validate_optimize_result(init_ir, dag, num_qubits1=2, num_qubits2=2)

        # test with basis_gates
        ir = [
            CX([0, 1]),
            # ---template1
            CX([0, 2]),
            # ---end
            CX([0, 1]),
            CX([0, 1]),
            # ---template2
            H([1]),
            CX([1, 2]),
            H([1]),
            # ---end
            CX([0, 1]),
        ]
        init_ir = copy.deepcopy(ir)
        # q_0: ──■────■────■────■───────────────────■──
        #      ┌─┴─┐  │  ┌─┴─┐┌─┴─┐┌───┐     ┌───┐┌─┴─┐
        # q_1: ┤ X ├──┼──┤ X ├┤ X ├┤ H ├──■──┤ H ├┤ X ├
        #      └───┘┌─┴─┐└───┘└───┘└───┘┌─┴─┐└───┘└───┘
        # q_2: ─────┤ X ├───────────────┤ X ├──────────
        #           └───┘               └───┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag, basis_gates={"cx"})
        assert cnt == 2
        # the second template will not be optimized
        # q_0: ──■────■───────────────────■──
        #        │  ┌─┴─┐┌───┐     ┌───┐┌─┴─┐
        # q_1: ──┼──┤ X ├┤ H ├──■──┤ H ├┤ X ├
        #      ┌─┴─┐└───┘└───┘┌─┴─┐└───┘└───┘
        # q_2: ┤ X ├──────────┤ X ├──────────
        #      └───┘          └───┘
        validate_optimize_result(init_ir, dag)

    def test_merge_rotations(self):
        opt = CliffordRzOptimization()
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
        init_ir = copy.deepcopy(ir)
        #      ┌───┐           ┌───┐┌─────────┐                  ┌───┐
        # q_0: ┤ H ├───────────┤ X ├┤ Rz(0.3) ├──■─────────■─────┤ H ├────────
        #      ├───┤┌─────────┐└─┬─┘└─────────┘┌─┴─┐     ┌─┴─┐┌──┴───┴──┐┌───┐
        # q_1: ┤ H ├┤ Rz(0.1) ├──■───────■─────┤ X ├──■──┤ X ├┤ Rz(0.4) ├┤ H ├
        #      ├───┤├─────────┤        ┌─┴─┐   ├───┤┌─┴─┐└───┘└─────────┘└───┘
        # q_2: ┤ H ├┤ Rz(0.2) ├────────┤ X ├───┤ H ├┤ X ├─────────────────────
        #      └───┘└─────────┘        └───┘   └───┘└───┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.merge_rotations(dag)
        # TODO: collect_blocks is different from former code
        assert cnt == 0
        validate_optimize_result(init_ir, dag)

        ir = [
            RZ([1], arg_value=[0.1]),
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            RZ([0], arg_value=[0.3]),
            RZ([1], arg_value=[0.4]),
            CX([1, 0]),
        ]
        init_ir = copy.deepcopy(ir)
        #                                      ┌─────────┐┌───┐
        # q_0: ─────────────■───────────────■──┤ Rz(0.3) ├┤ X ├
        #      ┌─────────┐┌─┴─┐┌─────────┐┌─┴─┐├─────────┤└─┬─┘
        # q_1: ┤ Rz(0.1) ├┤ X ├┤ Rz(0.2) ├┤ X ├┤ Rz(0.4) ├──■──
        #      └─────────┘└───┘└─────────┘└───┘└─────────┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.merge_rotations(dag)
        #                                      ┌─────────┐┌───┐
        # q_0: ─────────────■───────────────■──┤ Rz(0.3) ├┤ X ├
        #      ┌─────────┐┌─┴─┐┌─────────┐┌─┴─┐└─────────┘└─┬─┘
        # q_1: ┤ Rz(0.5) ├┤ X ├┤ Rz(0.2) ├┤ X ├─────────────■──
        #      └─────────┘└───┘└─────────┘└───┘
        assert cnt == 1
        rz_gates = []
        for node in dag.op_nodes():
            if node.name == "rz":
                rz_gates.append(node)
        assert np.isclose(rz_gates[0].op.arg_value[0], 0.5)
        assert np.isclose(rz_gates[1].op.arg_value[0], 0.2)
        assert np.isclose(rz_gates[2].op.arg_value[0], 0.3)
        validate_optimize_result(init_ir, dag)

        ir = [
            RZ([1], arg_value=[0.1]),
            X([1]),
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            RZ([0], arg_value=[0.3]),
            RZ([1], arg_value=[0.4]),
            CX([1, 0]),
            RZ([0], arg_value=[0.5]),
        ]
        init_ir = copy.deepcopy(ir)
        #                                           ┌─────────┐┌───┐┌─────────┐
        # q_0: ──────────────────■───────────────■──┤ Rz(0.3) ├┤ X ├┤ Rz(0.5) ├
        #      ┌─────────┐┌───┐┌─┴─┐┌─────────┐┌─┴─┐├─────────┤└─┬─┘└─────────┘
        # q_1: ┤ Rz(0.1) ├┤ X ├┤ X ├┤ Rz(0.2) ├┤ X ├┤ Rz(0.4) ├──■─────────────
        #      └─────────┘└───┘└───┘└─────────┘└───┘└─────────┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.merge_rotations(dag)
        #                                            ┌─────────┐┌───┐
        # q_0: ───────────────────■───────────────■──┤ Rz(0.3) ├┤ X ├
        #      ┌──────────┐┌───┐┌─┴─┐┌─────────┐┌─┴─┐└─────────┘└─┬─┘
        # q_1: ┤ Rz(-0.3) ├┤ X ├┤ X ├┤ Rz(0.7) ├┤ X ├─────────────■──
        #      └──────────┘└───┘└───┘└─────────┘└───┘
        assert cnt == 2
        rz_gates = []
        for node in dag.op_nodes():
            if node.name == "rz":
                rz_gates.append(node)
        assert np.isclose(rz_gates[0].op.arg_value[0], -0.3)
        assert np.isclose(rz_gates[1].op.arg_value[0], 0.7)
        assert np.isclose(rz_gates[2].op.arg_value[0], 0.3)
        validate_optimize_result(init_ir, dag)

        ir = [
            RZ([1], arg_value=[0.1]),
            RZ([2], arg_value=[0.2]),
            CX([1, 0]),
            RZ([0], arg_value=[0.3]),
            CX([1, 2]),
            CX([0, 1]),
            CX([0, 1]),
            RZ([1], arg_value=[0.4]),
        ]
        init_ir = copy.deepcopy(ir)
        #                 ┌───┐┌─────────┐
        # q_0: ───────────┤ X ├┤ Rz(0.3) ├──■────■─────────────
        #      ┌─────────┐└─┬─┘└─────────┘┌─┴─┐┌─┴─┐┌─────────┐
        # q_1: ┤ Rz(0.1) ├──■───────■─────┤ X ├┤ X ├┤ Rz(0.4) ├
        #      ├─────────┤        ┌─┴─┐   └───┘└───┘└─────────┘
        # q_2: ┤ Rz(0.2) ├────────┤ X ├────────────────────────
        #      └─────────┘        └───┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.merge_rotations(dag)
        #                 ┌───┐┌─────────┐
        # q_0: ───────────┤ X ├┤ Rz(0.3) ├──■────■──
        #      ┌─────────┐└─┬─┘└─────────┘┌─┴─┐┌─┴─┐
        # q_1: ┤ Rz(0.5) ├──■───────■─────┤ X ├┤ X ├
        #      ├─────────┤        ┌─┴─┐   └───┘└───┘
        # q_2: ┤ Rz(0.2) ├────────┤ X ├─────────────
        #      └─────────┘        └───┘
        assert cnt == 1
        rz_gates = []
        for node in dag.op_nodes():
            if node.name == "rz":
                rz_gates.append(node)
        assert np.isclose(rz_gates[0].op.arg_value[0], 0.5)
        assert np.isclose(rz_gates[1].op.arg_value[0], 0.2)
        assert np.isclose(rz_gates[2].op.arg_value[0], 0.3)
        validate_optimize_result(init_ir, dag)

        # test with basis_gates
        ir = [
            RZ([1], arg_value=[0.1]),
            X([1]),
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            RZ([0], arg_value=[0.3]),
            RZ([1], arg_value=[0.4]),
            CX([1, 0]),
            RZ([0], arg_value=[0.5]),
        ]
        init_ir = copy.deepcopy(ir)
        #                                           ┌─────────┐┌───┐┌─────────┐
        # q_0: ──────────────────■───────────────■──┤ Rz(0.3) ├┤ X ├┤ Rz(0.5) ├
        #      ┌─────────┐┌───┐┌─┴─┐┌─────────┐┌─┴─┐├─────────┤└─┬─┘└─────────┘
        # q_1: ┤ Rz(0.1) ├┤ X ├┤ X ├┤ Rz(0.2) ├┤ X ├┤ Rz(0.4) ├──■─────────────
        #      └─────────┘└───┘└───┘└─────────┘└───┘└─────────┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.merge_rotations(dag, basis_gates={"rz", "cx"})
        # the first Rz(0.1) will be split by X gate.
        #                                           ┌─────────┐┌───┐
        # q_0: ──────────────────■───────────────■──┤ Rz(0.3) ├┤ X ├
        #      ┌─────────┐┌───┐┌─┴─┐┌─────────┐┌─┴─┐├─────────┤└─┬─┘
        # q_1: ┤ Rz(0.1) ├┤ X ├┤ X ├┤ Rz(0.7) ├┤ X ├┤ Rz(0.4) ├──■──
        #      └─────────┘└───┘└───┘└─────────┘└───┘└─────────┘
        assert cnt == 1
        rz_gates = []
        for node in dag.op_nodes():
            if node.name == "rz":
                rz_gates.append(node)
        assert np.isclose(rz_gates[0].op.arg_value[0], 0.1)
        assert np.isclose(rz_gates[1].op.arg_value[0], 0.7)
        assert np.isclose(rz_gates[2].op.arg_value[0], 0.3)
        assert np.isclose(rz_gates[3].op.arg_value[0], 0.4)
        validate_optimize_result(init_ir, dag)

    def test_parameterize(self):
        ir = [S(targets=[0]), S(targets=[0])]
        dag = DAGCircuit.ir_to_dag(ir)
        dag.parameterize_all_rz()
        nodes = dag.op_nodes()
        assert nodes[0].name == "rz"
        assert nodes[1].name == "rz"
        counts = dag.count_ops()
        assert counts.get("rz", 0) == 2
        assert counts.get("s", 0) == 0

        dag.deparameterize_all_rz()
        nodes = dag.op_nodes()
        assert nodes[0].name == "s"
        assert nodes[1].name == "s"
        counts = dag.count_ops()
        assert counts.get("rz", 0) == 0
        assert counts.get("s", 0) == 2

    def test_optimize(self):
        opt = CliffordRzOptimization()
        ir = [
            H([0]),
            H([1]),
            CX([0, 1]),
            H([0]),
            H([1]),
            S([0]),
            CX([1, 0]),
            CX([0, 2]),
            CX([1, 0]),
            S([0]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        dag = opt.run(dag)
        counts = dag.count_ops()
        assert len(counts) == 2
        assert counts["cx"] == 2
        assert counts["z"] == 1
        validate_optimize_result(init_ir, dag)

        ir = [T([0]), CX([0, 1]), T([0]), CX([1, 2]), X([2]), CX([1, 2])]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        dag = opt.run(dag)
        counts = dag.count_ops()
        assert len(counts) == 3
        assert counts["s"] == 1
        assert counts["cx"] == 1
        assert counts["x"] == 1
        validate_optimize_result(init_ir, dag)

        ir = [
            Z([0]),
            CX([0, 1]),
            Z([0]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        dag = opt.run(dag)
        counts = dag.count_ops()
        assert len(counts) == 1
        assert counts["cx"] == 1
        validate_optimize_result(init_ir, dag)

    def test_random_optimize_by_gates(self):
        num_qubits = 5
        num_gates = 100
        loop_count = 10
        opt_level = 2

        # generate random circuit with gates
        for _ in range(loop_count):
            rcg = RandomCircuitGen()
            ir = rcg.random_circuit_with_gates(num_qubits, num_gates)
            # initial ir
            init_ir = copy.deepcopy(ir)
            init_circ = QuantumCircuit.from_ir(init_ir, num_qubits)
            # after optimized
            opt_ir = optimize(ir, opt_level)
            opt_circ = QuantumCircuit.from_ir(opt_ir, num_qubits)
            res = is_equal(init_circ, opt_circ)
            if not res:
                # print error test cases
                logger.info(ir)
                logger.info(opt_ir)
                logger.info("========")
            assert res

    def test_random_optimize_by_depth(self):
        # generate random circuit with depth
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_depth(
            num_qubits=10, depth=20, max_operands=4, measure=True, reset=True
        )
        assert rcg.num_qubits == 10 and abs(rcg.depth - 20) <= 2
        normal_gates = []
        normal_gates.extend(Constant.SINGLE_QUBIT_GATE_LIST)
        normal_gates.extend(Constant.TWO_QUBIT_GATE_LIST)
        normal_gates.extend(Constant.THREE_QUBIT_GATE_LIST)
        normal_gates.extend(Constant.FOUR_QUBIT_GATE_LIST)
        normal_gates.append(Constant.SINGLE_QUBIT_GATE_RESET)
        normal_gates.append("measure")
        flag = True
        measure_flag = False
        reset_flag = False
        for gate in ir:
            if gate.name not in normal_gates:
                flag = False
                break

            if gate.name == "measure":
                measure_flag = True
            if gate.name == "reset":
                reset_flag = True

        assert flag is True
        assert measure_flag is True
        assert reset_flag is True

        ir = rcg.random_circuit_with_depth(
            num_qubits=10, depth=20, max_operands=2, gate_type=0
        )
        assert rcg.num_qubits == 10 and abs(rcg.depth - 20) <= 2

        ir = rcg.random_circuit_with_depth(num_qubits=0, depth=0)
        assert len(ir) == 0

        with pytest.raises(CircuitException) as e:
            ir = rcg.random_circuit_with_depth(
                num_qubits=2, depth=1, outfile="CHANGELOG.md"
            )
        err_msg = str(e.value)
        assert "Output file has existed." in err_msg

        with pytest.raises(CircuitException) as e:
            ir = rcg.random_circuit_with_depth(
                num_qubits=10, depth=10, max_operands=0
            )
        err_msg = str(e.value)
        assert "Invalid max_operands" in err_msg

        with pytest.raises(CircuitException) as e:
            ir = rcg.random_circuit_with_depth(
                num_qubits=10, depth=10, max_operands=2, gate_type=2
            )
        err_msg = str(e.value)
        assert "Invalid gate_type" in err_msg

    @patch("wy_qcos.transpiler.cmss.circuit.utils.QasmConverter")
    def test_random_circuit_save(self, mock_qasm_converter):
        mock_instance_gates = mock_qasm_converter.return_value
        mock_instance_gates.save.return_value = None
        rcg = RandomCircuitGen()
        ir = rcg.random_circuit_with_gates(
            num_qubits=2, num_gates=2, outfile="output.log"
        )
        assert isinstance(ir, list)

        ir = rcg.random_circuit_with_depth(
            num_qubits=2, depth=2, outfile="output.log"
        )
        assert isinstance(ir, list)
