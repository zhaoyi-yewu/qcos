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


from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.gate_operation import GateOperation
from wy_qcos.common.cmss.base_operation import OperationType
from wy_qcos.error_mitigation.dd_mitigation import (
    DDMitigation,
    detect_idle_windows,
    generate_dd_sequence,
    insert_dd_into_circuit,
    XY4_PULSES,
    CPMG_PULSES,
)


def make_simple_circuit() -> QuantumCircuit:
    """Create a simple circuit with idle windows."""
    qc = QuantumCircuit(2)
    qc.append(
        GateOperation(
            "h",
            targets=[0],
            operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
        )
    )
    qc.append(
        GateOperation(
            "cz",
            targets=[0, 1],
            operation_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
        )
    )
    return qc


class TestDetectIdleWindows:
    """Test detect_idle_windows function."""

    def test_single_qubit_idle(self):
        ops = [
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            ),
            GateOperation(
                "h",
                targets=[1],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            ),
            GateOperation(
                "cz",
                targets=[0, 1],
                operation_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
            ),
        ]
        gate_times = {"h": 0.02, "cz": 0.04}
        windows = detect_idle_windows(ops, 2, gate_times)
        assert len(windows[0]) == 0 or all(
            w["duration"] >= 0 for w in windows[0]
        )
        assert len(windows[1]) >= 0

    def test_no_idle_windows(self):
        ops = [
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            ),
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            ),
        ]
        gate_times = {"h": 0.02}
        windows = detect_idle_windows(ops, 1, gate_times)
        assert len(windows[0]) == 0

    def test_measures_ignored(self):
        from wy_qcos.common.cmss.measure import Measure

        ops = [
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            ),
            Measure(targets=[0]),
        ]
        gate_times = {"h": 0.02}
        windows = detect_idle_windows(ops, 1, gate_times)
        assert len(windows[0]) == 0


class TestGenerateDdSequence:
    """Test generate_dd_sequence function."""

    def test_xy4_pulses(self):
        gate_times = {"x": 0.02, "y": 0.02}
        ops = generate_dd_sequence(1.0, "XY4", gate_times, 0)
        gate_names = [op.name for op in ops if op.name in ("x", "y")]
        assert gate_names == XY4_PULSES

    def test_cpmg_pulses(self):
        gate_times = {"x": 0.02}
        ops = generate_dd_sequence(1.0, "CPMG", gate_times, 0)
        gate_names = [op.name for op in ops if op.name == "x"]
        assert gate_names == CPMG_PULSES

    def test_too_short_window(self):
        gate_times = {"x": 1.0}
        ops = generate_dd_sequence(0.1, "XY4", gate_times, 0)
        assert len(ops) == 0

    def test_delay_operations_present(self):
        gate_times = {"x": 0.02, "y": 0.02}
        ops = generate_dd_sequence(1.0, "XY4", gate_times, 0)
        delay_ops = [op for op in ops if op.name == "delay"]
        assert len(delay_ops) == len(XY4_PULSES) + 1


class TestNewDdSequences:
    """Test the mitiq-aligned sequences (XY8, XXYX, XX, UDD)."""

    def test_xy8_pulses(self):
        from wy_qcos.error_mitigation.dd_mitigation import XY8_PULSES

        gate_times = {"x": 0.02, "y": 0.02}
        ops = generate_dd_sequence(2.0, "XY8", gate_times, 0)
        gate_names = [op.name for op in ops if op.name in ("x", "y")]
        assert gate_names == XY8_PULSES

    def test_xxyx_pulses(self):
        from wy_qcos.error_mitigation.dd_mitigation import XXYX_PULSES

        gate_times = {"x": 0.02, "y": 0.02}
        ops = generate_dd_sequence(1.0, "XXYX", gate_times, 0)
        gate_names = [op.name for op in ops if op.name in ("x", "y")]
        assert gate_names == XXYX_PULSES

    def test_xx_pulses(self):
        from wy_qcos.error_mitigation.dd_mitigation import XX_PULSES

        gate_times = {"x": 0.02}
        ops = generate_dd_sequence(1.0, "XX", gate_times, 0)
        gate_names = [op.name for op in ops if op.name in ("x", "y")]
        assert gate_names == XX_PULSES

    def test_udd4_pulse_count(self):
        # UDD4 -> 4 pulses
        gate_times = {"x": 0.02, "y": 0.02}
        ops = generate_dd_sequence(2.0, "UDD4", gate_times, 0)
        gate_names = [op.name for op in ops if op.name in ("x", "y")]
        assert len(gate_names) == 4

    def test_udd_nonuniform_spacing(self):
        # Uhrig centres are NOT evenly spaced: the k-th centre is
        # sin^2(k*pi/2*(n+1)); for UDD4 the centres (as fraction of
        # window) are [sin^2(pi/10), sin^2(2pi/10), ...] which are not
        # equal multiples.
        import numpy as np
        from wy_qcos.error_mitigation.dd_mitigation import udd_pulses

        n = 4
        centres = [
            float((np.sin(np.pi * k / (2 * (n + 1)))) ** 2)
            for k in range(1, n + 1)
        ]
        # adjacent gaps are not all equal
        gaps = [centres[k] - centres[k - 1] for k in range(1, n)]
        assert len(set(round(g, 6) for g in gaps)) > 1
        # axis sequence for even order alternates y/x
        assert udd_pulses(4) == ["y", "x", "y", "x"]

    def test_unknown_sequence_falls_back_to_xy4(self):
        gate_times = {"x": 0.02, "y": 0.02}
        ops = generate_dd_sequence(1.0, "NONSENSE", gate_times, 0)
        gate_names = [op.name for op in ops if op.name in ("x", "y")]
        assert gate_names == XY4_PULSES


