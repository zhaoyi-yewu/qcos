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

# ruff: noqa: S105

import sys
from types import ModuleType
from unittest.mock import patch, Mock

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_base import DriverBase
from wy_qcos.driver.spinq import driver_spinq_base
from wy_qcos.driver.spinq.driver_spinq_base import DriverSpinqBase
from wy_qcos.driver.spinq.spinq_sqc_25.driver_spinq_sqc_25 import (
    DriverSpinqSqc25,
)


# -- helpers (duplicated from test_driver_spinq_base for isolation) -----


class MockOp:
    def __init__(self, name, targets, arg_value=None):
        self.name = name
        self.targets = list(targets)
        self.arg_value = list(arg_value) if arg_value else []


class MockPlatform:
    def __init__(
        self,
        code="sqc_25_vp",
        max_bitnum=25,
        coupling_map=None,
        available=True,
    ):
        self.code = code
        self.max_bitnum = max_bitnum
        self.coupling_map = coupling_map or [(0, 1), (1, 0)]
        self.machine_count = 1 if available else 0
        self.active_qubits = [0, 1] if available else []

    def available(self):
        return self.machine_count > 0


class MockSpinQCloudResult:
    def __init__(self, counts=None, probabilities=None, shots=None):
        self.counts = counts
        self.probabilities = probabilities
        self._shots = shots


class MockSession:
    def __init__(self, status_code=200, json_data=None):
        self._json_data = json_data or {}
        self._response = Mock()
        self._response.status_code = status_code
        if status_code >= 400:
            self._response.raise_for_status.side_effect = Exception(
                f"HTTP {status_code}"
            )
        else:
            self._response.raise_for_status = Mock()
        self._response.json = Mock(return_value=self._json_data)

    def get(self, url):
        return self._response


class MockApiClient:
    def __init__(self, session=None):
        self._session = session or MockSession()


class MockCloudBackend:
    def __init__(self, platforms=None, session=None, execute_result=None):
        self.platforms = platforms or [MockPlatform()]
        self._api_client = MockApiClient(session=session)
        self._execute_result = execute_result

    def refresh_remote_platforms(self):
        pass

    def get_platform(self, code):
        for p in self.platforms:
            if p.code == code:
                return p
        raise ValueError(f"Platform '{code}' not found")

    def execute(self, ir, config):
        if self._execute_result is not None:
            return self._execute_result
        return MockSpinQCloudResult(counts={"00": 512, "11": 512})


def _make_mock_spinqit_modules():
    class GateObj:
        def __init__(self, name):
            self.name = name

    gate_names = [
        "I",
        "H",
        "X",
        "Y",
        "Z",
        "Rx",
        "Ry",
        "Rz",
        "P",
        "T",
        "Td",
        "S",
        "Sd",
        "CX",
        "CY",
        "CZ",
        "SWAP",
        "CCX",
        "U",
    ]
    gates = {n: GateObj(n) for n in gate_names}

    class MockCircuit:
        def __init__(self):
            self.gates = []
            self.num_qubits = 0

        def allocateQubits(self, n):
            self.num_qubits = n

        def __lshift__(self, item):
            self.gates.append(item)

    class MockCompiler:
        def compile(self, circ, mode=0):
            return Mock()

    class MockSpinQCloudConfig:
        def configure_platform(self, code):
            pass

        def configure_task(self, name, desc):
            pass

        def configure_shots(self, shots):
            pass

    spinqit_mod = ModuleType("spinqit")
    for k, v in gates.items():
        setattr(spinqit_mod, k, v)
    spinqit_mod.get_compiler = Mock(return_value=MockCompiler())
    model_mod = ModuleType("spinqit.model")
    model_mod.Circuit = MockCircuit
    backend_mod = ModuleType("spinqit.backend")
    backend_mod.get_spinq_cloud = Mock()
    backend_mod.SpinQCloudConfig = MockSpinQCloudConfig
    client_mod = ModuleType("spinqit.backend.client")
    client_mod.__path__ = []
    spinq_client_mod = ModuleType("spinqit.backend.client.spinq_client")
    spinq_client_mod.HOST = "http://cloud.spinq.com"
    spinq_session_mod = ModuleType("spinqit.backend.client.spinq_session")

    class MockSpinQSession:
        def __init__(self):
            pass

    spinq_session_mod.SpinQSession = MockSpinQSession
    client_mod.spinq_client = spinq_client_mod
    spinq_backend_mod = ModuleType("spinqit.backend.spinq_backend")
    spinq_backend_mod.SpinQCloudConfig = MockSpinQCloudConfig
    return {
        "spinqit": spinqit_mod,
        "spinqit.model": model_mod,
        "spinqit.backend": backend_mod,
        "spinqit.backend.client": client_mod,
        "spinqit.backend.client.spinq_client": spinq_client_mod,
        "spinqit.backend.client.spinq_session": spinq_session_mod,
        "spinqit.backend.spinq_backend": spinq_backend_mod,
    }


