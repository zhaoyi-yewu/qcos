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

import json

import pytest
from unittest.mock import patch, Mock

from wy_qcos.common.constant import HttpCode
from wy_qcos.common.library import Library
from wy_qcos.common.library import _s
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_base import DriverBase
from wy_qcos.driver.cetc.driver_cetc_base import DriverCetcBase


# -- helpers ---------------------------------------------------------------


class MockOp:
    """Lightweight stand-in for a GateOperation / BaseOperation."""

    def __init__(self, name, targets, arg_value=None):
        self.name = name
        self.targets = list(targets)
        self.arg_value = list(arg_value) if arg_value else []


# -- module-level fixtures -------------------------------------------------

driver_cetc = DriverCetcBase()
job_id = "00000000-0000-4000-8000-000000000001"
task_id = "test-instance-id"
num_qubits = 2
data_type = DriverBase.DATA_TYPE_GATE_SEQUENCE
shots = 1024


def _http_ok(text):
    """Build a successful call_http_api return tuple."""
    return (HttpCode.SUCCESS_OK, "OK", text, Mock())


def _http_err(status, reason="Not Found", text=""):
    """Build a failed call_http_api return tuple."""
    return (status, reason, text, Mock())


@pytest.mark.driver
class TestDriverCetcBase:
    """Unit tests for DriverCetcBase."""

    # -- lifecycle --------------------------------------------------------

    def test_init_driver(self):
        assert driver_cetc.init_driver() is None

    def test_close_driver(self):
        assert driver_cetc.close_driver() is None

    def test_cancel(self):
        assert driver_cetc.cancel("job-1") is None

    # -- config validation -----------------------------------------------

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs_valid(self, mock_validate):
        mock_validate.return_value = True, None
        configs = {"token": _s("tok"), "url": "http://localhost"}
        success, _ = driver_cetc.validate_driver_configs(configs)
        assert success is True

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs_invalid(self, mock_validate):
        mock_validate.return_value = False, ["token required"]
        success, err = driver_cetc.validate_driver_configs({})
        assert success is False
        assert "token required" in err

    # -- fetch_configs ----------------------------------------------------

    @patch.object(DriverCetcBase, "get_configs")
    def test_fetch_configs(self, mock_get_configs):
        mock_get_configs.return_value = {
            "token": "Bearer abc",
            "url": "http://localhost:8080/",
            "computer_type": 61,
        }
        driver_cetc.fetch_configs()
        assert driver_cetc.token == _s("Bearer abc")
        assert driver_cetc.base_url == "http://localhost:8080"
        assert driver_cetc.computer_type == 61
        assert driver_cetc.auth_headers["Authorization"] == "Bearer abc"

    @patch.object(DriverCetcBase, "get_configs")
    def test_fetch_configs_defaults(self, mock_get_configs):
        mock_get_configs.return_value = {}
        # Use a fresh instance so computer_type isn't polluted by
        # earlier tests that set it via config or driver_options.
        fresh = DriverCetcBase()
        fresh.fetch_configs()
        assert fresh.token == ""
        assert fresh.base_url == ""
        assert fresh.computer_type is None

    # -- update_driver_params_from_options -------------------------------

    def test_update_driver_params_from_options(self):
        driver_cetc.driver_options = {"computer_type": 61}
        driver_cetc.update_driver_params_from_options()
        assert driver_cetc.computer_type == 61

    # -- get_device_info --------------------------------------------------

    @patch.object(Library, "call_http_api")
    def test_get_device_info_success(self, mock_http):
        response = json.dumps({"code": 200, "msg": "", "data": {"state": 1}})
        mock_http.return_value = _http_ok(response)
        driver_cetc.base_url = "http://localhost"
        driver_cetc.token = _s("tok")
        success, err, data = driver_cetc.get_device_info()
        assert success is True
        assert data["code"] == 200

    @patch.object(Library, "call_http_api")
    def test_get_device_info_empty_body(self, mock_http):
        mock_http.return_value = _http_ok("")
        driver_cetc.base_url = "http://localhost"
        success, err, _ = driver_cetc.get_device_info()
        assert success is False
        assert "Empty response" in err

    @patch.object(Library, "call_http_api")
    def test_get_device_info_wrong_code(self, mock_http):
        response = json.dumps({"code": 500, "msg": "error"})
        mock_http.return_value = _http_ok(response)
        driver_cetc.base_url = "http://localhost"
        success, err, _ = driver_cetc.get_device_info()
        assert success is False
        assert "code=500" in err

    @patch.object(Library, "call_http_api")
    def test_get_device_info_http_error(self, mock_http):
        mock_http.return_value = _http_err(500, "Internal Error", "err")
        driver_cetc.base_url = "http://localhost"
        success, err, _ = driver_cetc.get_device_info()
        assert success is False
        assert "HTTP 500" in err

    # -- fetch_running_info ----------------------------------------------

    @patch.object(DriverCetcBase, "get_device_info")
    @patch.object(DriverCetcBase, "fetch_configs")
    def test_fetch_running_info_online(self, mock_fetch, mock_dev):
        mock_dev.return_value = (
            True,
            None,
            {
                "code": 200,
                "data": {
                    "state": 1,
                    "maxQubits": 25,
                    "jobNumber": 100,
                    "time": "2026-08-14",
                    "singleBitInfo": [
                        {
                            "quantumBit": "Q0",
                            "T1": 100,
                            "T2": 80,
                            "singleFidelity": 0.99,
                            "fidelity0": 0.98,
                            "fidelity1": 0.97,
                        },
                    ],
                    "doubleBitInfo": [
                        {"couplingQubits": "Q0-Q1", "czFidelity": 0.95},
                    ],
                },
            },
        )
        info = driver_cetc.fetch_running_info()
        assert info["status"] == Device.DEVICE_STATUS_ONLINE
        assert info["available_qubits"] == 25
        assert info["details"]["vendor_job_count"]["total"] == 100
        calib = info["details"]["calibration"]
        assert calib["qubit_metrics"][0]["qubit_id"] == 0
        assert calib["coupler_metrics"][0]["qubits"] == [0, 1]

    @patch.object(DriverCetcBase, "get_device_info")
    @patch.object(DriverCetcBase, "fetch_configs")
    def test_fetch_running_info_offline(self, mock_fetch, mock_dev):
        mock_dev.return_value = (
            True,
            None,
            {"code": 200, "data": {"state": 0, "maxQubits": 10}},
        )
        info = driver_cetc.fetch_running_info()
        assert info["status"] == Device.DEVICE_STATUS_OFFLINE

    @patch.object(DriverCetcBase, "get_device_info")
    @patch.object(DriverCetcBase, "fetch_configs")
    def test_fetch_running_info_dev_info_fail(self, mock_fetch, mock_dev):
        mock_dev.return_value = (False, "err", None)
        info = driver_cetc.fetch_running_info()
        assert info["status"] == Device.DEVICE_STATUS_OFFLINE
        assert info["details"] == {}

    @patch.object(DriverCetcBase, "get_device_info")
    @patch.object(DriverCetcBase, "fetch_configs")
    def test_fetch_running_info_maintain(self, mock_fetch, mock_dev):
        mock_dev.return_value = (
            True,
            None,
            {"code": 200, "data": {"state": 2, "maxQubits": 10}},
        )
        info = driver_cetc.fetch_running_info()
        assert info["status"] == Device.DEVICE_STATUS_MAINTAIN

    # -- convert_code -----------------------------------------------------

    def test_convert_code_empty(self):
        steps, n = driver_cetc.convert_code(2, "code", [])
        assert steps == []
        assert n == 2

    def test_convert_code_none(self):
        steps, n = driver_cetc.convert_code(2, "code", None)
        assert steps == []

    def test_convert_code_h_and_cz(self):
        ops = [
            MockOp("h", [0]),
            MockOp("cz", [0, 1]),
        ]
        steps, n = driver_cetc.convert_code(2, "code", ops)
        assert n == 2
        assert len(steps) == 2
        assert steps[0]["gates"][0]["name"] == "h"
        assert steps[0]["gates"][0]["targets"] == [0]
        assert steps[1]["gates"][0]["name"] == "cz"
        assert steps[1]["gates"][0]["targets"] == [0, 1]

    def test_convert_code_rzz_with_theta(self):
        ops = [MockOp("rzz", [1, 0], [2.27])]
        steps, n = driver_cetc.convert_code(2, "code", ops)
        assert steps[0]["gates"][0]["theta"] == 2.27

    def test_convert_code_measure(self):
        ops = [MockOp("measure", [0])]
        steps, n = driver_cetc.convert_code(1, "code", ops)
        gate = steps[0]["gates"][0]
        assert gate["name"] == "measure"
        assert gate["bit"] == 0
        assert gate["cBit"] == 0

    def test_convert_code_skip_ops(self):
        ops = [
            MockOp("barrier", [0, 1]),
            MockOp("sync", [0]),
            MockOp("swap", [0, 1]),
            MockOp("id", [0]),
            MockOp("i", [1]),
            MockOp("h", [0]),
        ]
        steps, n = driver_cetc.convert_code(2, "code", ops)
        assert len(steps) == 1
        assert steps[0]["gates"][0]["name"] == "h"

    def test_convert_code_qubit_remap(self):
        """Physical qubit indices > num_qubits get remapped to 0-based."""
        ops = [
            MockOp("h", [5]),
            MockOp("cz", [5, 7]),
        ]
        steps, n = driver_cetc.convert_code(2, "code", ops)
        assert n == 2
        assert steps[0]["gates"][0]["targets"] == [0]
        assert steps[1]["gates"][0]["targets"] == [0, 1]

    # -- convert_results --------------------------------------------------

    def test_convert_results(self):
        data = {
            "frequencyResult": [
                {"qState": "00", "freq": 512},
                {"qState": "11", "freq": 512},
            ],
        }
        results = driver_cetc.convert_results(data)
        assert results == {"00": 512, "11": 512}

    def test_convert_results_empty(self):
        results = driver_cetc.convert_results({})
        assert results == {}

    def test_convert_results_missing_key(self):
        data = {"frequencyResult": [{"qState": "01"}]}
        results = driver_cetc.convert_results(data)
        assert results == {"01": 0}

    # -- submit_task ------------------------------------------------------

    @patch.object(Library, "call_http_api")
    def test_submit_task_success(self, mock_http):
        response = json.dumps({
            "code": 200,
            "data": {"instanceId": task_id},
        })
        mock_http.return_value = _http_ok(response)
        driver_cetc.base_url = "http://localhost"
        driver_cetc.token = _s("tok")
        success, err, instance_id = driver_cetc.submit_task(
            job_id,
            2,
            [{"index": 0, "gates": [{"name": "h", "targets": [0]}]}],
            1024,
        )
        assert success is True
        assert instance_id == task_id

    @patch.object(Library, "call_http_api")
    def test_submit_task_api_error(self, mock_http):
        response = json.dumps({"code": 400, "msg": "bad request"})
        mock_http.return_value = _http_ok(response)
        driver_cetc.base_url = "http://localhost"
        success, err, instance_id = driver_cetc.submit_task(
            job_id, 2, [], 1024
        )
        assert success is False
        assert instance_id is None
        assert "code=400" in err

    @patch.object(Library, "call_http_api")
    def test_submit_task_http_error(self, mock_http):
        mock_http.return_value = _http_err(500, "Internal Error", "err")
        driver_cetc.base_url = "http://localhost"
        success, err, instance_id = driver_cetc.submit_task(
            job_id, 2, [], 1024
        )
        assert success is False
        assert instance_id is None
        assert "HTTP 500" in err

    # -- check_task_status ------------------------------------------------

    @patch.object(DriverCetcBase, "_get_task_detail")
    def test_check_task_status_completed(self, mock_detail):
        mock_detail.return_value = True, None, {"state": 2}
        success, err, status = driver_cetc.check_task_status(
            task_id, [driver_cetc.state_completed]
        )
        assert success is True
        assert status == 2

    @patch.object(DriverCetcBase, "_get_task_detail")
    def test_check_task_status_failed(self, mock_detail):
        mock_detail.return_value = True, None, {"state": 1}
        success, err, status = driver_cetc.check_task_status(
            task_id, [driver_cetc.state_completed]
        )
        assert success is False
        assert "Task failed" in err

    @patch.object(DriverCetcBase, "_get_task_detail")
    def test_check_task_status_pending(self, mock_detail):
        mock_detail.return_value = True, None, {"state": 3}
        success, err, status = driver_cetc.check_task_status(
            task_id, [driver_cetc.state_completed]
        )
        assert success is False
        assert status is None

    @patch.object(DriverCetcBase, "_get_task_detail")
    def test_check_task_status_detail_fail(self, mock_detail):
        mock_detail.return_value = False, "network error", None
        success, err, status = driver_cetc.check_task_status(
            task_id, [driver_cetc.state_completed]
        )
        assert success is False
        assert status is None

    # -- get_task_results -------------------------------------------------

    @patch.object(DriverCetcBase, "_get_task_detail")
    def test_get_task_results_success(self, mock_detail):
        mock_detail.return_value = (
            True,
            None,
            {
                "frequencyResult": [{"qState": "00", "freq": 1024}],
            },
        )
        success, err, results = driver_cetc.get_task_results(task_id)
        assert success is True
        assert results == {"00": 1024}

    @patch.object(DriverCetcBase, "_get_task_detail")
    def test_get_task_results_fail(self, mock_detail):
        mock_detail.return_value = False, "timeout", None
        success, err, results = driver_cetc.get_task_results(task_id)
        assert success is False
        assert results is None

    # -- _get_task_detail -------------------------------------------------

    @patch.object(Library, "call_http_api")
    def test_get_task_detail_success(self, mock_http):
        response = json.dumps({"code": 200, "data": {"state": 2}})
        mock_http.return_value = _http_ok(response)
        driver_cetc.base_url = "http://localhost"
        driver_cetc.token = _s("tok")
        success, err, data = driver_cetc._get_task_detail(task_id)
        assert success is True
        assert data["state"] == 2

    @patch.object(Library, "call_http_api")
    def test_get_task_detail_api_error(self, mock_http):
        response = json.dumps({"code": 404, "msg": "not found"})
        mock_http.return_value = _http_ok(response)
        driver_cetc.base_url = "http://localhost"
        success, err, data = driver_cetc._get_task_detail(task_id)
        assert success is False
        assert data is None

    @patch.object(Library, "call_http_api")
    def test_get_task_detail_http_error(self, mock_http):
        mock_http.return_value = _http_err(408, "Timeout", "")
        driver_cetc.base_url = "http://localhost"
        success, err, data = driver_cetc._get_task_detail(task_id)
        assert success is False

    # -- get_task_list ----------------------------------------------------

    @patch.object(Library, "call_http_api")
    def test_get_task_list_success(self, mock_http):
        response = json.dumps({"code": 200, "data": {"list": []}})
        mock_http.return_value = _http_ok(response)
        driver_cetc.base_url = "http://localhost"
        driver_cetc.token = _s("tok")
        success, err, data = driver_cetc.get_task_list()
        assert success is True
        assert data == {"list": []}

    @patch.object(Library, "call_http_api")
    def test_get_task_list_http_error(self, mock_http):
        mock_http.return_value = _http_err(500, "Server Error", "")
        driver_cetc.base_url = "http://localhost"
        success, err, data = driver_cetc.get_task_list()
        assert success is False
        assert data is None

    # -- run (end-to-end with mocks) -------------------------------------

    @pytest.mark.smoke
    @patch.object(DriverCetcBase, "get_task_results")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(DriverCetcBase, "submit_task")
    @patch.object(DriverCetcBase, "convert_code")
    def test_run(
        self,
        mock_convert,
        mock_submit,
        mock_loop,
        mock_get_results,
    ):
        mock_convert.return_value = (
            [{"index": 0, "gates": [{"name": "h", "targets": [0]}]}],
            1,
        )
        mock_submit.return_value = True, None, task_id
        mock_loop.return_value = True, None, None
        mock_get_results.return_value = True, None, {"00": 1024}

        data = {"index": 0, "source_code": "", "transpile_results": []}
        driver_cetc.run(job_id, num_qubits, data, data_type, shots)

    @patch.object(DriverCetcBase, "get_task_results")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(DriverCetcBase, "submit_task")
    @patch.object(DriverCetcBase, "convert_code")
    def test_run_submit_fail(
        self,
        mock_convert,
        mock_submit,
        mock_loop,
        mock_get_results,
    ):
        mock_convert.return_value = ([], 1)
        mock_submit.return_value = False, "HTTP 500", None

        data = {"index": 0, "source_code": "", "transpile_results": []}
        with pytest.raises(ValueError, match="Failed to submit task"):
            driver_cetc.run(job_id, num_qubits, data, data_type, shots)

    @patch.object(Library, "loop_with_timeout")
    @patch.object(DriverCetcBase, "submit_task")
    @patch.object(DriverCetcBase, "convert_code")
    def test_run_timeout(
        self,
        mock_convert,
        mock_submit,
        mock_loop,
    ):
        mock_convert.return_value = ([], 1)
        mock_submit.return_value = True, None, task_id
        mock_loop.return_value = False, "timeout", None

        data = {"index": 0, "source_code": "", "transpile_results": []}
        with pytest.raises(ValueError, match="Failed to get task results"):
            driver_cetc.run(job_id, num_qubits, data, data_type, shots)

    # -- static helpers ---------------------------------------------------

    def test_get_op_name_python(self):
        op = MockOp("h", [0])
        assert DriverCetcBase._get_op_name(op) == "h"

    def test_get_op_name_cpp(self):
        op = Mock(spec=[])
        op.gate_name = "cz"
        assert DriverCetcBase._get_op_name(op) == "cz"

    def test_get_op_targets_python(self):
        op = MockOp("h", [0, 1])
        assert DriverCetcBase._get_op_targets(op) == [0, 1]

    def test_get_op_targets_cpp(self):
        op = Mock(spec=[])
        op.qubits = [2, 3]
        assert DriverCetcBase._get_op_targets(op) == [2, 3]

    def test_get_op_arg_value_python(self):
        op = MockOp("rx", [0], [1.5])
        assert DriverCetcBase._get_op_arg_value(op) == [1.5]

    def test_get_op_arg_value_cpp(self):
        op = Mock(spec=[])
        op.params = [2.0]
        assert DriverCetcBase._get_op_arg_value(op) == [2.0]

    def test_get_op_name_none(self):
        op = object()
        assert DriverCetcBase._get_op_name(op) is None

    def test_get_op_targets_none(self):
        op = object()
        assert DriverCetcBase._get_op_targets(op) == []

    def test_get_op_arg_value_none(self):
        op = object()
        assert DriverCetcBase._get_op_arg_value(op) == []
