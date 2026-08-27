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
# MERCHANTABILITY or FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import json

import pytest
from unittest.mock import patch, Mock

from wy_qcos.common.constant import HttpCode
from wy_qcos.common.library import Library, _s
from wy_qcos.driver.cetc.driver_cetc_base import DriverCetcBase
from wy_qcos.driver.cetc.driver_cetc_baihua import DriverCetcBaihua


# -- helpers ---------------------------------------------------------------


class MockOp:
    """Lightweight stand-in for a GateOperation / BaseOperation."""

    def __init__(self, name, targets, arg_value=None):
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

driver_baihua = DriverCetcBaihua()
job_id = "00000000-0000-4000-8000-000000000002"
task_id = "baihua-instance-id"


@pytest.mark.driver
class TestDriverCetcBaihua:
    """Unit tests for DriverCetcBaihua (computer_type=60).

    These tests focus on baihua-specific defaults and the fact that
    computer_type=60 is propagated into API requests.  Core logic
    (convert_code, check_task_status, etc.) is already covered by
    test_driver_cetc_base.py and is inherited unchanged.
    """

    # -- subclass defaults ------------------------------------------------

    def test_inherits_from_base(self):
        assert isinstance(driver_baihua, DriverCetcBase)

    def test_default_computer_type(self):
        assert driver_baihua.computer_type == 60

    def test_alias_and_description(self):
        assert driver_baihua.alias_name == "国基量子 百花 超导驱动"
        assert "国基量子 百花 超导驱动" in driver_baihua.description

    def test_max_qubits_inherited(self):
        assert driver_baihua.max_qubits == 156

    def test_tech_type_inherited(self):
        assert driver_baihua.tech_type is not None

    # -- fetch_configs with baihua defaults --------------------------------

    @patch.object(DriverCetcBaihua, "get_configs")
    def test_fetch_configs_preserves_type(self, mock_get_configs):
        """When config has no computer_type, baihua default (60)."""
        mock_get_configs.return_value = {
            "token": "Bearer xyz",
            "url": "http://localhost:9090",
        }
        driver_baihua.fetch_configs()
        assert driver_baihua.computer_type == 60
        assert driver_baihua.token == _s("Bearer xyz")
        assert driver_baihua.base_url == "http://localhost:9090"

    @patch.object(DriverCetcBaihua, "get_configs")
    def test_fetch_configs_config_overrides_type(self, mock_get_configs):
        """Config-level computer_type overrides the baihua default."""
        mock_get_configs.return_value = {
            "token": _s("tok"),
            "url": "http://localhost",
            "computer_type": 61,
        }
        driver_baihua.fetch_configs()
        assert driver_baihua.computer_type == 61

    @patch.object(DriverCetcBaihua, "get_configs")
    def test_fetch_configs_opts_override_type(self, mock_get_configs):
        """driver_options computer_type takes priority over config."""
        mock_get_configs.return_value = {
            "token": _s("tok"),
            "url": "http://localhost",
            "computer_type": 61,
        }
        driver_baihua.driver_options["computer_type"] = 62
        driver_baihua.fetch_configs()
        assert driver_baihua.computer_type == 62
        driver_baihua.driver_options.pop("computer_type", None)

    # -- update_driver_params_from_options ---------------------------------

    def test_update_opts_computer_type(self):
        original = driver_baihua.computer_type
        driver_baihua.driver_options["computer_type"] = 61
        driver_baihua.update_driver_params_from_options()
        assert driver_baihua.computer_type == 61
        driver_baihua.driver_options.pop("computer_type", None)
        driver_baihua.computer_type = original

    # -- submit_task sends computerType=60 --------------------------------

    @patch.object(Library, "call_http_api")
    def test_submit_task_sends_baihua_type(self, mock_http):
        response = json.dumps({
            "code": 200,
            "data": {"instanceId": task_id},
        })
        mock_http.return_value = _http_ok(response)
        driver_baihua.base_url = "http://localhost"
        driver_baihua.computer_type = 60
        driver_baihua.token = _s("tok")
        success, _, instance_id = driver_baihua.submit_task(
            job_id,
            2,
            [{"index": 0, "gates": [{"name": "h", "targets": [0]}]}],
            1024,
        )
        assert success is True
        assert instance_id == task_id
        call_kwargs = mock_http.call_args.kwargs
        assert call_kwargs["json"]["computerType"] == 60

    @patch.object(Library, "call_http_api")
    def test_submit_task_body_structure(self, mock_http):
        """Verify the full submit body structure for baihua."""
        response = json.dumps({
            "code": 200,
            "data": {"instanceId": task_id},
        })
        mock_http.return_value = _http_ok(response)
        driver_baihua.base_url = "http://localhost"
        driver_baihua.computer_type = 60
        driver_baihua.token = _s("tok")
        steps = [{"index": 0, "gates": [{"name": "h", "targets": [0]}]}]
        driver_baihua.submit_task(job_id, 4, steps, 2048)
        body = mock_http.call_args.kwargs["json"]
        assert body["version"] == "1.1"
        assert body["computerType"] == 60
        assert body["quantum-num"] == 4
        assert body["classNumber"] == 4
        assert body["repetitions"] == 2048
        assert body["steps"] == steps
        assert body["projectName"] == job_id

    # -- get_device_info sends deviceid=60 --------------------------------

    @patch.object(Library, "call_http_api")
    def test_get_device_info_sends_baihua_id(self, mock_http):
        response = json.dumps({"code": 200, "msg": "", "data": {"state": 1}})
        mock_http.return_value = _http_ok(response)
        driver_baihua.base_url = "http://localhost"
        driver_baihua.computer_type = 60
        driver_baihua.token = _s("tok")
        success, _, _ = driver_baihua.get_device_info()
        assert success is True
        call_kwargs = mock_http.call_args.kwargs
        assert call_kwargs["params"]["deviceid"] == 60

    @patch.object(Library, "call_http_api")
    def test_get_device_info_url_construction(self, mock_http):
        response = json.dumps({"code": 200, "data": {"state": 1}})
        mock_http.return_value = _http_ok(response)
        driver_baihua.base_url = "http://localhost:8080"
        driver_baihua.computer_type = 60
        driver_baihua.token = _s("tok")
        driver_baihua.get_device_info()
        call_args = mock_http.call_args
        url = call_args.args[0]
        assert url == "http://localhost:8080/qdevicedetail"

    # -- fetch_running_info uses baihua device id --------------------------

    @patch.object(DriverCetcBaihua, "get_device_info")
    @patch.object(DriverCetcBaihua, "fetch_configs")
    def test_fetch_running_info_online(self, mock_fetch, mock_dev):
        mock_dev.return_value = (
            True,
            None,
            {
                "code": 200,
                "data": {
                    "state": 1,
                    "maxQubits": 156,
                    "jobNumber": 42,
                    "time": "2026-08-18",
                    "singleBitInfo": [],
                    "doubleBitInfo": [],
                },
            },
        )
        info = driver_baihua.fetch_running_info()
        assert info["status"] == "online"
        assert info["available_qubits"] == 156
        total = info["details"]["vendor_job_count"]["total"]
        assert total == 42

    # -- submit_task error path (baihua context) --------------------------

    @patch.object(Library, "call_http_api")
    def test_submit_task_http_error(self, mock_http):
        mock_http.return_value = _http_err(500, "Internal Error", "err")
        driver_baihua.base_url = "http://localhost"
        driver_baihua.computer_type = 60
        success, err, instance_id = driver_baihua.submit_task(
            job_id, 2, [], 1024
        )
        assert success is False
        assert instance_id is None
        assert "HTTP 500" in err

    # -- get_task_list (baihua context) -----------------------------------

    @patch.object(Library, "call_http_api")
    def test_get_task_list_success(self, mock_http):
        response = json.dumps({"code": 200, "data": {"list": []}})
        mock_http.return_value = _http_ok(response)
        driver_baihua.base_url = "http://localhost"
        driver_baihua.token = _s("tok")
        success, _, data = driver_baihua.get_task_list()
        assert success is True
        assert data == {"list": []}

    @patch.object(Library, "call_http_api")
    def test_get_task_list_with_state_filter(self, mock_http):
        response = json.dumps({"code": 200, "data": {"list": []}})
        mock_http.return_value = _http_ok(response)
        driver_baihua.base_url = "http://localhost"
        driver_baihua.token = _s("tok")
        success, _, _ = driver_baihua.get_task_list(state=2)
        assert success is True
        call_kwargs = mock_http.call_args.kwargs
        assert call_kwargs["params"]["state"] == 2

    # -- get_task_results (baihua context) --------------------------------

    @patch.object(DriverCetcBaihua, "_get_task_detail")
    def test_get_task_results_success(self, mock_detail):
        mock_detail.return_value = (
            True,
            None,
            {"frequencyResult": [{"qState": "11", "freq": 1024}]},
        )
        success, _, results = driver_baihua.get_task_results(task_id)
        assert success is True
        assert results == {"11": 1024}

    # -- convert_code inheritance smoke test -------------------------------

    def test_convert_code_inherited(self):
        """Verify baihua inherits convert_code from the base class."""
        ops = [MockOp("h", [0]), MockOp("cz", [0, 1])]
        steps, n = driver_baihua.convert_code(2, "code", ops)
        assert n == 2
        assert len(steps) == 2
        assert steps[0]["gates"][0]["name"] == "h"
        assert steps[1]["gates"][0]["name"] == "cz"

    # -- convert_results inheritance smoke test ---------------------------

    def test_convert_results_inherited(self):
        data = {
            "frequencyResult": [
                {"qState": "00", "freq": 512},
                {"qState": "11", "freq": 512},
            ],
        }
        results = driver_baihua.convert_results(data)
        assert results == {"00": 512, "11": 512}
