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
# Don't import library

from schema import And, Optional, Or, Regex, Use
from urllib.parse import urlparse

from .constant import Constant, HttpMethod


def is_valid_url(url, schemes):
    """Check if url is valid.

    Args:
        url: url to check
        schemes: url schemes

    Returns:
        True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme in schemes, result.netloc])
    except ValueError:
        return False
    return True


NAME_SCHEMA = And(
    Use(str),
    lambda s: 1 <= len(s) <= 64,
    Regex(r"^[a-zA-Z0-9_\-]+$"),
    error="Name can only consist of the following parts: "
    "letters, numbers, dashes, underscores. "
    "The length of name must between [1-64].",
)
SOURCE_CODE_SCHEMA = list
SOURCE_CODE_TEXT_SCHEMA = [str]

SOURCE_RESULTS_SUCCESS = {  # results
    "results": dict,
    Optional("num_qubits"): int,
}
SOURCE_RESULTS_ERROR = {  # error messages
    "code": int,
    "message": str,
}
SOURCE_SET_RESULTS = [Or(SOURCE_RESULTS_SUCCESS, SOURCE_RESULTS_ERROR)]

CALLBACKS_SCHEMA = [
    {
        "name": str,
        "type": Or(*Constant.CALLBACK_TYPES),
        "method": Or(HttpMethod.POST),
        "url": lambda s: is_valid_url(s, {"http", "https"}),
        Optional("headers"): dict,
        Optional("retries"): int,
        Optional("timeout"): int,
    }
]
DRIVER_OPTIONS = dict
TRANSPILER_OPTIONS = dict
