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
from pathlib import Path
from unittest.mock import patch

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.common.cmss.gate_operation import create_gate
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.cmss.mapping.empty_mapping import EmptyRoute
from wy_qcos.transpiler.cmss.transpiler_cmss import TranspilerCmss
from wy_qcos.driver.spinq.spinq_rpc.driver_spinq_rpc import DriverSpinQRpc
from wy_qcos.driver.cascoldatom.driver_wuyue_hanyuan1 import (
    DriverWuyueHanyuan1,
)
from wy_qcos.driver.cascoldatom.driver_hanyuan1 import DriverHanyuan1
from wy_qcos.tests.unit_tests.transpiler.comm import validate_gate_ir
from wy_qcos.tests.unit_tests.transpiler.comm import validate_non_gate_ir
from wy_qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS, SAMPLES
from wy_qcos.transpiler.cmss.mapping.na.na_mapping import NASingleRoute


@pytest.mark.usefixtures("global_configs")
class TestTranspilerCmss:
    @classmethod
    def setup_class(cls):
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        cls.etc_dir = GLOBAL_CONFIGS["etc_dir"]
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
        basis_gate_list, _, _ = transpiler.transpile(
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
        basis_gate_list, _, _ = transpiler.transpile(
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
        basis_gate_list, _, _ = transpiler.transpile(
            parse_result, expected_basis_gates
        )
        assert len(basis_gate_list) % 2 == 0
        # After optimization, measure gates are collected to the end.
        half = len(basis_gate_list) // 2
        for idx in range(half):
            assert basis_gate_list[idx].name == "rx"
            assert basis_gate_list[half + idx].name == "measure"

        src_code_info2 = {
            "000": qasm_data,
        }
        parse_result = transpiler.parse(src_code_info2)
        basis_gate_list, _, _ = transpiler.transpile(
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
        basis_gate_list, _, _ = transpiler.transpile(
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

    # ------------------------------------------------------------------
    # 真机 + openqasm 文件转译测试
    # ------------------------------------------------------------------
    # basis_gates 与 tech_type 直接从真机驱动读取
    # (driver.get_supported_basis_gates() / get_tech_type()),
    # 与 engine/job_engine.py 的真实调用路径一致, 不在测试里硬编码门集.
    # 每个测试用例固定一组配置 (驱动 + 拓扑 + qasm), 需要扩展时
    # 复制用例并替换常量即可.

    @classmethod
    def _load_qpu_cfg(cls, chip_name, toml_rel_path):
        """从 etc 下的 toml 拓扑配置加载指定芯片的 qpu_configs.

        Args:
            chip_name: toml 中的 section 名(芯片名).
            toml_rel_path: 相对 etc_dir 的 toml 路径.

        Returns:
            qpu_configs 字典. 文件缺失时返回 None.
        """
        config_file = Path(f"{cls.etc_dir}/{toml_rel_path}")
        if not config_file.exists():
            return None
        _, _, toml_doc = Library.read_toml_file(str(config_file))
        return toml_doc.unwrap()[chip_name]["transpiler"]["qpu_configs"]

    @staticmethod
    def _read_qasm(samples_dir, qasm_rel_path):
        """读取 samples 下的 qasm 文件, 缺失时跳过测试."""
        qasm_file = Path(f"{samples_dir}/{qasm_rel_path}")
        if not qasm_file.exists():
            pytest.skip(f"qasm file not found: {qasm_rel_path}")
        qasm_data = Library.read_file(str(qasm_file))
        assert qasm_data is not None
        return qasm_data

    @staticmethod
    def _assert_transpile_result(basis_gate_list, allowed_gate_names):
        """校验转译结果: 非空、门名合法、target 为非负整数、measure 在末尾."""
        assert basis_gate_list is not None
        assert len(basis_gate_list) > 0, "transpile result is empty"

        for gate in basis_gate_list:
            assert gate.name in allowed_gate_names, (
                f"gate '{gate.name}' not in allowed gates "
                f"{allowed_gate_names}"
            )
            for target in gate.targets:
                assert isinstance(target, int) and target >= 0, (
                    f"target {target} of {gate.name} is not a "
                    f"non-negative int"
                )

        seen_measure = False
        for gate in basis_gate_list:
            if gate.name == "measure":
                seen_measure = True
            elif seen_measure:
                assert False, (
                    f"non-measure gate '{gate.name}' appears after "
                    f"a measure gate"
                )

    def _run_transpile(
        self,
        driver,
        toml_rel_path,
        chip_name,
        qasm_rel_path,
        code_type,
        *,
        enable_na_move=False,
        sc_mapping_options=None,
    ):
        """通用的"读驱动门集 -> 加载拓扑 -> 转译 -> 校验"流程.

        Args:
            driver: 真机驱动实例, basis_gates/tech_type 从其读取.
            toml_rel_path: 相对 etc_dir 的拓扑 toml 路径.
            chip_name: toml 中的芯片 section 名.
            qasm_rel_path: 相对 samples_dir 的 qasm 路径.
            code_type: qasm 代码类型.
            enable_na_move: 是否启用 NA move (NARoute).
            sc_mapping_options: 超导路由选项, 默认 None.

        Returns:
            (basis_gate_list, mapping_dict, final_layout_dict).
        """
        basis_gates = driver.get_supported_basis_gates()
        tech_type = driver.get_tech_type()

        qpu_cfg = self._load_qpu_cfg(chip_name, toml_rel_path)
        if qpu_cfg is None:
            pytest.skip(f"topology config not found: {toml_rel_path}")
        qasm_data = self._read_qasm(self.samples_dir, qasm_rel_path)

        orig_state = (
            trans_cfg_inst.get_qpu_cfg(),
            trans_cfg_inst.get_tech_type(),
            trans_cfg_inst.get_max_qubits(),
        )
        trans_cfg_inst.set_qpu_cfg(qpu_cfg)
        trans_cfg_inst.set_tech_type(tech_type)
        trans_cfg_inst.set_max_qubits(qpu_cfg["qubits"])

        try:
            transpiler = TranspilerCmss(enable_na_move=enable_na_move)
            if sc_mapping_options is not None:
                transpiler.transpiler_options["sc_mapping_options"] = (
                    sc_mapping_options
                )

            parse_result = transpiler.parse(
                {"000": qasm_data}, code_type
            )
            basis_gate_list, mapping_dict, final_layout_dict = (
                transpiler.transpile(parse_result, basis_gates)
            )
        finally:
            trans_cfg_inst.set_qpu_cfg(orig_state[0])
            trans_cfg_inst.set_tech_type(orig_state[1])
            trans_cfg_inst.set_max_qubits(orig_state[2])

        return basis_gate_list, mapping_dict, final_layout_dict, basis_gates

    def test_transpile_with_superconducting_chip(self):
        """超导真机转译: DriverSpinQRpc + baihua_156 拓扑 + w-state 电路.

        basis={h,rx,ry,rz,cz}, 走 sabre 路由. 扩展方式: 复制本用例,
        替换驱动/topology/qasm 常量即可.
        """
        basis_gate_list, mapping_dict, final_layout_dict, basis_gates = (
            self._run_transpile(
                driver=DriverSpinQRpc(),
                toml_rel_path="topology/baihua_156.toml",
                chip_name="baihua_156",
                qasm_rel_path="qasm/2.0/w-state.qasm",
                code_type=Constant.CODE_TYPE_QASM,
                sc_mapping_options={"routing_algorithm": "sabre"},
            )
        )

        allowed_gate_names = set(basis_gates) | {"measure"}
        self._assert_transpile_result(
            basis_gate_list, allowed_gate_names
        )
        assert final_layout_dict is not None
        assert mapping_dict is not None

    def test_transpile_with_neutral_atom_chip_single_qubit_qasm(self):
        """中性原子真机转译: DriverHanyuan1 + hanyuan1_100 拓扑.

        basis={rx,ry,rz} 单比特门集, 含 simple-qasm 电路. 扩展方式:
        复制本用例, 替换驱动/topology/qasm 常量即可.
        """
        basis_gate_list, mapping_dict, final_layout_dict, basis_gates = (
            self._run_transpile(
                driver=DriverHanyuan1(),
                toml_rel_path="topology/hanyuan1_100.toml",
                chip_name="hanyuan1_100",
                qasm_rel_path="qasm/2.0/simple-qasm.qasm",
                code_type=Constant.CODE_TYPE_QASM,
                enable_na_move=False,
            )
        )

        # NA 路由会引入 move 门, 故允许集合为 basis ∪ {measure, move}.
        allowed_gate_names = set(basis_gates) | {"measure", "move"}
        self._assert_transpile_result(
            basis_gate_list, allowed_gate_names
        )
        assert final_layout_dict is not None
        assert mapping_dict is not None

    def test_transpile_with_neutral_atom_chip(self):
        """中性原子真机转译: DriverWuyueHanyuan1 + hanyuan1_100 + w-state.

        basis={rx,ry,cz}, 启用 enable_na_move 走 NARoute (支持 cz/move),
        结果会引入 NA 特有的 move 门. 扩展方式: 复制本用例, 替换
        驱动/topology/qasm 常量即可.
        """
        basis_gate_list, mapping_dict, final_layout_dict, basis_gates = (
            self._run_transpile(
                driver=DriverWuyueHanyuan1(),
                toml_rel_path="topology/hanyuan1_100.toml",
                chip_name="hanyuan1_100",
                qasm_rel_path="qasm/2.0/w-state.qasm",
                code_type=Constant.CODE_TYPE_QASM,
                enable_na_move=True,
            )
        )

        # NA 路由会引入 move 门, 故允许集合为 basis ∪ {measure, move}.
        allowed_gate_names = set(basis_gates) | {"measure", "move"}
        self._assert_transpile_result(
            basis_gate_list, allowed_gate_names
        )
        assert final_layout_dict is not None
        assert mapping_dict is not None
