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

import time

from qcos.transpiler.cmss.compiler.decomposer import decompose_gates
from qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate
from qcos.tests.unit_tests.transpiler.comm import read_qasm_from_file
from qcos.tests.unit_tests.transpiler.comm import validate_gate_ir


class TestPerformance:
    def test_compile_performance(self):
        file_path = "../../../samples/qasm/3.0/benchmark/100bits_50000d.qasm"
        qasm_data = read_qasm_from_file(file_path)
        if qasm_data is None:
            return

        start = time.time()
        tree = get_abs_tree(qasm_data)
        abs_end = time.time()
        print(f"get_abs_tree use {abs_end - start} seconds")
        assert tree is not None

        cir = get_ir(tree)
        ir_end = time.time()
        print(f"get_ir use {ir_end - abs_end} seconds")
        gates_list = cir.get_operations()
        assert len(gates_list) == 5000000
        validate_gate_ir(gates_list[0], "rx", ["0"], 1, False)
        validate_gate_ir(gates_list[99], "rx", ["99"], 1, False)

        optimized_ir = optimize_gate(gates_list)
        opt_end1 = time.time()
        print(f"optimize ir use {opt_end1 - ir_end} seconds")
        assert optimized_ir is not None
        assert len(optimized_ir) == 5000000
        validate_gate_ir(optimized_ir[0], "rx", ["0"], 1, False)
        validate_gate_ir(optimized_ir[99], "rx", ["99"], 1, False)

        transpiled_gates = decompose_gates(optimized_ir)
        decompose_end = time.time()
        print(f"decompose gates use {decompose_end - ir_end} seconds")
        assert transpiled_gates is not None
        assert len(transpiled_gates) == 5000000
        validate_gate_ir(transpiled_gates[0], "rx", ["0"], 1, False)
        validate_gate_ir(transpiled_gates[99], "rx", ["99"], 1, False)

        # 针对分解后的ir进行优化，
        # 主要是针对分解后可能存在的连续两个相同的旋转门
        optimized_gates = optimize_gate(transpiled_gates)
        end = time.time()
        assert optimized_gates is not None
        assert len(optimized_gates) == 5000000
        validate_gate_ir(optimized_gates[0], "rx", ["0"], 1, False)
        validate_gate_ir(optimized_gates[99], "rx", ["99"], 1, False)
        print(f"optimize basic gate use {end - decompose_end} seconds")
        print(f"whole procedure use {end - start} seconds")
