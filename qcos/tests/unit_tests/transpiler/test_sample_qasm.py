#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate
from qcos.tests.unit_tests.transpiler.comm import read_qasm_from_file
from qcos.tests.unit_tests.transpiler.comm import validate_gate_ir
from qcos.tests.unit_tests.transpiler.comm import validate_non_gate_ir


class TestSampleQasm:
    def test_adder_qasm(self):
        file_path = "../../../samples/qasm/2.0/adder.qasm"
        qasm_data = read_qasm_from_file(file_path)
        if qasm_data is None:
            return

        tree = get_abs_tree(qasm_data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 10
        assert len(ir) == 35
        opt_gates = optimize_gate(ir)
        assert len(opt_gates) == 35
        validate_gate_ir(opt_gates[0], "x", ["1"], 1, True)
        validate_gate_ir(opt_gates[1], "x", ["5"], 1, True)
        validate_gate_ir(opt_gates[2], "x", ["6"], 1, True)
        validate_gate_ir(opt_gates[3], "x", ["7"], 1, True)
        validate_gate_ir(opt_gates[4], "x", ["8"], 1, True)
        validate_gate_ir(opt_gates[5], "cx", ["1", "5"], 2, True)
        validate_gate_ir(opt_gates[6], "cx", ["1", "0"], 2, True)
        validate_gate_ir(opt_gates[7], "ccx", ["0", "5", "1"], 3, True)
        validate_gate_ir(opt_gates[8], "cx", ["2", "6"], 2, True)
        validate_gate_ir(opt_gates[9], "cx", ["2", "1"], 2, True)
        validate_gate_ir(opt_gates[10], "ccx", ["1", "6", "2"], 3, True)
        validate_non_gate_ir(opt_gates[30], "measure", [5], 0)
        validate_non_gate_ir(opt_gates[31], "measure", [6], 0)
        validate_non_gate_ir(opt_gates[32], "measure", [7], 0)
        validate_non_gate_ir(opt_gates[33], "measure", [8], 0)
        validate_non_gate_ir(opt_gates[34], "measure", [9], 0)

    def test_big_adder_qasm(self):
        file_path = "../../../samples/qasm/2.0/bigadder.qasm"
        qasm_data = read_qasm_from_file(file_path)
        if qasm_data is None:
            return

        tree = get_abs_tree(qasm_data)
        assert tree is not None
        q_num, ir = get_ir(tree)
        assert ir is not None
        assert q_num == 18
        assert len(ir) == 69
        opt_gates = optimize_gate(ir)
        assert len(opt_gates) == 69
        validate_gate_ir(opt_gates[0], "x", ["2"], 1, True)
        validate_gate_ir(opt_gates[1], "x", ["10"], 1, True)
        validate_gate_ir(opt_gates[2], "x", ["11"], 1, True)
        validate_gate_ir(opt_gates[3], "x", ["12"], 1, True)
        validate_gate_ir(opt_gates[4], "x", ["13"], 1, True)
        validate_gate_ir(opt_gates[5], "x", ["14"], 1, True)
        validate_gate_ir(opt_gates[6], "x", ["15"], 1, True)
        validate_gate_ir(opt_gates[7], "x", ["16"], 1, True)
        validate_gate_ir(opt_gates[8], "x", ["17"], 1, True)
        validate_gate_ir(opt_gates[9], "x", ["16"], 1, True)
        validate_gate_ir(opt_gates[10], "cx", ["2", "10"], 2, True)
        validate_gate_ir(opt_gates[11], "cx", ["2", "0"], 2, True)
        validate_gate_ir(opt_gates[12], "ccx", ["0", "10", "2"], 3, True)
        validate_non_gate_ir(opt_gates[60], "measure", [10], 0)
        validate_non_gate_ir(opt_gates[61], "measure", [11], 0)
        validate_non_gate_ir(opt_gates[62], "measure", [12], 0)
        validate_non_gate_ir(opt_gates[63], "measure", [13], 0)
        validate_non_gate_ir(opt_gates[64], "measure", [14], 0)
