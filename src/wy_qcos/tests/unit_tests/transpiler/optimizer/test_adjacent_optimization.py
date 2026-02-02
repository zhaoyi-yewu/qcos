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
import numpy as np

from wy_qcos.transpiler.cmss.optimizer.adjacent_optimization import (
    AdjacentPhaseOptPass,
)
from wy_qcos.transpiler.cmss.circuit.dag_circuit import DAGCircuit
from wy_qcos.transpiler.cmss.common.gate_operation import (
    RX,
    RY,
    RZ,
    CRX,
    CRY,
    CRZ,
    U1,
    S,
)
from wy_qcos.tests.unit_tests.transpiler.comm import validate_optimize_result


class TestAdjacentOptimization:
    def test_adjacent_optimization(self):
        opt = AdjacentPhaseOptPass()

        ir = [
            RX([0], [0.1]),
            RX([0], [0.2]),
            RY([1], [0.1]),
            RY([1], [0.2]),
            RZ([0], [0.1]),
            RZ([0], [0.2]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        opt.run(dag)
        nodes = list(dag.topological_op_nodes())
        assert len(nodes) == 3
        assert nodes[0].op.name == "rx"
        assert np.isclose(nodes[0].op.arg_value[0], 0.3)
        assert nodes[1].op.name == "rz"
        assert np.isclose(nodes[1].op.arg_value[0], 0.3)
        assert nodes[2].op.name == "ry"
        assert np.isclose(nodes[2].op.arg_value[0], 0.3)
        validate_optimize_result(init_ir, dag)

        ir = [
            CRX([0, 1], [0.1]),
            CRX([1, 0], [0.2]),
            CRY([0, 1], [0.1]),
            CRY([0, 1], [0.2]),
            CRZ([1, 0], [0.1]),
            CRZ([1, 0], [0.2]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        opt.run(dag)
        nodes = list(dag.topological_op_nodes())
        assert len(nodes) == 4
        assert nodes[0].op.name == "crx"
        assert np.isclose(nodes[0].op.arg_value[0], 0.1)
        assert nodes[1].op.name == "crx"
        assert np.isclose(nodes[1].op.arg_value[0], 0.2)
        assert nodes[2].op.name == "cry"
        assert np.isclose(nodes[2].op.arg_value[0], 0.3)
        assert nodes[3].op.name == "crz"
        assert np.isclose(nodes[3].op.arg_value[0], 0.3)
        validate_optimize_result(init_ir, dag)

        ir = [
            RX([0], [0.1]),
            RX([0], [0.2]),
            S([1]),
            S([1]),
            U1([0], [0.1]),
            U1([0], [0.1]),
            CRY([0, 1], [0.1]),
            CRY([0, 1], [0.2]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        opt.run(dag)
        nodes = list(dag.topological_op_nodes())
        assert len(nodes) == 4
        assert nodes[0].op.name == "rx"
        assert np.isclose(nodes[0].op.arg_value[0], 0.3)
        assert nodes[1].op.name == "u1"
        assert np.isclose(nodes[1].op.arg_value[0], 0.2)
        assert nodes[2].op.name == "z"
        assert nodes[2].op.arg_value == []
        assert nodes[3].op.name == "cry"
        assert np.isclose(nodes[3].op.arg_value[0], 0.3)
        validate_optimize_result(init_ir, dag)

        # test with basis_gates
        ir = [
            RX([0], [0.1]),
            RX([0], [0.2]),
            S([1]),
            S([1]),
            U1([0], [0.1]),
            U1([0], [0.1]),
        ]
        init_ir = copy.deepcopy(ir)
        dag = DAGCircuit.ir_to_dag(ir)
        cnt = opt.run(copy.deepcopy(dag), basis_gates=["rx", "u1"])
        assert cnt == 2
        validate_optimize_result(init_ir, dag)

        cnt = opt.run(copy.deepcopy(dag), basis_gates=["rx", "u1", "rz"])
        assert cnt == 3
        validate_optimize_result(init_ir, dag)
