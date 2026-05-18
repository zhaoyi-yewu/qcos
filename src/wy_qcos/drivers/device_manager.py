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
import logging
import threading

import redis
from schema import Optional

from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.common.constant import Constant

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
        self.redis_instance = redis.Redis(
            host=config.REDIS.REDIS_SERVER_IP,
            port=config.REDIS.REDIS_SERVER_PORT,
            decode_responses=True,
        )

    def load_devices(self):
        """Scan and load drivers."""
        logger.info("Load devices ...")
        devices = self.config.DEVICES.DEVICE_LIST
        for device_name in devices:
            logger.info(f"Loading device: {device_name}")
            extra_configs = self.config.get_extra_configs()
            device_configs = extra_configs.get(device_name)
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
                max_queued_jobs = device_configs.pop("max_queued_jobs", -1)
                driver = self.driver_manager.get_driver(driver_name)
                if driver:
                    device = Device(device_name, driver)
                    if alias_name is not None:
                        device.set_alias_name(alias_name)
                    if description is not None:
                        device.set_description(description)
                    if device_max_qubits is not None:
                        device.set_max_qubits(device_max_qubits)
                    if max_queued_jobs is not None:
                        device.set_max_queued_jobs(max_queued_jobs)
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

    def check_redis_connection(self):
        """Check connection to redis."""

        def is_connected():
            try:
                print(
                    f"Check connection to redis: "
                    f"{self.config.REDIS.REDIS_SERVER_IP}:"
                    f"{self.config.REDIS.REDIS_SERVER_PORT} ... "
                )
                self.redis_instance.ping()
                return True, None, None
            except Exception as e:
                return False, str(e), None

        success, err_msg, _ = Library.loop_with_timeout(is_connected, 60, 5)
        if not success:
            raise TimeoutError("Connection to redis timeout")

    def init_devices(self):
        """Init devices."""
        self.check_redis_connection()
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
                # Start subscribe device info by redis
            thread = threading.Thread(
                target=self.subscribe_device_info,
                args=(self.redis_instance, device),
            )
            thread.daemon = True
            thread.start()
            # Show driver info
            logger.info(f"\n{device.show_device_info()}")

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

    def subscribe_device_info(self, redis_instance, device):
        """Subscribe device info by redis."""
        pubsub = redis_instance.pubsub()
        running_info_channel = (
            device.name + Constant.DEVICE_RUNNING_INFO_REDIS_CHANNEL_SUFFIX
        )
        pubsub.subscribe(running_info_channel)
        for message in pubsub.listen():
            if message.get("type") == "message":
                channel = message.get("channel", b"")
                if isinstance(channel, bytes):
                    channel = channel.decode("utf-8")
                if channel == running_info_channel:
                    device_running_info = json.loads(message.get("data"))
                    device.set_device_running_info(device_running_info)