_MOCK_SPINQIT = _make_mock_spinqit_modules()


# -- module-level fixtures -------------------------------------------------

driver_sqc25 = DriverSpinqSqc25()
job_id = "00000000-0000-4000-8000-000000000002"
num_qubits = 2
data_type = DriverBase.DATA_TYPE_GATE_SEQUENCE
shots = 1024


@pytest.mark.driver
class TestDriverSpinqSqc25:
    """Unit tests for DriverSpinqSqc25 (platform=sqc_25_vp, max_qubits=25).

    These tests focus on SQC-25-specific defaults and overrides.
    Core logic is already covered by test_driver_spinq_base.py and is
    inherited unchanged.
    """

    # -- subclass defaults ------------------------------------------------

    def test_inherits_from_base(self):
        assert isinstance(driver_sqc25, DriverSpinqBase)

    def test_default_platform(self):
        assert driver_sqc25._platform == "sqc_25_vp"

    def test_max_qubits(self):
        assert driver_sqc25.max_qubits == 25

    def test_tech_type_inherited(self):
        assert driver_sqc25.tech_type == Constant.TECH_TYPE_SUPERCONDUCTING

    def test_supported_basis_gates(self):
        expected = [
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_I,
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_Y,
            Constant.SINGLE_QUBIT_GATE_Z,
            Constant.TWO_QUBIT_GATE_CX,
            Constant.SINGLE_QUBIT_GATE_RX,
        ]
        assert driver_sqc25.supported_basis_gates == expected

    def test_supported_transpilers(self):
        assert Constant.TRANSPILER_CMSS in driver_sqc25.supported_transpilers
        assert (
            Constant.TRANSPILER_HIGH_PERFORMANCE_CMSS
            in driver_sqc25.supported_transpilers
        )

    def test_enable_circuit_aggregation(self):
        assert driver_sqc25.enable_circuit_aggregation is True

    def test_default_data_type(self):
        assert (
            driver_sqc25.default_data_type
            == DriverBase.DATA_TYPE_GATE_SEQUENCE
        )

    # -- lifecycle --------------------------------------------------------

    def test_init_driver(self):
        assert driver_sqc25.init_driver() is None

    def test_close_driver(self):
        driver_sqc25._cloud_backend = Mock()
        assert driver_sqc25.close_driver() is None
        assert driver_sqc25._cloud_backend is None

    def test_cancel(self):
        assert driver_sqc25.cancel("job-1") is None

    # -- convert_results (inherited) -------------------------------------

    def test_convert_results_with_counts(self):
        result = MockSpinQCloudResult(counts={"00": 512, "11": 512})
        results = driver_sqc25.convert_results(result)
        assert results == {"00": 512, "11": 512}

    def test_convert_results_with_probabilities(self):
        result = MockSpinQCloudResult(
            probabilities={"00": 0.5, "11": 0.5}, shots=1024
        )
        results = driver_sqc25.convert_results(result)
        assert results == {"00": 512, "11": 512}

    def test_convert_results_none(self):
        with pytest.raises(ValueError, match="no result"):
            driver_sqc25.convert_results(None)

    def test_convert_results_empty(self):
        result = MockSpinQCloudResult()
        with pytest.raises(ValueError, match="no counts or probabilities"):
            driver_sqc25.convert_results(result)

    # -- convert_to_spinqit_circuit (inherited) --------------------------

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    def test_convert_circuit_h_and_cx(self):
        ops = [MockOp("h", [0]), MockOp("cx", [0, 1])]
        circ = driver_sqc25.convert_to_spinqit_circuit(ops, 2)
        assert circ.num_qubits == 2
        assert len(circ.gates) == 2

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    def test_convert_circuit_with_params(self):
        ops = [MockOp("rx", [0], [3.14])]
        circ = driver_sqc25.convert_to_spinqit_circuit(ops, 1)
        assert len(circ.gates) == 1
        assert len(circ.gates[0]) == 3

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    def test_convert_circuit_skip_measure(self):
        ops = [MockOp("h", [0]), MockOp("measure", [0])]
        circ = driver_sqc25.convert_to_spinqit_circuit(ops, 1)
        assert len(circ.gates) == 1

    # -- fetch_running_info ----------------------------------------------

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqSqc25, "fetch_configs")
    def test_fetch_running_info_online(self, mock_fetch):
        mock_fetch.return_value = {"qpu_configs": {"qubits": 25}}
        session = MockSession(
            json_data={
                "status": 200,
                "item": {
                    "maxBitNum": 25,
                    "latestReviseTime": "2026-08-21",
                    "singleQubitSpec": {
                        "1": {"t1": 100, "t2": 80, "f_ro": 0.99},
                        "2": {"t1": 90, "t2": 70, "f_ro": 0.98},
                    },
                    "dualQubitsSpec": {"1_2": {"f_cz": 0.95}},
                    "curCouplingMap": {"1": [2]},
                },
            }
        )
        mock_backend = MockCloudBackend(
            platforms=[MockPlatform(code="sqc_25_vp", available=True)],
            session=session,
        )
        driver_sqc25._cloud_backend = mock_backend
        driver_sqc25._platform = "sqc_25_vp"
        driver_sqc25._machine_code = "sqc_25_vp"
        driver_sqc25._host = "https://example.com/api"

        info = driver_sqc25.fetch_running_info()

        assert info["status"] == Device.DEVICE_STATUS_ONLINE
        assert info["available_qubits"] == 25
        calib = info["details"]["calibration"]
        assert calib["last_updated_at"] == "2026-08-21"
        assert len(calib["qubit_metrics"]) == 2
        assert calib["qubit_metrics"][0]["qubit_id"] == 0
        assert calib["qubit_metrics"][0]["t1"] == 100
        assert len(calib["coupler_metrics"]) == 1
        assert calib["coupler_metrics"][0]["qubits"] == [0, 1]
        assert calib["coupler_metrics"][0]["cz_fidelity"] == 0.95

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqSqc25, "fetch_configs")
    def test_fetch_running_info_offline(self, mock_fetch):
        mock_fetch.return_value = {"qpu_configs": {"qubits": 25}}
        mock_backend = MockCloudBackend(
            platforms=[MockPlatform(code="sqc_25_vp", available=False)],
        )
        driver_sqc25._cloud_backend = mock_backend
        driver_sqc25._platform = "sqc_25_vp"

        info = driver_sqc25.fetch_running_info()

        assert info["status"] == Device.DEVICE_STATUS_OFFLINE

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqSqc25, "fetch_configs")
    def test_fetch_running_info_cloud_backend_none(self, mock_fetch):
        mock_fetch.return_value = {"qpu_configs": {"qubits": 25}}
        mock_backend = MockCloudBackend(
            platforms=[MockPlatform(code="sqc_25_vp", available=True)],
        )
        driver_sqc25._cloud_backend = None

        def side_effect():
            driver_sqc25._cloud_backend = mock_backend
            return {"qpu_configs": {"qubits": 25}}

        mock_fetch.side_effect = side_effect
        driver_sqc25._platform = "sqc_25_vp"
        driver_sqc25._machine_code = "sqc_25_vp"
        driver_sqc25._host = "https://example.com/api"

        info = driver_sqc25.fetch_running_info()

        assert info["status"] == Device.DEVICE_STATUS_ONLINE

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqSqc25, "fetch_configs")
    def test_fetch_running_info_fetch_configs_fail(self, mock_fetch):
        mock_fetch.side_effect = Exception("Connection refused")
        driver_sqc25._cloud_backend = None

        info = driver_sqc25.fetch_running_info()

        assert info["status"] == Device.DEVICE_STATUS_OFFLINE
        assert info["details"] == {}

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqSqc25, "fetch_configs")
    def test_fetch_running_info_spec_api_error(self, mock_fetch):
        mock_fetch.return_value = {"qpu_configs": {"qubits": 25}}
        session = MockSession(
            json_data={
                "status": 500,
                "msg": "internal error",
            }
        )
        mock_backend = MockCloudBackend(
            platforms=[
                MockPlatform(
                    code="sqc_25_vp",
                    available=True,
                    coupling_map=[(0, 1)],
                ),
            ],
            session=session,
        )
        driver_sqc25._cloud_backend = mock_backend
        driver_sqc25._platform = "sqc_25_vp"
        driver_sqc25._machine_code = "sqc_25_vp"
        driver_sqc25._host = "https://example.com/api"

        info = driver_sqc25.fetch_running_info()

        assert info["status"] == Device.DEVICE_STATUS_ONLINE
        assert info["available_qubits"] == 25
        calib = info["details"]["calibration"]
        assert len(calib["qubit_metrics"]) == 2
        assert calib["qubit_metrics"][0]["qubit_id"] == 0
        assert len(calib["coupler_metrics"]) == 1
        assert calib["coupler_metrics"][0]["qubits"] == [0, 1]

    # -- run (end-to-end with mocks) -------------------------------------

    @pytest.mark.smoke
    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqSqc25, "convert_results")
    @patch.object(DriverSpinqSqc25, "convert_to_spinqit_circuit")
    def test_run(self, mock_convert_circuit, mock_convert_results):
        mock_convert_circuit.return_value = Mock()
        mock_convert_results.return_value = {"00": 512, "11": 512}

        mock_backend = MockCloudBackend()
        driver_sqc25._cloud_backend = mock_backend
        driver_sqc25._platform = "sqc_25_vp"

        data = {"index": 0, "source_code": "", "transpile_results": []}
        driver_sqc25.run(job_id, num_qubits, data, data_type, shots)

        assert driver_sqc25.get_progress() == 95

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqSqc25, "convert_to_spinqit_circuit")
    def test_run_execute_returns_none(self, mock_convert_circuit):
        mock_convert_circuit.return_value = Mock()
        mock_backend = MockCloudBackend()
        mock_backend.execute = Mock(return_value=None)
        driver_sqc25._cloud_backend = mock_backend
        driver_sqc25._platform = "sqc_25_vp"

        data = {"index": 0, "source_code": "", "transpile_results": []}
        with pytest.raises(ValueError, match="no result"):
            driver_sqc25.run(job_id, num_qubits, data, data_type, shots)

    # -- fetch_configs with sqc_25 defaults ------------------------------

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqSqc25, "get_configs")
    def test_fetch_configs_preserves_platform(self, mock_get_configs):
        mock_get_configs.return_value = {
            "username": "user",
            "keyfile": "/path/to/key",
            "host": "https://example.com/api",
        }
        mock_backend = MockCloudBackend(
            platforms=[MockPlatform(code="sqc_25_vp", max_bitnum=25)],
        )
        _MOCK_SPINQIT[
            "spinqit.backend"
        ].get_spinq_cloud.return_value = mock_backend

        configs = driver_sqc25.fetch_configs()

        assert configs["qpu_configs"]["qubits"] == 25
        assert driver_sqc25._platform == "sqc_25_vp"
        assert driver_sqc25._machine_code == "sqc_25_vp"

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqSqc25, "get_configs")
    def test_fetch_configs_config_overrides_platform(self, mock_get_configs):
        mock_get_configs.return_value = {
            "username": "user",
            "keyfile": "/path/to/key",
            "host": "https://example.com/api",
            "platform": "custom_platform",
            "machine_code": "custom_machine",
        }
        mock_backend = MockCloudBackend(
            platforms=[MockPlatform(code="custom_platform", max_bitnum=10)],
        )
        _MOCK_SPINQIT[
            "spinqit.backend"
        ].get_spinq_cloud.return_value = mock_backend

        configs = driver_sqc25.fetch_configs()

        assert configs["qpu_configs"]["qubits"] == 10
        assert driver_sqc25._platform == "custom_platform"
        assert driver_sqc25._machine_code == "custom_machine"
