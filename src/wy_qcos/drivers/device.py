#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
    DEVICE_STATUS_CALIBRATING = "calibrating"
    DEVICE_STATUS_MAINTAIN = "maintain"
    DEVICE_STATUS_UNKNOWN = "unknown"
    DEVICE_STATUSES = [
        DEVICE_STATUS_ONLINE,
        DEVICE_STATUS_OFFLINE,
        DEVICE_STATUS_BUSY,
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
        # tech_type
        self.tech_type = driver.get_tech_type()
        # progress
        self.progress = 0
        # configs
        self.configs = {}

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

    def get_device_info(self):
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
        ]
        return "\n".join(show_list)

    def set_max_qubits(self, max_qubits):
        """Set device max qubits.

        Args:
            max_qubits: device max qubits
        """
        self.max_qubits = max_qubits
