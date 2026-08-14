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
import csv
import time

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
from wy_qcos.transpiler.common.utils import (
    Timer,
    TranspileRuntime,
)
from wy_qcos.transpiler.qiskit.transpiler_qiskit import TranspilerQiskit
from wy_qcos.transpiler.qiskit.transpiler_qiskit_cmd import (
    QiskitTranspilerPerf,
    TranspileParams,
    main as qiskit_main,
    get_parse_args,
)

timer = Timer()

TRANSPILE_METHOD_PATH = (
    "wy_qcos.transpiler.qiskit.transpiler_qiskit_cmd."
    "TranspilerQiskit.transpile"
)


# ──────────────────────────────────────────────
# Timer tests
# ──────────────────────────────────────────────
class TestTimer:
    def test_timer_elapsed(self):
        with Timer() as t:
            time.sleep(0.05)
        assert t.elapsed >= 0.04

    def test_timer_context(self):
        t = Timer()
        enter_result = t.__enter__()
        assert enter_result is t
        t.__exit__(None, None, None)
        assert hasattr(t, "elapsed")
        assert t.elapsed >= 0


# ──────────────────────────────────────────────
# TranspileRuntime tests
# ──────────────────────────────────────────────
class TestTranspileRuntime:
    def test_default_values(self):
        runtime = TranspileRuntime()
        assert runtime.total_time == 0.0
        assert runtime.transpile_time == 0.0
        assert runtime.parse_time == 0.0
        assert runtime.transpiled_gate_count == 0
        assert runtime.transpiled_depth == 0

    def test_add_runtime(self):
        r1 = TranspileRuntime()
        r1.total_time = 1.0
        r1.transpile_time = 0.5
        r1.parse_time = 0.3
        r1.transpiled_gate_count = 10
        r1.transpiled_depth = 5

        r2 = TranspileRuntime()
        r2.total_time = 2.0
        r2.transpile_time = 1.0
        r2.parse_time = 0.6
        r2.transpiled_gate_count = 20
        r2.transpiled_depth = 8

        r1.add_runtime(r2)
        assert r1.total_time == pytest.approx(3.0)
        assert r1.transpile_time == pytest.approx(1.5)
        assert r1.parse_time == pytest.approx(0.9)
        assert r1.transpiled_gate_count == 30
        assert r1.transpiled_depth == 13

    def test_avg_runtime(self):
        r = TranspileRuntime()
        r.total_time = 4.0
        r.transpile_time = 2.0
        r.parse_time = 1.0
        r.transpiled_gate_count = 20
        r.transpiled_depth = 10
        r.avg_runtime(2)
        assert r.total_time == pytest.approx(2.0)
        assert r.transpile_time == pytest.approx(1.0)
        assert r.parse_time == pytest.approx(0.5)
        assert r.transpiled_gate_count == 10
        assert r.transpiled_depth == 5


# ──────────────────────────────────────────────
# TranspileParams tests
# ──────────────────────────────────────────────
class TestTranspileParams:
    def test_default_values(self):
        params = TranspileParams()
        assert params.output_log == ""
        assert params.csv_file == ""
        assert params.num_qubits == 0
        assert params.depth == 0
        assert params.basis_gates == []
        assert params.opt_level == 1
        assert params.tech_type == Constant.TECH_TYPE_SUPERCONDUCTING


