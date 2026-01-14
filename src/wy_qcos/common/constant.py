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


class Constant:
    """Constants."""

    # QCOS server default IP and port
    DEFAULT_API_SERVER_LISTEN_IP = ""
    DEFAULT_API_SERVER_LISTEN_PORT = 18400
    DEFAULT_API_VERSION = "v1"

    # QCOS client-side server default IP and port
    DEFAULT_QCOS_SERVER_IP = "127.0.0.1"
    DEFAULT_QCOS_SERVER_PORT = 18400

    # Security
    DEFAULT_FERNET_KEY = "qevBn4Ol_3bJ7t0IW7TmPCCZurqfw_QRa810U43o_m0="
    ENCRYPTION_PREFIX = "++"

    # Flow limit
    FLOW_LIMIT = 100000

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

    # Quantum Gates
    # single-qubit gates
    SINGLE_QUBIT_GATE_X = "x"
    SINGLE_QUBIT_GATE_Y = "y"
    SINGLE_QUBIT_GATE_Z = "z"
    SINGLE_QUBIT_GATE_H = "h"
    SINGLE_QUBIT_GATE_S = "s"
    SINGLE_QUBIT_GATE_T = "t"
    SINGLE_QUBIT_GATE_P = "p"
    SINGLE_QUBIT_GATE_U = "u"
    SINGLE_QUBIT_GATE_U_UPPERCASE = "U"
    SINGLE_QUBIT_GATE_R = "r"
    SINGLE_QUBIT_GATE_RX = "rx"
    SINGLE_QUBIT_GATE_RY = "ry"
    SINGLE_QUBIT_GATE_RZ = "rz"
    SINGLE_QUBIT_GATE_SX = "sx"
    SINGLE_QUBIT_GATE_SXDG = "sxdg"
    SINGLE_QUBIT_GATE_SDG = "sdg"
    SINGLE_QUBIT_GATE_TDG = "tdg"
    SINGLE_QUBIT_GATE_U1 = "u1"
    SINGLE_QUBIT_GATE_U2 = "u2"
    SINGLE_QUBIT_GATE_U3 = "u3"
    SINGLE_QUBIT_GATE_RESET = "reset"
    SINGLE_QUBIT_GATE_LIST = [
        SINGLE_QUBIT_GATE_X,
        SINGLE_QUBIT_GATE_Y,
        SINGLE_QUBIT_GATE_Z,
        SINGLE_QUBIT_GATE_H,
        SINGLE_QUBIT_GATE_S,
        SINGLE_QUBIT_GATE_T,
        SINGLE_QUBIT_GATE_P,
        SINGLE_QUBIT_GATE_U,
        SINGLE_QUBIT_GATE_U_UPPERCASE,
        SINGLE_QUBIT_GATE_R,
        SINGLE_QUBIT_GATE_RX,
        SINGLE_QUBIT_GATE_RY,
        SINGLE_QUBIT_GATE_RZ,
        SINGLE_QUBIT_GATE_SX,
        SINGLE_QUBIT_GATE_SXDG,
        SINGLE_QUBIT_GATE_SDG,
        SINGLE_QUBIT_GATE_TDG,
        SINGLE_QUBIT_GATE_U1,
        SINGLE_QUBIT_GATE_U2,
        SINGLE_QUBIT_GATE_U3,
    ]
    # two-qubit gates
    TWO_QUBIT_GATE_CH = "ch"
    TWO_QUBIT_GATE_CRX = "crx"
    TWO_QUBIT_GATE_CRY = "cry"
    TWO_QUBIT_GATE_CRZ = "crz"
    TWO_QUBIT_GATE_CX = "cx"
    TWO_QUBIT_GATE_CX_UPPERCASE = "CX"
    TWO_QUBIT_GATE_CY = "cy"
    TWO_QUBIT_GATE_CZ = "cz"
    TWO_QUBIT_GATE_SWAP = "swap"
    TWO_QUBIT_GATE_CU1 = "cu1"
    TWO_QUBIT_GATE_CP = "cp"
    TWO_QUBIT_GATE_CU3 = "cu3"
    TWO_QUBIT_GATE_CSX = "csx"
    TWO_QUBIT_GATE_CU = "cu"
    TWO_QUBIT_GATE_RXX = "rxx"
    TWO_QUBIT_GATE_RZZ = "rzz"
    TWO_QUBIT_GATE_LIST = [
        TWO_QUBIT_GATE_CH,
        TWO_QUBIT_GATE_CRX,
        TWO_QUBIT_GATE_CRY,
        TWO_QUBIT_GATE_CRZ,
        TWO_QUBIT_GATE_CX,
        TWO_QUBIT_GATE_CX_UPPERCASE,
        TWO_QUBIT_GATE_CY,
        TWO_QUBIT_GATE_CZ,
        TWO_QUBIT_GATE_SWAP,
        TWO_QUBIT_GATE_CU1,
        TWO_QUBIT_GATE_CP,
        TWO_QUBIT_GATE_CU3,
        TWO_QUBIT_GATE_CSX,
        TWO_QUBIT_GATE_CU,
        TWO_QUBIT_GATE_RXX,
        TWO_QUBIT_GATE_RZZ,
    ]
    # three-qubit gates
    THREE_QUBIT_GATE_CCX = "ccx"
    THREE_QUBIT_GATE_CSWAP = "cswap"
    THREE_QUBIT_GATE_RCCX = "rccx"
    THREE_QUBIT_GATE_LIST = [
        THREE_QUBIT_GATE_CCX,
        THREE_QUBIT_GATE_CSWAP,
        THREE_QUBIT_GATE_RCCX,
    ]
    # four-qubit gates
    FOUR_QUBIT_GATE_RC3X = "rc3x"
    FOUR_QUBIT_GATE_C3X = "c3x"
    FOUR_QUBIT_GATE_C3SQRTX = "c3sqrtx"
    FOUR_QUBIT_GATE_LIST = [
        FOUR_QUBIT_GATE_RC3X,
        FOUR_QUBIT_GATE_C3X,
        FOUR_QUBIT_GATE_C3SQRTX,
    ]
    # five-qubit gates
    FIVE_QUBIT_GATE_C4X = "c4x"
    FIVE_QUBIT_GATE_LIST = [
        FIVE_QUBIT_GATE_C4X,
    ]
    # all gate list
    ALL_GATE_LIST = (
        SINGLE_QUBIT_GATE_LIST
        + TWO_QUBIT_GATE_LIST
        + THREE_QUBIT_GATE_LIST
        + FOUR_QUBIT_GATE_LIST
        + FIVE_QUBIT_GATE_LIST
    )
    ALL_GATES = "all"

    # Drivers
    DRIVER_DUMMY = "dummy"
    DRIVERS = set()  # autofilled during driver registration

    # Devices
    DEVICE_DUMMY = "dummy"

    # Transpiler
    TRANSPILER_CMSS = "cmss"
    TRANSPILER_QISKIT = "qiskit"
    TRANSPILER_DUMMY = "dummy"
    TRANSPILERS = set()  # autofilled during plugin registration

    # Quantum computer tech type
    TECH_TYPE_NONE = "none"
    TECH_TYPE_NEUTRAL_ATOM = "neutral_atom"
    TECH_TYPE_ION_TRAP = "ion_trap"
    TECH_TYPE_SUPERCONDUCTING = "superconducting"
    TECH_TYPE_PHOTON = "photon"
    TECH_TYPE_NMR = "nmr"
    TECH_TYPE_GENERIC_SIMULATOR = "generic_simulator"
    TECH_TYPE_INFO = {
        TECH_TYPE_NONE: {"alias_name": "无"},
        TECH_TYPE_NEUTRAL_ATOM: {"alias_name": "中性原子"},
        TECH_TYPE_ION_TRAP: {"alias_name": "离子阱"},
        TECH_TYPE_SUPERCONDUCTING: {"alias_name": "超导"},
        TECH_TYPE_PHOTON: {"alias_name": "光量子"},
        TECH_TYPE_NMR: {"alias_name": "核磁共振"},
        TECH_TYPE_GENERIC_SIMULATOR: {"alias_name": "通用量子模拟器"},
    }

    # Job types
    JOB_TYPE_SAMPLING = "sampling"
    JOB_TYPE_ESTIMATION = "estimation"
    JOB_TYPES = [JOB_TYPE_SAMPLING, JOB_TYPE_ESTIMATION]

    # Results fetch mode
    RESULTS_FETCH_MODE_SYNC = "sync"
    RESULTS_FETCH_MODE_ASYNC = "async"
    RESULTS_FETCH_ASYNC_RETRIES = 3
    RESULTS_FETCH_ASYNC_TIMEOUT = 30

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
    PROFILING_INFO = {
        PROFILING_TYPE_ALL: {"alias_name": "使能所有性能评估类型"},
        PROFILING_TYPE_CODE: {"alias_name": "作业中单代码执行耗时"},
        PROFILING_TYPE_SCHEDULING: {"alias_name": "调度器耗时"},
        PROFILING_TYPE_DRIVER_PARSE: {"alias_name": "代码解析耗时"},
        PROFILING_TYPE_DRIVER_TRANSPILE: {"alias_name": "转译器耗时"},
        PROFILING_TYPE_DRIVER_RUN: {"alias_name": "后端运行耗时"},
    }

    # Callback types
    CALLBACK_TYPE_RESULTS = "results"
    CALLBACK_TYPES = [CALLBACK_TYPE_RESULTS]

    # Maximum jobs allowed in the system
    MAX_AGGREGATION_JOBS = 5

    # Job priority
    DEFAULT_JOB_PRIORITY = 5
    MIN_JOB_PRIORITY = 1
    MAX_JOB_PRIORITY = 10
    MAX_JOB_WORKER = 1
    DEFAULT_AGGREGATION_JOB_INTERVAL = 10

    # job engine property
    DEFAULT_JOB_POOL_TYPE = "process"
    DEFAULT_POOL_CONCURRENCY = 1
    DEFAULT_JOB_TIMEOUT = 300
    DEFAULT_JOB_INTERVAL = 5

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

    # Prefect flow state
    PREFECT_STATE_RUNNING = "RUNNING"
    PREFECT_STATE_SCHEDULED = "SCHEDULED"
    PREFECT_STATE_PENDING = "PENDING"
    PREFECT_STATE_LATE = "LATE"
    PREFECT_STATE_FAILED = "FAILED"
    PREFECT_STATE_COMPLETED = "COMPLETED"
    PREFECT_STATE_CRASHED = "CRASHED"
    PREFECT_STATE_CANCELLING = "CANCELLING"
    PREFECT_STATE_CANCELLED = "CANCELLED"
    PREFECT_STATE_PAUSED = "PAUSED"
    PREFECT_CANCEL_REQUIRED_STATES = [PREFECT_STATE_RUNNING]
    PREFECT_WAIT_STATES = [PREFECT_STATE_SCHEDULED, PREFECT_STATE_PENDING]

    VID_TAGS_PREFIX = "VIRTUAL_INSTANCE_ID"

    # Prefect job log
    PREFECT_JOB_LOG_FORMAT = (
        "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}"
    )

    # Shots
    DEFAULT_SHOTS = 1
    MIN_SHOTS = 1
    MAX_SHOTS = 10240

    # Qubits
    DEFAULT_QUBITS = 1
    MIN_QUBITS = 1
    MAX_QUBITS = 1024

    # Optimization level
    DEFAULT_OPTIMIZATION_LEVEL = 1
    MIN_OPTIMIZATION_LEVEL = 0
    MAX_OPTIMIZATION_LEVEL = 3

    # Max bitwidth
    MAX_QUBO_BIT_WIDTH = 8
    MAX_QUBO_QUBITS = 2000

    # Circuit cutting
    MAX_CIRCUIT_CUT = 100
    MAX_RERURSIVE_DEPTH = 100


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
    BAD_REQUEST_ERROR = 400
    UNAUTHORIZED_ERROR = 401
    FORBIDDEN_ERROR = 403
    NOT_FOUND_ERROR = 404
    TIMEOUT_ERROR = 408
    CONFLICT_ERROR = 409
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED_ERROR = 501
    SERVICE_UNAVAILABLE_ERROR = 503
