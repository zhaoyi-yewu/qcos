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
from unittest.mock import Mock

from wy_qcos.transpiler.cmss.mapping.utils.estimate import (
    SCEstimate,
    NAEstimate,
)
from wy_qcos.common.cmss.move import Move


class TestSCEstimate:
    """SCEstimate 类的单元测试."""

    def test_init_default_parameters(self):
        """测试默认参数初始化."""
        estimator = SCEstimate()
        assert estimator.single_gate_duration == 10.0
        assert estimator.multi_gate_duration == 50.0
        assert estimator.single_gate_fidelity == 0.995
        assert estimator.multi_gate_fidelity == 0.98

    def test_init_custom_parameters(self):
        """测试自定义参数初始化."""
        estimator = SCEstimate(
            single_gate_duration=15.0,
            multi_gate_duration=60.0,
            single_gate_fidelity=0.99,
            multi_gate_fidelity=0.95,
        )
        assert estimator.single_gate_duration == 15.0
        assert estimator.multi_gate_duration == 60.0
        assert estimator.single_gate_fidelity == 0.99
        assert estimator.multi_gate_fidelity == 0.95

    def test_set_circuit(self):
        """测试设置电路."""
        estimator = SCEstimate()
        circuit = []
        estimator.set_circuit(circuit)
        assert estimator.circuit == circuit

    def test_estimate_time_empty_circuit(self):
        """测试空电路的时间估计 - 会抛出ValueError因为max()无法处理空值."""
        estimator = SCEstimate()
        estimator.set_circuit([])
        # SCEstimate.estimate_time() 对空电路会抛出 ValueError
        # 这是原始代码的行为
        with pytest.raises(ValueError):
            estimator.estimate_time()

    def test_estimate_time_single_gate(self):
        """测试单个单比特门的时间估计."""
        estimator = SCEstimate(single_gate_duration=10.0)

        gate = Mock()
        gate.type = 1
        gate.targets = [0]

        estimator.set_circuit([gate])
        assert estimator.estimate_time() == 10.0

    def test_estimate_time_sequential_single_gates(self):
        """测试顺序执行的单比特门."""
        estimator = SCEstimate(single_gate_duration=10.0)

        gates = []
        for i in range(3):
            gate = Mock()
            gate.type = 1
            gate.targets = [i]
            gates.append(gate)

        estimator.set_circuit(gates)
        # 预期: 10.0 (所有比特并行执行)
        assert estimator.estimate_time() == 10.0

    def test_estimate_time_single_gate_on_same_qubit(self):
        """测试在同一比特上顺序执行单比特门."""
        estimator = SCEstimate(single_gate_duration=10.0)

        gates = []
        for i in range(3):
            gate = Mock()
            gate.type = 1
            gate.targets = [0]  # 同一比特
            gates.append(gate)

        estimator.set_circuit(gates)
        # 预期: 30.0 (同一比特上顺序执行)
        assert estimator.estimate_time() == 30.0

    def test_estimate_time_multi_qubit_gate(self):
        """测试两比特门的时间估计."""
        estimator = SCEstimate(multi_gate_duration=50.0)

        gate = Mock()
        gate.type = 2
        gate.targets = [0, 1]

        estimator.set_circuit([gate])
        assert estimator.estimate_time() == 50.0

    def test_estimate_time_mixed_gates(self):
        """测试混合门的时间估计."""
        estimator = SCEstimate(
            single_gate_duration=10.0, multi_gate_duration=50.0
        )

        gates = []

        # 单比特门在qubit 0
        single_gate1 = Mock()
        single_gate1.type = 1
        single_gate1.targets = [0]
        gates.append(single_gate1)

        # 两比特门在qubit 0, 1 (qubit 0上的时间已是10.0)
        multi_gate = Mock()
        multi_gate.type = 2
        multi_gate.targets = [0, 1]
        gates.append(multi_gate)

        # 单比特门在qubit 2
        single_gate2 = Mock()
        single_gate2.type = 1
        single_gate2.targets = [2]
        gates.append(single_gate2)

        estimator.set_circuit(gates)
        # 预期: max(10 + 50, 10, 10) = 60
        assert estimator.estimate_time() == 60.0

    def test_estimate_time_sync_operation(self):
        """测试同步操作（type=-1）."""
        estimator = SCEstimate(single_gate_duration=10.0)

        gates = []

        gate1 = Mock()
        gate1.type = 1
        gate1.targets = [0]
        gates.append(gate1)

        sync_op = Mock()
        sync_op.type = -1
        sync_op.targets = [1]
        gates.append(sync_op)

        gate2 = Mock()
        gate2.type = 1
        gate2.targets = [1]
        gates.append(gate2)

        estimator.set_circuit(gates)
        # 预期: max(10, 0, 10) = 10
        assert estimator.estimate_time() == 10.0

    def test_estimate_time_complex_circuit(self):
        """测试复杂电路的时间估计."""
        estimator = SCEstimate(
            single_gate_duration=10.0, multi_gate_duration=50.0
        )

        gates = []

        # qubit 0: 单比特门 (0-10)
        gate1 = Mock()
        gate1.type = 1
        gate1.targets = [0]
        gates.append(gate1)

        # qubit 1, 2: 两比特门 (0-50)
        gate2 = Mock()
        gate2.type = 2
        gate2.targets = [1, 2]
        gates.append(gate2)

        # qubit 0: 单比特门 (10-20)
        gate3 = Mock()
        gate3.type = 1
        gate3.targets = [0]
        gates.append(gate3)

        # qubit 1: 单比特门 (50-60)
        gate4 = Mock()
        gate4.type = 1
        gate4.targets = [1]
        gates.append(gate4)

        estimator.set_circuit(gates)
        # 预期: 60.0
        assert estimator.estimate_time() == 60.0

    def test_estimate_fidelity_empty_circuit(self):
        """测试空电路的保真度估计."""
        estimator = SCEstimate()
        estimator.set_circuit([])
        assert estimator.estimate_fidelity() == 1.0

    def test_estimate_fidelity_single_gate(self):
        """测试单比特门的保真度估计."""
        estimator = SCEstimate(single_gate_fidelity=0.995)

        gate = Mock()
        gate.type = 1
        gate.targets = [0]

        estimator.set_circuit([gate])
        assert estimator.estimate_fidelity() == 0.995

    def test_estimate_fidelity_multi_single_gates(self):
        """测试多个单比特门的保真度估计."""
        estimator = SCEstimate(single_gate_fidelity=0.995)

        gates = []
        for i in range(2):
            gate = Mock()
            gate.type = 1
            gate.targets = [i]
            gates.append(gate)

        estimator.set_circuit(gates)
        # 预期: 0.995 * 0.995 = 0.990025
        expected = 0.990025
        assert (
            pytest.approx(estimator.estimate_fidelity(), rel=1e-5) == expected
        )

    def test_estimate_fidelity_multi_qubit_gate(self):
        """测试两比特门的保真度估计."""
        estimator = SCEstimate(multi_gate_fidelity=0.98)

        gate = Mock()
        gate.type = 2
        gate.targets = [0, 1]

        estimator.set_circuit([gate])
        assert estimator.estimate_fidelity() == 0.98

    def test_estimate_fidelity_mixed_gates(self):
        """测试混合门的保真度估计."""
        estimator = SCEstimate(
            single_gate_fidelity=0.995, multi_gate_fidelity=0.98
        )

        gates = []

        single_gate = Mock()
        single_gate.type = 1
        single_gate.targets = [0]
        gates.append(single_gate)

        multi_gate = Mock()
        multi_gate.type = 2
        multi_gate.targets = [0, 1]
        gates.append(multi_gate)

        estimator.set_circuit(gates)
        # 预期: 0.995 * 0.98 = 0.9751
        assert pytest.approx(estimator.estimate_fidelity(), rel=1e-5) == 0.9751

    def test_estimate_fidelity_sync_operation(self):
        """测试同步操作不影响保真度."""
        estimator = SCEstimate(single_gate_fidelity=0.995)

        gates = []

        gate1 = Mock()
        gate1.type = 1
        gate1.targets = [0]
        gates.append(gate1)

        sync_op = Mock()
        sync_op.type = -1
        sync_op.targets = [1]
        gates.append(sync_op)

        gate2 = Mock()
        gate2.type = 1
        gate2.targets = [1]
        gates.append(gate2)

        estimator.set_circuit(gates)
        # 预期: 0.995 * 0.995 = 0.990025
        expected = 0.990025
        assert (
            pytest.approx(estimator.estimate_fidelity(), rel=1e-5) == expected
        )

    def test_estimate_fidelity_complex_circuit(self):
        """测试复杂电路的保真度估计."""
        estimator = SCEstimate(
            single_gate_fidelity=0.995, multi_gate_fidelity=0.98
        )

        gates = []

        gate1 = Mock()
        gate1.type = 1
        gate1.targets = [0]
        gates.append(gate1)

        gate2 = Mock()
        gate2.type = 2
        gate2.targets = [1, 2]
        gates.append(gate2)

        gate3 = Mock()
        gate3.type = 1
        gate3.targets = [0]
        gates.append(gate3)

        gate4 = Mock()
        gate4.type = 1
        gate4.targets = [1]
        gates.append(gate4)

        estimator.set_circuit(gates)
        # 预期: 0.995 * 0.98 * 0.995 * 0.995 = 0.960600125
        expected_fidelity = 0.995 * 0.98 * 0.995 * 0.995
        result = estimator.estimate_fidelity()
        assert pytest.approx(result, rel=1e-5) == expected_fidelity


