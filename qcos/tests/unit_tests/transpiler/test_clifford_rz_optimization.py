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
