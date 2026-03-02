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

from copy import deepcopy
from wy_qcos.common.constant import Constant
from wy_qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS

from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.cmss.transpiler_cmss import TranspilerCmss
from wy_qcos.transpiler.cmss.mapping.na.zap.na_zap_mapping import NA_ZAP_Route
from wy_qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate


@pytest.mark.usefixtures("global_configs")
class TestTranspilerNaZapMapping:
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
        cx q[2], q[1];
        h q[1];
        h q[2];
        cx q[2], q[0];
        cx q[0], q[2];
        rx(1) q[3];
        ry(1) q[3];
        cx q[1], q[3];
        cz q[3], q[1];
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

    def test_na_zap_mapping_prepare_data(self):
        src_code_info = {"000": self.simple_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NA_ZAP_Route()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        assert na.qpu_config is not None
        assert len(na.storage_area) == len(self.qpu_config["storage_area"])
        assert len(na.operate_area) == len(self.qpu_config["operate_area"])
        assert len(na.ag.edges) == len(self.qpu_config["coupler_map"])
        assert len(na.ag.nodes) == len(na.operate_area)
        assert na.gates == value[1]
        assert na.qbit_num == value[0]
        assert na.mapping is None
        assert len(na.gate_scheduling_list) == 0
        assert len(na.qubit_scheduling_list) == 0
        assert len(na.res) == 0

    def test_na_zap_mapping_scheduling(self):
        src_code_info = {"000": self.task2_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NA_ZAP_Route()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        measure_op = na.scheduling()

        assert len(na.storage_area_oloc) == len(na.gate_scheduling_list) + 1
        assert len(na.storage_area_oloc[0]) == len(na.storage_area)
        assert len(na.operate_area_oloc) == len(na.gate_scheduling_list) + 1
        assert len(na.operate_area_oloc[0]) == len(na.operate_area)
        assert na.operate_area_oloc[0]["P101"] == -1
        assert na.storage_area_oloc[0]["P145"] == -1

        assert len(na.gate_scheduling_list) >= 1
        assert len(measure_op) == na.qbit_num

    def test_get_init_mapping_and_placing(self):
        src_code_info = {"000": self.task3_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NA_ZAP_Route()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        measure_op = na.scheduling()

        mapping = [
            {a: None for a in range(na.qbit_num)}
            for _ in range(len(na.gate_scheduling_list) + 1)
        ]
        init_mapping = na.get_init_mapping_and_placing(mapping)

        assert len(measure_op) == na.qbit_num
        assert len(init_mapping) == len(na.gate_scheduling_list) + 1
        # 0 stage all qubit in storage_area
        for id in range(na.qbit_num):
            assert init_mapping[0][id] in na.storage_area

        # other stage two qubit gate qubits in operate_area,
        # others in storage_area
        assert init_mapping[1][0] in na.operate_area
        assert init_mapping[1][1] in na.operate_area
        assert init_mapping[1][2] in na.storage_area
        assert init_mapping[1][3] in na.storage_area

        assert init_mapping[2][0] in na.storage_area
        assert init_mapping[2][1] in na.operate_area
        assert init_mapping[2][2] in na.operate_area
        assert init_mapping[2][3] in na.storage_area

        assert init_mapping[3][0] in na.operate_area
        assert init_mapping[3][1] in na.operate_area
        assert init_mapping[3][2] in na.operate_area
        assert init_mapping[3][3] in na.operate_area

        assert init_mapping[4][0] in na.operate_area
        assert init_mapping[4][1] in na.operate_area
        assert init_mapping[4][2] in na.operate_area
        assert init_mapping[4][3] in na.operate_area

    def test_get_cost(self):
        src_code_info = {"000": self.simple_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NA_ZAP_Route()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        _ = na.scheduling()

        mapping = [
            {a: None for a in range(na.qbit_num)}
            for _ in range(len(na.gate_scheduling_list) + 1)
        ]
        init_mapping = na.get_init_mapping_and_placing(mapping)

        cost = na.get_cost(init_mapping)

        assert cost >= 0

    def test_find_ryd_pos(self):
        src_code_info = {"000": self.simple_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NA_ZAP_Route()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        _ = na.scheduling()
        stage = 1
        pos = na.find_ryd_pos(stage)

        assert pos[0] in na.operate_area
        assert pos[1] in na.operate_area

    def test_find_pos(self):
        src_code_info = {"000": self.simple_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NA_ZAP_Route()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        _ = na.scheduling()
        stage = 1
        pos = na.find_pos(stage)

        assert pos in na.storage_area

    def test_update_mapping(self):
        src_code_info = {"000": self.task3_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NA_ZAP_Route()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        _ = na.scheduling()

        mapping = [
            {a: None for a in range(na.qbit_num)}
            for _ in range(len(na.gate_scheduling_list) + 1)
        ]
        init_mapping = na.get_init_mapping_and_placing(mapping)

        # update mapping 1 times
        up_mapping_1 = deepcopy(init_mapping)
        _ = na.update_mapping(up_mapping_1)

        for id in range(na.qbit_num):
            assert up_mapping_1[0][id] in na.storage_area

        # 更新不破坏执行位置区域，只改变区域
        # other stage two qubit gate qubits in operate_area,
        # others in storage_area
        assert up_mapping_1[1][0] in na.operate_area
        assert up_mapping_1[1][1] in na.operate_area
        assert up_mapping_1[1][2] in na.storage_area
        assert up_mapping_1[1][3] in na.storage_area

        assert up_mapping_1[2][0] in na.storage_area
        assert up_mapping_1[2][1] in na.operate_area
        assert up_mapping_1[2][2] in na.operate_area
        assert up_mapping_1[2][3] in na.storage_area

        assert init_mapping[3][0] in na.operate_area
        assert init_mapping[3][1] in na.operate_area
        assert init_mapping[3][2] in na.operate_area
        assert init_mapping[3][3] in na.operate_area

        assert init_mapping[4][0] in na.operate_area
        assert init_mapping[4][1] in na.operate_area
        assert init_mapping[4][2] in na.operate_area
        assert init_mapping[4][3] in na.operate_area

        # update mapping 2 times
        up_mapping_2 = deepcopy(init_mapping)
        _ = na.update_mapping(up_mapping_2)

        for id in range(na.qbit_num):
            assert up_mapping_2[0][id] in na.storage_area

        # 更新不破坏执行位置区域，只改变区域
        # other stage two qubit gate qubits in operate_area,
        # others in storage_area
        assert up_mapping_2[1][0] in na.operate_area
        assert up_mapping_2[1][1] in na.operate_area
        assert up_mapping_2[1][2] in na.storage_area
        assert up_mapping_2[1][3] in na.storage_area

        assert up_mapping_2[2][0] in na.storage_area
        assert up_mapping_2[2][1] in na.operate_area
        assert up_mapping_2[2][2] in na.operate_area
        assert up_mapping_2[2][3] in na.storage_area

        assert up_mapping_2[3][0] in na.operate_area
        assert up_mapping_2[3][1] in na.operate_area
        assert up_mapping_2[3][2] in na.operate_area
        assert up_mapping_2[3][3] in na.operate_area

        assert up_mapping_2[4][0] in na.operate_area
        assert up_mapping_2[4][1] in na.operate_area
        assert up_mapping_2[4][2] in na.operate_area
        assert up_mapping_2[4][3] in na.operate_area

        # update mapping 3 times
        up_mapping_3 = deepcopy(init_mapping)
        _ = na.update_mapping(up_mapping_3)

        assert up_mapping_3[1][0] in na.operate_area
        assert up_mapping_3[1][1] in na.operate_area
        assert up_mapping_3[1][2] in na.storage_area
        assert up_mapping_3[1][3] in na.storage_area

        assert up_mapping_3[2][0] in na.storage_area
        assert up_mapping_3[2][1] in na.operate_area
        assert up_mapping_3[2][2] in na.operate_area
        assert up_mapping_3
        # update mapping 4 times
        up_mapping_4 = deepcopy(init_mapping)
        _ = na.update_mapping(up_mapping_4)

        assert up_mapping_4[3][0] in na.operate_area
        assert up_mapping_4[3][1] in na.operate_area
        assert up_mapping_4[3][2] in na.operate_area
        assert up_mapping_4[3][3] in na.operate_area

        assert up_mapping_4[4][0] in na.operate_area
        assert up_mapping_4[4][1] in na.operate_area
        assert up_mapping_4[4][2] in na.operate_area
        assert up_mapping_4[4][3] in na.operate_area

        # update mapping 20 times
        for _ in range(20):
            up_mapping = deepcopy(init_mapping)
            _ = na.update_mapping(up_mapping)

    def test_update_storage_and_operate_area_oloc(self):
        src_code_info = {"000": self.task3_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NA_ZAP_Route()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        _ = na.scheduling()

        mapping = [
            {a: None for a in range(na.qbit_num)}
            for _ in range(len(na.gate_scheduling_list) + 1)
        ]
        init_mapping = na.get_init_mapping_and_placing(mapping)

        # update mapping 1 times
        _ = na.update_mapping(init_mapping)

        na.update_storage_and_operate_area_oloc(init_mapping)

        assert na.storage_area_oloc[0][init_mapping[0][0]] == 0
        assert na.operate_area_oloc[-1][init_mapping[-1][0]] == 0

    def test_init_para(self):
        src_code_info = {"000": self.task3_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NA_ZAP_Route()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)
        alpha, t2, markovlen = na.init_para()

        assert alpha == 0.98
        assert t2[0] == 1
        assert t2[1] == 100
        assert markovlen == 200

    def test_sa_mapping_and_placing(self):
        src_code_info = {"000": self.task2_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NA_ZAP_Route()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        _ = na.scheduling()

        sa_mapping = na.sa_mapping_and_placing()

        assert len(sa_mapping) == len(na.gate_scheduling_list) + 1

        for id in range(na.qbit_num):
            assert sa_mapping[0][id] in na.storage_area

        assert sa_mapping[-1][0] in na.operate_area
        assert sa_mapping[-1][3] in na.operate_area

    def test_routing_asap(self):
        src_code_info = {"000": self.task2_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NA_ZAP_Route()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        measure_op = na.scheduling()

        sa_mapping = na.sa_mapping_and_placing()

        res = na.routing_asap(sa_mapping, measure_op)

        assert res[0].name == "move"
        assert res[-1].name == "measure"

    def test_execute_with_order(self):
        src_code_info = {"000": self.simple_data}
        parse_result = self.transpiler.parse(src_code_info)
        opt_result_dict = {}

        for key, value in parse_result.items():
            opt_result = optimize_gate(value[1], 1)
            opt_result_dict[key] = (value[0], opt_result)

        mapping_dict = {}

        na = NA_ZAP_Route()
        qpu_cfg = trans_cfg_inst.get_qpu_cfg()
        key, value = list(opt_result_dict.items())[0]
        mapping_dict[key] = value[0]
        na.prepare_data(value[0], value[1], qpu_cfg)

        res, _ = na.execute_with_order()

        assert res[0].name == "x"
        assert res[-1].name == "measure"
