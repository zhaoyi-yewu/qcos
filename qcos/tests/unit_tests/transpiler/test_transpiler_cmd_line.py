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

import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock, mock_open

from qcos.common.constant import Constant
from qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS
from qcos.transpiler.cmss.transpiler_cmd_line import (
    read_qasm_from_file,
    Timer,
    main_cmss_transpiler as main,
    main as cmss_main,
    get_parse_args,
    check_file_args,
)

timer = Timer()


@pytest.mark.usefixtures("global_configs")
class TestTranspilerCmdLine:
    @classmethod
    def setup_class(cls):
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        cls.etc_dir = GLOBAL_CONFIGS["etc_dir"]

    def test_read_qasm_from_file(self):
        read_qasm_from_file("None")

    @patch("qcos.transpiler.cmss.transpiler_cmd_line.decompose_gates")
    @patch("qcos.transpiler.cmss.transpiler_cmd_line.optimize_gate")
    @patch("qcos.transpiler.cmss.transpiler_cmd_line.get_ir")
    @patch("qcos.transpiler.cmss.transpiler_cmd_line.get_abs_tree")
    def test_main(
        self,
        mock_get_abs_tree,
        mock_get_ir,
        mock_optimize_gate,
        mock_decompose_gates,
    ):
        mock_obj = MagicMock()
        mock_obj.get_operations.return_value = None

        mock_get_abs_tree.return_value = None
        mock_get_ir.return_value = mock_obj
        mock_optimize_gate.return_value = None
        mock_decompose_gates.return_value = None
        default_input_file = (
            f"{self.samples_dir}/qasm/3.0/benchmark/100bits_50000d.qasm"
        )
        default_output_file = ""
        res = main(
            input_file=default_input_file, output_file=default_output_file
        )
        assert res is True

    def test_cmss_transpiler_tech_na(self):
        qasm_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        output_file = ""
        opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
        tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        config_file = f"{self.etc_dir}/qcos/conf.d/hanyuan1.toml"
        res = main(
            input_file=qasm_file,
            output_file=output_file,
            opt_level=opt_level,
            tech_type=tech_type,
            config_file=config_file,
        )
        assert res is True

    @patch(
        "qcos.transpiler.cmss.mapping.initial_mapping."
        "sc_initial_mapping.topgraph_mapping"
    )
    def test_cmss_transpiler_tech_sc(self, mock_topgraph_mapping):
        # Mock topgraph_mapping to return a valid mapping
        # instead of [None, None]
        def mock_mapping(dependency_graph, coupling_graph):
            # Return naive mapping which is always valid
            num_q = dependency_graph.get_dg_num_q()
            return list(range(num_q))

        mock_topgraph_mapping.side_effect = mock_mapping

        qasm_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        output_file = ""
        opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
        res = main(
            input_file=qasm_file,
            output_file=output_file,
            opt_level=opt_level,
            tech_type=Constant.TECH_TYPE_SUPERCONDUCTING,
            config_file=f"{self.etc_dir}/qcos/conf.d/spinq_rpc.toml",
        )
        assert res is True

    def test_cmss_transpiler_notech(self):
        qasm_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        output_file = ""
        opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
        res = main(
            input_file=qasm_file,
            output_file=output_file,
            opt_level=opt_level,
            tech_type="",
            config_file="",
        )
        assert res is True

    @patch("qcos.transpiler.cmss.transpiler_cmd_line.main_cmss_transpiler")
    def test_qiskit_parse_args(self, mock_main_cmss_transpiler):
        sys.argv = [
            "transpiler_cmd_line.py",
            "--input-file",
            f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm",
        ]
        cmss_args = get_parse_args()
        assert (
            cmss_args["input_file"]
            == f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        )
        assert cmss_args["output_file"] == ""
        assert cmss_args["opt_level"] == Constant.DEFAULT_OPTIMIZATION_LEVEL

        mock_main_cmss_transpiler.return_value = True
        with patch("sys.exit") as mock_sys_exit:
            cmss_main(sys.argv)
            mock_sys_exit.assert_called_with(mock_main_cmss_transpiler())

    def test_check_file_args(self):
        input_file1 = f"{self.samples_dir}/qasm/2.0/simple-qasm1.qasm"
        assert check_file_args(input_file1, "") is None

        input_file = f"{self.samples_dir}/qasm/2.0/simple-qasm.qasm"
        output_file = "CHANGELOG"
        output_file_path = Path(output_file).resolve()
        mock_file = mock_open()
        mock_file_handler = MagicMock()
        with (
            patch("builtins.open", mock_file),
            patch("logging.FileHandler", return_value=mock_file_handler),
            patch("logging.Logger.addHandler") as mock_add_handler,
        ):
            res = check_file_args(input_file, output_file)
            mock_file.assert_called_once_with(
                output_file_path, "w", encoding="utf-8"
            )
            mock_file().write.assert_called_once_with(
                f"testing file: {input_file}\n"
            )
            mock_add_handler.assert_called_once_with(mock_file_handler)
            assert res == Path(input_file).resolve()
