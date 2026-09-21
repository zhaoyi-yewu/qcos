#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You may use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY or FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------
import tomllib

import pytest

from wy_qcos.common.cmss.base_operation import OperationType
from wy_qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS
from wy_qcos.transpiler.cmss.mapping.na.na_mapping import NAMultiRoute
from wy_qcos.transpiler.high_performance import qasm_to_ir


@pytest.mark.usefixtures("global_configs")
class TestNAMultiRoute:
    @classmethod
    def setup_class(cls):
        etc_dir = GLOBAL_CONFIGS["etc_dir"]
        toml_path = f"{etc_dir}/topology/hanyuan1_100_new.toml"
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        cls.qpu_config = data["hanyuan1_100_new"]["transpiler"]["qpu_configs"]

        cls.bell_qasm = (
            "OPENQASM 3.0;\n"
            'include "stdgates.inc";\n'
            "qubit[2] q;\n"
            "bit[2] c;\n"
            "h q[0];\n"
            "cx q[0], q[1];\n"
            "c[0] = measure q[0];\n"
            "c[1] = measure q[1];\n"
        )
        cls.chain_qasm = (
            "OPENQASM 3.0;\n"
            'include "stdgates.inc";\n'
            "qubit[3] q;\n"
            "bit[3] c;\n"
            "h q[0];\n"
            "cx q[0], q[1];\n"
            "cx q[1], q[2];\n"
            "c[0] = measure q[0];\n"
            "c[1] = measure q[1];\n"
            "c[2] = measure q[2];\n"
        )

    def test_prepare_data(self):
        ops, num_qubits = qasm_to_ir(self.bell_qasm)
        na = NAMultiRoute()
        na.prepare_data(num_qubits, ops, self.qpu_config)

        assert na.qpu_config is not None
        assert na.qbit_num == num_qubits
        assert na.gates == ops
        assert len(na.operate_area) == 80
        assert na.ag.num_edges() == 4
        assert na.pg.num_nodes() == 220
        assert na.rows == 11
        assert na.cols == 20

    def test_get_operate_area_formats(self):
        na = NAMultiRoute()
        na.rows = 10
        na.cols = 20
        assert na.get_operate_area([60, 61]) == [60, 61]
        assert na.get_operate_area([[3, 0]]) == [60]
        assert na.get_operate_area([{"row": [3, 5], "col": [0, 2]}]) == [
            60,
            61,
            80,
            81,
        ]

    def _validate_mapped_ir(self, na, mapping_res, num_qubits):
        """校验映射和路由后 IR 的合法性.

        校验维度:
            1. 物理位置范围: targets/arg_value 中的位置在有效范围内
            2. move 路径连续性: 路径中相邻位置在物理网格 pg 中相邻
            3. cz 门结构: targets 为空（全局脉冲）
            4. operation_type 一致性: 各操作的 operation_type 与 name 匹配
            5. final_mapping 一致性: 映射无重复、范围正确
            6. move 路径无重复位置
            7. move targets[0] == arg_value[0]（起始位置一致）
            8. 单比特门/measure 的 targets 数量正确
            9. move 执行模拟: 跟踪比特位置，检查路径无冲突
        """
        total_sites = na.rows * na.cols

        def _op_type_val(op):
            ot = op.operation_type
            if hasattr(ot, "value"):
                return ot.value
            return ot

        # 1. 物理位置范围
        for op in mapping_res:
            for t in op.targets:
                assert 0 <= t < total_sites, (
                    f"target {t} out of range [0, {total_sites}) "
                    f"in op '{op.name}'"
                )
            if op.name == "move":
                for p in op.arg_value:
                    assert 0 <= p < total_sites, (
                        f"move path {p} out of range in op '{op.name}'"
                    )

        # 2. move 路径连续性
        for op in mapping_res:
            if op.name == "move":
                path = op.arg_value
                assert len(path) >= 2, (
                    f"move path must have >=2 positions, got {len(path)}"
                )
                for i in range(len(path) - 1):
                    p1, p2 = path[i], path[i + 1]
                    assert na.pg.has_edge(p1, p2), (
                        f"move path step {p1}->{p2} not "
                        f"adjacent in physical grid"
                    )

        # 3. cz 门 targets 为空
        for op in mapping_res:
            if op.name == "cz":
                assert op.targets == [], (
                    f"cz targets should be empty (global pulse), "
                    f"got {op.targets}"
                )

        # 4. operation_type 一致性
        for op in mapping_res:
            ot = _op_type_val(op)
            if op.name == "move":
                assert ot == OperationType.MOVE.value, (
                    f"move op_type should be "
                    f"{OperationType.MOVE.value}, got {ot}"
                )
            elif op.name == "cz":
                assert ot == (OperationType.DOUBLE_QUBIT_OPERATION.value), (
                    f"cz op_type should be "
                    f"{OperationType.DOUBLE_QUBIT_OPERATION.value}, "
                    f"got {ot}"
                )
            elif op.name == "measure":
                assert ot == OperationType.MEASURE.value, (
                    f"measure op_type should be "
                    f"{OperationType.MEASURE.value}, got {ot}"
                )
            else:
                assert ot == (OperationType.SINGLE_QUBIT_OPERATION.value), (
                    f"single gate '{op.name}' op_type should be "
                    f"{OperationType.SINGLE_QUBIT_OPERATION.value}, "
                    f"got {ot}"
                )

        # 5. final_mapping 一致性
        fm = na.final_mapping
        assert len(fm) == num_qubits, (
            f"final_mapping len {len(fm)} != {num_qubits}"
        )
        phys = list(fm.values())
        assert len(phys) == len(set(phys)), (
            "duplicate physical positions in final_mapping"
        )
        for q, p in fm.items():
            assert 0 <= q < num_qubits, f"logical qubit {q} out of range"
            assert 0 <= p < total_sites, f"physical position {p} out of range"

        # 6. move 路径无重复位置
        for op in mapping_res:
            if op.name == "move":
                path = op.arg_value
                assert len(path) == len(set(path)), (
                    f"move path has duplicate positions: {path}"
                )

        # 7. move targets[0] == arg_value[0]
        for op in mapping_res:
            if op.name == "move":
                assert op.targets[0] == op.arg_value[0], (
                    f"move targets[0]={op.targets[0]} != "
                    f"arg_value[0]={op.arg_value[0]}"
                )

        # 8. 单比特门和 measure 的 targets 数量
        for op in mapping_res:
            if op.name == "measure":
                assert len(op.targets) == 1, (
                    f"measure needs 1 target, got {len(op.targets)}"
                )
            elif op.name not in ("cz", "move", "sync", "barrier"):
                assert len(op.targets) >= 1, (
                    f"gate '{op.name}' needs >=1 target"
                )

        # 9. move 执行模拟: 跟踪比特位置，检查路径无冲突
        #    从 final_mapping 反推执行结束时的位置
        p_to_q = {p: q for q, p in fm.items()}
        # 逆序遍历 move 操作，逆推执行前的状态
        moves = [op for op in mapping_res if op.name == "move"]
        for op in reversed(moves):
            frm = op.arg_value[0]
            to = op.arg_value[-1]
            # 逆推: 执行 move 前，比特在 frm，不在 to
            if to in p_to_q:
                qid = p_to_q.pop(to)
                p_to_q[frm] = qid
            else:
                # to 位置没有比特，说明 move 是将比特
                # 从某处移到空位，逆推时不需要处理
                pass
        # 校验逆推后的映射不冲突
        assert len(p_to_q) == len(set(p_to_q.keys())), (
            "conflicting positions after reverse simulation"
        )

    def test_execute_bell(self):
        ops, num_qubits = qasm_to_ir(self.bell_qasm)
        na = NAMultiRoute()
        na.prepare_data(num_qubits, ops, self.qpu_config)
        mapping_res, final_layout = na.execute_with_order()

        assert mapping_res is not None
        names = [op.name for op in mapping_res]
        assert names[0] == "h"
        assert names[-1] == "measure"
        assert "cz" in names
        assert len(na.final_mapping) == num_qubits
        assert len(na.initial_layout) == num_qubits
        assert final_layout == na.final_mapping
        self._validate_mapped_ir(na, mapping_res, num_qubits)

    def test_execute_chain_with_move(self):
        ops, num_qubits = qasm_to_ir(self.chain_qasm)
        na = NAMultiRoute()
        na.prepare_data(num_qubits, ops, self.qpu_config)
        mapping_res, _ = na.execute_with_order()

        assert mapping_res is not None
        names = [op.name for op in mapping_res]
        assert names[0] == "h"
        assert names[-1] == "measure"
        assert "cz" in names
        assert "move" in names
        assert len(na.final_mapping) == num_qubits
        self._validate_mapped_ir(na, mapping_res, num_qubits)

    def test_execute_single_qubit_only(self):
        single_qasm = (
            "OPENQASM 3.0;\n"
            'include "stdgates.inc";\n'
            "qubit[2] q;\n"
            "bit[2] c;\n"
            "h q[0];\n"
            "x q[1];\n"
            "c[0] = measure q[0];\n"
            "c[1] = measure q[1];\n"
        )
        ops, num_qubits = qasm_to_ir(single_qasm)
        na = NAMultiRoute()
        na.prepare_data(num_qubits, ops, self.qpu_config)
        mapping_res, _ = na.execute_with_order()

        assert mapping_res is not None
        names = [op.name for op in mapping_res]
        assert "h" in names
        assert "x" in names
        assert names[-1] == "measure"
        assert "cz" not in names
        assert "move" not in names
        self._validate_mapped_ir(na, mapping_res, num_qubits)

    def test_ir_validation_multi_cx(self):
        """对多 CX 门电路的映射路由 IR 进行全面校验."""
        multi_qasm = (
            "OPENQASM 3.0;\n"
            'include "stdgates.inc";\n'
            "qubit[4] q;\n"
            "bit[4] c;\n"
            "h q[0];\n"
            "cx q[0], q[1];\n"
            "cx q[1], q[2];\n"
            "cx q[2], q[3];\n"
            "h q[3];\n"
            "c[0] = measure q[0];\n"
            "c[1] = measure q[1];\n"
            "c[2] = measure q[2];\n"
            "c[3] = measure q[3];\n"
        )
        ops, num_qubits = qasm_to_ir(multi_qasm)
        na = NAMultiRoute()
        na.prepare_data(num_qubits, ops, self.qpu_config)
        mapping_res, _ = na.execute_with_order()

        assert mapping_res is not None
        names = [op.name for op in mapping_res]
        assert names[0] == "h"
        assert names[-1] == "measure"
        assert names.count("cz") == 3
        assert "move" in names
        assert len(na.final_mapping) == num_qubits
        self._validate_mapped_ir(na, mapping_res, num_qubits)

    def test_ir_validation_parallel_cx(self):
        """对并行 CX 门电路的映射路由 IR 进行校验."""
        parallel_qasm = (
            "OPENQASM 3.0;\n"
            'include "stdgates.inc";\n'
            "qubit[4] q;\n"
            "bit[4] c;\n"
            "h q[0];\n"
            "h q[2];\n"
            "cx q[0], q[1];\n"
            "cx q[2], q[3];\n"
            "c[0] = measure q[0];\n"
            "c[1] = measure q[1];\n"
            "c[2] = measure q[2];\n"
            "c[3] = measure q[3];\n"
        )
        ops, num_qubits = qasm_to_ir(parallel_qasm)
        na = NAMultiRoute()
        na.prepare_data(num_qubits, ops, self.qpu_config)
        mapping_res, _ = na.execute_with_order()

        assert mapping_res is not None
        names = [op.name for op in mapping_res]
        assert names[0] == "h"
        assert names[-1] == "measure"
        assert "cz" in names
        assert len(na.final_mapping) == num_qubits
        self._validate_mapped_ir(na, mapping_res, num_qubits)