class TestNAEstimate:
    """NAEstimate 类的单元测试."""

    def test_set_circuit(self):
        """测试设置电路."""
        estimator = NAEstimate()
        circuit = []
        estimator.set_circuit(circuit)
        assert estimator.circuit == circuit

    def test_estimate_time_with_moves_and_multi_qubit(self):
        """测试含移动与两比特门的时间估计路径."""
        estimator = NAEstimate(
            single_gate_duration=6,
            multi_gate_duration=2,
            move_duration=1000,
        )

        gate1 = Mock()
        gate1.type = 1
        gate1.targets = [0]

        gate2 = Mock()
        gate2.type = 2
        gate2.targets = [0, 1]

        gate3 = Mock()
        gate3.type = 2
        gate3.targets = [2, 3]

        move = Move(targets=[0])

        gate4 = Mock()
        gate4.type = 2
        gate4.targets = [2, 3]

        estimator.set_circuit([gate1, gate2, gate3, move, gate4])

        # gate1: +6, gate2: +2, gate3: +0 (non-overlap), move: +1000,
        # gate4: +2 (after move reset)
        assert estimator.estimate_time() == 1010

    def test_estimate_fidelity_with_move(self):
        """测试含移动操作的保真度估计."""
        estimator = NAEstimate(
            single_gate_fidelity=0.99,
            multi_gate_fidelity=0.98,
            mov_fidelity=0.97,
        )

        gate1 = Mock()
        gate1.type = 1
        gate1.targets = [0, 1]

        gate2 = Mock()
        gate2.type = 2
        gate2.targets = [0, 1]

        move = Move(targets=[0])

        estimator.set_circuit([gate1, gate2, move])

        expected = (0.99 * 0.99) * 0.98 * 0.97
        assert (
            pytest.approx(estimator.estimate_fidelity(), rel=1e-6) == expected
        )
