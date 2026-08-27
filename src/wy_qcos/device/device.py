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

import logging

from wy_qcos.common.library import Library


logger = logging.getLogger(__name__)


class Device:
    """Device."""

    # Device status
    DEVICE_STATUS_ONLINE = "online"
    DEVICE_STATUS_OFFLINE = "offline"
    DEVICE_STATUS_BUSY = "busy"
    DEVICE_STATUS_DISCONNECTED = "disconnected"
    DEVICE_STATUS_CALIBRATING = "calibrating"
    DEVICE_STATUS_MAINTAIN = "maintain"
    DEVICE_STATUS_UNKNOWN = "unknown"
    DEVICE_STATUSES = [
        DEVICE_STATUS_ONLINE,
        DEVICE_STATUS_OFFLINE,
        DEVICE_STATUS_BUSY,
        DEVICE_STATUS_DISCONNECTED,
        DEVICE_STATUS_CALIBRATING,
        DEVICE_STATUS_MAINTAIN,
        DEVICE_STATUS_UNKNOWN,
    ]

    def __init__(self, name, driver):
        # name
        self.name = name
        # alias name
        self.alias_name = None
        # description
        self.description = None
        # driver
        self.driver = driver
        # enable this driver or not
        self.enable = False
        # status
        self.status = self.DEVICE_STATUS_OFFLINE
        # qubits
        self.max_qubits = driver.get_max_qubits()
        # available qubits
        self.available_qubits = None
        # tech_type
        self.tech_type = driver.get_tech_type()
        # progress
        self.progress = 0
        # configs
        self.configs = {}
        # device details info
        self.details = {}
        # device calibrate info
        self.calibrate_info = {}
        # device option info
        self.device_options_info = {}
        # device max queued jobs
        self.max_queued_jobs = -1
        # enable device monitor from config file
        self._enable_device_monitor = False
        # timestamp
        self.last_updated_at = None
        # flag to indicate maintain mode was set manually via API/CLI.
        # When True, set_device_running_info will NOT overwrite the status.
        self._manual_maintain_mode = False

    def init_device(self):
        """Init device.

        Returns:
            success, err_msgs
        """
        success = True
        err_msg = None
        return success, err_msg

    def get_name(self):
        """Get device name.

        Returns:
            device name
        """
        return self.name

    def get_driver(self):
        """Get device driver.

        Returns:
            device driver
        """
        return self.driver

    def set_enable(self, enable):
        """Set enable.

        Args:
            enable: enable or disable
        """
        self.enable = enable

    def get_enable(self):
        """Get enable.

        Returns:
            enable or disable
        """
        return self.enable

    def set_status(self, status):
        """Set device status.

        Args:
            status: device status
        """
        if status not in self.DEVICE_STATUSES:
            logger.warning(
                f"Failed to set device status: '{status}'."
                f"valid statuses: {', '.join(self.DEVICE_STATUSES)}"
            )
            return
        self.status = status

    def get_status(self):
        """Get device status."""
        return self.status

    def set_manual_maintain_mode(self, enabled):
        """Set manual maintain mode flag.

        When enabled, the device status will NOT be overwritten by
        monitor updates (set_device_running_info). This is used by
        the set-device-maintain-mode API/CLI to keep the device
        in maintain mode regardless of periodic monitor reports.

        Args:
            enabled: True to enable manual maintain mode protection,
                     False to disable it.
        """
        self._manual_maintain_mode = enabled

    def get_manual_maintain_mode(self):
        """Get manual maintain mode flag.

        Returns:
            True if manual maintain mode is active, False otherwise.
        """
        return self._manual_maintain_mode

    def set_alias_name(self, alias_name):
        """Set device alias name.

        Args:
            alias_name: device alias name
        """
        self.alias_name = alias_name

    def get_alias_name(self):
        """Get device alias name.

        Returns:
            device alias name
        """
        return self.alias_name

    def set_description(self, description):
        """Set device description.

        Args:
            description: device description
        """
        self.description = description

    def get_description(self):
        """Get device description.

        Returns:
            device description
        """
        return self.description

    def set_configs(self, configs):
        """Set device configs.

        Args:
            configs: device configs
        """
        self.configs = configs

    def get_configs(self, hide_password=False):
        """Get device configs.

        Args:
            hide_password: hide device password

        Returns:
            device configs
        """
        if hide_password:
            return Library.mask_password(self.configs)

        return self.configs

    def set_device_detail(self, details):
        """Set device details.

        Args:
            details: device details
        """
        self.details = details
        self.calibrate_info = details.get("calibration")
        self.device_options_info = details.get("device_options_info")

    def set_device_running_info(self, device_running_info):
        """Set device running info.

        Args:
            device_running_info: device running info
        """
        device_status = device_running_info.get("status")
        last_updated_at = device_running_info.get("last_updated_at")
        available_qubits = device_running_info.get("available_qubits")

        if not self._manual_maintain_mode:
            if device_status:
                self.set_status(device_status)
                self.last_updated_at = last_updated_at
                self.available_qubits = available_qubits

        details = device_running_info.get("details")
        if details:
            self.set_device_detail(details)
        return

    def show_device_info(self):
        """Show device info."""
        show_list = [
            f"device_name: {self.name}",
            f"device_alias_name: {self.alias_name}",
            f"description: {self.description}",
            f"driver_name: {self.driver.get_name()}",
            f"enable: {self.enable}",
            f"status: {self.status}",
            f"tech_type: {self.tech_type}",
            f"max_qubits: {self.max_qubits}",
            f"configs: {self.get_configs(hide_password=True)}",
            f"details: {self.details}",
        ]
        return "\n".join(show_list)

    def set_max_qubits(self, max_qubits):
        """Set device max qubits.

        Args:
            max_qubits: device max qubits
        """
        self.max_qubits = max_qubits

    def set_device_options_info(self, device_options_info):
        """Set device option info.

        Args:
            device_options_info: device option info
        """
        self.device_options_info = device_options_info

    def get_device_options_info(self):
        """Get device option info.

        Returns:
            device option info
        """
        return self.device_options_info

    def set_max_queued_jobs(self, max_queued_jobs: int):
        """Set Max Queued Kobs.

        Args:
            max_queued_jobs: max_queued_jobs
        """
        self.max_queued_jobs = max_queued_jobs

    def get_max_queued_jobs(self):
        """Set Max Queued Kobs.

        Returns:
            max_queued_jobs
        """
        return self.max_queued_jobs

    def set_enable_device_monitor(self, enable):
        """Set enable device monitor from config file.

        Args:
            enable: enable or disable (None means not set)
        """
        self._enable_device_monitor = enable

    def get_enable_device_monitor(self):
        """Get enable device monitor from config file.

        Returns:
            True, False or None (not set)
        """
        return self._enable_device_monitor
