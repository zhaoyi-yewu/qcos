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

from schema import Optional, Or

from .constant import Constant, HttpMethod
from .library import Library


SOURCE_CODE_SCHEMA = [str]
CALLBACKS_SCHEMA = [
    {
        "name": str,
        "type": Or(*Constant.CALLBACK_TYPES),
        "method": Or(HttpMethod.POST),
        "url": lambda s: Library.is_valid_url(s, {"http", "https"}),
        Optional("headers"): dict,
        Optional("retries"): int,
        Optional("timeout"): int
    }
]
