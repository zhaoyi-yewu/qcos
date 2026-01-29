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

import pytest
import numpy as np

from wy_qcos.transpiler.cmss.decomposer.decomposer import Decomposer
from wy_qcos.transpiler.cmss.common.gate_operation import create_gate
from wy_qcos.tests.unit_tests.transpiler.comm import (
    validate_gate_ir,
    validate_ir_equals,
    validate_gates_in_targets,
)
from wy_qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from wy_qcos.tests.unit_tests.transpiler.comm import read_qasm_from_file
from wy_qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
class TestDecomposer:
    def test_decompose_basis_only(self):
        d = Decomposer()
        source = [
            create_gate("rx", [0], [np.pi]),
            create_gate("ry", [0], [np.pi]),
            create_gate("rz", [0], [np.pi]),
            create_gate("cx", [0, 1], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)

        validate_gate_ir(result[0], "rx", [0], 1, False)
        validate_gate_ir(result[1], "ry", [0], 1, False)
        validate_gate_ir(result[2], "rz", [0], 1, False)
        validate_gate_ir(result[3], "cx", [0, 1], 2, True)

        validate_ir_equals(source, result)

    def test_decompose_h_gate(self):
        d = Decomposer()
        source = [
            create_gate("h", [0], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)

        assert len(result) == 2

        validate_gate_ir(result[0], "ry", [0], 1, False)
        validate_gate_ir(result[1], "rx", [0], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_x_gate(self):
        d = Decomposer()
        source = [
            create_gate("x", [0], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 1

        validate_gate_ir(result[0], "rx", [0], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_y_gate(self):
        d = Decomposer()
        source = [
            create_gate("y", [0], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 1

        validate_gate_ir(result[0], "ry", [0], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_z_gate(self):
        d = Decomposer()
        source = [
            create_gate("z", [0], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 1

        validate_gate_ir(result[0], "rz", [0], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_s_gate(self):
        d = Decomposer()
        source = [
            create_gate("s", [0], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 1

        validate_gate_ir(result[0], "rz", [0], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_p_gate(self):
        d = Decomposer()
        source = [
            create_gate("p", [0], [np.pi]),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 1

        validate_gate_ir(result[0], "rz", [0], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_sdg_gate(self):
        d = Decomposer()
        source = [
            create_gate("sdg", [0], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 1

        validate_gate_ir(result[0], "rz", [0], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_t_gate(self):
        d = Decomposer()
        source = [
            create_gate("t", [0], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 1

        validate_gate_ir(result[0], "rz", [0], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_tdg_gate(self):
        d = Decomposer()
        source = [
            create_gate("tdg", [0], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 1

        validate_gate_ir(result[0], "rz", [0], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_sx_gate(self):
        d = Decomposer()
        source = [
            create_gate("sx", [0], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 1

        validate_gate_ir(result[0], "rx", [0], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_sxdg_gate(self):
        d = Decomposer()
        source = [
            create_gate("sxdg", [0], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 1

        validate_gate_ir(result[0], "rx", [0], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_cy_gate(self):
        d = Decomposer()
        source = [
            create_gate("cy", [0, 1], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 3

        validate_gate_ir(result[0], "rz", [1], 1, False)
        validate_gate_ir(result[1], "cx", [0, 1], 2, True)
        validate_gate_ir(result[2], "rz", [1], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_cz_gate(self):
        d = Decomposer()
        source = [
            create_gate("cz", [0, 1], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 5

        validate_gate_ir(result[0], "ry", [1], 1, False)
        validate_gate_ir(result[1], "rx", [1], 1, False)
        validate_gate_ir(result[2], "cx", [0, 1], 2, True)
        validate_gate_ir(result[3], "ry", [1], 1, False)
        validate_gate_ir(result[4], "rx", [1], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_ch_gate(self):
        d = Decomposer()
        source = [
            create_gate("ch", [0, 1], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 9

        validate_gate_ir(result[0], "rz", [1], 1, False)
        validate_gate_ir(result[1], "ry", [1], 1, False)
        validate_gate_ir(result[2], "rx", [1], 1, False)
        validate_gate_ir(result[3], "rz", [1], 1, False)
        validate_gate_ir(result[4], "cx", [0, 1], 2, True)
        validate_gate_ir(result[5], "rz", [1], 1, False)
        validate_gate_ir(result[6], "ry", [1], 1, False)
        validate_gate_ir(result[7], "rx", [1], 1, False)
        validate_gate_ir(result[8], "rz", [1], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_swap_gate(self):
        d = Decomposer()
        source = [
            create_gate("swap", [0, 1], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 3

        validate_gate_ir(result[0], "cx", [0, 1], 2, True)
        validate_gate_ir(result[1], "cx", [1, 0], 2, True)
        validate_gate_ir(result[2], "cx", [0, 1], 2, True)

        validate_ir_equals(source, result)

    def test_decompose_crx_gate(self):
        d = Decomposer()
        source = [
            create_gate("crx", [0, 1], [np.pi]),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 6

        validate_gate_ir(result[0], "rz", [1], 1, False)
        validate_gate_ir(result[1], "cx", [0, 1], 2, True)
        validate_gate_ir(result[2], "ry", [1], 1, False)
        validate_gate_ir(result[3], "cx", [0, 1], 2, True)
        validate_gate_ir(result[4], "ry", [1], 1, False)
        validate_gate_ir(result[5], "rz", [1], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_cry_gate(self):
        d = Decomposer()
        source = [
            create_gate("cry", [0, 1], [np.pi]),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 4

        validate_gate_ir(result[0], "ry", [1], 1, False)
        validate_gate_ir(result[1], "cx", [0, 1], 2, True)
        validate_gate_ir(result[2], "ry", [1], 1, False)
        validate_gate_ir(result[3], "cx", [0, 1], 2, True)

        validate_ir_equals(source, result)

    def test_decompose_crz_gate(self):
        d = Decomposer()
        source = [
            create_gate("crz", [0, 1], [np.pi]),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 4

        validate_gate_ir(result[0], "rz", [1], 1, False)
        validate_gate_ir(result[1], "cx", [0, 1], 2, True)
        validate_gate_ir(result[2], "rz", [1], 1, False)
        validate_gate_ir(result[3], "cx", [0, 1], 2, True)

        validate_ir_equals(source, result)

    def test_decompose_cu1_gate(self):
        d = Decomposer()
        source = [
            create_gate("cu1", [0, 1], [np.pi]),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 5

        validate_gate_ir(result[0], "rz", [0], 1, False)
        validate_gate_ir(result[1], "cx", [0, 1], 2, True)
        validate_gate_ir(result[2], "rz", [1], 1, False)
        validate_gate_ir(result[3], "cx", [0, 1], 2, True)
        validate_gate_ir(result[4], "rz", [1], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_cp_gate(self):
        d = Decomposer()
        source = [
            create_gate("cp", [0, 1], [np.pi]),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 5

        validate_gate_ir(result[0], "rz", [0], 1, False)
        validate_gate_ir(result[1], "cx", [0, 1], 2, True)
        validate_gate_ir(result[2], "rz", [1], 1, False)
        validate_gate_ir(result[3], "cx", [0, 1], 2, True)
        validate_gate_ir(result[4], "rz", [1], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_cu3_gate(self):
        d = Decomposer()
        source = [
            create_gate("cu3", [0, 1], [np.pi, np.pi, np.pi]),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 14

        validate_gate_ir(result[0], "rz", [0], 1, False)
        validate_gate_ir(result[1], "rz", [1], 1, False)
        validate_gate_ir(result[2], "cx", [0, 1], 2, True)
        validate_gate_ir(result[3], "rz", [1], 1, False)
        validate_gate_ir(result[4], "rx", [1], 1, False)
        validate_gate_ir(result[5], "rz", [1], 1, False)
        validate_gate_ir(result[6], "rx", [1], 1, False)
        validate_gate_ir(result[7], "rz", [1], 1, False)
        validate_gate_ir(result[8], "cx", [0, 1], 2, True)
        validate_gate_ir(result[9], "rz", [1], 1, False)
        validate_gate_ir(result[10], "rx", [1], 1, False)
        validate_gate_ir(result[11], "rz", [1], 1, False)
        validate_gate_ir(result[12], "rx", [1], 1, False)
        validate_gate_ir(result[13], "rz", [1], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_csx_gate(self):
        d = Decomposer()
        source = [
            create_gate("csx", [0, 1], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 9

        validate_gate_ir(result[0], "ry", [1], 1, False)
        validate_gate_ir(result[1], "rx", [1], 1, False)
        validate_gate_ir(result[2], "rz", [0], 1, False)
        validate_gate_ir(result[3], "cx", [0, 1], 2, True)
        validate_gate_ir(result[4], "rz", [1], 1, False)
        validate_gate_ir(result[5], "cx", [0, 1], 2, True)
        validate_gate_ir(result[6], "rz", [1], 1, False)
        validate_gate_ir(result[7], "ry", [1], 1, False)
        validate_gate_ir(result[8], "rx", [1], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_cu_gate(self):
        d = Decomposer()
        source = [
            create_gate("cu", [0, 1], [np.pi, np.pi, np.pi, np.pi]),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 15

        validate_gate_ir(result[0], "rz", [0], 1, False)
        validate_gate_ir(result[1], "rz", [0], 1, False)
        validate_gate_ir(result[2], "rz", [1], 1, False)
        validate_gate_ir(result[3], "cx", [0, 1], 2, True)
        validate_gate_ir(result[4], "rz", [1], 1, False)
        validate_gate_ir(result[5], "rx", [1], 1, False)
        validate_gate_ir(result[6], "rz", [1], 1, False)
        validate_gate_ir(result[7], "rx", [1], 1, False)
        validate_gate_ir(result[8], "rz", [1], 1, False)
        validate_gate_ir(result[9], "cx", [0, 1], 2, True)
        validate_gate_ir(result[10], "rz", [1], 1, False)
        validate_gate_ir(result[11], "rx", [1], 1, False)
        validate_gate_ir(result[12], "rz", [1], 1, False)
        validate_gate_ir(result[13], "rx", [1], 1, False)
        validate_gate_ir(result[14], "rz", [1], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_rxx_gate(self):
        d = Decomposer()
        source = [
            create_gate("rxx", [0, 1], [np.pi]),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 11

        validate_gate_ir(result[0], "ry", [0], 1, False)
        validate_gate_ir(result[1], "rx", [0], 1, False)
        validate_gate_ir(result[2], "ry", [1], 1, False)
        validate_gate_ir(result[3], "rx", [1], 1, False)
        validate_gate_ir(result[4], "cx", [0, 1], 2, True)
        validate_gate_ir(result[5], "rz", [1], 1, False)
        validate_gate_ir(result[6], "cx", [0, 1], 2, True)
        validate_gate_ir(result[7], "ry", [0], 1, False)
        validate_gate_ir(result[8], "rx", [0], 1, False)
        validate_gate_ir(result[9], "ry", [1], 1, False)
        validate_gate_ir(result[10], "rx", [1], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_rzz_gate(self):
        d = Decomposer()
        source = [
            create_gate("rzz", [0, 1], [np.pi]),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 3

        validate_gate_ir(result[0], "cx", [0, 1], 2, True)
        validate_gate_ir(result[1], "rz", [1], 1, False)
        validate_gate_ir(result[2], "cx", [0, 1], 2, True)

        validate_ir_equals(source, result)

    def test_decompose_ccx_gate(self):
        d = Decomposer()
        source = [
            create_gate("ccx", [0, 1, 2], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 17

        validate_gate_ir(result[0], "ry", [2], 1, False)
        validate_gate_ir(result[1], "rx", [2], 1, False)
        validate_gate_ir(result[2], "cx", [1, 2], 2, True)
        validate_gate_ir(result[3], "rz", [2], 1, False)
        validate_gate_ir(result[4], "cx", [0, 2], 2, True)
        validate_gate_ir(result[5], "rz", [2], 1, False)
        validate_gate_ir(result[6], "cx", [1, 2], 2, True)
        validate_gate_ir(result[7], "rz", [2], 1, False)
        validate_gate_ir(result[8], "cx", [0, 2], 2, True)
        validate_gate_ir(result[9], "rz", [1], 1, False)
        validate_gate_ir(result[10], "rz", [2], 1, False)
        validate_gate_ir(result[11], "ry", [2], 1, False)
        validate_gate_ir(result[12], "rx", [2], 1, False)
        validate_gate_ir(result[13], "cx", [0, 1], 2, True)
        validate_gate_ir(result[14], "rz", [0], 1, False)
        validate_gate_ir(result[15], "rz", [1], 1, False)
        validate_gate_ir(result[16], "cx", [0, 1], 2, True)

        validate_ir_equals(source, result)

    def test_decompose_cswap_gate(self):
        d = Decomposer()
        source = [
            create_gate("cswap", [0, 1, 2], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 19

        validate_gate_ir(result[0], "cx", [2, 1], 2, True)
        validate_gate_ir(result[1], "ry", [2], 1, False)
        validate_gate_ir(result[2], "rx", [2], 1, False)
        validate_gate_ir(result[3], "cx", [1, 2], 2, True)
        validate_gate_ir(result[4], "rz", [2], 1, False)
        validate_gate_ir(result[5], "cx", [0, 2], 2, True)
        validate_gate_ir(result[6], "rz", [2], 1, False)
        validate_gate_ir(result[7], "cx", [1, 2], 2, True)
        validate_gate_ir(result[8], "rz", [2], 1, False)
        validate_gate_ir(result[9], "cx", [0, 2], 2, True)
        validate_gate_ir(result[10], "rz", [1], 1, False)
        validate_gate_ir(result[11], "rz", [2], 1, False)
        validate_gate_ir(result[12], "ry", [2], 1, False)
        validate_gate_ir(result[13], "rx", [2], 1, False)
        validate_gate_ir(result[14], "cx", [0, 1], 2, True)
        validate_gate_ir(result[15], "rz", [0], 1, False)
        validate_gate_ir(result[16], "rz", [1], 1, False)
        validate_gate_ir(result[17], "cx", [0, 1], 2, True)
        validate_gate_ir(result[18], "cx", [2, 1], 2, True)

        validate_ir_equals(source, result)

    def test_decompose_rccx_gate(self):
        d = Decomposer()
        source = [
            create_gate("rccx", [0, 1, 2], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 11

        validate_gate_ir(result[0], "ry", [2], 1, False)
        validate_gate_ir(result[1], "rx", [2], 1, False)
        validate_gate_ir(result[2], "rz", [2], 1, False)
        validate_gate_ir(result[3], "cx", [1, 2], 2, True)
        validate_gate_ir(result[4], "rz", [2], 1, False)
        validate_gate_ir(result[5], "cx", [0, 2], 2, True)
        validate_gate_ir(result[6], "rz", [2], 1, False)
        validate_gate_ir(result[7], "cx", [1, 2], 2, True)
        validate_gate_ir(result[8], "rz", [2], 1, False)
        validate_gate_ir(result[9], "ry", [2], 1, False)
        validate_gate_ir(result[10], "rx", [2], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_rc3x_gate(self):
        d = Decomposer()
        source = [
            create_gate("rc3x", [0, 1, 2, 3], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 34

        validate_gate_ir(result[0], "rz", [3], 1, False)
        validate_gate_ir(result[1], "rx", [3], 1, False)
        validate_gate_ir(result[2], "rz", [3], 1, False)
        validate_gate_ir(result[3], "rx", [3], 1, False)
        validate_gate_ir(result[4], "rz", [3], 1, False)

        validate_gate_ir(result[5], "rz", [3], 1, False)
        validate_gate_ir(result[6], "cx", [2, 3], 2, True)
        validate_gate_ir(result[7], "rz", [3], 1, False)

        validate_gate_ir(result[8], "rz", [3], 1, False)
        validate_gate_ir(result[9], "rx", [3], 1, False)
        validate_gate_ir(result[10], "rz", [3], 1, False)
        validate_gate_ir(result[11], "rx", [3], 1, False)
        validate_gate_ir(result[12], "rz", [3], 1, False)

        validate_gate_ir(result[13], "cx", [0, 3], 2, True)

        validate_gate_ir(result[14], "rz", [3], 1, False)
        validate_gate_ir(result[15], "cx", [1, 3], 2, True)
        validate_gate_ir(result[16], "rz", [3], 1, False)
        validate_gate_ir(result[17], "cx", [0, 3], 2, True)
        validate_gate_ir(result[18], "rz", [3], 1, False)
        validate_gate_ir(result[19], "cx", [1, 3], 2, True)
        validate_gate_ir(result[20], "rz", [3], 1, False)

        validate_gate_ir(result[21], "rz", [3], 1, False)
        validate_gate_ir(result[22], "rx", [3], 1, False)
        validate_gate_ir(result[23], "rz", [3], 1, False)
        validate_gate_ir(result[24], "rx", [3], 1, False)
        validate_gate_ir(result[25], "rz", [3], 1, False)

        validate_gate_ir(result[26], "rz", [3], 1, False)
        validate_gate_ir(result[27], "cx", [2, 3], 2, True)
        validate_gate_ir(result[28], "rz", [3], 1, False)

        validate_gate_ir(result[29], "rz", [3], 1, False)
        validate_gate_ir(result[30], "rx", [3], 1, False)
        validate_gate_ir(result[31], "rz", [3], 1, False)
        validate_gate_ir(result[32], "rx", [3], 1, False)
        validate_gate_ir(result[33], "rz", [3], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_c3x_gate(self):
        d = Decomposer()
        source = [
            create_gate("c3x", [0, 1, 2, 3], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)

        assert len(result) == 33

        validate_gate_ir(result[0], "ry", [3], 1, False)
        validate_gate_ir(result[1], "rx", [3], 1, False)

        validate_gate_ir(result[2], "rz", [0], 1, False)
        validate_gate_ir(result[3], "rz", [1], 1, False)
        validate_gate_ir(result[4], "rz", [2], 1, False)
        validate_gate_ir(result[5], "rz", [3], 1, False)

        validate_gate_ir(result[6], "cx", [0, 1], 2, True)
        validate_gate_ir(result[7], "rz", [1], 1, False)
        validate_gate_ir(result[8], "cx", [0, 1], 2, True)

        validate_gate_ir(result[9], "cx", [1, 2], 2, True)
        validate_gate_ir(result[10], "rz", [2], 1, False)
        validate_gate_ir(result[11], "cx", [0, 2], 2, True)
        validate_gate_ir(result[12], "rz", [2], 1, False)
        validate_gate_ir(result[13], "cx", [1, 2], 2, True)
        validate_gate_ir(result[14], "rz", [2], 1, False)
        validate_gate_ir(result[15], "cx", [0, 2], 2, True)

        validate_gate_ir(result[16], "cx", [2, 3], 2, True)
        validate_gate_ir(result[17], "rz", [3], 1, False)
        validate_gate_ir(result[18], "cx", [1, 3], 2, True)
        validate_gate_ir(result[19], "rz", [3], 1, False)
        validate_gate_ir(result[20], "cx", [2, 3], 2, True)
        validate_gate_ir(result[21], "rz", [3], 1, False)
        validate_gate_ir(result[22], "cx", [0, 3], 2, True)
        validate_gate_ir(result[23], "rz", [3], 1, False)
        validate_gate_ir(result[24], "cx", [2, 3], 2, True)
        validate_gate_ir(result[25], "rz", [3], 1, False)
        validate_gate_ir(result[26], "cx", [1, 3], 2, True)
        validate_gate_ir(result[27], "rz", [3], 1, False)
        validate_gate_ir(result[28], "cx", [2, 3], 2, True)
        validate_gate_ir(result[29], "rz", [3], 1, False)
        validate_gate_ir(result[30], "cx", [0, 3], 2, True)

        validate_gate_ir(result[31], "ry", [3], 1, False)
        validate_gate_ir(result[32], "rx", [3], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_c3sqrtx_gate(self):
        d = Decomposer()
        source = [
            create_gate("c3sqrtx", [0, 1, 2, 3], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)

        assert len(result) == 69

        validate_gate_ir(result[0], "ry", [3], 1, False)
        validate_gate_ir(result[1], "rx", [3], 1, False)

        validate_gate_ir(result[2], "rz", [0], 1, False)
        validate_gate_ir(result[3], "cx", [0, 3], 2, True)
        validate_gate_ir(result[4], "rz", [3], 1, False)
        validate_gate_ir(result[5], "cx", [0, 3], 2, True)
        validate_gate_ir(result[6], "rz", [3], 1, False)

        validate_gate_ir(result[7], "ry", [3], 1, False)
        validate_gate_ir(result[8], "rx", [3], 1, False)

        validate_gate_ir(result[9], "cx", [0, 1], 2, True)

        validate_gate_ir(result[10], "ry", [3], 1, False)
        validate_gate_ir(result[11], "rx", [3], 1, False)
        validate_gate_ir(result[12], "rz", [1], 1, False)
        validate_gate_ir(result[13], "cx", [1, 3], 2, True)
        validate_gate_ir(result[14], "rz", [3], 1, False)
        validate_gate_ir(result[15], "cx", [1, 3], 2, True)
        validate_gate_ir(result[16], "rz", [3], 1, False)

        validate_gate_ir(result[17], "ry", [3], 1, False)
        validate_gate_ir(result[18], "rx", [3], 1, False)

        validate_gate_ir(result[19], "cx", [0, 1], 2, True)

        validate_gate_ir(result[20], "ry", [3], 1, False)
        validate_gate_ir(result[21], "rx", [3], 1, False)
        validate_gate_ir(result[22], "rz", [1], 1, False)
        validate_gate_ir(result[23], "cx", [1, 3], 2, True)
        validate_gate_ir(result[24], "rz", [3], 1, False)
        validate_gate_ir(result[25], "cx", [1, 3], 2, True)
        validate_gate_ir(result[26], "rz", [3], 1, False)

        validate_gate_ir(result[27], "ry", [3], 1, False)
        validate_gate_ir(result[28], "rx", [3], 1, False)

        validate_gate_ir(result[29], "cx", [1, 2], 2, True)

        validate_gate_ir(result[30], "ry", [3], 1, False)
        validate_gate_ir(result[31], "rx", [3], 1, False)
        validate_gate_ir(result[32], "rz", [2], 1, False)
        validate_gate_ir(result[33], "cx", [2, 3], 2, True)
        validate_gate_ir(result[34], "rz", [3], 1, False)
        validate_gate_ir(result[35], "cx", [2, 3], 2, True)
        validate_gate_ir(result[36], "rz", [3], 1, False)

        validate_gate_ir(result[37], "ry", [3], 1, False)
        validate_gate_ir(result[38], "rx", [3], 1, False)

        validate_gate_ir(result[39], "cx", [0, 2], 2, True)

        validate_gate_ir(result[40], "ry", [3], 1, False)
        validate_gate_ir(result[41], "rx", [3], 1, False)
        validate_gate_ir(result[42], "rz", [2], 1, False)
        validate_gate_ir(result[43], "cx", [2, 3], 2, True)
        validate_gate_ir(result[44], "rz", [3], 1, False)
        validate_gate_ir(result[45], "cx", [2, 3], 2, True)
        validate_gate_ir(result[46], "rz", [3], 1, False)

        validate_gate_ir(result[47], "ry", [3], 1, False)
        validate_gate_ir(result[48], "rx", [3], 1, False)

        validate_gate_ir(result[49], "cx", [1, 2], 2, True)

        validate_gate_ir(result[50], "ry", [3], 1, False)
        validate_gate_ir(result[51], "rx", [3], 1, False)
        validate_gate_ir(result[52], "rz", [2], 1, False)
        validate_gate_ir(result[53], "cx", [2, 3], 2, True)
        validate_gate_ir(result[54], "rz", [3], 1, False)
        validate_gate_ir(result[55], "cx", [2, 3], 2, True)
        validate_gate_ir(result[56], "rz", [3], 1, False)

        validate_gate_ir(result[57], "ry", [3], 1, False)
        validate_gate_ir(result[58], "rx", [3], 1, False)

        validate_gate_ir(result[59], "cx", [0, 2], 2, True)

        validate_gate_ir(result[60], "ry", [3], 1, False)
        validate_gate_ir(result[61], "rx", [3], 1, False)
        validate_gate_ir(result[62], "rz", [2], 1, False)
        validate_gate_ir(result[63], "cx", [2, 3], 2, True)
        validate_gate_ir(result[64], "rz", [3], 1, False)
        validate_gate_ir(result[65], "cx", [2, 3], 2, True)
        validate_gate_ir(result[66], "rz", [3], 1, False)

        validate_gate_ir(result[67], "ry", [3], 1, False)
        validate_gate_ir(result[68], "rx", [3], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_c4x_gate(self):
        d = Decomposer()
        source = [
            create_gate("c4x", [0, 1, 2, 3, 4], []),
        ]
        target = ["rx", "ry", "rz", "cx"]

        result = d.decompose(source, target)
        assert len(result) == 153

        validate_gate_ir(result[0], "ry", [4], 1, False)
        validate_gate_ir(result[1], "rx", [4], 1, False)

        validate_gate_ir(result[2], "rz", [3], 1, False)
        validate_gate_ir(result[3], "cx", [3, 4], 2, True)
        validate_gate_ir(result[4], "rz", [4], 1, False)
        validate_gate_ir(result[5], "cx", [3, 4], 2, True)
        validate_gate_ir(result[6], "rz", [4], 1, False)

        validate_gate_ir(result[7], "ry", [4], 1, False)
        validate_gate_ir(result[8], "rx", [4], 1, False)

        validate_gate_ir(result[9], "ry", [3], 1, False)
        validate_gate_ir(result[10], "rx", [3], 1, False)

        validate_gate_ir(result[11], "rz", [0], 1, False)
        validate_gate_ir(result[12], "rz", [1], 1, False)
        validate_gate_ir(result[13], "rz", [2], 1, False)
        validate_gate_ir(result[14], "rz", [3], 1, False)

        validate_gate_ir(result[15], "cx", [0, 1], 2, True)
        validate_gate_ir(result[16], "rz", [1], 1, False)
        validate_gate_ir(result[17], "cx", [0, 1], 2, True)

        validate_gate_ir(result[18], "cx", [1, 2], 2, True)
        validate_gate_ir(result[19], "rz", [2], 1, False)
        validate_gate_ir(result[20], "cx", [0, 2], 2, True)
        validate_gate_ir(result[21], "rz", [2], 1, False)
        validate_gate_ir(result[22], "cx", [1, 2], 2, True)
        validate_gate_ir(result[23], "rz", [2], 1, False)
        validate_gate_ir(result[24], "cx", [0, 2], 2, True)

        validate_gate_ir(result[25], "cx", [2, 3], 2, True)
        validate_gate_ir(result[26], "rz", [3], 1, False)
        validate_gate_ir(result[27], "cx", [1, 3], 2, True)
        validate_gate_ir(result[28], "rz", [3], 1, False)
        validate_gate_ir(result[29], "cx", [2, 3], 2, True)
        validate_gate_ir(result[30], "rz", [3], 1, False)
        validate_gate_ir(result[31], "cx", [0, 3], 2, True)

        validate_gate_ir(result[32], "rz", [3], 1, False)
        validate_gate_ir(result[33], "cx", [2, 3], 2, True)
        validate_gate_ir(result[34], "rz", [3], 1, False)
        validate_gate_ir(result[35], "cx", [1, 3], 2, True)
        validate_gate_ir(result[36], "rz", [3], 1, False)
        validate_gate_ir(result[37], "cx", [2, 3], 2, True)
        validate_gate_ir(result[38], "rz", [3], 1, False)
        validate_gate_ir(result[39], "cx", [0, 3], 2, True)

        validate_gate_ir(result[40], "ry", [3], 1, False)
        validate_gate_ir(result[41], "rx", [3], 1, False)

        validate_ir_equals(source, result)

    def test_decompose_simple_qasm(self):
        data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[6];
        creg c[6];
        gate test_single(theta, phi) a{
            rx(theta) a;
            h a;
            ry(-phi) a;
            rz(theta + phi) a;
            x a;
            y a;
            z a;
            s a;
            sdg a;
            tdg a;
            t a;
        }
        gate test_two(x, y) a, b{
            test_single(x, y) a;
            cx a, b;
            cy a, b;
            cz a, b;
            ch a, b;
            crx(x) a, b;
            cry(y) a, b;
            crz(x+y) a, b;
        }
        test_two(sin(1.2), 1.3) q[2], q[3];
        ccx q[0], q[1], q[4];
        barrier q;
        measure q[1] -> c[1];
        """
        tree = get_abs_tree(data)
        assert tree is not None

        cir = get_ir(tree)
        q_num, gates_list = cir.num_qubits, cir.get_operations()
        assert q_num == 6
        assert len(gates_list) == 21
        d = Decomposer()
        target = ["rx", "ry", "rz", "cx", "sync", "measure"]
        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

        target = ["rx", "ry", "cx", "sync", "measure"]
        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

        # hanyuan quantum instructions set
        target = ["rx", "ry", "cz", "sync", "measure"]
        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

        # Spinq quantum instructions set
        target = [
            "h",
            "i",
            "x",
            "y",
            "z",
            "rx",
            "ry",
            "rz",
            "p",
            "s",
            "t",
            "tdg",
            "u",
            "cx",
            "cy",
            "cz",
            "swap",
            "ccx",
            "ccz",
            "sync",
            "measure",
        ]
        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

        # Uqc quantum instructions set
        target = ["rx", "ry", "rzz", "sync", "measure"]
        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

        # Ibmq quantum instructions set
        target = ["rz", "sx", "x", "cx", "sync", "measure"]
        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

        # Ionq quantum instructions set
        target = ["rxx", "rx", "ry", "rz", "sync", "measure"]
        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

        # Nam quantum instructions set
        target = ["cx", "h", "rz", "sync", "measure"]
        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

        # Origin quantum instructions set
        target = ["cz", "u3", "sync", "measure"]
        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

        # Quafu quantum instructions set
        target = ["cx", "rx", "ry", "rz", "h", "sync", "measure"]
        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

        # USTC quantum instructions set
        target = ["cx", "rx", "ry", "rz", "h", "x", "sync", "measure"]
        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

    def test_basis_change_n3_qasm_file(self):
        samples_dir = GLOBAL_CONFIGS["samples_dir"]
        file_path = (
            f"{samples_dir}/qasm/benchpress/qasmbench-small/"
            f"basis_change_n3/basis_change_n3.qasm"
        )
        qasm_data = read_qasm_from_file(file_path)

        tree = get_abs_tree(qasm_data)
        assert tree is not None
        cir = get_ir(tree)
        _, gates_list = cir.num_qubits, cir.get_operations()
        d = Decomposer()

        # Spinq quantum instructions set
        target = [
            "h",
            "i",
            "x",
            "y",
            "z",
            "rx",
            "ry",
            "rz",
            "p",
            "s",
            "t",
            "tdg",
            "u",
            "cx",
            "cy",
            "cz",
            "swap",
            "ccx",
            "ccz",
            "sync",
            "measure",
        ]

        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

    def test_simple_qasm_file(self):
        samples_dir = GLOBAL_CONFIGS["samples_dir"]
        file_path = f"{samples_dir}/qasm/2.0/simple-qasm.qasm"
        qasm_data = read_qasm_from_file(file_path)

        tree = get_abs_tree(qasm_data)
        assert tree is not None
        cir = get_ir(tree)
        _, gates_list = cir.num_qubits, cir.get_operations()
        d = Decomposer()

        # Spinq quantum instructions set
        target = [
            "rx",
            "ry",
            "cz",
        ]

        decomposed_gates = d.decompose(gates_list, target)
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)

    def test_decompose_multi_same_gate(self):
        data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[6];
        creg c[6];
        ccx q[0], q[1], q[4];
        ccx q[0], q[1], q[4];
        measure q[1] -> c[1];
        """
        tree = get_abs_tree(data)
        assert tree is not None

        cir = get_ir(tree)
        _, gates_list = cir.num_qubits, cir.get_operations()
        d = Decomposer()
        target = ["rx", "ry", "rz", "cx", "sync", "measure"]
        decomposed_gates = d.decompose(gates_list, target)
        assert id(decomposed_gates[0]) != id(decomposed_gates[17])
        validate_gates_in_targets(decomposed_gates, target)
        validate_ir_equals(gates_list, decomposed_gates)
