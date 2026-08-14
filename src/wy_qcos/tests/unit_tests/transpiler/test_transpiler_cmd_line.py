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
from wy_qcos.transpiler.high_performance import TranspileTimings
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
        perf.run_count = 2
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
            mock_transpiler = MagicMock()
            MockTranspilerHighPerformanceCmss.return_value = mock_transpiler
            mock_transpiler.parse.return_value = {"000": (1, ["x"])}
            mock_transpiler.transpile.return_value = (
                [X([0])],
                None,
            )
            mock_result = MagicMock()
            mock_result.timings = TranspileTimings()
            mock_transpiler.transpile_single.return_value = mock_result

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
                    "tech_type": ["superconducting"],
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
                    "tech_type": ["superconducting"],
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
            'tech_type = ["superconducting"]\n'
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
        "CMSSTranspilerPerf.output_csv_file"
    )
    def test_main_cmss_transpiler_csv_without_single_ok(
        self,
        mock_output_csv_file,
        mock_parse_file_args,
        mock_get_transpile_result,
    ):
        mock_parse_file_args.return_value = None
        mock_get_transpile_result.return_value = None
        mock_output_csv_file.return_value = None
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
            'tech_type = ["superconducting"]\n'
            'config_file = ["./etc/qcos/conf.d/spinq_rpc.toml"]\n',
            encoding="utf-8",
        )
        perf.main_cmss_transpiler(str(conf_path))
        assert perf.enable_transpile_single is False
        assert perf.csv_file == "cmss_perf.csv"
        mock_get_transpile_result.assert_called_once()
        mock_output_csv_file.assert_called_once()

    def _build_mock_transpiler_for_single(self):
        mock_transpiler = MagicMock()
        mock_transpiler.transpiler_options = {}
        mock_result = MagicMock()
        mock_result.timings = TranspileRuntime()
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
        mock_transpiler.transpile.return_value = ([X([0])], None)
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
        mock_transpiler.transpile.return_value = ([X([0])], None)
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
        mock_transpiler.transpile.return_value = ([X([0])], None)
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
        mock_transpiler.transpile.return_value = ([X([0])], None)
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
            assert runtime.transpiled_gate_count == 1
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
            basis_gate_list, _ = transpiler.transpile(
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
