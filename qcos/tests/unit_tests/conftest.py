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

import os
import pytest
from pathlib import Path


GLOBAL_CONFIGS = {}


@pytest.fixture(scope="session")
def global_configs():
    current_path = os.path.dirname(__file__)
    top_dir = Path(current_path).resolve().parent.parent.parent
    GLOBAL_CONFIGS["base_dir"] = str(top_dir)
    GLOBAL_CONFIGS["samples_dir"] = f"{top_dir}/samples"
