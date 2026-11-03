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


import sys
from types import ModuleType
from unittest.mock import patch, Mock

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.driver.driver_base import DriverBase
from wy_qcos.driver.spinq import driver_spinq_base
from wy_qcos.driver.spinq.driver_spinq_base import DriverSpinqBase


# -- helpers ---------------------------------------------------------------


class MockOp:
    """Lightweight stand-in for a GateOperation / BaseOperation."""

    def __init__(self, name, targets, arg_value=None):
        self.name = name
        self.targets = list(targets)
        self.arg_value = list(arg_value) if arg_value else []


class MockPlatform:
    """Stand-in for a spinqit Platform object."""

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
    """Stand-in for a SpinQCloudResult object."""

    def __init__(self, counts=None, probabilities=None, shots=None):
        self.counts = counts
        self.probabilities = probabilities
        self._shots = shots


class MockSession:
    """Mock HTTP session for fetch_running_info tests."""

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
    """Stand-in for spinqit SpinQCloudBackend."""

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
    """Create mock spinqit modules to avoid torch/autograd import issues."""

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
    gates = {name: GateObj(name) for name in gate_names}

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
    spinq_client_mod.HOST = "https://cloud.spinq.com"

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

driver_spinq = DriverSpinqBase()
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 2
data_type = DriverBase.DATA_TYPE_GATE_SEQUENCE
shots = 1024


