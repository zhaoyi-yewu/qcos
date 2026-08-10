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
    except ValueError:
        return False
    return all([result.scheme in schemes, result.netloc])


NAME_SCHEMA = And(
    Use(str),
    lambda s: 1 <= len(s) <= 64,
    Regex(r"^[a-zA-Z0-9_\-\.]+$"),
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
TAGS_SCHEMA = [str]

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
DEVICE_INFO_SCHEMA = {
    "status": str,
    Optional("details"): {
        Optional("vendor_job_count"): {
            Optional("unknown"): int,
            Optional("queued"): int,
            Optional("running"): int,
            Optional("failed"): int,
            Optional("completed"): int,
            Optional("cancelling"): int,
            Optional("cancelled"): int,
            Optional("deleting"): int,
            Optional("deleted"): int,
            Optional("total"): int,
        },
        Optional("calibration"): {
            Optional("last_updated_at"): str,
            Optional("qubit_metrics"): [
                {
                    "qubit_id": int,
                    Optional("xeb_fidelity"): Or(int, float),
                    Optional("t1"): Or(int, float),
                    Optional("t2"): Or(int, float),
                    Optional("readout_fidelity_0"): Or(int, float),
                    Optional("readout_fidelity_1"): Or(int, float),
                }
            ],
            Optional("coupler_metrics"): [
                {
                    "qubits": [int],
                    Optional("cz_fidelity"): Or(int, float),
                }
            ],
        },
    },
    Optional("available_qubits"): int,
    Optional("last_updated_at"): str,
}

# Config schema
# Note: enable_device_monitor and monitor_log_file have been moved
# into the [device.device_monitor] sub-table; they are validated
# there and are no longer top-level driver config keys.
DEFAULT_DRIVER_CONFIG_SCHEMA = {
    Optional("debug"): bool,
    Optional("device_log_file"): str,
    Optional("mgr_log_file"): str,
    Optional("max_queued_jobs"): int,
    Optional("log_format"): str,
    Optional("log_rotate_max_size_mb"): int,
    Optional("log_rotate_backup_count"): int,
    Optional("log_rotate_compression"): bool,
    Optional("max_job_wait_time"): int,
    Optional("job_query_interval"): int,
    Optional("device_monitor"): {
        Optional("enable_device_monitor"): bool,
        Optional("monitor_log_file"): str,
        Optional("polling_interval"): int,
    },
}

# Options schema
DRIVER_OPTIONS = dict
TRANSPILER_OPTIONS = dict
QEC_OPTIONS = dict
