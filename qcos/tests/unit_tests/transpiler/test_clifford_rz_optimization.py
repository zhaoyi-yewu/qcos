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
