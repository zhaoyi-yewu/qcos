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

# ruff: noqa: E402
# load driver venv
#
# Shared driver-behavior tests (init_driver, fetch_configs,
# submit_task, get_task_results, convert_results, run,
# convert_code_to_qasm, get_device_info, fetch_running_info,
# etc.) live in test_driver_lq_base.py. This file only verifies
# the QZ01-surface_code-specific overrides (alias_name,
# description, max_qubits) that differ from the base class.

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library


org_path = Library.set_driver_venv_path(
    "DriverLqQZ01SurfaceCode", Config.DEFAULT.VENV_DIR
)

import pytest

from wy_qcos.driver.logical_qubit.driver_lq_qz01_surface_code import (
    DriverLqQZ01SurfaceCode,
)


@pytest.mark.driver
class TestDriverLqQZ01SurfaceCode:
    """Verify QZ01-surface_code-specific attribute overrides.

    All shared behaviour is covered by test_driver_lq_base.py.
    """

    def test_init_overrides(self):
        driver = DriverLqQZ01SurfaceCode()
        assert driver.version == "0.0.1"
        assert driver.alias_name == "逻辑比特 QZ01-surface_code 超导驱动"
        assert driver.description == "逻辑比特 QZ01-surface_code 超导驱动"
        assert driver.max_qubits == 17
