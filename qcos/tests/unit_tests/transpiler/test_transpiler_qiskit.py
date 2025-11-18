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

import pytest
from unittest.mock import patch

from qcos.common.constant import Constant
from qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.qiskit.transpiler_qiskit import TranspilerQiskit
from qcos.transpiler.qiskit.transpiler_qiskit_cmd import (
    read_qasm_from_file,
    Timer,
    main,
)

timer = Timer()

TRANSPILE_METHOD_PATH = (
    "qcos.transpiler.qiskit.transpiler_qiskit_cmd.TranspilerQiskit.transpile"
)


@pytest.mark.usefixtures("global_configs")
class TestTranspilerQiskit:
    @classmethod
    def setup_class(cls):
        cls.simple_data = """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[1];
        creg c[1];
        h q[0];
        x q[0];
        rx(1) q[0];
        measure q->c;
        """

    def test_read_qasm_from_file(self):
        read_qasm_from_file("None")

    def test_transpiler_qiskit(self):
        expected_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CX,
        ]
        trans_cfg_inst.set_driver_name("DriverQiskitAerSim")
        transpiler = TranspilerQiskit()
        src_code_info = {"000": self.simple_data}
        parse_result = transpiler.parse(src_code_info)
        transpiled_circuit = transpiler.transpile(
            parse_result, expected_basis_gates
        )
        assert len(transpiled_circuit) == 3

    def test_transpiler_qiskit_abnormal(self):
        trans_cfg_inst.set_driver_name("DriverQiskitAerSim")
        transpiler = TranspilerQiskit()
        src_code_info = {"000": self.simple_data}
        try:
            transpiler.parse(src_code_info)
        except Exception as e:
            assert "unsupported input" in str(e)

    @patch(TRANSPILE_METHOD_PATH)
    def test_transpiler_qiskit_noconfig(self, mock_transpile):
        mock_transpile.return_value = None

        self.qasm_path = GLOBAL_CONFIGS["samples_dir"]
        qasm_file = f"{self.qasm_path}/qasm/2.0/simple-qasm.qasm"
        output_file = ""
        expected_basis_gates = "rx,ry,cx"
        opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
        res = main(
            input_file=qasm_file,
            output_file=output_file,
            basis_gates=expected_basis_gates,
            opt_level=opt_level,
            config_file="etc/topology/qiskit_marrakesh.toml",
        )
        assert res is True

    def test_transpiler_qiskit_tech_sc(self):
        self.qasm_path = GLOBAL_CONFIGS["samples_dir"]
        qasm_file = f"{self.qasm_path}/qasm/2.0/simple-qasm.qasm"
        output_file = ""
        opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
        res = main(
            input_file=qasm_file,
            output_file=output_file,
            opt_level=opt_level,
            config_file="etc/topology/qiskit_marrakesh.toml",
        )
        assert res is True
