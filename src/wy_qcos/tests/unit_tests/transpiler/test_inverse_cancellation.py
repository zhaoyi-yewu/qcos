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

from wy_qcos.transpiler.cmss.optimizer.inverse_cancellation import (
    InverseCancellation,
)
from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.common.gate_operation import (
    H,
    CX,
    S,
    SDG,
    X,
    Y,
    Z,
    SWAP,
    T,
    TDG,
    CZ,
)


class TestInverseCancellation:
    def test_self_inverse_h(self):
        optimizer = InverseCancellation([H()])
        ir = [H([0]), H([0]), H([1]), H([1]), H([1])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts["h"] == 1

        ir = [H([0]), H([1])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts.get("h", 0) == 2

    def test_self_inverse_cx(self):
        optimizer = InverseCancellation([CX()])
        ir = [CX([0, 1]), CX([0, 1])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts.get("cx", 0) == 0

        ir = [CX([0, 1]), CX([0, 1]), CX([0, 1])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts.get("cx", 0) == 1

        ir = [CX([0, 1]), CX([1, 0])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts.get("cx", 0) == 2

    def test_self_inverse_cx_h(self):
        optimizer = InverseCancellation([H(), CX()])
        ir = [H([0]), H([0]), H([1]), CX([0, 1]), CX([0, 1]), H([1])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts.get("cx", 0) == 0
        assert counts.get("h", 0) == 2

    def test_inverse_s_sdg(self):
        optimizer = InverseCancellation([(S(), SDG())])
        ir = [S([0]), SDG([0])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts.get("s", 0) == 0
        assert counts.get("sdg", 0) == 0

        ir = [SDG([0]), S([0])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts.get("s", 0) == 0
        assert counts.get("sdg", 0) == 0

        ir = [S([0]), SDG([1])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts.get("s", 0) == 1
        assert counts.get("sdg", 0) == 1

        ir = [S([0]), H([0]), SDG([0])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts.get("s", 0) == 1
        assert counts.get("sdg", 0) == 1
        assert counts.get("h", 0) == 1

    def test_inverse_t_tdg(self):
        optimizer = InverseCancellation([(T(), TDG())])
        ir = [T([0]), TDG([0])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()

        assert counts.get("t", 0) == 0
        assert counts.get("tdg", 0) == 0

        ir = [TDG([0]), T([0])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()

        assert counts.get("t", 0) == 0
        assert counts.get("tdg", 0) == 0

    def test_self_inverse_pauli(self):
        optimizer = InverseCancellation([X(), Y(), Z()])
        ir = [
            X([0]),
            X([0]),
            Y([1]),
            Y([1]),
            Z([2]),
            Z([2]),
            Z([2]),
        ]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()

        assert counts.get("x", 0) == 0
        assert counts.get("y", 0) == 0
        assert counts.get("z", 0) == 1

    def test_self_inverse_swap(self):
        optimizer = InverseCancellation([SWAP()])
        ir = [
            SWAP([0, 1]),
            SWAP([0, 1]),
            SWAP([0, 1]),
        ]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts.get("swap", 0) == 1

    def test_self_inverse_cz(self):
        optimizer = InverseCancellation([CZ()])
        ir = [CZ([0, 1]), CZ([0, 1])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts.get("cz", 0) == 0

        ir = [CZ([0, 1]), CZ([1, 0])]
        dag = DAGCircuit.ir_to_dag(ir)
        new_dag = optimizer.run(dag)
        counts = new_dag.count_ops()
        assert counts.get("cz", 0) == 2
