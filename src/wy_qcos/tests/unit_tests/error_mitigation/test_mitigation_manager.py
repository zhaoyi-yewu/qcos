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
import numpy as np

from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.gate_operation import GateOperation
from wy_qcos.common.cmss.base_operation import OperationType
from wy_qcos.error_mitigation.mitigation_manager import MitigationManager


def make_test_circuit() -> QuantumCircuit:
    """Create a simple test circuit."""
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


class TestMitigationManagerConfigure:
    """Test MitigationManager configuration."""

    def test_configure_rem(self):
        mgr = MitigationManager()
        mgr.configure({"rem": {"enabled": True, "calibration_shots": 4096}})
        assert mgr.has_enabled()
        assert "rem" in mgr.get_enabled_names()

    def test_configure_multiple(self):
        mgr = MitigationManager()
        mgr.configure({
            "rem": {"enabled": True},
            "zne": {"enabled": True},
            "dd": {"enabled": False},
        })
        assert len(mgr.get_enabled_names()) == 2
        assert "rem" in mgr.get_enabled_names()
        assert "zne" in mgr.get_enabled_names()
        assert "dd" not in mgr.get_enabled_names()

    def test_configure_none_enabled(self):
        mgr = MitigationManager()
        mgr.configure({
            "rem": {"enabled": False},
            "zne": {"enabled": False},
        })
        assert not mgr.has_enabled()

    def test_configure_empty(self):
        mgr = MitigationManager()
        mgr.configure({})
        assert not mgr.has_enabled()


class TestMitigationManagerValidation:
    """Test device validation."""

    def test_validate_rem(self):
        mgr = MitigationManager()
        mgr.configure({"rem": {"enabled": True}})
        valid, msg = mgr.validate_device({})
        assert valid is True

    def test_validate_zne_without_cz(self):
        mgr = MitigationManager()
        mgr.configure({"zne": {"enabled": True}})
        valid, msg = mgr.validate_device({"basis_gates": ["u3", "cx"]})
        assert valid is False
        assert "CZ" in msg

    def test_validate_zne_with_cz(self):
        mgr = MitigationManager()
        mgr.configure({"zne": {"enabled": True}})
        valid, msg = mgr.validate_device({"basis_gates": ["u3", "cz"]})
        assert valid is True


class TestMitigationManagerCalibration:
    """Test calibration management."""

    def test_needs_calibration(self):
        mgr = MitigationManager()
        mgr.configure({"rem": {"enabled": True}})
        assert "rem" in mgr.needs_calibration()

    def test_no_calibration_needed(self):
        mgr = MitigationManager()
        mgr.configure({"zne": {"enabled": True}})
        assert "zne" not in mgr.needs_calibration()

    def test_get_calibration_circuits(self):
        mgr = MitigationManager()
        mgr.configure({"rem": {"enabled": True}})
        qc = make_test_circuit()
        circuits = mgr.get_calibration_circuits(qc, [0, 1])
        assert "readout" in circuits
        assert len(circuits["readout"]) == 4

    def test_store_calibration_data(self):
        mgr = MitigationManager()
        mgr.store_calibration_data("readout", {"test": True})
        assert "readout" in mgr._calibration_data


class TestMitigationManagerTransform:
    """Test circuit transformation."""

    def test_transform_no_mitigation(self):
        mgr = MitigationManager()
        mgr.configure({})
        qc = make_test_circuit()
        variants = mgr.transform_circuit(qc)
        assert len(variants) == 1

    def test_transform_zne(self):
        mgr = MitigationManager()
        mgr.configure({"zne": {"enabled": True}})
        qc = make_test_circuit()
        variants = mgr.transform_circuit(qc)
        assert len(variants) == 2
        labels = [v["label"] for v in variants]
        assert "original" in labels
        assert "scaled" in labels


class TestMitigationManagerPostprocess:
    """Test result post-processing."""

    def test_postprocess_no_mitigation(self):
        mgr = MitigationManager()
        mgr.configure({})
        results = {"original": {"00": 500, "11": 500}}
        output = mgr.postprocess_results(results, num_qubits=2)
        assert output["results"] == results
        assert output["mitigation_metadata"]["techniques_applied"] == []

    def test_postprocess_rem(self):
        mgr = MitigationManager()
        mgr.configure({"rem": {"enabled": True}})
        mgr.store_calibration_data(
            "readout",
            {
                "per_qubit_confusion": {
                    0: np.array([[0.95, 0.05], [0.05, 0.95]]),
                    1: np.array([[0.95, 0.05], [0.05, 0.95]]),
                },
                "target_qubits": [0, 1],
            },
        )
        results = {"original": {"00": 4500, "01": 200, "10": 300, "11": 5000}}
        output = mgr.postprocess_results(
            results, num_qubits=2, target_qubits=[0, 1]
        )
        assert "readout" in output["mitigation_metadata"]["techniques_applied"]

    def test_postprocess_rem_zne(self):
        mgr = MitigationManager()
        mgr.configure({"rem": {"enabled": True}, "zne": {"enabled": True}})
        mgr.store_calibration_data(
            "readout",
            {
                "per_qubit_confusion": {
                    0: np.array([[0.95, 0.05], [0.05, 0.95]]),
                    1: np.array([[0.95, 0.05], [0.05, 0.95]]),
                },
                "target_qubits": [0, 1],
            },
        )
        results = {
            "original": {"00": 4500, "01": 200, "10": 300, "11": 5000},
            "scaled": {"00": 4000, "01": 400, "10": 600, "11": 5000},
        }
        output = mgr.postprocess_results(
            results, num_qubits=2, target_qubits=[0, 1]
        )
        techniques = output["mitigation_metadata"]["techniques_applied"]
        assert "readout" in techniques
        assert "zne" in techniques

    def test_postprocess_preserves_raw_results(self):
        mgr = MitigationManager()
        mgr.configure({"rem": {"enabled": True}})
        mgr.store_calibration_data(
            "readout",
            {
                "per_qubit_confusion": {
                    0: np.array([[0.95, 0.05], [0.05, 0.95]]),
                },
                "target_qubits": [0],
            },
        )
        results = {"original": {"0": 600, "1": 400}}
        output = mgr.postprocess_results(
            results, num_qubits=1, target_qubits=[0]
        )
        assert "raw_results" in output["mitigation_metadata"]
        assert output["mitigation_metadata"]["raw_results"] == results
