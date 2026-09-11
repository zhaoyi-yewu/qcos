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

from wy_qcos.device.device import Device
from wy_qcos.driver.dummy.driver_dummy import DriverDummy

device = Device("dummy", DriverDummy())


class TestDevice:
    def test_init_device(self):
        success, err_msg = device.init_device()
        assert success is True
        assert err_msg is None

    def test_get_name(self):
        name = device.get_name()
        assert name == "dummy"

    @pytest.mark.smoke
    def test_get_driver(self):
        driver = device.get_driver()
        assert isinstance(driver, DriverDummy)

    def test_set_enable(self):
        device.set_enable(True)
        enable = device.get_enable()
        assert enable is True

    def test_set_status(self):
        assert device.set_status("status") is None
        device.set_status(device.DEVICE_STATUS_ONLINE)
        status = device.get_status()
        assert status == "online"

    def test_set_alias_name(self):
        device.set_alias_name("alias_name")
        alias_name = device.get_alias_name()
        assert alias_name == "alias_name"

    def test_set_description(self):
        device.set_description("description")
        description = device.get_description()
        assert description == "description"

    def test_set_configs(self):
        device.set_configs("configs")
        configs = device.get_configs()
        assert configs == "configs"

    def test_set_device_detail(self):
        details = {}
        calibrate_info = {}
        calibrate_info["step"] = 0.1
        details["calibration"] = calibrate_info
        device.set_device_detail(details)
        assert device.details is not None
        assert device.calibrate_info is not None
        assert device.calibrate_info["step"] == 0.1

    def test_set_device_option(self):
        dev_opt_info = {}
        dev_opt_info["gap"] = 50
        device.set_device_options_info(dev_opt_info)
        res = device.get_device_options_info()
        assert res is not None
        assert res["gap"] == 50

    def test_set_and_get_max_queued_jobs(self):
        device.set_max_queued_jobs(10)
        res = device.get_max_queued_jobs()
        assert res == 10

    def test_state_default_auto(self):
        assert device.get_state() == device.DEVICE_STATE_AUTO

    def test_set_state_maintain(self):
        device.set_state(device.DEVICE_STATUS_MAINTAIN)
        assert device.get_state() == device.DEVICE_STATUS_MAINTAIN
        # Clean up
        device.set_state(device.DEVICE_STATE_AUTO)

    def test_set_state_auto(self):
        device.set_state(device.DEVICE_STATUS_MAINTAIN)
        device.set_state(device.DEVICE_STATE_AUTO)
        assert device.get_state() == device.DEVICE_STATE_AUTO

    def test_get_effective_status_auto(self):
        device.set_state(device.DEVICE_STATE_AUTO)
        device.set_status(device.DEVICE_STATUS_ONLINE)
        status, is_manual = device.get_effective_status()
        assert status == device.DEVICE_STATUS_ONLINE
        assert is_manual is False

    def test_get_effective_status_manual(self):
        device.set_state(device.DEVICE_STATUS_MAINTAIN)
        status, is_manual = device.get_effective_status()
        assert status == device.DEVICE_STATUS_MAINTAIN
        assert is_manual is True
        # Clean up
        device.set_state(device.DEVICE_STATE_AUTO)

    def test_set_device_running_info_skipped_manual_state(self):
        # Setup: set device state to maintain (manual override)
        device.set_state(device.DEVICE_STATUS_MAINTAIN)

        # Simulate monitor reporting online status
        device.set_device_running_info({"status": "online"})

        # Effective status should still be maintain
        status, _ = device.get_effective_status()
        assert status == device.DEVICE_STATUS_MAINTAIN
        # Clean up
        device.set_state(device.DEVICE_STATE_AUTO)

    def test_set_device_running_info_applied_auto_state(self):
        device.set_state(device.DEVICE_STATE_AUTO)
        device.set_status(device.DEVICE_STATUS_ONLINE)

        # Simulate monitor reporting busy status
        device.set_device_running_info({"status": "busy"})

        # Status should be updated to busy
        assert device.get_status() == device.DEVICE_STATUS_BUSY
        # Clean up
        device.set_status(device.DEVICE_STATUS_ONLINE)

    def test_set_device_running_info_maintain_from_monitor(self):
        device.set_state(device.DEVICE_STATE_AUTO)
        device.set_status(device.DEVICE_STATUS_ONLINE)

        # Monitor reports maintain
        device.set_device_running_info({"status": "maintain"})
        assert device.get_status() == device.DEVICE_STATUS_MAINTAIN

        # Monitor then reports online again
        device.set_device_running_info({"status": "online"})
        assert device.get_status() == device.DEVICE_STATUS_ONLINE

    def test_set_device_running_info_details_still_updated(self):
        device.set_state(device.DEVICE_STATUS_MAINTAIN)

        device.set_device_running_info({
            "status": "online",
            "details": {"calibration": {"step": 0.5}},
        })

        # Status should remain maintain (manual override)
        status, _ = device.get_effective_status()
        assert status == device.DEVICE_STATUS_MAINTAIN
        # But details should still be updated
        assert device.calibrate_info is not None
        assert device.calibrate_info["step"] == 0.5
        # Clean up
        device.set_state(device.DEVICE_STATE_AUTO)

    def test_set_status_disconnected(self):
        """Test setting device status to disconnected."""
        device.set_status(device.DEVICE_STATUS_DISCONNECTED)
        assert device.get_status() == device.DEVICE_STATUS_DISCONNECTED

    def test_disconnected_in_device_statuses(self):
        """Test that disconnected is in DEVICE_STATUSES list."""
        assert device.DEVICE_STATUS_DISCONNECTED in device.DEVICE_STATUSES

    def test_set_device_running_info_disconnected(self):
        """Test that monitor can set device to disconnected status."""
        device.set_state(device.DEVICE_STATE_AUTO)
        device.set_status(device.DEVICE_STATUS_ONLINE)

        # Monitor reports disconnected
        device.set_device_running_info({
            "status": device.DEVICE_STATUS_DISCONNECTED
        })
        assert device.get_status() == device.DEVICE_STATUS_DISCONNECTED

        # Monitor then reports online again
        device.set_device_running_info({"status": "online"})
        assert device.get_status() == device.DEVICE_STATUS_ONLINE
