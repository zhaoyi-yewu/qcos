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

"""Unit tests for pulse_ir package initialization."""

import importlib
from unittest.mock import patch


def test_pulse_ir_package_exports_expected_metadata():
    """Test pulse_ir package metadata exports."""
    module = importlib.import_module("wy_qcos.transpiler.common.pulse_ir")

    assert module.__all__ == []
    assert module.__name__ == "wy_qcos.transpiler.common.pulse_ir"
    assert module.__doc__ == "WY QCOS pulse_ir namespace package."


def test_is_main_process_uses_stdlib_parent_process():
    """Test main-process detection using the parent process."""
    module = importlib.import_module(
        "wy_qcos.transpiler.common.pulse_ir.utils.multiprocessing"
    )

    with patch.object(module, "parent_process", return_value=None):
        assert module.is_main_process() is True
    with patch.object(module, "parent_process", return_value=object()):
        assert module.is_main_process() is False


def test_lazy_subprocess_tester_uses_exit_status():
    """Test command availability handling without executing a real tool."""
    module = importlib.import_module(
        "wy_qcos.transpiler.common.pulse_ir.utils.lazy_tester"
    )
    tester = module.LazySubprocessTester(("tool", "-V"))

    with patch.object(module, "_run_command", return_value=0) as run_mock:
        assert tester._is_available() is True
        run_mock.assert_called_once_with(("tool", "-V"))
    with patch.object(module, "_run_command", return_value=1):
        assert tester._is_available() is False
    with patch.object(module, "_run_command", side_effect=OSError):
        assert tester._is_available() is False