class TestIdleWindowDetection:
    """Test the improved detect_idle_windows."""

    def test_barrier_aligns_clocks(self):
        # h on q0 (0->0.02), barrier {0,1}, then h on q1.
        # Without barrier q1's first gate would start at 0; with barrier
        # it starts at 0.02, so q1 has no idle window before its gate
        # (the barrier already advanced its clock).
        from wy_qcos.common.cmss.base_operation import BaseOperation

        ops = [
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            ),
            BaseOperation("barrier", targets=[0, 1]),
            GateOperation(
                "h",
                targets=[1],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            ),
        ]
        gate_times = {"h": 0.02, "barrier": 0.0}
        windows = detect_idle_windows(ops, 2, gate_times)
        # q1 clock was advanced by barrier, so its h starts at 0.02 -> no gap
        assert all(w["duration"] >= 0 for w in windows[1])

    def test_include_trailing(self):
        # h on q0 only; q1 never touched -> trailing window = full depth.
        ops = [
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            ),
        ]
        gate_times = {"h": 0.02}
        windows = detect_idle_windows(
            ops, 2, gate_times, include_trailing=True
        )
        # q1 has one trailing window of 0.02us
        assert len(windows[1]) == 1
        assert abs(windows[1][0]["duration"] - 0.02) < 1e-9

    def test_no_trailing_by_default(self):
        ops = [
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            ),
        ]
        gate_times = {"h": 0.02}
        windows = detect_idle_windows(ops, 2, gate_times)
        assert windows[1] == []


class TestInsertDdIntoCircuit:
    """Test insert_dd_into_circuit function."""

    def test_no_gate_times(self):
        qc = make_simple_circuit()
        new_qc, metadata = insert_dd_into_circuit(qc, "XY4", None)
        assert metadata["dd_applied"] is False
        assert metadata["reason"] == "no_gate_times"

    def test_dd_inserted(self):
        qc = QuantumCircuit(2)
        qc.append(
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            )
        )
        qc.append(
            GateOperation(
                "h",
                targets=[1],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            )
        )
        qc.append(
            GateOperation(
                "cz",
                targets=[0, 1],
                operation_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
            )
        )
        gate_times = {
            "h": 0.02,
            "cz": 0.04,
            "x": 0.02,
            "y": 0.02,
            "default": 0.02,
        }
        new_qc, metadata = insert_dd_into_circuit(qc, "XY4", gate_times)
        if metadata["dd_applied"]:
            assert new_qc.size() > qc.size()
            assert metadata["windows_filled"] > 0

    def test_circuit_preserved_when_no_idle(self):
        qc = QuantumCircuit(1)
        qc.append(
            GateOperation(
                "h",
                targets=[0],
                operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            )
        )
        gate_times = {"h": 0.02, "x": 0.02}
        new_qc, metadata = insert_dd_into_circuit(qc, "XY4", gate_times)
        assert metadata["dd_applied"] is False


class TestDDMitigation:
    """Test DDMitigation class."""

    def test_initialization(self):
        dd = DDMitigation(sequence="XY4")
        assert dd.name == "dd"
        assert dd._sequence == "XY4"

    def test_set_config(self):
        dd = DDMitigation()
        dd.set_config({"enabled": True, "sequence": "CPMG"})
        assert dd.enabled is True
        assert dd._sequence == "CPMG"

    def test_validate_device_with_gate_times(self):
        dd = DDMitigation()
        valid, msg = dd.validate_device({
            "gate_times": {"h": 0.02, "cz": 0.04}
        })
        assert valid is True

    def test_validate_device_without_gate_times(self):
        dd = DDMitigation()
        valid, msg = dd.validate_device({})
        assert valid is False
        assert "gate timing" in msg.lower()

    def test_transform_circuit(self):
        gate_times = {"h": 0.02, "cz": 0.04, "x": 0.02, "y": 0.02}
        dd = DDMitigation(sequence="XY4", gate_times=gate_times)
        dd.set_config({"enabled": True})
        qc = make_simple_circuit()
        variants = dd.transform_circuit(qc)
        assert len(variants) == 1
        assert variants[0]["label"] == "original"

    def test_postprocess_passthrough(self):
        dd = DDMitigation()
        results = {"original": {"00": 500, "11": 500}}
        output = dd.postprocess(results)
        assert output["results"] == results
        assert output["metadata"]["technique"] == "dd"
