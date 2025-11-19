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
from qcos.transpiler.cmss.transpiler_cmd_line import (
    read_qasm_from_file,
    Timer,
    main,
)

timer = Timer()


@pytest.mark.usefixtures("global_configs")
class TestTranspilerCmdLine:
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
        mock_get_abs_tree.return_value = None
        mock_get_ir.return_value = (None, None)
        mock_optimize_gate.return_value = None
        mock_decompose_gates.return_value = None
        default_input_file = "samples/qasm/3.0/benchmark/100bits_50000d.qasm"
        default_output_file = ""
        res = main(
            input_file=default_input_file, output_file=default_output_file
        )
        assert res is True

    def test_cmss_transpiler_tech_na(self):
        self.qasm_path = GLOBAL_CONFIGS["samples_dir"]
        qasm_file = f"{self.qasm_path}/qasm/2.0/simple-qasm.qasm"
        output_file = ""
        opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
        tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        config_file = "etc/qcos/conf.d/hanyuan1.toml"
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

        self.qasm_path = GLOBAL_CONFIGS["samples_dir"]
        qasm_file = f"{self.qasm_path}/qasm/2.0/simple-qasm.qasm"
        output_file = ""
        opt_level = Constant.DEFAULT_OPTIMIZATION_LEVEL
        res = main(
            input_file=qasm_file,
            output_file=output_file,
            opt_level=opt_level,
            tech_type=Constant.TECH_TYPE_SUPERCONDUCTING,
            config_file="etc/qcos/conf.d/spinq_rpc.toml",
        )
        assert res is True

    def test_cmss_transpiler_notech(self):
        self.qasm_path = GLOBAL_CONFIGS["samples_dir"]
        qasm_file = f"{self.qasm_path}/qasm/2.0/simple-qasm.qasm"
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
