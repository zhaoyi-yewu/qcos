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

from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.cmss.common.move import Move
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst

from wy_qcos.transpiler.cmss.transpiler_cmss import TranspilerCmss
from wy_qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS
from wy_qcos.transpiler.cmss.mapping.na_mapping import NARoute
from wy_qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate


@pytest.mark.usefixtures("global_configs")
class TestTranspilerNaMapping:
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
        cls.task2_data = """OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[5];
        creg c[5];
        x q[0];
        cx q[0], q[1];
        cz q[0], q[2];
        cz q[0], q[3];
        measure q->c;
        """
        cls.task3_data = """OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[4];
        creg c[4];
        h q[0];
        cx q[1], q[0];
        h q[0];
        cx q[1], q[2];
        h q[1];
        h q[2];
        cx q[2], q[0];
        cx q[0], q[2];
        rx(1) q[3];
        ry(1) q[3];
        measure q->c;
        """

        cls.qpu_config = {
            "qubits": 36,
            "storage_area": [
                "P144",
                "P145",
                "P146",
                "P147",
                "P148",
                "P149",
                "P150",
                "P151",
                "P152",
                "P153",
                "P154",
                "P155",
                "P164",
                "P165",
                "P166",
                "P167",
                "P168",
                "P169",
                "P170",
                "P171",
                "P172",
                "P173",
                "P174",
                "P175",
                "P184",
                "P185",
                "P186",
                "P187",
                "P188",
                "P189",
                "P190",
                "P191",
                "P192",
                "P193",
                "P194",
                "P195",
            ],
            "operate_area": [
                "P100",
                "P101",
                "P106",
                "P107",
                "P112",
                "P113",
                "P118",
                "P119",
            ],
            "coupler_map": {
                "R_G0": ["P100", "P101"],
                "R_G1": ["P106", "P107"],
                "R_G2": ["P112", "P113"],
                "R_G3": ["P118", "P119"],
            },
            "readout_error": {
                "P144": 1.0,
                "P145": 2.0,
                "P146": 3.0,
                "P147": 4.0,
                "P148": 5.0,
                "P149": 5.0,
                "P150": 6.0,
                "P151": 7.0,
                "P152": 6.0,
                "P153": 5.0,
                "P154": 4.0,
                "P155": 3.0,
                "P164": 1.0,
                "P165": 2.0,
                "P166": 2.0,
                "P167": 3.0,
                "P168": 4.0,
                "P169": 5.0,
                "P170": 6.0,
                "P171": 7.0,
                "P172": 1.0,
                "P173": 3.0,
                "P174": 2.0,
                "P175": 4.0,
                "P184": 5.0,
                "P185": 6.0,
                "P186": 7.0,
                "P187": 8.0,
                "P188": 5.0,
                "P189": 3.0,
                "P190": 4.0,
                "P191": 3.0,
                "P192": 4.0,
                "P193": 5.0,
                "P194": 3.0,
                "P195": 2.0,
            },
            "coupler_error_ryd": {
                "R_G0": 3.0,
                "R_G1": 3.0,
                "R_G2": 3.0,
                "R_G3": 3.0,
            },
        }
        trans_cfg_inst.set_qpu_cfg(cls.qpu_config)
        trans_cfg_inst.set_tech_type(Constant.TECH_TYPE_NEUTRAL_ATOM)
        trans_cfg_inst.set_max_qubits(cls.qpu_config.get("qubits"))
        cls.transpiler = TranspilerCmss()
        cls.expected_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CZ,
        ]

    def test_na_mapping_prepare_data(self):
        src_code_info = {"000": self.simple_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NARoute()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        assert na.qpu_config is not None
        assert len(na.ag.nodes) == 8
        assert na.gates == value[1]
        assert na.qbit_num == value[0]
        assert na.mapping is None

    def test_execute_with_order(self):
        src_code_info = {"000": self.simple_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}
        na = NARoute()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)
        mapping_res = na.execute_with_order()

        assert len(na.mapping) == na.qbit_num
        assert mapping_res is not None
        assert mapping_res[0].name == "x"
        assert mapping_res[-1].name == "measure"

    def test_execute_with_opt(self):
        src_code_info = {"000": self.simple_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}
        na = NARoute()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)
        mapping_res = na.execute_with_opt()

        assert len(na.mapping) == na.qbit_num
        assert mapping_res is not None
        assert mapping_res[0].name == "x"
        assert mapping_res[-1].name == "measure"

    def test_2_qubit_gate_na_mapping(self):
        src_code_info = {"000": self.task2_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}
        na = NARoute()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)
        order_mapping_res = na.execute_with_order()

        assert len(na.mapping) == na.qbit_num
        assert order_mapping_res is not None
        assert order_mapping_res[0].name == "move"
        assert order_mapping_res[-1].name == "measure"

    def test_2_qubit_gate_na_mapping_opt(self):
        src_code_info = {"000": self.task2_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}
        na = NARoute()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        opt_mapping_res = na.execute_with_opt()
        assert len(na.mapping) == na.qbit_num
        assert opt_mapping_res is not None
        assert opt_mapping_res[0].name == "move"
        assert opt_mapping_res[-1].name == "measure"

    def test_add_put(self):
        src_code_info = {"000": self.task2_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}
        na = NARoute()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)
        na.get_init_mapping()
        res = []
        res.append(Move(targets=[0], arg_value=["P144", "P100"]))
        opt = Move(targets=[0], arg_value=["P100", "P155"])
        na.ohas.add("P100")
        na.oloc[0] = "P100"
        result = na.add_put(res, opt)
        assert len(result) == 0

    def test_execute_overlap(self):
        src_code_info = {"000": self.task3_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}
        na = NARoute()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)
        mapping_res = na.execute_with_order()

        assert len(na.mapping) == na.qbit_num
        assert mapping_res is not None
        assert mapping_res[0].name == "move"
        assert mapping_res[-1].name == "measure"