# ──────────────────────────────────────────────
# QiskitTranspilerPerf init and init_transpile_params tests
# ──────────────────────────────────────────────
@pytest.mark.usefixtures("global_configs")
class TestQiskitTranspilerPerfInit:
    @classmethod
    def setup_class(cls):
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        cls.etc_dir = GLOBAL_CONFIGS["etc_dir"]

    def test_init_defaults(self):
        perf = QiskitTranspilerPerf()
        assert perf.params_list == []
        assert perf.run_count == 1
        assert perf.output_log == ""
        assert perf.csv_file == ""
        assert perf.basis_gates == []
        assert perf.opt_level == [1]
        assert perf.config_file == ""
        assert perf.parse_results == {}
        assert perf.transpile_errors == {}

    def test_init_transpile_params_normal(self):
        perf = QiskitTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "dirs": [],
                "perf_enabled": False,
                "transpiler": {
                    "config_file": (
                        f"{self.etc_dir}/topology/qiskit_marrakesh.toml"
                    )
                },
                "optimize": {"opt_level": [0, 1]},
                "basis_gates": {"gates": ["rx, ry, rz, x, h, cx, cz"]},
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.run_count == 1
        assert perf.opt_level == [0, 1]
        assert len(perf.basis_gates) == 1
        assert perf.basis_gates[0] == ["rx", "ry", "rz", "x", "h", "cx", "cz"]
        assert (
            perf.config_file
            == f"{self.etc_dir}/topology/qiskit_marrakesh.toml"
        )

    def test_init_transpile_params_run_count_zero(self):
        perf = QiskitTranspilerPerf()
        extra_configs = {
            "transpile": {
                "run_count": 0,
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "dirs": [],
                "transpiler": {"config_file": ""},
                "optimize": {"opt_level": [1]},
                "basis_gates": {"gates": ["rx, ry, cx"]},
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.run_count == 1

    def test_init_transpile_params_run_count_over_five(self):
        perf = QiskitTranspilerPerf()
        extra_configs = {
            "transpile": {
                "run_count": 10,
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "dirs": [],
                "transpiler": {"config_file": ""},
                "optimize": {"opt_level": [1]},
                "basis_gates": {"gates": ["rx, ry, cx"]},
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.run_count == 5

    def test_init_transpile_params_empty_basis_gates(self):
        """When basis_gates.gates is empty, default gate set is used."""
        perf = QiskitTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "dirs": [],
                "transpiler": {"config_file": ""},
                "optimize": {"opt_level": [1]},
                "basis_gates": {"gates": []},
            }
        }
        perf.init_transpile_params(extra_configs)
        assert len(perf.basis_gates) == 1
        expected_default = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.TWO_QUBIT_GATE_CX,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
        assert perf.basis_gates[0] == expected_default

    def test_init_transpile_params_illegal_gate(self):
        """Illegal gate name raises ValueError."""
        perf = QiskitTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "dirs": [],
                "transpiler": {"config_file": ""},
                "optimize": {"opt_level": [1]},
                "basis_gates": {"gates": ["rx, illegal_gate, cx"]},
            }
        }
        with pytest.raises(ValueError) as e:
            perf.init_transpile_params(extra_configs)
        assert "illegal_gate" in str(e.value)

    def test_init_transpile_params_no_files_nor_dirs(self):
        """Both files and dirs empty raises ValueError."""
        perf = QiskitTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [],
                "dirs": [],
                "transpiler": {"config_file": ""},
                "optimize": {"opt_level": [1]},
                "basis_gates": {"gates": ["rx, ry, cx"]},
            }
        }
        with pytest.raises(ValueError) as e:
            perf.init_transpile_params(extra_configs)
        assert "not configured" in str(e.value)

    def test_init_transpile_params_none_config(self):
        """None extra_configs raises ValueError."""
        perf = QiskitTranspilerPerf()
        with pytest.raises(ValueError):
            perf.init_transpile_params(None)

    def test_init_transpile_params_missing_transpile_key(self):
        """Missing 'transpile' key raises ValueError."""
        perf = QiskitTranspilerPerf()
        with pytest.raises(ValueError):
            perf.init_transpile_params({"other": {}})