@pytest.mark.driver
class TestDriverSpinBase:
    """Unit tests for DriverSpinqBase."""

    # -- lifecycle --------------------------------------------------------

    def test_init_driver(self):
        assert driver_spinq.init_driver() is None

    def test_close_driver(self):
        driver_spinq._cloud_backend = Mock()
        assert driver_spinq.close_driver() is None
        assert driver_spinq._cloud_backend is None

    def test_cancel(self):
        assert driver_spinq.cancel("job-1") is None

    # -- config validation -----------------------------------------------

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs_valid(self, mock_validate):
        mock_validate.return_value = True, None
        configs = {
            "username": "user",
            "keyfile": "/path/to/key",
            "host": "https://example.com",
        }
        success, _ = driver_spinq.validate_driver_configs(configs)
        assert success is True

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs_invalid(self, mock_validate):
        mock_validate.return_value = False, ["username required"]
        success, err = driver_spinq.validate_driver_configs({})
        assert success is False
        assert "username required" in err

    # -- fetch_configs ----------------------------------------------------

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqBase, "get_configs")
    def test_fetch_configs_success(self, mock_get_configs):
        mock_get_configs.return_value = {
            "username": "user",
            "keyfile": "/path/to/key",
            "host": "https://example.com/api",
            "platform": "sqc_25_vp",
        }
        mock_backend = MockCloudBackend(
            platforms=[MockPlatform(code="sqc_25_vp", max_bitnum=25)],
        )
        _MOCK_SPINQIT[
            "spinqit.backend"
        ].get_spinq_cloud.return_value = mock_backend

        configs = driver_spinq.fetch_configs()

        assert configs["qpu_configs"]["qubits"] == 25
        assert "0" in configs["qpu_configs"]["coupler_map"]
        assert "1" in configs["qpu_configs"]["coupler_map"]
        assert driver_spinq._host == "https://example.com/api"
        assert driver_spinq._platform == "sqc_25_vp"

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqBase, "get_configs")
    def test_fetch_configs_coupler_map_bidirectional(self, mock_get_configs):
        mock_get_configs.return_value = {
            "username": "user",
            "keyfile": "/path/to/key",
            "host": "https://example.com/api",
            "platform": "sqc_25_vp",
        }
        mock_backend = MockCloudBackend(
            platforms=[
                MockPlatform(
                    code="sqc_25_vp",
                    max_bitnum=25,
                    coupling_map=[(0, 1), (1, 2), (2, 0)],
                ),
            ],
        )
        _MOCK_SPINQIT[
            "spinqit.backend"
        ].get_spinq_cloud.return_value = mock_backend

        configs = driver_spinq.fetch_configs()

        coupler_map = configs["qpu_configs"]["coupler_map"]
        assert "1" in coupler_map["0"]
        assert "0" in coupler_map["1"]
        assert "2" in coupler_map["1"]
        assert "1" in coupler_map["2"]
        assert "0" in coupler_map["2"]
        assert "2" in coupler_map["0"]

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqBase, "get_configs")
    def test_fetch_configs_platform_not_found(self, mock_get_configs):
        mock_get_configs.return_value = {
            "username": "user",
            "keyfile": "/path/to/key",
            "host": "https://example.com/api",
            "platform": "nonexistent",
        }
        mock_backend = MockCloudBackend(
            platforms=[MockPlatform(code="sqc_25_vp", max_bitnum=25)],
        )
        _MOCK_SPINQIT[
            "spinqit.backend"
        ].get_spinq_cloud.return_value = mock_backend

        with pytest.raises(ValueError, match="not found"):
            driver_spinq.fetch_configs()

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqBase, "get_configs")
    def test_fetch_configs_auth_failure(self, mock_get_configs):
        mock_get_configs.return_value = {
            "username": "user",
            "keyfile": "/path/to/key",
            "host": "https://example.com/api",
            "platform": "sqc_25_vp",
        }
        _MOCK_SPINQIT[
            "spinqit.backend"
        ].get_spinq_cloud.side_effect = Exception("Auth failed")

        with pytest.raises(ValueError, match="authentication failed"):
            driver_spinq.fetch_configs()

        _MOCK_SPINQIT["spinqit.backend"].get_spinq_cloud.side_effect = None

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqBase, "get_configs")
    def test_fetch_configs_no_platform(self, mock_get_configs):
        mock_get_configs.return_value = {
            "username": "user",
            "keyfile": "/path/to/key",
            "host": "https://example.com/api",
        }
        fresh = DriverSpinqBase()
        fresh._platform = None
        with pytest.raises(ValueError, match="No platform specified"):
            fresh.fetch_configs()

    # -- convert_to_spinqit_circuit ---------------------------------------

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    def test_convert_circuit_h_and_cx(self):
        ops = [MockOp("h", [0]), MockOp("cx", [0, 1])]
        circ = driver_spinq.convert_to_spinqit_circuit(ops, 2)
        assert circ.num_qubits == 2
        assert len(circ.gates) == 2

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    def test_convert_circuit_with_params(self):
        ops = [MockOp("rx", [0], [3.14])]
        circ = driver_spinq.convert_to_spinqit_circuit(ops, 1)
        assert len(circ.gates) == 1
        assert len(circ.gates[0]) == 3

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    def test_convert_circuit_skip_measure(self):
        ops = [MockOp("h", [0]), MockOp("measure", [0])]
        circ = driver_spinq.convert_to_spinqit_circuit(ops, 1)
        assert len(circ.gates) == 1

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    def test_convert_circuit_skip_barrier(self):
        ops = [MockOp("barrier", [0, 1]), MockOp("h", [0])]
        circ = driver_spinq.convert_to_spinqit_circuit(ops, 2)
        assert len(circ.gates) == 1

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    def test_convert_circuit_unsupported_gate(self):
        ops = [MockOp("unsupported_gate", [0])]
        with pytest.raises(ValueError, match="not supported"):
            driver_spinq.convert_to_spinqit_circuit(ops, 1)

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    def test_convert_circuit_empty_ops(self):
        circ = driver_spinq.convert_to_spinqit_circuit([], 2)
        assert circ.num_qubits == 2
        assert len(circ.gates) == 0

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    def test_convert_circuit_skip_reset_move_sync(self):
        ops = [
            MockOp("reset", [0]),
            MockOp("move", [0, 1]),
            MockOp("sync", [0, 1]),
            MockOp("h", [0]),
        ]
        circ = driver_spinq.convert_to_spinqit_circuit(ops, 2)
        assert len(circ.gates) == 1

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    def test_convert_circuit_multi_param_gate(self):
        ops = [MockOp("u", [0], [1.0, 2.0, 3.0])]
        circ = driver_spinq.convert_to_spinqit_circuit(ops, 1)
        assert len(circ.gates) == 1
        gate_entry = circ.gates[0]
        assert len(gate_entry) == 3
        assert gate_entry[2] == 1.0

    # -- convert_results -------------------------------------------------

    def test_convert_results_with_counts(self):
        result = MockSpinQCloudResult(counts={"00": 512, "11": 512})
        results = driver_spinq.convert_results(result)
        assert results == {"00": 512, "11": 512}

    def test_convert_results_with_probabilities(self):
        result = MockSpinQCloudResult(
            probabilities={"00": 0.5, "11": 0.5}, shots=1024
        )
        results = driver_spinq.convert_results(result)
        assert results == {"00": 512, "11": 512}

    def test_convert_results_none(self):
        with pytest.raises(ValueError, match="no result"):
            driver_spinq.convert_results(None)

    def test_convert_results_empty(self):
        result = MockSpinQCloudResult()
        with pytest.raises(ValueError, match="no counts or probabilities"):
            driver_spinq.convert_results(result)

    def test_convert_results_counts_takes_priority(self):
        result = MockSpinQCloudResult(
            counts={"00": 512, "11": 512},
            probabilities={"00": 0.25, "11": 0.75},
            shots=1024,
        )
        results = driver_spinq.convert_results(result)
        assert results == {"00": 512, "11": 512}

    # -- run (end-to-end with mocks) -------------------------------------

    @pytest.mark.smoke
    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqBase, "convert_results")
    @patch.object(DriverSpinqBase, "convert_to_spinqit_circuit")
    def test_run(self, mock_convert_circuit, mock_convert_results):
        mock_convert_circuit.return_value = Mock()
        mock_convert_results.return_value = {"00": 512, "11": 512}

        mock_backend = MockCloudBackend()
        driver_spinq._cloud_backend = mock_backend
        driver_spinq._platform = "sqc_25_vp"

        data = {"index": 0, "source_code": "", "transpile_results": []}
        driver_spinq.run(job_id, num_qubits, data, data_type, shots)

        assert driver_spinq.get_progress() == 95

    @pytest.mark.smoke
    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqBase, "convert_results")
    @patch.object(DriverSpinqBase, "convert_to_spinqit_circuit")
    def test_run_no_cloud_backend(
        self, mock_convert_circuit, mock_convert_results
    ):
        mock_convert_circuit.return_value = Mock()
        mock_convert_results.return_value = {"00": 512}
        driver_spinq._cloud_backend = None
        driver_spinq._platform = "sqc_25_vp"

        data = {"index": 0, "source_code": "", "transpile_results": []}
        with pytest.raises(AttributeError):
            driver_spinq.run(job_id, num_qubits, data, data_type, shots)

    @patch.dict(sys.modules, _MOCK_SPINQIT)
    @patch.object(driver_spinq_base, "_spinqit_gates", None)
    @patch.object(DriverSpinqBase, "convert_to_spinqit_circuit")
    def test_run_execute_returns_none(self, mock_convert_circuit):
        mock_convert_circuit.return_value = Mock()
        mock_backend = MockCloudBackend(execute_result=None)
        mock_backend.execute = Mock(return_value=None)
        driver_spinq._cloud_backend = mock_backend
        driver_spinq._platform = "sqc_25_vp"

        data = {"index": 0, "source_code": "", "transpile_results": []}
        with pytest.raises(ValueError, match="no result"):
            driver_spinq.run(job_id, num_qubits, data, data_type, shots)

    # -- class attributes ------------------------------------------------

    def test_default_host(self):
        assert DriverSpinqBase.default_host == "https://cloud.spinq.com/api"

    def test_default_shots(self):
        assert DriverSpinqBase.default_shots == 1024

    def test_supported_basis_gates(self):
        assert driver_spinq.supported_basis_gates == []

    def test_transpiler(self):
        assert driver_spinq.transpiler == Constant.TRANSPILER_CMSS

    def test_max_qubits(self):
        assert driver_spinq.max_qubits == 0
