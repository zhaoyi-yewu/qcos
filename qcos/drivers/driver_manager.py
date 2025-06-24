#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.drivers.driver_base import DriverBase


logger = logging.getLogger(__name__)


class DriverManager:
    """
    Driver manager
    """

    def __init__(self):
        self.drivers = {}

    def load_drivers(self):
        """
        Scan and load drivers
        """
        logger.info("Loading drivers ...")
        base_module_name = "qcos.drivers"
        base_dir = os.path.dirname(__file__)
        module_dirs = Library.find_dirs(base_dir=base_dir, recursive=True)
        for pkg_dir in module_dirs:
            classes = Library.import_classes(
                pkg_dir, base_module_name=base_module_name,
                base_dir=base_dir,
                base_class=DriverBase)
            for class_name, _class, in classes.items():
                logger.info(f"Loading driver: {class_name}")
                class_instance = _class()
                if not class_instance.enable:
                    logger.warning(f"driver: {class_name} is disabled")
                    continue
                self.drivers[class_name] = class_instance
                class_instance.set_name(class_name)
                class_instance.set_module_name(_class.__module__)
                class_instance.set_class_name(_class.__qualname__)
                Constant.DRIVERS.add(class_name)

    def init_drivers(self):
        """
        Init drivers
        """
        for driver_name, driver in self.drivers.items():
            # Load driver configs
            driver.load_driver_configs()
            # Init driver
            driver.init_driver()
            # Show driver info
            logger.info(driver.get_driver_info())

    def has_driver(self, driver_name):
        """
        Has driver

        :param driver_name: driver name
        :return: True or False
        """
        return driver_name in self.drivers

    def get_driver(self, driver_name):
        """
        Get driver

        :param driver_name: driver name
        """
        return self.drivers.get(driver_name, None)

    def get_drivers(self):
        """
        Get all drivers

        :return: dict of drivers
        """
        return self.drivers
