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

import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock, mock_open

from wy_qcos.common.constant import Constant
from wy_qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS
from wy_qcos.transpiler.common.errors import TranspilerException
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.common.utils import (
    Timer,
    TranspileRuntime,
)
from wy_qcos.transpiler.cmss.transpiler_cmss_for_cpp import (
    TranspilerHighPerformanceCmss,
)
from wy_qcos.transpiler.cmss.transpiler_cmd_line import (
    CMSSTranspilerPerf,
    TranspileParams,
    main as cmss_main,
    get_parse_args,
)

from wy_qcos.common.cmss.gate_operation import X
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit

timer = Timer()


@pytest.mark.usefixtures("global_configs")
class TestTranspilerCmdLine:
    @classmethod
    def setup_class(cls):
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        cls.etc_dir = GLOBAL_CONFIGS["etc_dir"]

    def test_read_qasm_from_file(self):
        perf = CMSSTranspilerPerf()
        perf.read_qasm_from_file("invalid_file")

    def test_init_output_head(self):
        m = mock_open()
        with patch("builtins.open", m):
            output_file_path = Path("test.txt")
            file_path = Path("input.txt")
            opt_level = 1
            tech_type = "sc"
            config_file = "config.yaml"
            mapping_options = {}
            CMSSTranspilerPerf.init_output_head(
                output_file_path,
                file_path,
                opt_level,
                tech_type,
                config_file,
                mapping_options,
            )
            m.assert_called_once_with(output_file_path, "a", encoding="utf-8")

    def test_parse_args(self):
        sys.argv = [
            "transpiler_cmd_line.py",
            "--trans-config-file",
            f"{self.etc_dir}/perf/transpile_conf.toml",
        ]
        cmss_args = get_parse_args()
        assert "etc/perf/transpile_conf.toml" in cmss_args["trans_config_file"]

        with patch(
            "wy_qcos.transpiler.cmss.transpiler_cmd_line.CMSSTranspilerPerf"
        ) as MockPerf:
            mock_perf = MockPerf()
            mock_perf.main_cmss_transpiler(
                cmss_args["trans_config_file"]
            ).return_value = True
            with patch("sys.exit") as mock_sys_exit:
                cmss_main(sys.argv)
                mock_sys_exit.assert_called_with(
                    mock_perf.main_cmss_transpiler(
                        cmss_args["trans_config_file"]
                    )
                )

    def test_parse_file_args(self):
        perf = CMSSTranspilerPerf()
        perf.file_list = [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"]
        perf.dir_list = [f"{self.samples_dir}/qasm/2.0/benchmark"]
        perf.parse_file_args()
        assert len(perf.total_files) > 0

        perf = CMSSTranspilerPerf()
        perf.file_list = [f"{self.samples_dir}/qasm/2.0/simple-qasm1.qasm"]
        perf.dir_list = [f"{self.samples_dir}/qasm/2.0/benchmark"]
        perf.total_files = [1]
        perf.parse_file_args()
        assert len(perf.total_files) > 0

        perf = CMSSTranspilerPerf()
        perf.file_list = [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"]
        perf.dir_list = [f"{self.samples_dir}/qasm/2.0/benchmark1"]
        perf.total_files = [1]
        perf.parse_file_args()
        assert len(perf.total_files) > 0

    def test_check_file_args(self):
        perf = CMSSTranspilerPerf()
        with pytest.raises(FileNotFoundError) as e:
            input_file1 = f"{self.samples_dir}/qasm/2.0/simple-qasm-2.qasm"
            _, _ = perf.check_file_args(input_file1, "")
        err_msg = str(e.value)
        assert "Input file not existed!" in err_msg

        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        output_file = "publish.py"
        mock_file = mock_open()
        mock_file_handler = MagicMock()
        with (
            patch("builtins.open", mock_file),
            patch("logging.FileHandler", return_value=mock_file_handler),
        ):
            res, output_file_path = perf.check_file_args(
                input_file, output_file
            )
            mock_file.assert_called_once_with(
                output_file_path, "w", encoding="utf-8"
            )
            mock_file().write.assert_called_once_with(
                f"testing file: {input_file}.\n"
            )
            assert res == Path(input_file).resolve()

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf.get_transpile_result"
    )
    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf.parse_file_args"
    )
    def test_main_cmss_transpiler(
        self, mock_parse_file_args, mock_get_transpile_result
    ):
        params = TranspileParams()
        assert params is not None

        mock_parse_file_args.return_value = None
        mock_get_transpile_result.return_value = None
        perf = CMSSTranspilerPerf()
        trans_config_file = (
            GLOBAL_CONFIGS["etc_dir"] + "/perf/transpile_conf.toml"
        )
        perf.total_files = ["0", "1"]
        perf.main_cmss_transpiler(trans_config_file)
        mock_parse_file_args.assert_called_once()

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf.cmss_transpiler_perf_exec"
    )
    def test_get_transpile_result(self, mock_cmss_transpiler_perf_exec):
        mock_cmss_transpiler_perf_exec.return_value = TranspileRuntime()

        perf = CMSSTranspilerPerf()
        perf.total_files = ["file1"]
        params = TranspileParams()
        params.mapping_info = ("0", "1")
        perf.params_list.append(params)
        perf.get_transpile_result()
        assert perf.transpile_result is not None

        perf.params_list.append(params)
        perf.get_transpile_result()

        assert perf.transpile_result is not None

    def test_cmss_transpiler_perf_exec_by_na(self):
        with patch(
            "wy_qcos.transpiler.cmss.transpiler_cmd_line."
            "TranspilerHighPerformanceCmss"
        ) as MockTranspilerHighPerformanceCmss:
            mock_transpiler = self._build_mock_transpiler_for_single()
            MockTranspilerHighPerformanceCmss.return_value = mock_transpiler
            mock_transpiler.parse.return_value = {"000": (1, ["x"])}
            mock_transpiler.transpile.return_value = (
                [X([0])],
                None,
                None,
            )

            perf = CMSSTranspilerPerf()
            input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
            opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
            basis_gates = ["rx", "ry", "cz"]
            tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
            config_file = (
                GLOBAL_CONFIGS["etc_dir"] + "/qcos/conf.d/hanyuan1.toml"
            )

            runtime = perf.cmss_transpiler_perf_exec(
                input_file, opt_level, basis_gates, tech_type, config_file
            )
            assert runtime is not None

    def test_cmss_transpiler_perf_exec_by_sc(self):
        with patch(
            "wy_qcos.transpiler.cmss.transpiler_cmd_line."
            "TranspilerHighPerformanceCmss"
        ) as MockTranspilerHighPerformanceCmss:
            mock_transpiler = MagicMock()
            MockTranspilerHighPerformanceCmss.return_value = mock_transpiler
            mock_transpiler.parse.return_value = {"000": (1, ["x"])}
            mock_transpiler.transpile.return_value = (
                [X([0])],
                None,
                None,
            )

            perf = CMSSTranspilerPerf()
            input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
            opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
            basis_gates = ["rx", "ry", "cx"]
            tech_type = Constant.TECH_TYPE_SUPERCONDUCTING
            config_file = (
                GLOBAL_CONFIGS["etc_dir"] + "/qcos/conf.d/spinq_rpc.toml"
            )

            runtime = perf.cmss_transpiler_perf_exec(
                input_file, opt_level, basis_gates, tech_type, config_file
            )
            assert runtime is not None

    def test_cmss_transpiler_perf_exec_by_non(self):
        with patch(
            "wy_qcos.transpiler.cmss.transpiler_cmd_line."
            "TranspilerHighPerformanceCmss"
        ) as MockTranspilerHighPerformanceCmss:
            mock_transpiler = MagicMock()
            MockTranspilerHighPerformanceCmss.return_value = mock_transpiler
            mock_transpiler.parse.return_value = {"000": (1, ["x"])}
            mock_transpiler.transpile.return_value = (
                [X([0])],
                None,
                None,
            )
            perf = CMSSTranspilerPerf()

            input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
            opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
            basis_gates = ["rx", "ry", "cx"]
            tech_type = ""
            config_file = (
                GLOBAL_CONFIGS["etc_dir"] + "/qcos/conf.d/spinq_rpc.toml"
            )

            runtime = perf.cmss_transpiler_perf_exec(
                input_file, opt_level, basis_gates, tech_type, config_file
            )
            assert runtime is not None

    def test_output_csv_file(self):
        perf = CMSSTranspilerPerf()
        perf.csv_file = ""
        assert perf.output_csv_file() is None

        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        file_path, _ = perf.check_file_args(
            input_file=input_file, output_file=""
        )
        qasm_data = perf.read_qasm_from_file(str(file_path))
        transpiler = TranspilerHighPerformanceCmss()
        src_code_info = {"000": qasm_data}
        parse_result = transpiler.parse(src_code_info)
        perf.parse_results[file_path] = list(parse_result.values())[0]
        perf.csv_file = "cmss_perf.csv"
        params = TranspileParams()
        params.file = Path(
            f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        ).resolve()
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "config.yaml",
        )
        perf.transpile_result[params] = TranspileRuntime()
        file_path = perf.output_csv_file()
        if file_path.exists():
            file_path.unlink()
        assert file_path is not None

    def test_enable_transpile_single_default(self):
        perf = CMSSTranspilerPerf()
        assert perf.enable_transpile_single is True

    @pytest.mark.parametrize(
        "conf_value,expected",
        [
            (True, True),
            (False, False),
        ],
    )
    def test_init_transpile_params_enable_transpile_single(
        self, conf_value, expected
    ):
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "enable_transpile_single": conf_value,
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "config_file": [
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"
                    ],
                },
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.enable_transpile_single is expected

    def test_init_transpile_params_enable_transpile_single_default(self):
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "config_file": [
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"
                    ],
                },
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.enable_transpile_single is True

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf.get_transpile_result"
    )
    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf.parse_file_args"
    )
    def test_main_cmss_transpiler_csv_with_single_raises(
        self, mock_parse_file_args, mock_get_transpile_result
    ):
        mock_parse_file_args.return_value = None
        mock_get_transpile_result.return_value = None
        perf = CMSSTranspilerPerf()
        conf_path = Path(GLOBAL_CONFIGS["temp_dir"]) / "csv_single_conf.toml"
        conf_path.write_text(
            "[transpile]\n"
            'csv_file = "cmss_perf.csv"\n'
            "enable_transpile_single = true\n"
            'files = ["./samples/qasm/2.0/simple-qasm.qasm"]\n'
            "[transpile.transpiler]\n"
            'base_gates = ["rx, ry, cx"]\n'
            "[transpile.optimize]\n"
            "opt_level = [1]\n"
            "[transpile.mapping]\n"
            'config_file = ["./etc/qcos/conf.d/spinq_rpc.toml"]\n',
            encoding="utf-8",
        )
        with pytest.raises(TranspilerException) as e:
            perf.main_cmss_transpiler(str(conf_path))
        assert "enable_transpile_single is true" in str(e.value)
        mock_get_transpile_result.assert_not_called()

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf.get_transpile_result"
    )
    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf.parse_file_args"
    )
    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf._init_csv_file"
    )
    def test_main_cmss_transpiler_csv_without_single_ok(
        self,
        mock_init_csv_file,
        mock_parse_file_args,
        mock_get_transpile_result,
    ):
        mock_parse_file_args.return_value = None
        mock_get_transpile_result.return_value = None
        mock_init_csv_file.return_value = None
        perf = CMSSTranspilerPerf()
        conf_path = Path(GLOBAL_CONFIGS["temp_dir"]) / "csv_nosingle_conf.toml"
        conf_path.write_text(
            "[transpile]\n"
            'csv_file = "cmss_perf.csv"\n'
            "enable_transpile_single = false\n"
            'files = ["./samples/qasm/2.0/simple-qasm.qasm"]\n'
            "[transpile.transpiler]\n"
            'base_gates = ["rx, ry, cx"]\n'
            "[transpile.optimize]\n"
            "opt_level = [1]\n"
            "[transpile.mapping]\n"
            'config_file = ["./etc/qcos/conf.d/spinq_rpc.toml"]\n',
            encoding="utf-8",
        )
        perf.main_cmss_transpiler(str(conf_path))
        assert perf.enable_transpile_single is False
        assert perf.csv_file == "cmss_perf.csv"
        mock_get_transpile_result.assert_called_once()
        mock_init_csv_file.assert_called_once()

    def _build_mock_transpiler_for_single(self):
        mock_transpiler = MagicMock()
        mock_transpiler.transpiler_options = {}
        mock_result = MagicMock()
        mock_result.timings = TranspileRuntime()
        mock_result.basis_gate_list = [X([0])]
        mock_result.num_qubits = 1
        mock_transpiler.transpile_single.return_value = mock_result
        return mock_transpiler

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "TranspilerHighPerformanceCmss"
    )
    def test_cmss_transpiler_perf_exec_uses_cpp_single(self, MockTranspiler):
        mock_transpiler = self._build_mock_transpiler_for_single()
        MockTranspiler.return_value = mock_transpiler

        perf = CMSSTranspilerPerf()
        perf.enable_transpile_single = True
        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        perf.cmss_transpiler_perf_exec(
            input_file=input_file,
            opt_level=Constant.DEFAULT_OPTIMIZATION_LEVEL,
            base_gates=["rx", "ry", "cx"],
            tech_type=Constant.TECH_TYPE_SUPERCONDUCTING,
            config_file=(
                GLOBAL_CONFIGS["etc_dir"] + "/qcos/conf.d/spinq_rpc.toml"
            ),
            sc_mapping_options={"routing_algorithm": "sabre"},
        )
        assert mock_transpiler.transpile_single.called
        assert not mock_transpiler.transpile.called

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "TranspilerHighPerformanceCmss"
    )
    def test_cmss_transpiler_perf_exec_single_disabled_skips_cpp(
        self, MockTranspiler
    ):
        mock_transpiler = MagicMock()
        mock_transpiler.transpiler_options = {}
        mock_transpiler.parse.return_value = {"000": (1, ["x"])}
        mock_transpiler.transpile.return_value = ([X([0])], None, None)
        MockTranspiler.return_value = mock_transpiler

        perf = CMSSTranspilerPerf()
        perf.enable_transpile_single = False
        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        runtime = perf.cmss_transpiler_perf_exec(
            input_file=input_file,
            opt_level=Constant.DEFAULT_OPTIMIZATION_LEVEL,
            base_gates=["rx", "ry", "cx"],
            tech_type=Constant.TECH_TYPE_SUPERCONDUCTING,
            config_file=(
                GLOBAL_CONFIGS["etc_dir"] + "/qcos/conf.d/spinq_rpc.toml"
            ),
            sc_mapping_options={"routing_algorithm": "sabre"},
        )
        assert not mock_transpiler.transpile_single.called
        assert mock_transpiler.transpile.called
        assert runtime.transpiled_gate_count == 1
        assert runtime.transpiled_depth > 0

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "TranspilerHighPerformanceCmss"
    )
    def test_cmss_transpiler_perf_exec_non_sabre_skips_cpp(
        self, MockTranspiler
    ):
        mock_transpiler = MagicMock()
        mock_transpiler.transpiler_options = {}
        mock_transpiler.parse.return_value = {"000": (1, ["x"])}
        mock_transpiler.transpile.return_value = ([X([0])], None, None)
        MockTranspiler.return_value = mock_transpiler

        perf = CMSSTranspilerPerf()
        perf.enable_transpile_single = True
        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        runtime = perf.cmss_transpiler_perf_exec(
            input_file=input_file,
            opt_level=Constant.DEFAULT_OPTIMIZATION_LEVEL,
            base_gates=["rx", "ry", "cx"],
            tech_type=Constant.TECH_TYPE_SUPERCONDUCTING,
            config_file=(
                GLOBAL_CONFIGS["etc_dir"] + "/qcos/conf.d/spinq_rpc.toml"
            ),
            sc_mapping_options={"routing_algorithm": "sc"},
        )
        assert not mock_transpiler.transpile_single.called
        assert mock_transpiler.transpile.called
        assert runtime.transpiled_gate_count == 1

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "TranspilerHighPerformanceCmss"
    )
    def test_cmss_transpiler_perf_exec_transpiled_stats_with_max_qubits(
        self, MockTranspiler
    ):
        mock_transpiler = MagicMock()
        mock_transpiler.transpiler_options = {}
        mock_transpiler.parse.return_value = {"000": (1, ["x"])}
        mock_transpiler.transpile.return_value = ([X([0])], None, None)
        MockTranspiler.return_value = mock_transpiler

        orig_max_qubits = trans_cfg_inst.get_max_qubits()
        trans_cfg_inst.set_max_qubits(5)
        try:
            perf = CMSSTranspilerPerf()
            perf.enable_transpile_single = False
            input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
            runtime = perf.cmss_transpiler_perf_exec(
                input_file=input_file,
                opt_level=Constant.DEFAULT_OPTIMIZATION_LEVEL,
                base_gates=["rx", "ry", "cx"],
                tech_type=Constant.TECH_TYPE_SUPERCONDUCTING,
                config_file=(
                    GLOBAL_CONFIGS["etc_dir"] + "/qcos/conf.d/spinq_rpc.toml"
                ),
                sc_mapping_options={"routing_algorithm": "sc"},
            )
            assert runtime.transpiled_gate_count == 1
            assert runtime.transpiled_depth > 0
        finally:
            trans_cfg_inst.set_max_qubits(orig_max_qubits)

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "TranspilerHighPerformanceCmss"
    )
    def test_cmss_transpiler_perf_exec_transpiled_stats_fallback_qubits(
        self, MockTranspiler
    ):
        mock_transpiler = MagicMock()
        mock_transpiler.transpiler_options = {}
        mock_transpiler.parse.return_value = {"000": (3, ["x"])}
        mock_transpiler.transpile.return_value = (
            [X([0]), X([4])],
            None,
            None,
        )
        MockTranspiler.return_value = mock_transpiler

        orig_max_qubits = trans_cfg_inst.get_max_qubits()
        trans_cfg_inst.set_max_qubits(0)
        try:
            perf = CMSSTranspilerPerf()
            perf.enable_transpile_single = False
            input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
            runtime = perf.cmss_transpiler_perf_exec(
                input_file=input_file,
                opt_level=Constant.DEFAULT_OPTIMIZATION_LEVEL,
                base_gates=["rx", "ry", "cx"],
                tech_type=Constant.TECH_TYPE_SUPERCONDUCTING,
                config_file=(
                    GLOBAL_CONFIGS["etc_dir"] + "/qcos/conf.d/spinq_rpc.toml"
                ),
                sc_mapping_options={"routing_algorithm": "sc"},
            )
            assert runtime.transpiled_gate_count == 2
            assert runtime.transpiled_depth > 0
        finally:
            trans_cfg_inst.set_max_qubits(orig_max_qubits)

    def test_ising_model_10_redundant_u_gates_analysis(self):
        """检查 ising_model_10 转译后是否仍存在可合并的连续 U 门.

        复现同事脚本发现的问题：优化后的门列表中同一量子比特上仍残留
        大量相邻 U 门，理论上应被优化器合并为单个 U 门。

        判定规则：
        - 同一量子比特上，两个 U 门之间仅夹杂 measure/barrier/reset 等
          非酉操作（这些操作不影响酉等价性），即可视为可合并。
        - 若两个 U 门之间夹杂了其他酉门（如 cz），则不可合并。
        """
        from pathlib import Path
        from collections import defaultdict
        from wy_qcos.common.config import Config

        qasm_file = (
            f"{self.samples_dir}/qasm/2.0/benchmark/compiler_qasm/"
            "ising_model_10.qasm"
        )
        if not Path(qasm_file).exists():
            pytest.skip(f"QASM file not found: {qasm_file}")

        config_file = f"{self.etc_dir}/topology/baihua_156.toml"

        chip_name = Path(config_file).stem
        extra_configs = Config.get_extra_configs()
        Config.load_config_file(config_file, extra_config=True)
        qpu_config = extra_configs[chip_name]["transpiler"]["qpu_configs"]

        orig_max_qubits = trans_cfg_inst.get_max_qubits()
        trans_cfg_inst.set_qpu_cfg(qpu_config)
        trans_cfg_inst.set_tech_type(Constant.TECH_TYPE_SUPERCONDUCTING)
        trans_cfg_inst.set_max_qubits(qpu_config["qubits"])

        try:
            perf = CMSSTranspilerPerf()
            qasm_data = perf.read_qasm_from_file(qasm_file)
            assert qasm_data is not None

            opt_level = 1
            basis_gates = ["u", "cz"]
            transpiler = TranspilerHighPerformanceCmss(
                optimization_level=opt_level
            )

            src_code_info = {"000": qasm_data}
            parse_result = transpiler.parse(src_code_info)
            transpiler.transpiler_options["enable_mapping"] = True
            transpiler.transpiler_options["sc_mapping_options"] = {
                "routing_algorithm": "sabre"
            }
            basis_gate_list, _, _ = transpiler.transpile(
                parse_result, basis_gates
            )

            # 门分类：酉门（u/cz）vs 非酉门（measure/barrier/reset/sync）
            NON_UNITARY = {"measure", "barrier", "reset", "sync"}
            u_gates = [g for g in basis_gate_list if g.name == "u"]

            # 按量子比特收集 U 门索引；中间若出现非酉门则不中断该链，
            # 若出现其他酉门（cz）则当前链结束，开启新链。
            qubit_runs = defaultdict(list)
            current_run = defaultdict(list)
            for idx, gate in enumerate(basis_gate_list):
                if gate.name in NON_UNITARY:
                    continue
                if gate.name == "u":
                    qubit = gate.targets[0]
                    current_run[qubit].append(idx)
                else:
                    affected = gate.targets
                    for q in affected:
                        if current_run[q]:
                            qubit_runs[q].append(current_run[q])
                            current_run[q] = []
            for q, run in current_run.items():
                if run:
                    qubit_runs[q].append(run)

            # 提取可合并的运行（长度 >= 2）
            mergable_runs = []
            for qubit, runs in qubit_runs.items():
                for run in runs:
                    if len(run) >= 2:
                        mergable_runs.append((qubit, run))

            # 统计可节省的门数
            total_mergable = sum(len(run) - 1 for _, run in mergable_runs)

            # 断言：优化后不应再存在可合并的连续 U 门
            assert len(u_gates) > 0, "Should have U gates"
            assert total_mergable == 0, (
                f"Optimizer left {len(mergable_runs)} mergable U-gate runs "
                f"({total_mergable} redundant U gates) on the same qubit "
                f"that could be combined into single U gates"
            )

        finally:
            trans_cfg_inst.set_max_qubits(orig_max_qubits)

    def test_init_transpile_params_unknown_driver_raises(self):
        """config_file 的 driver 不在支持的映射表中时应报错."""
        perf = CMSSTranspilerPerf()
        conf_path = Path(GLOBAL_CONFIGS["temp_dir"]) / "unknown_driver.toml"
        conf_path.write_text(
            '[unknown_chip]\nalias_name = "unknown driver chip"\n'
            'driver = "DriverUnknown"\n',
            encoding="utf-8",
        )
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "config_file": [str(conf_path)],
                },
            }
        }
        with pytest.raises(ValueError) as e:
            perf.init_transpile_params(extra_configs)
        assert "cannot infer tech_type" in str(e.value)

    def test_init_transpile_params_no_driver_raises(self):
        """config_file 无 driver 字段时无法判定 tech_type，应报错."""
        perf = CMSSTranspilerPerf()
        conf_path = Path(GLOBAL_CONFIGS["temp_dir"]) / "no_driver.toml"
        conf_path.write_text(
            '[unknown_chip]\nalias_name = "no driver chip"\nqubits = 4\n',
            encoding="utf-8",
        )
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "config_file": [str(conf_path)],
                },
            }
        }
        with pytest.raises(ValueError) as e:
            perf.init_transpile_params(extra_configs)
        assert "cannot infer tech_type" in str(e.value)

    def test_init_transpile_params_infer_sc_from_spinq_rpc(self):
        """spinq_rpc.toml 的 driver=DriverSpinQRpc 应推断为超导."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "config_file": [
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"
                    ],
                },
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.mapping_info == [
            (
                Constant.TECH_TYPE_SUPERCONDUCTING,
                f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml",
            )
        ]

    def test_init_transpile_params_tech_type_str(self):
        """tech_type 以字符串形式配置时应自动转为列表."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "tech_type": Constant.TECH_TYPE_SUPERCONDUCTING,
                    "config_file": [
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"
                    ],
                },
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.tech_type == [Constant.TECH_TYPE_SUPERCONDUCTING]

    def test_init_transpile_params_tech_type_sc_default_config(self):
        """只配置超导 tech_type 时应使用默认 spinq_rpc_156.toml."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "tech_type": [Constant.TECH_TYPE_SUPERCONDUCTING],
                },
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.tech_type == [Constant.TECH_TYPE_SUPERCONDUCTING]
        assert perf.mapping_config_file == [
            "./etc/topology/spinq_rpc_156.toml"
        ]

    def test_init_transpile_params_tech_type_na_default_config(self):
        """只配置中性原子 tech_type 时应使用默认 hanyuan1_100.toml."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cz"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "tech_type": [Constant.TECH_TYPE_NEUTRAL_ATOM],
                },
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.tech_type == [Constant.TECH_TYPE_NEUTRAL_ATOM]
        assert perf.mapping_config_file == ["./etc/topology/hanyuan1_100.toml"]

    def test_init_transpile_params_no_tech_no_config_raises(self):
        """tech_type 和 config_file 都未配置时应报错."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {},
            }
        }
        with pytest.raises(ValueError) as e:
            perf.init_transpile_params(extra_configs)
        assert "tech_type or config_file must be configured" in str(e.value)

    def test_init_transpile_params_tech_type_unsupported_raises(self):
        """不支持的 tech_type 应报错."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "tech_type": ["ion_trap"],
                },
            }
        }
        with pytest.raises(ValueError) as e:
            perf.init_transpile_params(extra_configs)
        assert "no default config_file for tech_type" in str(e.value)

    def test_init_transpile_params_tech_count_mismatch_raises(self):
        """tech_type 和 config_file 数量不匹配时应报错."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "tech_type": [
                        Constant.TECH_TYPE_SUPERCONDUCTING,
                        Constant.TECH_TYPE_NEUTRAL_ATOM,
                    ],
                    "config_file": [
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml",
                    ],
                },
            }
        }
        with pytest.raises(ValueError) as e:
            perf.init_transpile_params(extra_configs)
        assert "does not match config_file count" in str(e.value)

    def test_init_transpile_params_tech_config_mismatch_raises(self):
        """tech_type 与 config_file driver 不匹配时应报错."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "tech_type": [Constant.TECH_TYPE_NEUTRAL_ATOM],
                    "config_file": [
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"
                    ],
                },
            }
        }
        with pytest.raises(ValueError) as e:
            perf.init_transpile_params(extra_configs)
        assert "does not match config" in str(e.value)

    def test_init_transpile_params_config_file_str(self):
        """config_file 以字符串形式配置时应自动转为列表."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "config_file": (
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"
                    ),
                },
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.tech_type == [Constant.TECH_TYPE_SUPERCONDUCTING]

    def test_init_transpile_params_sc_mapping_empty_str(self):
        """sc_mapping_options 包含空字符串时应解析为空字典."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "config_file": [
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"
                    ],
                    "sc_mapping_options": [""],
                },
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.sc_mapping_options == [{}]

    def test_init_transpile_params_sc_mapping_too_many_raises(self):
        """sc_mapping_options 数量超过 config_file 数量时应报错."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "config_file": [
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"
                    ],
                    "sc_mapping_options": [
                        '{"routing_algorithm": "sabre"}',
                        '{"routing_algorithm": "sc"}',
                    ],
                },
            }
        }
        with pytest.raises(ValueError) as e:
            perf.init_transpile_params(extra_configs)
        assert "should not be more than" in str(e.value)

    def test_normalize_na_mapping_type_variants(self):
        """na_mapping_type 大小写不敏感."""
        assert (
            CMSSTranspilerPerf._normalize_na_mapping_type("default")
            == "default"
        )
        assert CMSSTranspilerPerf._normalize_na_mapping_type("zap") == "ZAP"
        assert CMSSTranspilerPerf._normalize_na_mapping_type("ZAP") == "ZAP"
        assert CMSSTranspilerPerf._normalize_na_mapping_type("zac") == "ZAC"
        assert CMSSTranspilerPerf._normalize_na_mapping_type(None) == "default"

    def test_normalize_na_mapping_type_invalid_raises(self):
        """无效的 na_mapping_type 应报错."""
        with pytest.raises(ValueError) as e:
            CMSSTranspilerPerf._normalize_na_mapping_type("invalid")
        assert "is not supported" in str(e.value)

    def test_infer_tech_type_config_read_error(self):
        """config_file 不存在时应返回 None."""
        result = CMSSTranspilerPerf._infer_tech_type_from_config(
            "/nonexistent/path/to/config.toml"
        )
        assert result is None

    def test_infer_tech_type_config_no_driver_field(self):
        """config_file 无 driver 字段时应返回 None."""
        conf_path = Path(GLOBAL_CONFIGS["temp_dir"]) / "no_driver.toml"
        conf_path.write_text(
            '[some_chip]\nalias_name = "no driver"\nqubits = 4\n',
            encoding="utf-8",
        )
        result = CMSSTranspilerPerf._infer_tech_type_from_config(
            str(conf_path)
        )
        assert result is None

    def test_check_file_args_output_exists(self):
        """output_file 已存在时应自动重命名."""
        perf = CMSSTranspilerPerf()
        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        output_file = str(
            Path(GLOBAL_CONFIGS["temp_dir"]) / "existing_output.log"
        )
        Path(output_file).write_text("existing", encoding="utf-8")

        mock_file_handler = MagicMock()
        with patch("logging.FileHandler", return_value=mock_file_handler):
            _, output_file_path = perf.check_file_args(input_file, output_file)
        assert output_file_path != Path(output_file).resolve()
        assert output_file_path.exists()

    def test_format_basis_gate_set(self):
        """_format_basis_gate_set 应正确格式化门集."""
        perf = CMSSTranspilerPerf()
        gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CX,
        ]
        result = perf._format_basis_gate_set(gates)
        assert "rx" in result
        assert "ry" in result
        assert "cx" in result
        assert perf._format_basis_gate_set([999]) == "?"

    def test_init_csv_file(self):
        """_init_csv_file 应正确创建 CSV 文件."""
        perf = CMSSTranspilerPerf()
        perf.csv_file = str(Path(GLOBAL_CONFIGS["temp_dir"]) / "test_init.csv")
        perf.enable_transpiler = True
        perf.enable_mapping = True
        csv_file_path = perf._init_csv_file()
        assert csv_file_path is not None
        assert csv_file_path.exists()

    def test_init_csv_file_empty_returns_none(self):
        """csv_file 为空时应返回 None."""
        perf = CMSSTranspilerPerf()
        perf.csv_file = ""
        assert perf._init_csv_file() is None

    def test_init_csv_file_not_csv_raises(self):
        """非 .csv 后缀文件应报错."""
        perf = CMSSTranspilerPerf()
        perf.csv_file = str(Path(GLOBAL_CONFIGS["temp_dir"]) / "test.txt")
        with pytest.raises(ValueError) as e:
            perf._init_csv_file()
        assert "is not a csv file" in str(e.value)

    def test_init_csv_file_exists_renamed(self):
        """已存在的 CSV 文件应自动重命名."""
        perf = CMSSTranspilerPerf()
        csv_path = Path(GLOBAL_CONFIGS["temp_dir"]) / "existing.csv"
        csv_path.write_text("existing", encoding="utf-8")
        perf.csv_file = str(csv_path)
        perf.enable_transpiler = True
        perf.enable_mapping = True
        csv_file_path = perf._init_csv_file()
        assert csv_file_path != csv_path.resolve()

    def test_build_csv_error_row_with_parse_results(self):
        """_build_csv_error_row 有 parse_results 时应计算 depth."""
        perf = CMSSTranspilerPerf()
        perf.enable_transpiler = True
        perf.enable_mapping = True
        params = TranspileParams()
        params.file = Path("test.qasm")
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "config.toml",
        )
        params.opt_level = 1
        perf.parse_results[params.file] = (2, [X([0])])
        row = perf._build_csv_error_row(params, "test error")
        assert row[1] == 2
        assert row[6] == "test error"

    def test_build_csv_error_row_no_transpiler(self):
        """enable_transpiler=False 时错误行结构正确."""
        perf = CMSSTranspilerPerf()
        perf.enable_transpiler = False
        perf.enable_mapping = True
        params = TranspileParams()
        params.file = Path("test.qasm")
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "config.toml",
        )
        params.opt_level = 1
        row = perf._build_csv_error_row(params, "error")
        assert len(row) > 7

    def test_build_csv_error_row_no_mapping(self):
        """enable_mapping=False 时错误行结构正确."""
        perf = CMSSTranspilerPerf()
        perf.enable_transpiler = True
        perf.enable_mapping = False
        params = TranspileParams()
        params.file = Path("test.qasm")
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "config.toml",
        )
        params.opt_level = 1
        row = perf._build_csv_error_row(params, "error")
        assert len(row) > 7

    def test_build_csv_row_with_mapping(self):
        """_build_csv_row transpiler+mapping 都启用."""
        params = TranspileParams()
        params.file = Path("test.qasm")
        params.num_qubits = 2
        params.depth = 3
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "config.toml",
        )
        params.opt_level = 1
        runtime = TranspileRuntime()
        parse_results = {params.file: (2, [X([0])])}
        row = CMSSTranspilerPerf._build_csv_row(
            params, runtime, parse_results, True, True
        )
        assert len(row) > 7

    def test_build_csv_row_no_transpiler(self):
        """_build_csv_row enable_transpiler=False 分支."""
        params = TranspileParams()
        params.file = Path("test.qasm")
        params.num_qubits = 2
        params.depth = 3
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "config.toml",
        )
        params.opt_level = 1
        runtime = TranspileRuntime()
        parse_results = {params.file: (2, [X([0])])}
        row = CMSSTranspilerPerf._build_csv_row(
            params, runtime, parse_results, False, True
        )
        assert len(row) == 8

    def test_build_csv_row_no_mapping(self):
        """_build_csv_row enable_mapping=False 分支."""
        params = TranspileParams()
        params.file = Path("test.qasm")
        params.num_qubits = 2
        params.depth = 3
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "config.toml",
        )
        params.opt_level = 1
        runtime = TranspileRuntime()
        parse_results = {params.file: (2, [X([0])])}
        row = CMSSTranspilerPerf._build_csv_row(
            params, runtime, parse_results, True, False
        )
        assert len(row) == 17

    def test_get_csv_titles_all_enabled(self):
        """_get_csv_titles transpiler+mapping 都启用."""
        titles = CMSSTranspilerPerf._get_csv_titles(True, True)
        assert len(titles) > 7

    def test_get_csv_titles_no_transpiler(self):
        """_get_csv_titles enable_transpiler=False."""
        titles = CMSSTranspilerPerf._get_csv_titles(False, True)
        assert len(titles) == 9

    def test_get_csv_titles_no_mapping(self):
        """_get_csv_titles enable_mapping=False."""
        titles = CMSSTranspilerPerf._get_csv_titles(True, False)
        assert len(titles) == 18

    def test_pre_scan_file(self):
        """_pre_scan_file 应返回正确的比特数和门数."""
        perf = CMSSTranspilerPerf()
        file_path = Path(f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm")
        num_qubits, gate_count = perf._pre_scan_file(file_path)
        assert num_qubits > 0
        assert gate_count > 0

    def test_pre_scan_file_invalid(self):
        """_pre_scan_file 无效文件应返回 (0, 0)."""
        perf = CMSSTranspilerPerf()
        result = perf._pre_scan_file(Path("/nonexistent/file.qasm"))
        assert result == (0, 0)

    def test_sort_files_by_scale(self):
        """_sort_files_by_scale 应按规模排序."""
        perf = CMSSTranspilerPerf()
        perf.total_files = [
            Path(f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"),
        ]
        perf._sort_files_by_scale()
        assert len(perf.total_files) == 1

    def test_output_qasm_file(self):
        """output_qasm_file 应正确写出 qasm 文件."""
        perf = CMSSTranspilerPerf()
        perf.qasm_output_dir = GLOBAL_CONFIGS["temp_dir"]
        perf.qasm_version = "2.0"
        qc = QuantumCircuit(num_qubits=2)
        qc.append_operations([X([0])])
        input_file = Path(f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm")
        perf.output_qasm_file(
            qc, input_file, 1, Constant.TECH_TYPE_SUPERCONDUCTING
        )
        out_file = (
            Path(GLOBAL_CONFIGS["temp_dir"])
            / f"{input_file.stem}_superconducting_opt1.qasm"
        )
        assert out_file.exists()

    def test_output_qasm_file_no_dir(self):
        """output_qasm_file 无指定目录时写到输入文件旁."""
        perf = CMSSTranspilerPerf()
        perf.qasm_output_dir = ""
        perf.qasm_version = "2.0"
        qc = QuantumCircuit(num_qubits=2)
        qc.append_operations([X([0])])
        input_file = Path(f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm")
        perf.output_qasm_file(
            qc, input_file, 0, Constant.TECH_TYPE_NEUTRAL_ATOM
        )
        out_file = (
            input_file.resolve().parent
            / f"{input_file.stem}_neutral_atom_opt0.qasm"
        )
        assert out_file.exists()
        out_file.unlink()

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf.cmss_transpiler_perf_exec"
    )
    def test_get_transpile_result_tmax_skip(self, mock_exec):
        """Tmax 超时后应跳过后续组合."""
        runtime = TranspileRuntime()
        runtime.total_time = 100.0
        mock_exec.return_value = runtime
        perf = CMSSTranspilerPerf()
        perf.tmax = 1
        perf.na_mapping_type = "default"
        perf.total_files = [Path("file1.qasm")]
        params = TranspileParams()
        params.file = Path("file1.qasm")
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "1",
        )
        perf.params_list.append(params)
        perf.params_list.append(params)
        perf.get_transpile_result()

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf.cmss_transpiler_perf_exec"
    )
    def test_get_transpile_result_failed_params(self, mock_exec):
        """Transpile 失败时应记录 failed_params."""
        mock_exec.side_effect = Exception("transpile error")
        perf = CMSSTranspilerPerf()
        perf.na_mapping_type = "default"
        perf.total_files = [Path("file1.qasm")]
        params = TranspileParams()
        params.file = Path("file1.qasm")
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "1",
        )
        perf.params_list.append(params)
        perf.get_transpile_result()

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "TranspilerHighPerformanceCmss"
    )
    def test_cmss_transpiler_perf_exec_enable_detail_true(
        self, MockTranspiler
    ):
        """enable_detail=True 时输出完整日志."""
        mock_transpiler = MagicMock()
        mock_transpiler.transpiler_options = {}
        mock_transpiler.parse.return_value = {"000": (1, ["x"])}
        mock_transpiler.transpile.return_value = ([X([0])], None, None)
        MockTranspiler.return_value = mock_transpiler

        perf = CMSSTranspilerPerf()
        perf.enable_transpile_single = False
        perf.enable_detail = True
        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        runtime = perf.cmss_transpiler_perf_exec(
            input_file=input_file,
            opt_level=Constant.DEFAULT_OPTIMIZATION_LEVEL,
            base_gates=["rx", "ry", "cx"],
            tech_type=Constant.TECH_TYPE_SUPERCONDUCTING,
            config_file=(f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"),
            sc_mapping_options={"routing_algorithm": "sc"},
        )
        assert runtime is not None

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "TranspilerHighPerformanceCmss"
    )
    def test_cmss_transpiler_perf_exec_output_qasm_enabled(
        self, MockTranspiler
    ):
        """enable_output_qasm=True 时应写出 qasm 文件."""
        mock_transpiler = MagicMock()
        mock_transpiler.transpiler_options = {}
        mock_transpiler.parse.return_value = {"000": (1, ["x"])}
        mock_transpiler.transpile.return_value = (
            [X([0])],
            None,
            None,
        )
        MockTranspiler.return_value = mock_transpiler

        perf = CMSSTranspilerPerf()
        perf.enable_transpile_single = False
        perf.enable_output_qasm = True
        perf.qasm_output_dir = GLOBAL_CONFIGS["temp_dir"]
        perf.qasm_version = "2.0"
        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        perf.cmss_transpiler_perf_exec(
            input_file=input_file,
            opt_level=Constant.DEFAULT_OPTIMIZATION_LEVEL,
            base_gates=["rx", "ry", "cx"],
            tech_type=Constant.TECH_TYPE_SUPERCONDUCTING,
            config_file=(f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"),
            sc_mapping_options={"routing_algorithm": "sc"},
        )

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "TranspilerHighPerformanceCmss"
    )
    def test_cmss_transpiler_perf_exec_cpp_enable_detail(self, MockTranspiler):
        """C++ 路径 enable_detail=True 时输出完整日志."""
        mock_transpiler = MagicMock()
        mock_transpiler.transpiler_options = {}
        mock_result = MagicMock()
        mock_result.timings = TranspileRuntime()
        mock_result.basis_gate_list = [X([0])]
        mock_result.num_qubits = 1
        mock_transpiler.transpile_single.return_value = mock_result
        MockTranspiler.return_value = mock_transpiler

        perf = CMSSTranspilerPerf()
        perf.enable_transpile_single = True
        perf.enable_detail = True
        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        perf.cmss_transpiler_perf_exec(
            input_file=input_file,
            opt_level=Constant.DEFAULT_OPTIMIZATION_LEVEL,
            base_gates=["rx", "ry", "cx"],
            tech_type=Constant.TECH_TYPE_SUPERCONDUCTING,
            config_file=(f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"),
            sc_mapping_options={"routing_algorithm": "sabre"},
        )
        assert mock_transpiler.transpile_single.called

    def test_parse_file_args_dir_not_directory_raises(self):
        """Dir 指向文件而非目录时应报错."""
        perf = CMSSTranspilerPerf()
        perf.file_list = []
        perf.dir_list = [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"]
        perf.total_files = [1]
        with pytest.raises(ValueError) as e:
            perf.parse_file_args()
        assert "is not a valid directory" in str(e.value)

    def test_parse_file_args_file_is_directory_raises(self):
        """File 指向目录而非文件时应报错."""
        perf = CMSSTranspilerPerf()
        perf.file_list = [f"{self.samples_dir}/qasm/2.0"]
        perf.dir_list = []
        perf.total_files = [1]
        with pytest.raises(ValueError) as e:
            perf.parse_file_args()
        assert "is not a valid file" in str(e.value)

    def test_parse_file_args_no_valid_input_raises(self):
        """无有效输入文件时应报错."""
        perf = CMSSTranspilerPerf()
        perf.file_list = []
        perf.dir_list = []
        with pytest.raises(ValueError) as e:
            perf.parse_file_args()
        assert "no valid input file" in str(e.value)

    def test_init_transpile_params_base_gates_empty_default(self):
        """base_gates 未配置时应设置为 [()] 空占位."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "config_file": [
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"
                    ],
                },
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.base_gates == [()]

    def test_init_transpile_params_base_gates_unsupported_raises(self):
        """不支持的 gate 应报错."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["invalid_gate"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "config_file": [
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"
                    ],
                },
            }
        }
        with pytest.raises(ValueError) as e:
            perf.init_transpile_params(extra_configs)
        assert "is not supported" in str(e.value)

    def test_init_transpile_params_enable_detail(self):
        """enable_detail 配置应正确读取."""
        perf = CMSSTranspilerPerf()
        extra_configs = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "enable_detail": True,
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "config_file": [
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"
                    ],
                },
            }
        }
        perf.init_transpile_params(extra_configs)
        assert perf.enable_detail is True

    def test_output_csv_file_no_transpiler(self):
        """output_csv_file enable_transpiler=False 分支."""
        perf = CMSSTranspilerPerf()
        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        file_path, _ = perf.check_file_args(input_file, "")
        qasm_data = perf.read_qasm_from_file(str(file_path))
        transpiler = TranspilerHighPerformanceCmss()
        parse_result = transpiler.parse({"000": qasm_data})
        perf.parse_results[file_path] = list(parse_result.values())[0]
        perf.csv_file = str(
            Path(GLOBAL_CONFIGS["temp_dir"]) / "test_no_transpiler.csv"
        )
        perf.enable_transpiler = False
        perf.enable_mapping = True
        params = TranspileParams()
        params.file = file_path
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "config.yaml",
        )
        perf.transpile_result[params] = TranspileRuntime()
        result_path = perf.output_csv_file()
        assert result_path is not None
        assert result_path.exists()

    def test_output_csv_file_no_mapping(self):
        """output_csv_file enable_mapping=False 分支."""
        perf = CMSSTranspilerPerf()
        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        file_path, _ = perf.check_file_args(input_file, "")
        qasm_data = perf.read_qasm_from_file(str(file_path))
        transpiler = TranspilerHighPerformanceCmss()
        parse_result = transpiler.parse({"000": qasm_data})
        perf.parse_results[file_path] = list(parse_result.values())[0]
        perf.csv_file = str(
            Path(GLOBAL_CONFIGS["temp_dir"]) / "test_no_mapping.csv"
        )
        perf.enable_transpiler = True
        perf.enable_mapping = False
        params = TranspileParams()
        params.file = file_path
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "config.yaml",
        )
        perf.transpile_result[params] = TranspileRuntime()
        result_path = perf.output_csv_file()
        assert result_path is not None
        assert result_path.exists()


# ──────────────────────────────────────────────
# run_count config tests
# ──────────────────────────────────────────────
@pytest.mark.usefixtures("global_configs")
class TestRunCountConfig:
    @classmethod
    def setup_class(cls):
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        cls.etc_dir = GLOBAL_CONFIGS["etc_dir"]

    def _base_configs(self, **overrides):
        cfg = {
            "transpile": {
                "files": [f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"],
                "transpiler": {"base_gates": ["rx, ry, cx"]},
                "optimize": {"opt_level": [1]},
                "mapping": {
                    "config_file": [
                        f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"
                    ],
                },
            }
        }
        cfg["transpile"].update(overrides)
        return cfg

    def test_run_count_default(self):
        """run_count 未配置时默认为 1."""
        perf = CMSSTranspilerPerf()
        perf.init_transpile_params(self._base_configs())
        assert perf.run_count == 1

    def test_run_count_below_one_clamped(self):
        """run_count < 1 时强制为 1."""
        perf = CMSSTranspilerPerf()
        perf.init_transpile_params(self._base_configs(run_count=0))
        assert perf.run_count == 1

    def test_run_count_negative_clamped(self):
        """run_count 为负数时强制为 1."""
        perf = CMSSTranspilerPerf()
        perf.init_transpile_params(self._base_configs(run_count=-3))
        assert perf.run_count == 1

    def test_run_count_normal(self):
        """run_count 正常值保留."""
        perf = CMSSTranspilerPerf()
        perf.init_transpile_params(self._base_configs(run_count=5))
        assert perf.run_count == 5


# ──────────────────────────────────────────────
# _log_runtime_perf tests
# ──────────────────────────────────────────────
class TestLogRuntimePerfCmss:
    def test_log_runtime_perf_detail_true(self):
        """enable_detail=True → outputs all stage labels."""
        runtime = TranspileRuntime()
        runtime.parse_time = 0.01
        runtime.opt_time1 = 0.02
        runtime.transpile_time = 0.05
        runtime.total_time = 0.08
        with patch(
            "wy_qcos.transpiler.cmss.transpiler_cmd_line.log_perf"
        ) as mock_log:
            perf = CMSSTranspilerPerf()
            perf.enable_detail = True
            perf._log_runtime_perf(runtime)
            assert mock_log.call_count >= 5
            logged = " ".join(str(c) for c in mock_log.call_args_list)
            assert "0.0100" in logged
            assert "0.0800" in logged

    def test_log_runtime_perf_detail_false(self):
        """enable_detail=False → outputs only parse and total."""
        runtime = TranspileRuntime()
        runtime.parse_time = 0.01
        runtime.total_time = 0.06
        with patch(
            "wy_qcos.transpiler.cmss.transpiler_cmd_line.log_perf"
        ) as mock_log:
            perf = CMSSTranspilerPerf()
            perf.enable_detail = False
            perf._log_runtime_perf(runtime)
            logged = " ".join(str(c) for c in mock_log.call_args_list)
            assert "0.0100" in logged
            assert "0.0600" in logged
            assert "opt_time1" not in logged


# ──────────────────────────────────────────────
# get_transpile_result with run_count tests
# ──────────────────────────────────────────────
@pytest.mark.usefixtures("global_configs")
class TestGetTranspileResultRunCountCmss:
    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf.cmss_transpiler_perf_exec"
    )
    def test_run_count_one_calls_exec_once(self, mock_exec):
        """run_count=1 → exec called once, suppress_perf=False."""
        mock_exec.return_value = TranspileRuntime()
        perf = CMSSTranspilerPerf()
        perf.run_count = 1
        perf.na_mapping_type = "default"
        perf.total_files = [Path("file1.qasm")]
        params = TranspileParams()
        params.file = Path("file1.qasm")
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "1",
        )
        perf.params_list = [params]
        perf.get_transpile_result()
        assert mock_exec.call_count == 1
        _, kwargs = mock_exec.call_args
        assert kwargs.get("suppress_perf") is False

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf.cmss_transpiler_perf_exec"
    )
    @patch("wy_qcos.transpiler.cmss.transpiler_cmd_line.log_perf")
    def test_run_count_gt_one_picks_shortest(self, mock_log_perf, mock_exec):
        """run_count>1 picks shortest total_time.

        Each run prints its total time; average is printed at end.
        exec called run_count times, suppress_perf=True.
        """
        r1 = TranspileRuntime()
        r1.total_time = 5.0
        r2 = TranspileRuntime()
        r2.total_time = 2.0
        r3 = TranspileRuntime()
        r3.total_time = 8.0
        mock_exec.side_effect = [r1, r2, r3]

        perf = CMSSTranspilerPerf()
        perf.run_count = 3
        perf.na_mapping_type = "default"
        perf.total_files = [Path("file1.qasm")]
        params = TranspileParams()
        params.file = Path("file1.qasm")
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "1",
        )
        perf.params_list = [params]
        perf.get_transpile_result()

        assert mock_exec.call_count == 3
        for call in mock_exec.call_args_list:
            _, kwargs = call
            assert kwargs.get("suppress_perf") is True
        best = perf.transpile_result[params]
        assert best.total_time == 2.0

        total_msgs = [
            call.args[1]
            for call in mock_log_perf.call_args_list
            if "total running time of cmss-transpiler" in call.args[1]
        ]
        assert len(total_msgs) == 4
        assert "5.0000s" in total_msgs[0]
        assert "2.0000s" in total_msgs[1]
        assert "8.0000s" in total_msgs[2]
        assert "average" in total_msgs[3]
        assert "5.0000s" in total_msgs[3]

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmd_line."
        "CMSSTranspilerPerf.cmss_transpiler_perf_exec"
    )
    def test_run_count_failure_sets_error(self, mock_exec):
        """When exec raises, failed_params is populated."""
        mock_exec.side_effect = Exception("boom")
        perf = CMSSTranspilerPerf()
        perf.run_count = 2
        perf.na_mapping_type = "default"
        perf.total_files = [Path("file1.qasm")]
        params = TranspileParams()
        params.file = Path("file1.qasm")
        params.mapping_info = (
            Constant.TECH_TYPE_SUPERCONDUCTING,
            "1",
        )
        perf.params_list = [params]
        perf.transpile_result[params] = None
        perf.get_transpile_result()
        assert perf.transpile_result[params] is None


# ──────────────────────────────────────────────
# suppress_perf tests on cmss_transpiler_perf_exec
# ──────────────────────────────────────────────
@pytest.mark.usefixtures("global_configs")
class TestSuppressPerfCmss:
    @classmethod
    def setup_class(cls):
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        cls.etc_dir = GLOBAL_CONFIGS["etc_dir"]

    @patch("wy_qcos.transpiler.cmss.transpiler_cmd_line.log_perf")
    def test_suppress_perf_skips_log(self, mock_log_perf):
        """suppress_perf=True → log_perf not called inside exec."""
        with patch(
            "wy_qcos.transpiler.cmss.transpiler_cmd_line."
            "TranspilerHighPerformanceCmss"
        ) as MockTranspiler:
            mock_transpiler = MagicMock()
            mock_transpiler.transpiler_options = {}
            mock_transpiler.parse.return_value = {"000": (1, ["x"])}
            mock_transpiler.transpile.return_value = (
                [X([0])],
                None,
                None,
            )
            MockTranspiler.return_value = mock_transpiler

            perf = CMSSTranspilerPerf()
            perf.enable_transpile_single = False
            input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
            perf.cmss_transpiler_perf_exec(
                input_file=input_file,
                opt_level=Constant.DEFAULT_OPTIMIZATION_LEVEL,
                base_gates=["rx", "ry", "cx"],
                tech_type=Constant.TECH_TYPE_SUPERCONDUCTING,
                config_file=(f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"),
                sc_mapping_options={"routing_algorithm": "sc"},
                suppress_perf=True,
            )
            mock_log_perf.assert_not_called()

    @patch("wy_qcos.transpiler.cmss.transpiler_cmd_line.log_perf")
    def test_no_suppress_emits_log(self, mock_log_perf):
        """suppress_perf=False (default) → log_perf is called."""
        with patch(
            "wy_qcos.transpiler.cmss.transpiler_cmd_line."
            "TranspilerHighPerformanceCmss"
        ) as MockTranspiler:
            mock_transpiler = MagicMock()
            mock_transpiler.transpiler_options = {}
            mock_transpiler.parse.return_value = {"000": (1, ["x"])}
            mock_transpiler.transpile.return_value = (
                [X([0])],
                None,
                None,
            )
            MockTranspiler.return_value = mock_transpiler

            perf = CMSSTranspilerPerf()
            perf.enable_transpile_single = False
            input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
            perf.cmss_transpiler_perf_exec(
                input_file=input_file,
                opt_level=Constant.DEFAULT_OPTIMIZATION_LEVEL,
                base_gates=["rx", "ry", "cx"],
                tech_type=Constant.TECH_TYPE_SUPERCONDUCTING,
                config_file=(f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml"),
                sc_mapping_options={"routing_algorithm": "sc"},
                suppress_perf=False,
            )
            assert mock_log_perf.call_count > 0
