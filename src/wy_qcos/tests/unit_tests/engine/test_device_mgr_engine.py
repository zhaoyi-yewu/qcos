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

"""Unit tests for device_mgr_engine module."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock prefect.flow before importing device_mgr_engine to avoid
# starting a temporary Prefect server during tests.
import prefect


def _mock_flow(*args, **kwargs):
    def decorator(fn):
        return fn

    if len(args) == 1 and callable(args[0]):
        return args[0]
    return decorator


prefect.flow = _mock_flow

# Remove cached engine module so it is re-imported with the mocked
# prefect.flow. Do NOT pop task_manager here, because that would break
# other tests that rely on the already-imported task_manager module.
sys.modules.pop("wy_qcos.engine.device_mgr_engine", None)

from wy_qcos.engine.device_mgr_engine import (
    call_device_method,
    device_manager_flow,
)


class TestCallDeviceMethod:
    """Test call_device_method function."""

    def test_call_existing_method(self):
        """Test calling an existing method on driver."""
        driver = MagicMock()
        driver.test_method.return_value = "result"
        result = call_device_method(driver, "test_method", "arg1", key="value")
        assert result == "result"
        driver.test_method.assert_called_once_with("arg1", key="value")

    def test_call_method_with_no_args(self):
        """Test calling method with no arguments."""
        driver = MagicMock()
        driver.simple_method.return_value = 42
        result = call_device_method(driver, "simple_method")
        assert result == 42

    def test_call_nonexistent_method_raises(self):
        """Test calling a method that does not exist raises AttributeError."""
        driver = MagicMock(spec=[])  # no methods
        with pytest.raises(
            AttributeError, match="driver has no missing_method method"
        ):
            call_device_method(driver, "missing_method")


class TestDeviceManagerFlow:
    """Test device_manager_flow function."""

    @patch("wy_qcos.engine.device_mgr_engine.init_logger")
    @patch("wy_qcos.engine.device_mgr_engine.init_driver")
    def test_flow_success(self, mock_init_driver, mock_init_logger):
        """Test successful device manager flow execution."""
        # Setup mock driver
        mock_driver = MagicMock()
        mock_driver.get_status.return_value = "online"

        # Setup mock init_driver future
        mock_future = MagicMock()
        mock_future.result.return_value = {"driver": mock_driver}
        mock_init_driver.submit.return_value = mock_future

        # Build device_mgr_info
        device_mgr_info = {
            "data": {
                "device_name": "test_device",
                "method": "get_status",
            },
            "device": {
                "configs": {
                    "debug": True,
                    "log_format": "%(message)s",
                },
            },
            "global": {
                "configs": {"DEBUG": False},
            },
            "driver": {"class": "TestDriver"},
        }

        result = device_manager_flow(device_mgr_info)
        assert result == "online"
        mock_init_logger.assert_called_once()
        mock_init_driver.submit.assert_called_once()

    @patch("wy_qcos.engine.device_mgr_engine.init_logger")
    @patch("wy_qcos.engine.device_mgr_engine.init_driver")
    def test_flow_driver_init_error(self, mock_init_driver, mock_init_logger):
        """Test flow raises ValueError when driver init fails."""
        mock_future = MagicMock()
        mock_future.result.return_value = {"error": "init failed"}
        mock_init_driver.submit.return_value = mock_future

        device_mgr_info = {
            "data": {
                "device_name": "test_device",
                "method": "get_status",
            },
            "device": {"configs": {}},
            "global": {"configs": {}},
            "driver": {"class": "TestDriver"},
        }

        with pytest.raises(ValueError, match="init failed"):
            device_manager_flow(device_mgr_info)

    @patch("wy_qcos.engine.device_mgr_engine.init_logger")
    @patch("wy_qcos.engine.device_mgr_engine.init_driver")
    def test_flow_global_debug_fallback(
        self, mock_init_driver, mock_init_logger
    ):
        """Test flow falls back to global DEBUG when device has none."""
        mock_driver = MagicMock()
        mock_driver.method.return_value = "ok"
        mock_future = MagicMock()
        mock_future.result.return_value = {"driver": mock_driver}
        mock_init_driver.submit.return_value = mock_future

        device_mgr_info = {
            "data": {"device_name": "dev1", "method": "method"},
            "device": {"configs": {}},
            "global": {"configs": {"DEBUG": True}},
            "driver": {"class": "TestDriver"},
        }

        device_manager_flow(device_mgr_info)
        call_kwargs = mock_init_logger.call_args[1]
        assert call_kwargs["debug"] is True

    @patch("wy_qcos.engine.device_mgr_engine.init_logger")
    @patch("wy_qcos.engine.device_mgr_engine.init_driver")
    def test_flow_uses_custom_log_file(
        self, mock_init_driver, mock_init_logger
    ):
        """Test flow uses custom mgr_log_file from device configs."""
        mock_driver = MagicMock()
        mock_driver.method.return_value = "ok"
        mock_future = MagicMock()
        mock_future.result.return_value = {"driver": mock_driver}
        mock_init_driver.submit.return_value = mock_future

        device_mgr_info = {
            "data": {"device_name": "dev1", "method": "method"},
            "device": {"configs": {"mgr_log_file": "/custom/path.log"}},
            "global": {"configs": {}},
            "driver": {"class": "TestDriver"},
        }

        device_manager_flow(device_mgr_info)
        call_kwargs = mock_init_logger.call_args[1]
        assert call_kwargs["log_file_path"] == "/custom/path.log"
