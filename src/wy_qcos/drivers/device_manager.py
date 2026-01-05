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

from schema import Optional

from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device


logger = logging.getLogger(__name__)


class DeviceManager:
    """Device manager."""

    def __init__(self, config, driver_manager):
        self.config = config
        self.driver_manager = driver_manager
        self.devices = {}
        self.default_device_config_schema = {
            "driver": str,
            Optional("alias_name"): str,
            Optional("description"): str,
            Optional("device_max_qubits"): int,
        }

    def load_devices(self):
        """Scan and load drivers."""
        logger.info("Load devices ...")
        devices = self.config.DEVICE_LIST
        for device_name in devices:
            logger.info(f"Loading device: {device_name}")
            device_configs = self.config.EXTRA_CONFIGS.get(device_name)
            if device_configs:
                _success, err_msgs = Library.validate_schema(
                    device_configs,
                    self.default_device_config_schema,
                    ignore_extra_keys=True,
                )
                if not _success:
                    _err_msg = "\n".join(err_msgs)
                    err_msg = (
                        f"device: {device_name} is disabled. "
                        f"device config file error: {_err_msg}"
                    )
                    logger.warning(err_msg)
                    continue

                driver_name = device_configs.pop("driver", None)
                alias_name = device_configs.pop("alias_name", None)
                description = device_configs.pop("description", None)
                device_max_qubits = device_configs.pop(
                    "device_max_qubits", None
                )

                driver = self.driver_manager.get_driver(driver_name)
                if driver:
                    device = Device(device_name, driver)
                    if alias_name is not None:
                        device.set_alias_name(alias_name)
                    if description is not None:
                        device.set_description(description)
                    if device_max_qubits is not None:
                        device.set_max_qubits(device_max_qubits)
                    success, err_msg = driver.validate_driver_configs(
                        device_configs
                    )
                    if success:
                        device.set_configs(device_configs)
                        device.set_enable(True)
                        self.devices[device_name] = device
                    else:
                        logger.warning(
                            f"device: {device_name} is disabled. "
                            f"reason: {err_msg}"
                        )
                else:
                    logger.warning(
                        f"device: {device_name} is disabled. "
                        f"reason: driver name: {driver_name} is not found"
                    )
            else:
                logger.warning(
                    f"device: {device_name} is not loaded. "
                    f"reason: device config file is not found"
                )

    def init_devices(self):
        """Init devices."""
        for device_name, device in self.devices.items():
            device.set_status(device.DEVICE_STATUS_ONLINE)
            # Init driver
            success, err_msg = device.init_device()
            if not success:
                logger.error(
                    f"Device: {device_name} is disabled. "
                    f"Error message: {err_msg}"
                )
                device.set_enable(False)
                device.set_status(device.DEVICE_STATUS_OFFLINE)
            # Show driver info
            logger.info(f"\n{device.get_device_info()}")

    def has_device(self, device_name):
        """Has device.

        Args:
            device_name: device name

        Returns:
            True or False
        """
        return device_name in self.devices

    def get_device(self, device_name):
        """Get device.

        Args:
            device_name: device name

        Returns:
            device instance
        """
        return self.devices.get(device_name, None)

    def get_devices(self):
        """Get devices.

        Returns:
            dict of device instances
        """
        return self.devices
