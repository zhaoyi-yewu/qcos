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

import numpy as np

from qcos.transpiler.cmss.optimizer.clifford_rz_optimization import (
    CliffordRzOptimization,
)
from qcos.transpiler.cmss.common.gate_operation import (
    RZ,
    X,
    H,
    CX,
    S,
    SDG,
)
from qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit


class TestCliffordRzOptimization:
    def test_reduce_hadamard_gates(self):
        opt = CliffordRzOptimization()

        ir = [H([0]), S([0]), H([0])]
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(dag)
        assert ret == 1
        counts = dag.count_ops()
        assert counts.get("h", 0) == 1
        assert counts.get("s", 0) == 0
        assert counts.get("sdg", 0) == 2

        ir = [H([0]), SDG([0]), H([0])]
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(dag)
        assert ret == 1
        counts = dag.count_ops()
        assert counts.get("h", 0) == 1
        assert counts.get("s", 0) == 2
        assert counts.get("sdg", 0) == 0

        ir = [H([0]), H([1]), CX([0, 1]), H([0]), H([1])]
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(dag)
        assert ret == 4
        counts = dag.count_ops()
        assert counts.get("h", 0) == 0
        assert counts["cx"] == 1

        ir = [H([1]), S([1]), CX([0, 1]), SDG([1]), H([1])]
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(dag)
        assert ret == 2

        ir = [H([1]), SDG([1]), CX([0, 1]), S([1]), H([1])]
        dag = DAGCircuit.ir_to_dag(ir)
        ret = opt.reduce_hadamard_gates(dag)
        assert ret == 2

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
        # q_0: ─────────────────────────────■──────────────────
        #      ┌─────────┐┌─────────┐┌───┐┌─┴─┐┌───┐┌─────────┐
        # q_1: ┤ Rz(0.1) ├┤ Rz(0.1) ├┤ H ├┤ X ├┤ H ├┤ Rz(0.1) ├
        #      └─────────┘└─────────┘└───┘└───┘└───┘└─────────┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 2

        # test2
        ir = [
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
        ]
        # q_0: ─────────────■───────────────■─────────────
        #      ┌─────────┐┌─┴─┐┌─────────┐┌─┴─┐┌─────────┐
        # q_1: ┤ Rz(0.2) ├┤ X ├┤ Rz(0.2) ├┤ X ├┤ Rz(0.2) ├
        #      └─────────┘└───┘└─────────┘└───┘└─────────┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1

        # test3
        ir = [RZ([0], arg_value=[0.3]), CX([0, 1]), RZ([0], arg_value=[0.3])]
        #      ┌─────────┐     ┌─────────┐
        # q_0: ┤ Rz(0.3) ├──■──┤ Rz(0.3) ├
        #      └─────────┘┌─┴─┐└─────────┘
        # q_1: ───────────┤ X ├───────────
        #                 └───┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1

        # test4
        ir = [
            RZ([0], arg_value=[0.1]),
            CX([1, 0]),
            CX([0, 2]),
            CX([1, 0]),
            RZ([0], arg_value=[0.1]),
        ]
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

        # test5
        ir = [
            RZ([0], arg_value=[0.1]),
            H([0]),
            X([0]),
            H([0]),
            RZ([0], arg_value=[0.2]),
        ]
        #    ┌─────────┐┌───┐┌───┐┌───┐┌─────────┐
        # q: ┤ Rz(0.1) ├┤ H ├┤ X ├┤ H ├┤ Rz(0.2) ├
        #    └─────────┘└───┘└───┘└───┘└─────────┘
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1

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
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1

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
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1

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
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1

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
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1

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
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1

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
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_single_qubit_gates(dag)
        assert cnt == 1

    def test_cancel_two_qubit_gates(self):
        opt = CliffordRzOptimization()
        # test for control qubit template
        # test1
        ir = [CX([0, 1]), CX([0, 2]), CX([0, 1])]
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2

        # test2
        ir = [CX([0, 1]), RZ([0], arg_value=[0.1]), CX([0, 1])]
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2

        # test for target qubit template
        # test1
        ir = [CX([0, 2]), CX([1, 2]), CX([0, 2])]
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2

        # test2
        ir = [CX([0, 1]), H([1]), CX([1, 2]), H([1]), CX([0, 1])]
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2

        # test3
        ir = [CX([0, 1]), X([1]), CX([0, 1])]
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2

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
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 4

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
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 4

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
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2

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
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.cancel_two_qubit_gates(dag)
        assert cnt == 2

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

        ir = [
            RZ([1], arg_value=[0.1]),
            CX([0, 1]),
            RZ([1], arg_value=[0.2]),
            CX([0, 1]),
            RZ([0], arg_value=[0.3]),
            RZ([1], arg_value=[0.4]),
            CX([1, 0]),
        ]
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
