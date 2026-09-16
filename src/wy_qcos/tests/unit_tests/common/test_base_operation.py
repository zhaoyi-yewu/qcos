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

import math
import pytest

from wy_qcos.common.cmss.base_operation import BaseOperation, OperationType


class TestBaseOperation:
    def test_init_single_qubit_no_param(self):
        op = BaseOperation("h", targets=[0])
        assert op.name == "h"
        assert op.targets == [0]
        assert op.arg_value == []
        assert op.operation_type == OperationType.SINGLE_QUBIT_OPERATION.value

    def test_init_single_qubit_with_param(self):
        op = BaseOperation("rx", targets=[1], arg_value=[math.pi])
        assert op.name == "rx"
        assert op.targets == [1]
        assert op.arg_value == [math.pi]

    def test_to_openqasm_single_qubit_no_param(self):
        op = BaseOperation("h", targets=[0])
        assert op.to_openqasm() == "h q[0];"

    def test_to_openqasm_single_qubit_with_param(self):
        op = BaseOperation("rx", targets=[1], arg_value=[math.pi / 2])
        assert op.to_openqasm() == "rx(1.5707963267948966) q[1];"

    def test_to_openqasm_multi_qubit_no_space_after_comma(self):
        op = BaseOperation("cx", targets=[0, 1])
        assert op.to_openqasm() == "cx q[0],q[1];"

    def test_to_openqasm_multi_param_no_space_after_comma(self):
        op = BaseOperation(
            "u3", targets=[0], arg_value=[math.pi / 2, math.pi / 4, 0.5]
        )
        assert (
            op.to_openqasm()
            == "u3(1.5707963267948966,0.7853981633974483,0.5) q[0];"
        )

    def test_to_openqasm_targets_empty_raises(self):
        op = BaseOperation("h", targets=[])
        with pytest.raises(ValueError, match="targets cannot be empty"):
            op.to_openqasm()

    def test_to_openqasm_sync_to_barrier(self):
        op = BaseOperation("sync", targets=[0, 1, 2])
        assert op.to_openqasm() == "barrier q[0],q[1],q[2];"

    def test_to_openqasm_custom_qubit_prefix(self):
        op = BaseOperation("x", targets=[0])
        assert op.to_openqasm(qubit_prefix="r") == "x r[0];"

    def test_to_openqasm_triple_qubit_no_space(self):
        op = BaseOperation("ccx", targets=[0, 1, 2])
        assert op.to_openqasm() == "ccx q[0],q[1],q[2];"

    def test_to_openqasm_multi_qubit_and_param_no_space(self):
        op = BaseOperation(
            "u3", targets=[0, 1], arg_value=[math.pi, 0.5, 0.25]
        )
        expected = "u3(3.141592653589793,0.5,0.25) q[0],q[1];"
        assert op.to_openqasm() == expected

    def test_to_openqasm_sync_no_space(self):
        op = BaseOperation("sync", targets=[0, 1, 2, 3])
        assert op.to_openqasm() == "barrier q[0],q[1],q[2],q[3];"

    def test_to_openqasm_measure_no_space(self):
        op = BaseOperation("measure", targets=[0, 1])
        assert op.to_openqasm() == "measure q[0],q[1];"

    def test_to_openqasm_reset_no_space(self):
        op = BaseOperation("reset", targets=[0])
        assert op.to_openqasm() == "reset q[0];"

    def test_to_openqasm_no_space_in_arg_str(self):
        """验证 arg_str 中逗号后没有空格."""
        op = BaseOperation(
            "rzz", targets=[0, 1], arg_value=[0.1, 0.2, 0.3, 0.4]
        )
        qasm = op.to_openqasm()
        # 参数部分不应包含 ", " (逗号后跟空格)
        assert ", " not in qasm

    def test_to_openqasm_no_space_in_targets_str(self):
        """验证 targets_str 中逗号后没有空格."""
        op = BaseOperation("h", targets=[0, 1, 2, 3, 4])
        qasm = op.to_openqasm()
        # 量子比特部分不应包含 ", " (逗号后跟空格)
        assert ", " not in qasm
