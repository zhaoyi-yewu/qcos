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
from wy_qcos.transpiler.common.utils import (
    Timer,
    TranspileRuntime,
    trans_logger,
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

        trans_logger.set_allowed_tags(["PERF", "WARNING", "ERROR"])
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
        trans_logger.set_allowed_tags(["PERF", "WARNING", "ERROR"])
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
        trans_logger.set_allowed_tags(["PERF", "WARNING", "ERROR"])
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
            "wy_qcos.transpiler.cmss.transpiler_cmd_line.TranspilerHighPerformanceCmss"
        ) as MockTranspilerHighPerformanceCmss:
            mock_transpiler = MagicMock()
            MockTranspilerHighPerformanceCmss.return_value = mock_transpiler
            mock_transpiler.parse.return_value = {"000": (1, ["x"])}
            mock_transpiler.transpile.return_value = (
                "transpiled_circuit",
                None,
            )
            trans_logger.set_allowed_tags(["PERF", "WARNING", "ERROR"])
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
            "wy_qcos.transpiler.cmss.transpiler_cmd_line.TranspilerHighPerformanceCmss"
        ) as MockTranspilerHighPerformanceCmss:
            mock_transpiler = MagicMock()
            MockTranspilerHighPerformanceCmss.return_value = mock_transpiler
            mock_transpiler.parse.return_value = {"000": (1, ["x"])}
            mock_transpiler.transpile.return_value = (
                "transpiled_circuit",
                None,
            )
            trans_logger.set_allowed_tags(["PERF", "WARNING", "ERROR"])
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
            "wy_qcos.transpiler.cmss.transpiler_cmd_line.TranspilerHighPerformanceCmss"
        ) as MockTranspilerHighPerformanceCmss:
            mock_transpiler = MagicMock()
            MockTranspilerHighPerformanceCmss.return_value = mock_transpiler
            mock_transpiler.parse.return_value = {"000": (1, ["x"])}
            mock_transpiler.transpile.return_value = (
                "transpiled_circuit",
                None,
            )
            perf = CMSSTranspilerPerf()
            trans_logger.set_allowed_tags(["PERF", "WARNING", "ERROR"])
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
