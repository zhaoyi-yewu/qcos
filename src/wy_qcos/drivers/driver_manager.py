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
import os

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.drivers.device import Device
from wy_qcos.drivers.driver_base import DriverBase


logger = logging.getLogger(__name__)


class DriverManager:
    """Driver manager."""

    def __init__(self):
        self.drivers = {}

    def load_drivers(self):
        """Scan and load drivers."""
        logger.info("Loading drivers ...")
        base_module_name = "wy_qcos.drivers"
        base_dir = os.path.dirname(__file__)
        module_dirs = Library.find_dirs(
            base_dir=base_dir, recursive=True, excludes=["*__pycache__"]
        )
        for pkg_dir in module_dirs:
            classes = Library.import_classes(
                pkg_dir,
                base_module_name=base_module_name,
                base_dir=base_dir,
                base_class=DriverBase,
                excluded_class="Base$",
            )
            for (
                class_name,
                _class,
            ) in classes.items():
                logger.info(f"Loading driver: {class_name}")
                class_instance = _class()
                name = class_name
                self.drivers[name] = class_instance
                Constant.DRIVERS.add(name)
                class_instance.set_module_name(_class.__module__)
                class_instance.set_class_name(_class.__qualname__)

    def init_drivers(self):
        """Init drivers."""
        for driver_name, driver in self.drivers.items():
            # Validate driver
            success, err_msg = driver.validate_driver()
            if success:
                # Init driver
                driver.init_driver()
            if not success:
                logger.error(
                    f"Driver: {driver_name} is disabled. "
                    f"Error message: {err_msg}"
                )
                driver.enable = False
                driver.set_device_status(Device.DEVICE_STATUS_OFFLINE)
            # Show driver info
            logger.info(f"\n{driver.get_driver_info()}")

    def has_driver(self, driver_name):
        """Has driver.

        Args:
            driver_name: driver name

        Returns:
            True or False
        """
        return driver_name in self.drivers

    def get_driver(self, driver_name):
        """Get driver.

        Args:
            driver_name: driver name
        """
        return self.drivers.get(driver_name, None)

    def get_drivers(self):
        """Get drivers.

        Returns:
            dict of drivers
        """
        return self.drivers
