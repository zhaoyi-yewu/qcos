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
# pylint: disable=bad-continuation

"""Unit tests for the Qudoor AbaQu100 quantum device driver."""

import json

import pytest
from unittest.mock import patch, Mock

from wy_qcos.common.constant import HttpCode
from wy_qcos.common.library import Library
from wy_qcos.driver.qudoor.driver_qudoor_abaqu100 import (
    DriverQudoorAbaQu100,
)
from wy_qcos.driver.qudoor.driver_qudoor_base import (
    CODE_SUCCESS,
    TASK_STATUS_SUCCESS,
)
from wy_qcos.device.device import Device


# -- helpers ---------------------------------------------------------------


class MockOp:
    """Lightweight stand-in for a GateOperation / BaseOperation."""

    def __init__(self, name, targets, arg_value=None):
        """Initialize a mock operation with its gate and target data."""
        self.name = name
        self.targets = list(targets)
        self.arg_value = list(arg_value) if arg_value else []


def _http_ok(text):
    """Build a successful call_http_api return tuple."""
    return (HttpCode.SUCCESS_OK, "OK", text, Mock())


def _http_err(status, reason="Not Found", text=""):
    """Build a failed call_http_api return tuple."""
    return (status, reason, text, Mock())


# -- module-level fixtures -------------------------------------------------

driver = DriverQudoorAbaQu100()
driver.base_url = "http://localhost:8081"
driver.client_id = "cmccos"
driver.eng_code = "lizi0001"
driver.user_id = "demo_user"