# ──────────────────────────────────────────────
# parse_file_args tests
# ──────────────────────────────────────────────
@pytest.mark.usefixtures("global_configs")
class TestQiskitTranspilerPerfFileArgs:
    @classmethod
    def setup_class(cls):
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]

    def test_parse_file_args_normal(self):
        perf = QiskitTranspilerPerf()
        perf.file_list = [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"]
        perf.dir_list = []
        perf.parse_file_args()
        assert len(perf.total_files) > 0

    def test_parse_file_args_dir_scan(self):
        perf = QiskitTranspilerPerf()
        perf.file_list = []
        perf.dir_list = [f"{self.samples_dir}/qasm/2.0/benchmark"]
        perf.parse_file_args()
        assert len(perf.total_files) > 0

    def test_parse_file_args_skip_non_qasm(self):
        """Non-.qasm files in file_list are skipped."""
        perf = QiskitTranspilerPerf()
        perf.file_list = [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"]
        perf.dir_list = []
        # Also add a non-qasm file that exists
        perf.file_list.append(
            f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm" + ".bak"
        )
        # The .bak won't exist, but parse_file_args warns and continues
        perf.parse_file_args()
        # Should still have the .qasm file
        assert len(perf.total_files) > 0
        assert perf.total_files[0].suffix == ".qasm"

    def test_parse_file_args_no_valid_files(self):
        """No valid files raises ValueError."""
        perf = QiskitTranspilerPerf()
        perf.file_list = [f"{self.samples_dir}/nonexistent_file.qasm"]
        perf.dir_list = [f"{self.samples_dir}/nonexistent_dir"]
        with pytest.raises(ValueError) as e:
            perf.parse_file_args()
        assert "no valid input file" in str(e.value)

    def test_parse_file_args_dir_is_file_raises(self):
        """A file path in dir_list raises ValueError."""
        perf = QiskitTranspilerPerf()
        perf.file_list = [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"]
        # Point dir_list to a real file instead of a directory
        perf.dir_list = [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"]
        with pytest.raises(ValueError) as e:
            perf.parse_file_args()
        assert "not a valid directory" in str(e.value)


# ──────────────────────────────────────────────
# output_csv_file tests
# ──────────────────────────────────────────────
@pytest.mark.usefixtures("global_configs")
class TestOutputCsvFile:
    def test_no_csv_file(self):
        """csv_file="" returns None."""
        perf = QiskitTranspilerPerf()
        perf.csv_file = ""
        result = perf.output_csv_file()
        assert result is None

    def test_runtime_none_failed(self, tmp_path):
        """runtime=None writes FAILED row."""
        perf = QiskitTranspilerPerf()
        csv_path = tmp_path / "output.csv"
        perf.csv_file = str(csv_path)

        params = TranspileParams()
        params.file = Path("test.qasm")
        perf.transpile_result = {params: None}
        perf.parse_results = {}
        perf.transpile_errors = {}

        result = perf.output_csv_file()
        assert result is not None
        # Read back CSV and check FAILED status
        with open(result, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        # Header + 1 data row
        assert len(rows) == 2
        assert rows[1][-2] == "FAILED"

    def test_normal_success(self, tmp_path):
        """Normal runtime writes SUCCESS row."""
        perf = QiskitTranspilerPerf()
        csv_path = tmp_path / "output.csv"
        perf.csv_file = str(csv_path)

        params = TranspileParams()
        params.file = Path("test.qasm")
        params.opt_level = 1

        runtime = TranspileRuntime()
        runtime.parse_time = 0.01
        runtime.transpile_time = 0.05
        runtime.total_time = 0.06
        runtime.transpiled_gate_count = 10
        runtime.transpiled_depth = 5

        perf.transpile_result = {params: runtime}
        perf.parse_results = {
            params.file: (2, 3, 4),  # num_qubits, depth, gate_count
        }
        perf.transpile_errors = {}

        result = perf.output_csv_file()
        assert result is not None
        with open(result, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[1][-2] == "SUCCESS"

    def test_csv_file_suffix_check(self, tmp_path):
        """Non-.csv suffix raises ValueError."""
        perf = QiskitTranspilerPerf()
        txt_path = tmp_path / "output.txt"
        perf.csv_file = str(txt_path)

        with pytest.raises(ValueError) as e:
            perf.output_csv_file()
        assert "not a csv file" in str(e.value)

    def test_skip_csv_output_parse_not_available(self, tmp_path):
        """params.file not in parse_results: skip row, log warning."""
        perf = QiskitTranspilerPerf()
        csv_path = tmp_path / "output.csv"
        perf.csv_file = str(csv_path)

        params = TranspileParams()
        params.file = Path("missing.qasm")
        params.opt_level = 1

        runtime = TranspileRuntime()
        runtime.parse_time = 0.01
        runtime.transpile_time = 0.05
        runtime.total_time = 0.06

        perf.transpile_result = {params: runtime}
        perf.parse_results = {}  # No parse result for this file
        perf.transpile_errors = {}

        result = perf.output_csv_file()
        assert result is not None
        with open(result, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)
        # Only header, data row skipped
        assert len(rows) == 1


# ──────────────────────────────────────────────
# Existing TestTranspilerQiskit (expanded)
# ──────────────────────────────────────────────
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
        QiskitTranspilerPerf.read_qasm_from_file("None")

    def test_read_qasm_from_file_success(self):
        qasm_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        result = QiskitTranspilerPerf.read_qasm_from_file(qasm_file)
        assert result is not None
        assert "OPENQASM" in result

    def test_init_output_head_with_path(self):
        m = mock_open()
        with patch("builtins.open", m):
            output_file_path = Path("test.txt")
            file_path = Path("input.qasm")
            QiskitTranspilerPerf.init_output_head(
                output_file_path, file_path, 1, ["rx", "ry", "cx"]
            )
            m.assert_called_once_with(output_file_path, "a", encoding="utf-8")

    def test_init_output_head_without_path(self):
        """output_file_path is None: no file write."""
        m = mock_open()
        with patch("builtins.open", m):
            QiskitTranspilerPerf.init_output_head(
                None, Path("input.qasm"), 1, ["rx", "ry", "cx"]
            )
            # open should not be called since output_file_path is falsy
            m.assert_not_called()

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
        transpiled_circuit, _, _ = transpiler.transpile(
            parse_result, expected_basis_gates
        )
        assert len(transpiled_circuit) == 3

    def test_transpiler_qiskit_abnormal(self):
        """Passing a non-dict input to parse should raise."""
        trans_cfg_inst.set_driver_name("DriverQiskitAerSim")
        transpiler = TranspilerQiskit()
        with pytest.raises(Exception) as e:
            transpiler.parse(["invalid", "input"])
        assert "unsupported input" in str(e.value)

    @patch(TRANSPILE_METHOD_PATH)
    def test_transpiler_qiskit_noconfig(self, mock_transpile):
        mock_transpile.return_value = (None, None, None)

        etc_path = GLOBAL_CONFIGS["etc_dir"]
        qasm_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        expected_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CX,
        ]
        opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL

        perf = QiskitTranspilerPerf()
        perf.config_file = f"{etc_path}/topology/qiskit_marrakesh.toml"
        runtime = perf.qiskit_transpiler_perf_exec(
            input_file=qasm_file,
            opt_level=opt_level,
            basis_gates=expected_basis_gates,
        )
        assert runtime is not None
        # When transpile returns None, gate count and depth should be 0
        assert runtime.transpiled_gate_count == 0
        assert runtime.transpiled_depth == 0

    def test_transpiler_qiskit_tech_sc(self):
        qiskit_logger = logging.getLogger("qiskit")
        qiskit_logger.setLevel(logging.WARNING)
        qasm_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
        basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CX,
        ]

        perf = QiskitTranspilerPerf()
        perf.config_file = f"{self.etc_path}/topology/qiskit_marrakesh.toml"
        runtime = perf.qiskit_transpiler_perf_exec(
            input_file=qasm_file,
            opt_level=opt_level,
            basis_gates=basis_gates,
        )
        assert runtime is not None

    def test_perf_exec_config_not_exist(self):
        """config_file points to non-existent file → ValueError."""
        qasm_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        perf = QiskitTranspilerPerf()
        perf.config_file = "/nonexistent/config.toml"
        with pytest.raises(ValueError) as e:
            perf.qiskit_transpiler_perf_exec(
                input_file=qasm_file,
                opt_level=1,
                basis_gates=["rx", "ry", "cx"],
            )
        assert "not existed" in str(e.value)

    def test_perf_exec_read_qasm_fail(self):
        """read_qasm_from_file returns None → ValueError."""
        perf = QiskitTranspilerPerf()
        perf.config_file = ""
        with patch.object(
            QiskitTranspilerPerf,
            "read_qasm_from_file",
            return_value=None,
        ):
            qasm_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
            with pytest.raises(ValueError) as e:
                perf.qiskit_transpiler_perf_exec(
                    input_file=qasm_file,
                    opt_level=1,
                    basis_gates=["rx", "ry", "cx"],
                )
            assert "read qasm data" in str(e.value)

    @patch(
        "wy_qcos.transpiler.qiskit.transpiler_qiskit_cmd."
        "QiskitTranspilerPerf.main_qiskit_transpiler"
    )
    def test_qiskit_parse_args(self, mock_main_qiskit_transpiler):
        sys.argv = [
            "transpiler_qiskit_cmd.py",
            "--trans-config-file",
            "etc/perf/qiskit_transpile_conf.toml",
        ]
        qiskit_args = get_parse_args()
        assert (
            qiskit_args["trans_config_file"]
            == "etc/perf/qiskit_transpile_conf.toml"
        )

        mock_main_qiskit_transpiler.return_value = None
        with patch("sys.exit") as mock_sys_exit:
            qiskit_main(sys.argv)
            mock_sys_exit.assert_called_with(mock_main_qiskit_transpiler())

    def test_get_parse_args_default(self):
        """Default config file path when no args given."""
        with patch("sys.argv", ["transpiler_qiskit_cmd.py"]):
            qiskit_args = get_parse_args()
            assert (
                qiskit_args["trans_config_file"]
                == "etc/perf/qiskit_transpile_conf.toml"
            )

    def test_check_file_args(self):
        with pytest.raises(FileNotFoundError) as e:
            input_file1 = f"{self.samples_dir}/qasm/2.0/simple-qasm-2.qasm"
            _, _ = QiskitTranspilerPerf.check_file_args(input_file1, "")
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
            res, _ = QiskitTranspilerPerf.check_file_args(
                input_file, output_file
            )
            mock_file.assert_called_once_with(
                output_file_path, "w", encoding="utf-8"
            )
            mock_file().write.assert_called_once_with(
                f"testing file: {input_file}.\n"
            )
            assert res == Path(input_file).resolve()

    def test_check_file_args_no_output(self):
        """output_file="" → output_file_path is None."""
        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        res, output_file_path = QiskitTranspilerPerf.check_file_args(
            input_file, ""
        )
        assert res == Path(input_file).resolve()
        assert output_file_path is None
