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
# Don't import any libraries


def _s(secret):
    """Secret text wrapper.

    Args:
        secret: secret text to be wrapped

    Returns:
        wrapped secret text
    """
    return secret


class Constant:
    """Constants."""

    # QCOS server default IP and port
    DEFAULT_API_SERVER_LISTEN_IP = ""
    DEFAULT_API_SERVER_LISTEN_PORT = 18400
    DEFAULT_API_VERSION = "v1"

    # QCOS client-side server default IP and port
    DEFAULT_QCOS_SERVER_IP = "127.0.0.1"
    DEFAULT_QCOS_SERVER_PORT = 18400

    # Code types
    CODE_TYPE_QASM = "qasm"
    CODE_TYPE_QASM2 = "qasm2"
    CODE_TYPE_QASM3 = "qasm3"
    CODE_TYPE_QUBO = "qubo"
    CODE_TYPES_ALL_QASM = [CODE_TYPE_QASM, CODE_TYPE_QASM2, CODE_TYPE_QASM3]
    CODE_TYPES = [
        CODE_TYPE_QASM,
        CODE_TYPE_QASM2,
        CODE_TYPE_QASM3,
        CODE_TYPE_QUBO,
    ]

    # Callback types
    CALLBACK_TYPE_RESULTS = "results"
    CALLBACK_TYPES = [CALLBACK_TYPE_RESULTS]

    # Aggregation types
    AGGREGATION_TYPE_INTERNAL = "internal"
    AGGREGATION_TYPE_EXTERNAL = "external"
    AGGREGATION_TYPE_NONE = "None"
    AGGREGATION_TYPES = [
        AGGREGATION_TYPE_NONE,
        AGGREGATION_TYPE_INTERNAL,
        AGGREGATION_TYPE_EXTERNAL,
    ]

    # File types
    FILE_TYPE_QASM = ".qasm"
    FILE_TYPE_JSON = ".json"
    FILE_TYPE_CSV = ".csv"

    # Description length
    MIN_DESCRIPTION_LENGTH = 1
    MAX_DESCRIPTION_LENGTH = 255

    # Job types
    JOB_TYPE_SAMPLING = "sampling"
    JOB_TYPE_ESTIMATION = "estimation"
    JOB_TYPES = [JOB_TYPE_SAMPLING, JOB_TYPE_ESTIMATION]

    # Job priority
    DEFAULT_JOB_PRIORITY = 5
    MIN_JOB_PRIORITY = 1
    MAX_JOB_PRIORITY = 10

    # User
    ENV_VAR_ACCESS_TOKEN = _s("QCOS_ACCESS_TOKEN")
    ENV_VAR_REFRESH_TOKEN = _s("QCOS_REFRESH_TOKEN")
    ENV_VAR_VIRTUAL_INSTANCE_ID = "QCOS_VIRTUAL_INSTANCE_ID"

    # Job status
    JOB_STATUS_UNKNOWN = "UNKNOWN"
    JOB_STATUS_QUEUED = "QUEUED"
    JOB_STATUS_RUNNING = "RUNNING"
    JOB_STATUS_FAILED = "FAILED"
    JOB_STATUS_COMPLETED = "COMPLETED"
    JOB_STATUS_CANCELLING = "CANCELLING"
    JOB_STATUS_CANCELLED = "CANCELLED"
    JOB_STATUS_DELETED = "DELETED"
    JOB_STATUSES = [
        JOB_STATUS_UNKNOWN,
        JOB_STATUS_QUEUED,
        JOB_STATUS_RUNNING,
        JOB_STATUS_FAILED,
        JOB_STATUS_COMPLETED,
        JOB_STATUS_CANCELLING,
        JOB_STATUS_CANCELLED,
        JOB_STATUS_DELETED,
    ]

    # Shots
    DEFAULT_SHOTS = 1
    MIN_SHOTS = 1
    MAX_SHOTS = 10240

    # Drivers
    DRIVER_DUMMY = "dummy"

    # Devices
    DEVICE_DUMMY = "dummy"

    # Transpiler
    TRANSPILER_CMSS = "cmss"

    # Profiling types
    PROFILING_TYPE_ALL = "all"
    PROFILING_TYPE_CODE = "code"
    PROFILING_TYPE_SCHEDULING = "scheduling"
    PROFILING_TYPE_DRIVER_PARSE = "driver:parse"
    PROFILING_TYPE_DRIVER_TRANSPILE = "driver:transpile"
    PROFILING_TYPE_DRIVER_RUN = "driver:run"
    PROFILING_TYPES = [
        PROFILING_TYPE_ALL,
        PROFILING_TYPE_CODE,
        PROFILING_TYPE_SCHEDULING,
        PROFILING_TYPE_DRIVER_PARSE,
        PROFILING_TYPE_DRIVER_TRANSPILE,
        PROFILING_TYPE_DRIVER_RUN,
    ]


class HttpHeaders:
    # headers
    DEFAULT_JSON_HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


class HttpMethod:
    """HTTP methods."""

    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"


class HttpCode:
    """HTTP status codes."""

    SUCCESS_OK = 200
    SUCCESS_CREATED = 201
    SUCCESS_ACCEPTED = 202
    SUCCESS_NO_CONTENT = 204
    ERROR_BAD_REQUEST = 400
    ERROR_UNAUTHORIZED = 401
    ERROR_FORBIDDEN = 403
    ERROR_NOT_FOUND = 404
    ERROR_TIMEOUT = 408
    ERROR_CONFLICT = 409
    ERROR_INTERNAL_SERVER = 500
    ERROR_INTERNAL_SERVER_ERROR = 500
    ERROR_NOT_IMPLEMENTED = 501
    ERROR_SERVICE_UNAVAILABLE = 503
