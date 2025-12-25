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

import os
import tempfile

import pytest
from pathlib import Path

from qcos.common.library import Library


GLOBAL_CONFIGS = {}
SAMPLES = {}


@pytest.fixture(scope="session")
def global_configs():
    current_path = os.path.dirname(__file__)
    top_dir = Path(current_path).resolve().parent.parent.parent
    GLOBAL_CONFIGS["base_dir"] = str(top_dir)
    GLOBAL_CONFIGS["samples_dir"] = f"{top_dir}/samples"
    GLOBAL_CONFIGS["etc_dir"] = f"{top_dir}/etc"
    samples_dir = GLOBAL_CONFIGS["samples_dir"]
    SAMPLES["simple-qasm.qasm"] = Library.read_file(
        f"{samples_dir}/qasm/2.0/simple-qasm.qasm"
    )
    with tempfile.TemporaryDirectory(prefix="qcos_test_") as temp_dir:
        os.makedirs(temp_dir, exist_ok=True)
        GLOBAL_CONFIGS["temp_dir"] = temp_dir
        yield temp_dir
