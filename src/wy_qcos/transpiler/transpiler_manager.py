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
from wy_qcos.transpiler.transpiler_base import TranspilerBase

logger = logging.getLogger(__name__)


class TranspilerManager:
    """Transpiler manager."""

    def __init__(self):
        self.transpilers = {}

    def load_transpilers(self):
        """Scan and load transpilers."""
        logger.info("Loading transpilers ...")
        base_module_name = "wy_qcos.transpiler"
        base_dir = os.path.dirname(__file__)
        module_dirs = Library.find_dirs(base_dir=base_dir, recursive=True)
        for pkg_dir in module_dirs:
            classes = Library.import_classes(
                pkg_dir,
                base_module_name=base_module_name,
                base_dir=base_dir,
                base_class=TranspilerBase,
                excluded_class="Base$",
            )
            for (
                class_name,
                _class,
            ) in classes.items():
                logger.info(f"Loading transpiler: {class_name}")
                class_instance = _class()
                if not class_instance.enable:
                    logger.warning(f"transpiler: {class_name} is disabled")
                    continue
                name = class_instance.get_name()
                self.transpilers[name] = class_instance
                Constant.TRANSPILERS.add(name)
                class_instance.set_module_name(_class.__module__)
                class_instance.set_class_name(_class.__qualname__)

    def init_transpilers(self):
        """Init transpilers."""
        for _, transpiler in self.transpilers.items():
            # Init transpiler
            transpiler.init_transpiler()
            # Show transpiler options
            logger.info(f"\n{transpiler.get_transpiler_info()}")

    def has_transpiler(self, transpiler_name):
        """Has transpiler.

        Args:
            transpiler_name: transpiler name

        Returns:
            True or False
        """
        return transpiler_name in self.transpilers

    def get_transpiler(self, transpiler_name):
        """Get transpiler.

        Args:
            transpiler_name: transpiler name

        Returns:
            transpiler instance
        """
        return self.transpilers.get(transpiler_name, None)

    def get_transpilers(self):
        """Get all transpilers.

        Returns:
            dict of transpilers
        """
        return self.transpilers