@pytest.mark.driver
class TestDriverQudoorAbaQu100:
    """Unit tests for DriverQudoorAbaQu100."""

    # -- lifecycle --------------------------------------------------------

    def test_init_driver(self):
        """Verify driver initialization completes without a return value."""
        assert driver.init_driver() is None

    def test_close_driver(self):
        """Verify driver closure completes without a return value."""
        assert driver.close_driver() is None

    def test_cancel(self):
        """Verify task cancellation completes without a return value."""
        assert driver.cancel("job-1") is None

    # -- config validation -----------------------------------------------

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs_valid(self, mock_validate):
        """Verify valid driver configurations pass schema validation."""
        mock_validate.return_value = True, None
        configs = {"url": "http://localhost"}
        success, _ = driver.validate_driver_configs(configs)
        assert success is True

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs_invalid(self, mock_validate):
        """Verify invalid driver configurations return validation errors."""
        mock_validate.return_value = False, ["url required"]
        success, err = driver.validate_driver_configs({})
        assert success is False
        assert "url required" in err

    # -- fetch_configs ----------------------------------------------------

    @patch.object(DriverQudoorAbaQu100, "get_configs")
    def test_fetch_configs(self, mock_get_configs):
        """Verify fetched configuration values populate driver settings."""
        mock_get_configs.return_value = {
            "url": "http://localhost:8080/",
            "client_id": "myclient",
            "eng_code": "eng001",
            "user_id": "user001",
            "device_code": "dev001",
        }
        driver.fetch_configs()
        assert driver.base_url == "http://localhost:8080"
        assert driver.client_id == "myclient"
        assert driver.eng_code == "eng001"
        assert driver.user_id == "user001"
        assert driver.device_code == "dev001"

    @patch.object(DriverQudoorAbaQu100, "get_configs")
    def test_fetch_configs_defaults(self, mock_get_configs):
        """Verify missing configuration values retain driver defaults."""
        mock_get_configs.return_value = {}
        fresh = DriverQudoorAbaQu100()
        fresh.fetch_configs()
        assert fresh.base_url == ""
        assert fresh.client_id == "cmccos"
        assert fresh.user_id == "demo_user"

    # -- update_driver_params_from_options -------------------------------

    def test_update_driver_params_from_options(self):
        """Verify driver options update all supported connection settings."""
        driver.driver_options = {
            "url": "http://new-host:9999/",
            "client_id": "new_client",
            "eng_code": "new_eng",
            "user_id": "new_user",
            "device_code": "new_dev",
        }
        driver.update_driver_params_from_options()
        assert driver.base_url == "http://new-host:9999"
        assert driver.client_id == "new_client"
        assert driver.eng_code == "new_eng"
        assert driver.user_id == "new_user"
        assert driver.device_code == "new_dev"

    # -- get_device_info -------------------------------------------------

    DEVICE_GET_RESPONSE = json.dumps({
        "clientId": "cmccos",
        "engCode": "lizi0001",
        "type": 10,
        "status": 1,
        "statusDesc": "在线",
        "statusStartTime": "2026-09-16 00:00:00",
        "statusEndTime": "2026-09-16 23:59:59",
        "sign": "3b92e84a6616b2a70d5c86a3cd3dca06",
        "params": {
            "paramUpdateTime": "2024-03-01 00:00:00",
            "trappedIon": {
                "maxQubits": 20,
                "timing": {
                    "t1Min": 86400000,
                    "t2Min": 100,
                    "t1Avg": 86400000,
                    "t2Avg": 600,
                    "t1Opt": 86400000,
                    "t2Opt": 800000,
                },
                "singleQubit": {
                    "fidelityMin": 95.0,
                    "fidelityAvg": 98.0,
                    "fidelityOpt": 99.0,
                },
                "doubleQubit": {
                    "fidelityMin": 80.0,
                    "fidelityAvg": 95.0,
                    "fidelityOpt": 97.0,
                },
                "spamError": {"min": 0.06, "avg": 0.035, "opt": 0.008},
            },
        },
    })

    @patch.object(Library, "call_http_api")
    def test_get_device_info_success(self, mock_http):
        """Verify device information is parsed from a successful response."""
        mock_http.return_value = _http_ok(self.DEVICE_GET_RESPONSE)
        success, err, data = driver.get_device_info()
        assert success is True
        assert data is not None
        assert data["status"] == 1
        assert data["statusDesc"] == "在线"
        assert data["params"]["trappedIon"]["maxQubits"] == 20

    @patch.object(Library, "call_http_api")
    def test_get_device_info_http_error(self, mock_http):
        """Verify an HTTP device information failure returns an error."""
        mock_http.return_value = _http_err(500, "Internal Error", "err")
        success, err, data = driver.get_device_info()
        assert success is False
        assert "HTTP 500" in err
        assert data is None

    @patch.object(Library, "call_http_api")
    def test_get_device_info_empty_body(self, mock_http):
        """Verify an empty device information response returns an error."""
        mock_http.return_value = _http_ok("")
        success, err, data = driver.get_device_info()
        assert success is False
        assert "Empty response body" in err
        assert data is None

    @patch.object(Library, "call_http_api")
    def test_get_device_info_invalid_json(self, mock_http):
        """Verify malformed device information JSON returns an error."""
        mock_http.return_value = _http_ok("not json")
        success, err, data = driver.get_device_info()
        assert success is False
        assert "Failed to parse response" in err
        assert data is None

    @patch.object(Library, "call_http_api")
    def test_get_device_info_not_dict(self, mock_http):
        """Verify a non-object device information response returns an error."""
        mock_http.return_value = _http_ok(json.dumps([1, 2, 3]))
        success, err, data = driver.get_device_info()
        assert success is False
        assert "Invalid response format" in err
        assert data is None

    # -- fetch_running_info ----------------------------------------------

    @patch.object(Library, "call_http_api")
    def test_fetch_running_info_online(self, mock_http):
        """Verify online device data is converted to running information."""
        mock_http.return_value = _http_ok(self.DEVICE_GET_RESPONSE)
        info = driver.fetch_running_info()
        assert info["status"] == Device.DEVICE_STATUS_ONLINE
        assert info["available_qubits"] == 20
        assert "calibration" in info["details"]
        calibration = info["details"]["calibration"]
        assert calibration["timing"]["t1_min"] == 86400000
        assert calibration["single_qubit_fidelity"]["fidelity_opt"] == 99.0
        assert calibration["double_qubit_fidelity"]["fidelity_avg"] == 95.0
        assert calibration["spam_error"]["opt"] == 0.008

    @patch.object(Library, "call_http_api")
    def test_fetch_running_info_offline(self, mock_http):
        """Verify offline device data maps to offline running information."""
        resp = json.dumps({"status": 0, "params": {}})
        mock_http.return_value = _http_ok(resp)
        info = driver.fetch_running_info()
        assert info["status"] == Device.DEVICE_STATUS_OFFLINE
        assert info["available_qubits"] == 0

    @patch.object(Library, "call_http_api")
    def test_fetch_running_info_http_error(self, mock_http):
        """Verify device query failures produce offline running information."""
        mock_http.return_value = _http_err(500, "Error", "err")
        info = driver.fetch_running_info()
        assert info["status"] == Device.DEVICE_STATUS_OFFLINE
        assert info["details"] == {}

    # -- _split_controls_targets -----------------------------------------

    def test_split_controls_targets_single_qubit(self):
        """Verify a single-qubit gate has only a target qubit."""
        op = MockOp("h", [0])
        controls, targets = driver._split_controls_targets(op)
        assert controls == []
        assert targets == [0]

    def test_split_controls_targets_controlled_gate(self):
        """Verify a controlled gate separates its control and target."""
        op = MockOp("cx", [0, 1])
        controls, targets = driver._split_controls_targets(op)
        assert controls == [0]
        assert targets == [1]

    def test_split_controls_targets_double_controlled_gate(self):
        """Verify a doubly controlled gate separates controls and target."""
        op = MockOp("ccx", [0, 1, 2])
        controls, targets = driver._split_controls_targets(op)
        assert controls == [0, 1]
        assert targets == [2]

    def test_split_controls_targets_symmetric_gate(self):
        """Verify a symmetric gate treats all qubits as targets."""
        op = MockOp("swap", [0, 1])
        controls, targets = driver._split_controls_targets(op)
        assert controls == []
        assert targets == [0, 1]

    # -- _build_qasmdef ---------------------------------------------------

    def test_build_qasmdef_no_args(self):
        """Verify QASM generation for a gate without arguments."""
        op = MockOp("h", [0])
        qasmdef = driver._build_qasmdef(op)
        assert qasmdef == "h q[0]"

    def test_build_qasmdef_with_args(self):
        """Verify QASM generation includes gate arguments."""
        op = MockOp("rx", [0], arg_value=[1.57])
        qasmdef = driver._build_qasmdef(op)
        assert qasmdef == "rx(1.57) q[0]"

    def test_build_qasmdef_controlled_gate(self):
        """Verify QASM generation for a controlled gate."""
        op = MockOp("cx", [0, 1])
        qasmdef = driver._build_qasmdef(op)
        assert qasmdef == "cx q[0],q[1]"

    # -- convert_code -----------------------------------------------------

    def test_convert_code_empty(self):
        """Verify an empty operation list produces no circuit instructions."""
        circuits, nq = driver.convert_code(2, [])
        assert circuits == []
        assert nq == 2

    def test_convert_code_no_name_attr(self):
        """Verify operations without a name attribute are ignored."""
        circuits, nq = driver.convert_code(2, [object()])
        assert circuits == []
        assert nq == 2

    def test_convert_code_skip_ops(self):
        """Verify unsupported operations are omitted from the circuit."""
        ops = [MockOp("barrier", [0, 1]), MockOp("h", [0])]
        circuits, nq = driver.convert_code(2, ops)
        assert len(circuits) == 1
        assert circuits[0]["gate"] == "h"

    def test_convert_code_normal(self):
        """Verify supported operations become circuit instructions."""
        ops = [
            MockOp("x", [0]),
            MockOp("h", [1]),
            MockOp("cz", [0, 1]),
            MockOp("measure", [0]),
            MockOp("measure", [1]),
        ]
        circuits, nq = driver.convert_code(2, ops)
        assert len(circuits) == 5
        assert circuits[0]["gate"] == "x"
        assert circuits[2]["gate"] == "cz"
        assert circuits[3]["gate"] == "measure"
        assert nq == 2

    def test_convert_code_expands_qubits(self):
        """Verify conversion expands the qubit count for higher indices."""
        ops = [MockOp("x", [3])]
        circuits, nq = driver.convert_code(2, ops)
        assert nq == 4

    # -- submit_task ------------------------------------------------------

    @patch.object(Library, "call_http_api")
    def test_submit_task_success(self, mock_http):
        """Verify successful task submission returns its ID and status."""
        resp = json.dumps({
            "code": CODE_SUCCESS,
            "msg": "已提交.",
            "data": {"taskId": "task-001", "taskStatus": 1},
        })
        mock_http.return_value = _http_ok(resp)
        success, err, tid, status = driver.submit_task(
            "job-1", [{"gate": "h"}], 2, 1024
        )
        assert success is True
        assert tid == "task-001"
        assert status == 1

    @patch.object(Library, "call_http_api")
    def test_submit_task_http_error(self, mock_http):
        """Verify a task submission HTTP error returns no task ID."""
        mock_http.return_value = _http_err(500, "Internal Error", "err")
        success, err, tid, status = driver.submit_task("job-1", [], 2, 1024)
        assert success is False
        assert "HTTP 500" in err
        assert tid is None

    @patch.object(Library, "call_http_api")
    def test_submit_task_empty_body(self, mock_http):
        """Verify an empty task submission response returns an error."""
        mock_http.return_value = _http_ok("")
        success, err, tid, status = driver.submit_task("job-1", [], 2, 1024)
        assert success is False
        assert "Empty response body" in err

    @patch.object(Library, "call_http_api")
    def test_submit_task_invalid_json(self, mock_http):
        """Verify malformed task submission JSON returns an error."""
        mock_http.return_value = _http_ok("not json")
        success, err, tid, status = driver.submit_task("job-1", [], 2, 1024)
        assert success is False
        assert "Failed to parse response" in err

    @patch.object(Library, "call_http_api")
    def test_submit_task_error_code(self, mock_http):
        """Verify a task submission error code returns a failure."""
        resp = json.dumps({"code": 1011, "msg": "invalid params"})
        mock_http.return_value = _http_ok(resp)
        success, err, tid, status = driver.submit_task("job-1", [], 2, 1024)
        assert success is False
        assert "code=1011" in err

    # -- check_task_status ------------------------------------------------

    @patch.object(Library, "call_http_api")
    def test_check_task_status_success(self, mock_http):
        """Verify a task status matching the expected state succeeds."""
        resp = json.dumps({"taskStatus": TASK_STATUS_SUCCESS})
        mock_http.return_value = _http_ok(resp)
        success, err, status = driver.check_task_status(
            "task-1", TASK_STATUS_SUCCESS
        )
        assert success is True
        assert status == TASK_STATUS_SUCCESS

    @patch.object(Library, "call_http_api")
    def test_check_task_status_not_ready(self, mock_http):
        """Verify an unexpected task status remains incomplete."""
        resp = json.dumps({"taskStatus": 1})
        mock_http.return_value = _http_ok(resp)
        success, err, status = driver.check_task_status(
            "task-1", TASK_STATUS_SUCCESS
        )
        assert success is False
        assert status == 1

    @patch.object(Library, "call_http_api")
    def test_check_task_status_failed(self, mock_http):
        """Verify a failed task status raises an error."""
        resp = json.dumps({"taskStatus": 6})
        mock_http.return_value = _http_ok(resp)
        with pytest.raises(ValueError, match="failed with status 6"):
            driver.check_task_status("task-1", TASK_STATUS_SUCCESS)

    @patch.object(Library, "call_http_api")
    def test_check_task_status_http_error(self, mock_http):
        """Verify a task status HTTP error returns no status."""
        mock_http.return_value = _http_err(500, "Error", "err")
        success, err, status = driver.check_task_status(
            "task-1", TASK_STATUS_SUCCESS
        )
        assert success is False
        assert "HTTP 500" in err
        assert status is None

    @patch.object(Library, "call_http_api")
    def test_check_task_status_empty_body(self, mock_http):
        """Verify an empty task status response returns an error."""
        mock_http.return_value = _http_ok("")
        success, err, status = driver.check_task_status(
            "task-1", TASK_STATUS_SUCCESS
        )
        assert success is False
        assert "Empty response body" in err

    @patch.object(Library, "call_http_api")
    def test_check_task_status_invalid_json(self, mock_http):
        """Verify malformed task status JSON returns an error."""
        mock_http.return_value = _http_ok("bad json")
        success, err, status = driver.check_task_status(
            "task-1", TASK_STATUS_SUCCESS
        )
        assert success is False
        assert "Failed to parse response" in err

    @patch.object(Library, "call_http_api")
    def test_check_task_status_list_expected(self, mock_http):
        """Verify task status checks accept a list of expected states."""
        resp = json.dumps({"taskStatus": TASK_STATUS_SUCCESS})
        mock_http.return_value = _http_ok(resp)
        success, _, status = driver.check_task_status(
            "task-1", [TASK_STATUS_SUCCESS]
        )
        assert success is True
        assert status == TASK_STATUS_SUCCESS

    # -- get_task_results -------------------------------------------------

    @patch.object(Library, "call_http_api")
    def test_get_task_results_success_dict(self, mock_http):
        """Verify task results accept dictionary output data."""
        resp = json.dumps({
            "taskStatus": TASK_STATUS_SUCCESS,
            "outData": {
                "probs": [
                    {"qstate": "00", "prob": 0.5},
                    {"qstate": "11", "prob": 0.5},
                ]
            },
        })
        mock_http.return_value = _http_ok(resp)
        success, err, data, mp = driver.get_task_results("task-1")
        assert success is True
        assert "probs" in data
        assert len(data["probs"]) == 2

    @patch.object(Library, "call_http_api")
    def test_get_task_results_success_str_outdata(self, mock_http):
        """Verify task results decode JSON string output data."""
        out_data_str = json.dumps({"probs": [{"qstate": "00", "prob": 1.0}]})
        resp = json.dumps({
            "taskStatus": TASK_STATUS_SUCCESS,
            "outData": out_data_str,
        })
        mock_http.return_value = _http_ok(resp)
        success, err, data, mp = driver.get_task_results("task-1")
        assert success is True
        assert "probs" in data

    @patch.object(Library, "call_http_api")
    def test_get_task_results_machine_profiling_timestamps(self, mock_http):
        """Verify machine profiling uses Unix timestamps."""
        resp = json.dumps({
            "taskStatus": TASK_STATUS_SUCCESS,
            "outData": {"counts": {"00": 1}},
            "execStartTime": 1700000000000000,
            "execEndTime": 1700000000500000,
            "timeConsume": 500,
        })
        mock_http.return_value = _http_ok(resp)

        success, _, _, machine_profiling = driver.get_task_results("task-1")

        assert success is True
        assert machine_profiling == {
            "machine_started_at": 1700000000.0,
            "machine_ended_at": 1700000000.5,
            "machine_duration": 500.0,
        }
        assert Library.to_iso(machine_profiling["machine_started_at"])
        assert Library.to_iso(machine_profiling["machine_ended_at"])

    @patch.object(Library, "call_http_api")
    def test_get_task_results_invalid_profiling_timestamps(self, mock_http):
        """Verify invalid machine timestamps are ignored."""
        resp = json.dumps({
            "taskStatus": TASK_STATUS_SUCCESS,
            "outData": {},
            "execStartTime": "invalid",
            "execEndTime": {"invalid": "timestamp"},
        })
        mock_http.return_value = _http_ok(resp)

        success, _, _, machine_profiling = driver.get_task_results("task-1")

        assert success is True
        assert machine_profiling == {}

    @patch.object(Library, "call_http_api")
    def test_get_task_results_not_succeeded(self, mock_http):
        """Verify results are rejected when the task has not succeeded."""
        resp = json.dumps({"taskStatus": 1, "outData": "已提交."})
        mock_http.return_value = _http_ok(resp)
        success, err, data, mp = driver.get_task_results("task-1")
        assert success is False
        assert "task not succeeded" in err
        assert data is None

    @patch.object(Library, "call_http_api")
    def test_get_task_results_http_error(self, mock_http):
        """Verify a task results HTTP error returns no data."""
        mock_http.return_value = _http_err(500, "Error", "err")
        success, err, data, mp = driver.get_task_results("task-1")
        assert success is False
        assert "HTTP 500" in err
        assert data is None

    @patch.object(Library, "call_http_api")
    def test_get_task_results_empty_body(self, mock_http):
        """Verify an empty task results response returns an error."""
        mock_http.return_value = _http_ok("")
        success, err, data, mp = driver.get_task_results("task-1")
        assert success is False
        assert "Empty response body" in err

    @patch.object(Library, "call_http_api")
    def test_get_task_results_invalid_json(self, mock_http):
        """Verify malformed task results JSON returns an error."""
        mock_http.return_value = _http_ok("bad json")
        success, err, data, mp = driver.get_task_results("task-1")
        assert success is False
        assert "Failed to parse response" in err

    @patch.object(Library, "call_http_api")
    def test_get_task_results_outdata_none(self, mock_http):
        """Verify missing task output data produces an empty dictionary."""
        resp = json.dumps({"taskStatus": TASK_STATUS_SUCCESS})
        mock_http.return_value = _http_ok(resp)
        success, err, data, mp = driver.get_task_results("task-1")
        assert success is True
        assert data == {}

    # -- _probs_to_counts ------------------------------------------------

    def test_probs_to_counts_normal(self):
        """Verify probabilities are converted to integer measurement counts."""
        probs = [
            {"qstate": "00", "prob": 0.25},
            {"qstate": "11", "prob": 0.75},
        ]
        result = DriverQudoorAbaQu100._probs_to_counts(probs, 1024)
        assert result["00"] == 256
        assert result["11"] == 768

    def test_probs_to_counts_empty(self):
        """Verify empty probabilities produce an empty counts dictionary."""
        result = DriverQudoorAbaQu100._probs_to_counts([], 1024)
        assert result == {}

    def test_probs_to_counts_rounding_adjust(self):
        """Verify rounding adjustment preserves the requested shot count."""
        probs = [
            {"qstate": "0", "prob": 0.333},
            {"qstate": "1", "prob": 0.333},
        ]
        result = DriverQudoorAbaQu100._probs_to_counts(probs, 1000)
        total = sum(result.values())
        assert total == 1000

    def test_probs_to_counts_state_field_fallback(self):
        """Verify probability conversion accepts the state field fallback."""
        probs = [{"state": "00", "prob": 1.0}]
        result = DriverQudoorAbaQu100._probs_to_counts(probs, 100)
        assert result["00"] == 100

    # -- convert_results --------------------------------------------------

    def test_convert_results_probs(self):
        """Verify probability results are converted to counts."""
        results = {"probs": [{"qstate": "00", "prob": 1.0}]}
        out = driver.convert_results(results, 100)
        assert out == {"00": 100}

    def test_convert_results_counts(self):
        """Verify an existing counts dictionary is returned unchanged."""
        results = {"counts": {"00": 50, "11": 50}}
        out = driver.convert_results(results, 100)
        assert out == {"00": 50, "11": 50}

    def test_convert_results_direct(self):
        """Verify direct measurement counts are returned unchanged."""
        results = {"00": 10, "11": 20}
        out = driver.convert_results(results, 100)
        assert out == {"00": 10, "11": 20}

    def test_convert_results_none(self):
        """Verify missing results produce an empty counts dictionary."""
        out = driver.convert_results(None, 100)
        assert out == {}

    def test_convert_results_empty_probs(self):
        """Verify empty probabilities produce an empty counts dictionary."""
        results = {"probs": []}
        out = driver.convert_results(results, 100)
        assert out == {}

    # -- run (integration with mocks) ------------------------------------

    @patch.object(DriverQudoorAbaQu100, "set_results")
    @patch.object(DriverQudoorAbaQu100, "convert_results")
    @patch.object(DriverQudoorAbaQu100, "get_task_results")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(DriverQudoorAbaQu100, "submit_task")
    @patch.object(DriverQudoorAbaQu100, "convert_code")
    def test_run_success(
        self,
        mock_convert_code,
        mock_submit,
        mock_loop,
        mock_get_results,
        mock_convert_results,
        mock_set_results,
    ):
        """Verify a successful job run stores the converted results."""
        mock_convert_code.return_value = (
            [{"gate": "h"}],
            2,
        )
        mock_submit.return_value = (True, None, "task-1", 1)
        mock_loop.return_value = (True, None, TASK_STATUS_SUCCESS)
        mock_get_results.return_value = (
            True,
            "",
            {"probs": [{"qstate": "00", "prob": 1.0}]},
            {"machine_started_at": None, "machine_ended_at": None},
        )
        mock_convert_results.return_value = {"00": 1024}

        data = {
            "index": 0,
            "source_code": "OPENQASM 2.0;",
            "transpile_results": [MockOp("h", [0])],
        }
        driver.run("job-1", 2, data, "gate_sequence", shots=1024)

        mock_set_results.assert_called_once()

    @patch.object(DriverQudoorAbaQu100, "submit_task")
    @patch.object(DriverQudoorAbaQu100, "convert_code")
    def test_run_submit_failure(self, mock_convert_code, mock_submit):
        """Verify a submission failure raises an error during a job run."""
        mock_convert_code.return_value = ([{"gate": "h"}], 2)
        mock_submit.return_value = (False, "submit error", None, None)

        data = {
            "index": 0,
            "source_code": "",
            "transpile_results": [MockOp("h", [0])],
        }
        with pytest.raises(ValueError, match="Failed to submit task"):
            driver.run("job-1", 2, data, "gate_sequence", shots=1024)
