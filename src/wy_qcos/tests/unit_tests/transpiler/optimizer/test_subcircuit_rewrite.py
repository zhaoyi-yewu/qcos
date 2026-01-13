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

from wy_qcos.transpiler.cmss.common.gate_operation import (
    X,
    H,
    Z,
    RY,
)
from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.optimizer.subcircuit_rewrite import (
    EquivalencePass,
)
from wy_qcos.tests.unit_tests.transpiler.comm import validate_optimize_result


class TestSubcircuitRewrite:
    def test_subcircuit_rewrite(self):
        ir = [H([0]), Z([0]), H([0])]
        dag = DAGCircuit.ir_to_dag(ir)
        opt = EquivalencePass()
        opt.run(dag)
        counts = dag.count_ops()
        assert len(counts) == 1
        assert counts["x"] == 1
        validate_optimize_result(ir, dag)

        ir = [H([0]), X([0]), H([0])]
        dag = DAGCircuit.ir_to_dag(ir)
        opt = EquivalencePass()
        opt.run(dag)
        counts = dag.count_ops()
        assert len(counts) == 1
        assert counts["z"] == 1
        validate_optimize_result(ir, dag)

        ir = [H([0]), X([0]), H([0]), H([1]), Z([1]), H([1])]
        dag = DAGCircuit.ir_to_dag(ir)
        opt = EquivalencePass()
        opt.run(dag)
        nodes = list(dag.topological_op_nodes())
        assert len(nodes) == 2
        assert nodes[0].op.name == "z"
        assert nodes[0].op.targets == [0]
        assert nodes[1].op.name == "x"
        assert nodes[1].op.targets == [1]
        validate_optimize_result(ir, dag)

        ir = [X([1]), RY([1], [0.1]), X([1])]
        dag = DAGCircuit.ir_to_dag(ir)
        opt = EquivalencePass()
        opt.run(dag)
        nodes = list(dag.topological_op_nodes())
        assert len(nodes) == 1
        assert nodes[0].op.arg_value == [-0.1]
        validate_optimize_result(ir, dag)
