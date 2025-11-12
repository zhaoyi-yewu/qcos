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
import pytest

from qcos.common.constant import Constant
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.cmss.transpiler_cmss import TranspilerCmss
from qcos.tests.unit_tests.transpiler.comm import validate_gate_ir
from qcos.tests.unit_tests.transpiler.comm import validate_non_gate_ir
from qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS, SAMPLES


@pytest.mark.usefixtures("global_configs")
class TestTranspilerCmss:
    @classmethod
    def setup_class(cls):
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        cls.simple_data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c[1];
        h q[0];
        h q[0];
        x q[0];
        rx(1) q[0];
        measure q->c;
        """

        cls.qpu_config = {
            "qubits": 6,
            "storage_area": ["S27", "S28", "S29", "S35", "S36", "S37"],
            "operate_area": ["P27", "P28", "P29", "P35", "P36", "P37"],
            "coupler_map": {
                "G0": ["P27", "P35"],
                "G1": ["P28", "P36"],
                "G2": ["P29", "P37"],
                "G3": ["P27", "P28"],
                "G4": ["P35", "P36"],
                "G5": ["P28", "P29"],
            },
            "readout_error": {
                "S27": 1.0,
                "S28": 2.0,
                "S35": 3.0,
                "S36": 4.0,
                "S29": 5.0,
                "S37": 6.0,
            },
            "coupler_error": {
                "G0": 3.0,
                "G1": 3.0,
                "G2": 3.0,
                "G3": 3.0,
                "G4": 3.0,
                "G5": 3.0,
            },
            "closest": {
                "P27": "S27",
                "P28": "S28",
                "P35": "S35",
                "P36": "S36",
                "P29": "S29",
                "P37": "S37",
            },
        }
        trans_cfg_inst.set_qpu_cfg(cls.qpu_config)
        trans_cfg_inst.set_tech_type(Constant.TECH_TYPE_NEUTRAL_ATOM)
        trans_cfg_inst.set_max_qubits(6)

    def test_transpiler_cmss(self):
        transpiler = TranspilerCmss()
        expected_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
        ]
        src_code_info = {"000": self.simple_data}
        parse_result = transpiler.parse(src_code_info)
        basis_gate_list, _ = transpiler.transpile(
            parse_result, expected_basis_gates
        )
        assert len(basis_gate_list) == 2
        validate_gate_ir(basis_gate_list[0], "rx", [27], 1, False)
        validate_non_gate_ir(basis_gate_list[1], "measure", [27], 0)

    def test_transpiler_aggregation_succ(self):
        transpiler = TranspilerCmss()
        expected_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
        ]
        src_code_info = {
            "000": self.simple_data,
            "111": self.simple_data,
            "222": self.simple_data,
            "333": self.simple_data,
            "444": self.simple_data,
        }
        parse_result = transpiler.parse(src_code_info)
        basis_gate_list, _ = transpiler.transpile(
            parse_result, expected_basis_gates
        )
        assert len(basis_gate_list) == 10

    def test_transpiler_aggregation_partly_succ(self):
        qasm_data = SAMPLES["simple-qasm.qasm"]
        if qasm_data is None:
            return

        transpiler = TranspilerCmss()
        expected_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
        ]
        src_code_info = {
            "000": qasm_data,
            "111": qasm_data,
            "222": qasm_data,
        }
        parse_result = transpiler.parse(src_code_info)
        basis_gate_list, _ = transpiler.transpile(
            parse_result, expected_basis_gates
        )
        assert len(basis_gate_list) == 8
