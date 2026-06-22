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
import types
from unittest.mock import patch

from wy_qcos.common.constant import Constant
from wy_qcos.common.cmss.gate_operation import create_gate
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.cmss.mapping.empty_mapping import EmptyRoute
from wy_qcos.transpiler.cmss.transpiler_cmss import TranspilerCmss
from wy_qcos.tests.unit_tests.transpiler.comm import validate_gate_ir
from wy_qcos.tests.unit_tests.transpiler.comm import validate_non_gate_ir
from wy_qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS, SAMPLES
from wy_qcos.transpiler.cmss.mapping.na.na_mapping import NASingleRoute


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

    @pytest.mark.smoke
    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmss."
        "MappingFactory.get_mapper_by_type"
    )
    def test_transpiler_cmss(self, mock_get_mapper):
        # Create a real mapper instance
        mapper = NASingleRoute()
        # Mock execute_with_order to return (mapped_ir, final_layout)
        original_execute = mapper.execute_with_order

        def mock_execute_with_order(self_ref):
            result = original_execute()
            # If result is a list, wrap it in a tuple with empty dict
            if isinstance(result, list):
                return result, {}
            return result

        mapper.execute_with_order = types.MethodType(
            mock_execute_with_order, mapper
        )
        mock_get_mapper.return_value = mapper

        transpiler = TranspilerCmss()
        expected_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CX,
        ]
        src_code_info = {"000": self.simple_data}
        parse_result = transpiler.parse(src_code_info)
        basis_gate_list, _ = transpiler.transpile(
            parse_result, expected_basis_gates
        )
        assert len(basis_gate_list) == 2
        validate_gate_ir(basis_gate_list[0], "rx", [27], 1, False)
        validate_non_gate_ir(basis_gate_list[1], "measure", [27], 0)

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmss."
        "MappingFactory.get_mapper_by_type"
    )
    def test_transpiler_aggregation_succ(self, mock_get_mapper):
        # Create a real mapper instance
        mapper = NASingleRoute()
        # Mock execute_with_order to return (mapped_ir, final_layout)
        original_execute = mapper.execute_with_order

        def mock_execute_with_order(self_ref):
            result = original_execute()
            # If result is a list, wrap it in a tuple with empty dict
            if isinstance(result, list):
                return result, {}
            return result

        mapper.execute_with_order = types.MethodType(
            mock_execute_with_order, mapper
        )
        mock_get_mapper.return_value = mapper

        transpiler = TranspilerCmss()
        expected_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CX,
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

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmss."
        "MappingFactory.get_mapper_by_type"
    )
    def test_transpiler_aggregation_partly_succ(self, mock_get_mapper):
        qasm_data = SAMPLES["simple-qasm.qasm"]
        if qasm_data is None:
            return

        # Create a real mapper instance
        mapper = NASingleRoute()
        # Mock execute_with_order to return (mapped_ir, final_layout)
        original_execute = mapper.execute_with_order

        def mock_execute_with_order(self_ref):
            result = original_execute()
            # If result is a list, wrap it in a tuple with empty dict
            if isinstance(result, list):
                return result, {}
            return result

        mapper.execute_with_order = types.MethodType(
            mock_execute_with_order, mapper
        )
        mock_get_mapper.return_value = mapper

        transpiler = TranspilerCmss()
        expected_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CX,
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
        assert len(basis_gate_list) % 2 == 0
        for idx in range(0, len(basis_gate_list), 2):
            assert basis_gate_list[idx].name == "rx"
            assert basis_gate_list[idx + 1].name == "measure"

        src_code_info2 = {
            "000": qasm_data,
        }
        parse_result = transpiler.parse(src_code_info2)
        basis_gate_list, _ = transpiler.transpile(
            parse_result, expected_basis_gates
        )
        assert len(basis_gate_list) % 2 == 0

    def test_transpiler_with_no_mapping(self):
        transpiler = TranspilerCmss()
        transpiler.transpiler_options["enable_mapping"] = False
        expected_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CX,
        ]
        src_code_info = {
            "000": self.simple_data,
        }
        parse_result = transpiler.parse(src_code_info)
        basis_gate_list, _ = transpiler.transpile(
            parse_result, expected_basis_gates
        )
        assert len(basis_gate_list) == 2

    @patch(
        "wy_qcos.transpiler.cmss.transpiler_cmss."
        "MappingFactory.get_mapper_by_type"
    )
    def test_empty_route_aggregation_offsets_circuits(self, mock_get_mapper):
        mock_get_mapper.return_value = EmptyRoute()

        first_ops = [
            create_gate("x", [0]),
            create_gate("measure", [0]),
        ]
        second_ops = [
            create_gate("cx", [0, 1]),
            create_gate("measure", [0]),
            create_gate("measure", [1]),
        ]
        opt_result_dict = {
            "job-0": (1, first_ops),
            "job-1": (2, second_ops),
        }

        transpiler = TranspilerCmss()
        mapping_res, mapping_dict, init_layout_dict, final_layout_dict = (
            transpiler.mapping({}, opt_result_dict)
        )

        assert mapping_dict == {"job-0": 1, "job-1": 2}
        assert init_layout_dict == {}
        assert final_layout_dict == {}
        assert [operation.targets for operation in mapping_res] == [
            [0],
            [0],
            [1, 2],
            [1],
            [2],
        ]
        assert second_ops[0].targets == [0, 1]
