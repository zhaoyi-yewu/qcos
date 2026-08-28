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

# ruff: noqa: E402
# load driver venv

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library


org_path = Library.set_driver_venv_path(
    "logical_qubit", Config.DEFAULT.VENV_DIR
)

import pytest
from unittest.mock import patch, Mock

from wy_qcos.common.cmss.base_operation import BaseOperation
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import _s
from wy_qcos.device.device import Device
from wy_qcos.driver.logical_qubit.driver_lq_base import (
    DriverLogicalQubitBase,
)
from wy_qcos.driver.driver_base import DriverBase

# OperationType.DOUBLE_QUBIT_OPERATION has integer value 2;
# use the literal to avoid importing the compiled
# high_performance module (Linux-only) at test-collection time.
_OP_TYPE_DOUBLE_QUBIT = 2

driver_logical_qubit = DriverLogicalQubitBase()
shots = 10
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 5
data = {
    "index": 0,
    "source_code": "code",
    "transpile_results": [],
    "final_layout_dict": {job_id: {0: 0, 1: 1, 2: 9, 3: 4, 4: 3}},
}
data_type = DriverBase.DATA_TYPE_QASM2
result = {"count": {"11111": 9, "00000": 1}}
driver_configs = {
    "token": _s("test-token"),
    "url": "http://test.example.com",
    "chip_name": "qz01",
}


