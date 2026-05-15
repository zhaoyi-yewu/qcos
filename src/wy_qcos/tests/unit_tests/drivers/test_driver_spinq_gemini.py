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
from unittest.mock import patch

from wy_qcos.common.library import Library
from wy_qcos.drivers.spinq.spinq_nmr.driver_spinq_gemini import (
    DriverSpinQGemini,
)

spinq_gemini = DriverSpinQGemini()
spinq_gemini._nmr_conn_str = (
    f"http://{spinq_gemini.default_nmr_host}:{spinq_gemini.default_nmr_port}"
)


@pytest.mark.driver
class TestDriverSpinQGemini:
    def test_init_driver(self):
        assert spinq_gemini.init_driver() is None

    @pytest.mark.smoke
    @patch.object(DriverSpinQGemini, "send_request_and_process_response")
    def test_fetch_running_info(self, mock_send_request_and_process_response):
        mock_send_request_and_process_response.return_value = (
            True,
            None,
            {
                "status": "online",
                "details": {
                    "calibrate_info": {
                        "step": 0.1,
                        "shot": 800,
                    },
                    "device_options_info": {"shot_gap": 0},
                },
            },
        )
        dev_running_info = spinq_gemini.fetch_running_info()
        assert "details" in dev_running_info
        assert dev_running_info["details"]["calibrate_info"]["step"] == 0.1
        assert dev_running_info["details"]["calibrate_info"]["shot"] == 800
        assert (
            dev_running_info["details"]["device_options_info"]["shot_gap"] == 0
        )
        assert dev_running_info["status"] == "online"

    @patch.object(DriverSpinQGemini, "send_request_and_process_response")
    def test_calibrate_deivce(self, mock_send_request_and_process_response):
        mock_send_request_and_process_response.return_value = (
            True,
            None,
            "calibrate device request msg receved",
        )
        data = "calibrate"
        succ, err_msgs, result = spinq_gemini.calibrate_device(data)
        assert succ is True
        assert err_msgs is None
        assert result == "calibrate device request msg receved"

    @patch.object(DriverSpinQGemini, "send_request_and_process_response")
    def test_set_device_options(self, mock_send_request_and_process_response):
        mock_send_request_and_process_response.return_value = (
            True,
            None,
            "set device options request msg receved",
        )
        data = "set device options"
        succ, err_msgs, result = spinq_gemini.set_device_options(data)
        assert succ is True
        assert err_msgs is None
        assert result == "set device options request msg receved"

    @patch.object(DriverSpinQGemini, "send_request_and_process_response")
    def test_get_device_options(self, mock_send_request_and_process_response):
        mock_send_request_and_process_response.return_value = (
            True,
            None,
            "get device options request msg receved",
        )
        data = "set device options"
        succ, err_msgs, result = spinq_gemini.get_device_options(data)
        assert succ is True
        assert err_msgs is None
        assert result == "get device options request msg receved"

    @patch.object(Library, "call_http_api")
    def test_send_request_and_process_response(self, mock_call_http_api):
        api_result = {
            "status": 200,
            "result": {
                "status": "online",
                "details": {
                    "calibrate_info": {
                        "step": 0.1,
                        "shot": 800,
                    },
                    "device_options_info": {"shot_gap": 0},
                },
            },
        }

        mock_call_http_api.return_value = (
            200,
            None,
            json.dumps(api_result),
            None,
        )
        data = "spinq_gemini"
        url = f"{spinq_gemini._nmr_conn_str}/fetch_running_info"
        func_name = "fetch_running_info"
        succ, err_msgs, result = (
            spinq_gemini.send_request_and_process_response(
                data, url, func_name
            )
        )
        assert succ is True
        assert err_msgs == ""
        assert "details" in result
        assert result["details"]["calibrate_info"]["step"] == 0.1
        assert result["details"]["calibrate_info"]["shot"] == 800
        assert result["details"]["device_options_info"]["shot_gap"] == 0
        assert result["status"] == "online"
