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

# ruff: noqa: E402
# load driver venv
import sys

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library

org_path = Library.set_driver_venv_path(
    "DriverQiskitQasmSim", Config.DEFAULT.VENV_DIR
)

import logging
from pathlib import Path
import pytest
from unittest.mock import patch, mock_open, MagicMock

from wy_qcos.common.constant import Constant
from wy_qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.qiskit.transpiler_qiskit import TranspilerQiskit
from wy_qcos.transpiler.qiskit.transpiler_qiskit_cmd import (
    read_qasm_from_file,
    Timer,
    main_qiskit_transpiler as main,
    main as qiskit_main,
    get_parse_args,
    check_file_args,
)

timer = Timer()

TRANSPILE_METHOD_PATH = (
    "wy_qcos.transpiler.qiskit.transpiler_qiskit_cmd."
    "TranspilerQiskit.transpile"
)


@pytest.mark.usefixtures("global_configs")
class TestTranspilerQiskit:
    @classmethod
    def setup_class(cls):
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        cls.etc_path = GLOBAL_CONFIGS["etc_dir"]
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

    @classmethod
    def teardown_class(cls):
        sys.path = org_path

    def test_read_qasm_from_file(self):
        read_qasm_from_file("None")

    @pytest.mark.smoke
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

        etc_path = GLOBAL_CONFIGS["etc_dir"]
        qasm_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        output_file = ""
        expected_basis_gates = "rx,ry,cx"
        opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
        res = main(
            input_file=qasm_file,
            output_file=output_file,
            basis_gates=expected_basis_gates,
            opt_level=opt_level,
            config_file=f"{etc_path}/topology/qiskit_marrakesh.toml",
        )
        assert res is True

    def test_transpiler_qiskit_tech_sc(self):
        qiskit_logger = logging.getLogger("qiskit")
        qiskit_logger.setLevel(logging.WARNING)
        qasm_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        output_file = ""
        opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
        res = main(
            input_file=qasm_file,
            output_file=output_file,
            opt_level=opt_level,
            config_file=f"{self.etc_path}/topology/qiskit_marrakesh.toml",
        )
        assert res is True

    @patch(
        "wy_qcos.transpiler.qiskit.transpiler_qiskit_cmd."
        "main_qiskit_transpiler"
    )
    def test_qiskit_parse_args(self, mock_main_qiskit_transpiler):
        sys.argv = [
            "transpiler_qiskit_cmd.py",
            "--input-file",
            f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm",
            "--gates-list",
            "rx,ry,cx",
        ]
        qiskit_args = get_parse_args()
        assert (
            qiskit_args["input_file"]
            == f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        )
        assert qiskit_args["basis_gates"] == "rx,ry,cx"
        assert qiskit_args["output_file"] == ""

        mock_main_qiskit_transpiler.return_value = True
        with patch("sys.exit") as mock_sys_exit:
            qiskit_main(sys.argv)
            mock_sys_exit.assert_called_with(mock_main_qiskit_transpiler())

    def test_check_file_args(self):
        with pytest.raises(FileNotFoundError) as e:
            input_file1 = f"{self.samples_dir}/qasm/2.0/simple-qasm-2.qasm"
            _, _ = check_file_args(input_file1, "")
        err_msg = str(e.value)
        assert "Input file not existed!" in err_msg

        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        output_file = "CHANGELOG"
        output_file_path = Path(output_file).resolve()
        mock_file = mock_open()
        mock_file_handler = MagicMock()
        with (
            patch("builtins.open", mock_file),
            patch("logging.FileHandler", return_value=mock_file_handler),
        ):
            res = check_file_args(input_file, output_file)
            mock_file.assert_called_once_with(
                output_file_path, "w", encoding="utf-8"
            )
            mock_file().write.assert_called_once_with(
                f"testing file: {input_file}.\n"
            )
            assert res == Path(input_file).resolve()