@pytest.mark.driver
class TestDriverLogicalQubit:
    # -- 1. init attributes --
    def test_init(self):
        assert driver_logical_qubit.version == "0.0.1"
        assert driver_logical_qubit.alias_name == "逻辑比特 QZ01 超导驱动"
        assert driver_logical_qubit.description == "逻辑比特 QZ01 超导驱动"
        assert driver_logical_qubit.transpiler == Constant.TRANSPILER_CMSS
        assert (
            driver_logical_qubit.tech_type
            == Constant.TECH_TYPE_SUPERCONDUCTING
        )
        assert driver_logical_qubit.supported_basis_gates == [
            Constant.SINGLE_QUBIT_GATE_I,
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_S,
            Constant.SINGLE_QUBIT_GATE_SDG,
            Constant.SINGLE_QUBIT_GATE_T,
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_Y,
            Constant.SINGLE_QUBIT_GATE_Z,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
        assert driver_logical_qubit.supported_transpilers == [
            Constant.TRANSPILER_CMSS,
            Constant.TRANSPILER_HIGH_PERFORMANCE_CMSS,
        ]
        assert driver_logical_qubit.enable_circuit_aggregation is False
        assert driver_logical_qubit.max_qubits == 17
        assert driver_logical_qubit.enable_device_monitor is True
        assert driver_logical_qubit.backend is None
        assert driver_logical_qubit.provider is None
        assert driver_logical_qubit.qpu_name is None
        assert driver_logical_qubit.url is None
        assert driver_logical_qubit.token is None

    # -- 2. init_driver --
    @patch.object(DriverLogicalQubitBase, "set_device_status")
    @patch("wy_qcos.driver.logical_qubit.driver_lq_base.LQCloudProvider")
    def test_init_driver(self, mock_provider_cls, mock_set_status):
        driver = DriverLogicalQubitBase()
        driver.set_configs(driver_configs)
        mock_provider = Mock()
        mock_provider_cls.return_value = mock_provider

        driver.init_driver()

        assert driver.token == _s("test-token")
        assert driver.url == "http://test.example.com"
        assert driver.qpu_name == "qz01"
        assert driver.provider is mock_provider
        mock_provider_cls.assert_called_once_with(
            api_key=_s("test-token"),
            url="http://test.example.com",
        )
        mock_set_status.assert_called_once_with(Device.DEVICE_STATUS_ONLINE)

    # -- 3. fetch_configs --
    @patch("wy_qcos.driver.logical_qubit.driver_lq_base.LQCloudProvider")
    def test_fetch_configs_success(self, mock_provider_cls):
        driver = DriverLogicalQubitBase()
        driver.set_configs(driver_configs)
        mock_provider = Mock()
        mock_backend = Mock()
        mock_provider.get_backend.return_value = mock_backend
        mock_provider_cls.return_value = mock_provider

        driver.fetch_configs()

        assert driver.token == _s("test-token")
        assert driver.url == "http://test.example.com"
        assert driver.qpu_name == "qz01"
        assert driver.provider is mock_provider
        assert driver.backend is mock_backend
        mock_provider.get_backend.assert_called_once_with("qz01")

    @patch("wy_qcos.driver.logical_qubit.driver_lq_base.LQCloudProvider")
    def test_fetch_configs_failure(self, mock_provider_cls):
        driver = DriverLogicalQubitBase()
        driver.set_configs(driver_configs)
        mock_provider_cls.side_effect = RuntimeError("conn refused")

        with pytest.raises(ValueError) as exc_info:
            driver.fetch_configs()

        assert "Logical_qubit exception" in str(exc_info.value)
        assert "conn refused" in str(exc_info.value)

    # -- 4. validate_driver_configs --
    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs_success(self, mock_validate_schema):
        mock_validate_schema.return_value = True, None
        configs = {
            "token": _s("t"),
            "chip_name": "c",
            "url": "u",
            "transpiler": {
                "qpu_configs": {
                    "qubits": 5,
                    "coupler_map": {"0": ["1"]},
                    "readout_error": {"0": 0.01},
                    "coupler_error": {"0": 0.02},
                }
            },
        }
        success, err_msg = driver_logical_qubit.validate_driver_configs(
            configs
        )
        assert success is True
        assert err_msg is None

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs_failure(self, mock_validate_schema):
        mock_validate_schema.return_value = (
            False,
            ["token is required"],
        )
        success, err_msg = driver_logical_qubit.validate_driver_configs({})
        assert success is False
        assert "token is required" in err_msg

    # -- 5. submit_task --
    def test_submit_task_success(self):
        driver = DriverLogicalQubitBase()
        driver.backend = Mock()
        expected_task = Mock(name="FakeTaskObject")
        driver.backend.run.return_value = expected_task
        qc = Mock()

        success, err_msg, task = driver.submit_task(qc, shots)

        assert success is True
        assert err_msg is None
        assert task is expected_task
        driver.backend.run.assert_called_once()

    def test_submit_task_failure(self):
        driver = DriverLogicalQubitBase()
        driver.backend = Mock()
        driver.backend.run.side_effect = RuntimeError("backend down")
        qc = Mock()

        success, err_msg, task = driver.submit_task(qc, shots)

        assert success is False
        assert "backend down" in err_msg
        assert task is None

    # -- 6. get_task_results --
    def test_get_task_results_success(self):
        driver = DriverLogicalQubitBase()
        mock_task = Mock()
        expected_data = {
            "status": "completed",
            "data": {"00000": 9, "11111": 1},
        }
        mock_task.result.return_value = expected_data

        success, err_msg, result = driver.get_task_results(mock_task)

        assert success is True
        assert err_msg is None
        assert result == expected_data

    def test_get_task_results_failure(self):
        driver = DriverLogicalQubitBase()
        mock_task = Mock()
        mock_task.result.side_effect = TimeoutError("task timeout")

        success, err_msg, result = driver.get_task_results(mock_task)

        assert success is False
        assert "task timeout" in err_msg
        assert result is None

    # -- 7. convert_results --
    def test_convert_results(self):
        driver = DriverLogicalQubitBase()
        mock_task = Mock()
        expected_data = {"00000": 9, "11111": 1}
        mock_task.get_counts.return_value = expected_data

        result = driver.convert_results(mock_task)

        assert result == {"00000": 9, "11111": 1}

    # -- 8. run (smoke) --
    @pytest.mark.smoke
    @patch.object(DriverLogicalQubitBase, "set_results")
    @patch.object(DriverLogicalQubitBase, "set_optimized_circuit")
    @patch.object(DriverLogicalQubitBase, "convert_code_to_qasm")
    @patch.object(DriverLogicalQubitBase, "convert_results")
    @patch.object(DriverLogicalQubitBase, "get_task_results")
    @patch.object(DriverLogicalQubitBase, "submit_task")
    @patch.object(DriverLogicalQubitBase, "convert_code")
    @patch.object(DriverLogicalQubitBase, "set_device_status")
    def test_run(
        self,
        mock_set_status,
        mock_convert_code,
        mock_submit_task,
        mock_get_task_results,
        mock_convert_results,
        mock_convert_code_to_qasm,
        mock_set_optimized_circuit,
        mock_set_results,
    ):
        mock_convert_code.return_value = Mock()
        mock_submit_task.return_value = (True, None, Mock())
        # _results must expose a ``.metadata`` attribute (accessed by
        # driver run() for machine profiling); use Mock with empty
        # metadata so the profiling branches are skipped.
        mock_results = Mock()
        mock_results.metadata = {}
        mock_get_task_results.return_value = (
            True,
            None,
            mock_results,
        )
        mock_convert_results.return_value = {
            "11111": 9,
            "00000": 1,
        }
        mock_convert_code_to_qasm.return_value = "qasm"

        driver_logical_qubit.run(job_id, num_qubits, data, data_type, shots)

        # device status flow: BUSY during run, ONLINE at end
        mock_set_status.assert_any_call(Device.DEVICE_STATUS_BUSY)
        mock_set_status.assert_any_call(Device.DEVICE_STATUS_ONLINE)
        # convert_code called with transpile_results
        assert mock_convert_code.called
        # submit_task called
        mock_submit_task.assert_called_once()
        # results stored
        mock_set_results.assert_called_once()
        _, kwargs = mock_set_results.call_args
        assert kwargs.get("result_type") == (Constant.RESULT_TYPE_SAMPLING)
        assert kwargs.get("results") == {
            "11111": 9,
            "00000": 1,
        }
        # optimized circuit set
        mock_set_optimized_circuit.assert_called_once_with("qasm")

    # -- 9. convert_code_to_qasm --
    def test_convert_code_to_qasm_empty_transpile(self):
        driver = DriverLogicalQubitBase()
        src = "OPENQASM 2.0;"
        result = driver.convert_code_to_qasm(num_qubits, src, [])
        assert result == src

    def test_convert_code_to_qasm_none_transpile(self):
        driver = DriverLogicalQubitBase()
        src = "OPENQASM 2.0;"
        result = driver.convert_code_to_qasm(num_qubits, src, None)
        assert result == src

    def test_convert_code_to_qasm_non_list_transpile(self):
        driver = DriverLogicalQubitBase()
        src = "OPENQASM 2.0;"
        result = driver.convert_code_to_qasm(num_qubits, src, "not-a-list")
        assert result == src

    def test_convert_code_to_qasm_valid_operations(self):
        driver = DriverLogicalQubitBase()
        ops = [
            BaseOperation(name="h", targets=[0]),
            BaseOperation(
                name="cz",
                targets=[0, 1],
                operation_type=_OP_TYPE_DOUBLE_QUBIT,
            ),
        ]
        result = driver.convert_code_to_qasm(num_qubits, "src", ops)
        assert isinstance(result, str)
        assert "h" in result
        assert "cz" in result

    def test_convert_code_to_qasm_non_baseoperation(self):
        driver = DriverLogicalQubitBase()
        src = "OPENQASM 2.0;"
        ops = [{"name": "h", "targets": [0]}]
        result = driver.convert_code_to_qasm(num_qubits, src, ops)
        assert result == src

    # -- 10. get_device_info --
    def test_get_device_info_success(self):
        driver = DriverLogicalQubitBase()
        driver.provider = Mock()
        cfg = {"qubits": 5, "status": "active"}
        driver.provider.get_backend_config.return_value = cfg

        success, err_msg, result = driver.get_device_info()

        assert success is True
        assert err_msg is None
        assert result == cfg

    def test_get_device_info_failure(self):
        driver = DriverLogicalQubitBase()
        driver.provider = Mock()
        driver.provider.get_backend_config.side_effect = RuntimeError(
            "network error"
        )

        success, err_msg, result = driver.get_device_info()

        assert success is False
        assert "network error" in err_msg
        assert result is None

    # -- 11. fetch_running_info --
    @patch("wy_qcos.common.library.Library.call_http_api")
    @patch.object(DriverLogicalQubitBase, "get_device_info")
    def test_fetch_running_info_success(
        self, mock_get_device_info, mock_call_http
    ):
        driver = DriverLogicalQubitBase()
        driver.token = _s("tok")
        driver.url = "http://test.example.com"
        driver.qpu_name = "qz01"
        cfg = {
            "qubits": 5,
            "status": "active",
            "properties": {
                "last_update": "2026-08-14 06:00:00",
                "qubit_metrics": [
                    {
                        "id": 0,
                        "xeb_fidelity": 0.99,
                        "t1": 100.0,
                        "t2": 80.0,
                        "measure_f0": 0.98,
                        "measure_f1": 0.97,
                    }
                ],
                "coupler_metrics": [{"qubits": [0, 1], "cz_fidelity": 0.95}],
            },
        }
        mock_get_device_info.return_value = (True, None, cfg)
        mock_response = Mock()
        mock_response.json.return_value = {
            "qz01": {
                "queued": 2,
                "running": 1,
                "total_pending": 3,
            }
        }
        mock_call_http.return_value = (
            200,
            "ok",
            "",
            mock_response,
        )

        info = driver.fetch_running_info()

        assert info["status"] == Device.DEVICE_STATUS_ONLINE
        assert info["available_qubits"] == 5
        assert "calibration" in info["details"]
        assert "last_updated_at" in info["details"]["calibration"]
        assert "qubit_metrics" in info["details"]["calibration"]
        assert "coupler_metrics" in info["details"]["calibration"]
        assert info["details"]["vendor_job_count"] == {
            "queued": 2,
            "running": 1,
            "total": 3,
        }

    @patch.object(DriverLogicalQubitBase, "get_device_info")
    def test_fetch_running_info_device_failure(self, mock_get_device_info):
        driver = DriverLogicalQubitBase()
        mock_get_device_info.return_value = (
            False,
            "unreachable",
            None,
        )

        info = driver.fetch_running_info()

        assert info["status"] == Device.DEVICE_STATUS_DISCONNECTED
        assert info["details"] == {}

    # -- 12. simple methods --
    def test_update_driver_options(self):
        driver = DriverLogicalQubitBase()
        original = dict(driver.driver_options)
        driver.update_driver_options({"qes": {"enable": True}})
        assert driver.driver_options.get("qes") == {"enable": True}
        for key in original:
            assert key in driver.driver_options

    def test_set_and_get_optimized_circuit(self):
        driver = DriverLogicalQubitBase()
        assert driver.get_optimized_circuit() is None
        driver.set_optimized_circuit("circuit-data")
        assert driver.get_optimized_circuit() == "circuit-data"

    def test_close_driver(self):
        driver = DriverLogicalQubitBase()
        assert driver.close_driver() is None

    def test_cancel(self):
        driver = DriverLogicalQubitBase()
        assert driver.cancel("job-1") is None
