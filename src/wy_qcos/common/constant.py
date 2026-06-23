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

# Don't import any other libraries
from wy_qcos.common.qcos_version import QcosVersion

_s = lambda x: x


class Constant:
    """Constants."""

    PROGRAM_NAME = "WuYue-QCOS"
    PROGRAM_AUTHOR = "CMSS"
    PLATFORM_NAME = "五岳量子计算操作系统(QCOS)"
    PLATFORM_VERSION = f"{PLATFORM_NAME} v{QcosVersion.VERSION}"
    COPYRIGHT = "2024-2026 中移（苏州）软件技术有限公司"

    # API version
    API_VERSION_V1 = "v1"
    API_VERSION = API_VERSION_V1

    # QCOS server default IP and port
    DEFAULT_API_SERVER_LISTEN_IP = ""
    DEFAULT_API_SERVER_LISTEN_PORT = 18400
    DEFAULT_API_VERSION = "v1"

    # Metrics server defaults
    DEFAULT_METRICS_SERVER_LISTEN_IP = ""
    DEFAULT_METRICS_SERVER_LISTEN_PORT = 19400
    DEFAULT_UPDATE_METRICS_INTERVAL_SECONDS = 15

    # QCOS client-side server default IP and port
    DEFAULT_QCOS_SERVER_IP = "127.0.0.1"
    DEFAULT_QCOS_SERVER_PORT = 18400

    # REDIS server default IP and port
    DEFAULT_REDIS_SERVER_IP = "127.0.0.1"
    DEFAULT_REDIS_SERVER_PORT = 6379
    REDIS_CHANNEL_QCOS_PREFIX = "/qcos"
    REDIS_CHANNEL_DEVICE_RUNNING_INFO_PREFIX = (
        f"{REDIS_CHANNEL_QCOS_PREFIX}/device_running_info"
    )
    REDIS_CHANNEL_JOB_AGG_PREFIX = f"{REDIS_CHANNEL_QCOS_PREFIX}/job_agg"

    # DATABASE
    DB_DIALECT_POSTGRESQL = "postgresql"

    # Security
    DEFAULT_FERNET_KEY = "qevBn4Ol_3bJ7t0IW7TmPCCZurqfw_QRa810U43o_m0="
    ENCRYPTION_PREFIX = "++"

    # Flow limit
    FLOW_LIMIT = 100000

    # Python bin
    PYTHON_BIN = "python3"
    PYPY_BIN = "pypy"

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
    JOB_AGG_FLOW_PAUSE_WAIT_TIMEOUT = 10

    # File types
    FILE_TYPE_QASM = ".qasm"
    FILE_TYPE_JSON = ".json"
    FILE_TYPE_CSV = ".csv"

    # User length
    MIN_USER_LENGTH = 2
    MAX_USER_LENGTH = 64

    # Role length
    MIN_ROLE_LENGTH = 2
    MAX_ROLE_LENGTH = 64

    # Project length
    MIN_PROJECT_LENGTH = 2
    MAX_PROJECT_LENGTH = 64

    # Description length
    MIN_DESCRIPTION_LENGTH = 1
    MAX_DESCRIPTION_LENGTH = 255

    # Password length
    MIN_PASSWORD_LENGTH = 6
    MAX_PASSWORD_LENGTH = 32

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
    TWO_QUBIT_GATE_ISWAP = "iswap"
    TWO_QUBIT_GATE_CU1 = "cu1"
    TWO_QUBIT_GATE_CP = "cp"
    TWO_QUBIT_GATE_CS = "cs"
    TWO_QUBIT_GATE_CSDG = "csdg"
    TWO_QUBIT_GATE_CU3 = "cu3"
    TWO_QUBIT_GATE_ECR = "ecr"
    TWO_QUBIT_GATE_DCX = "dcx"
    TWO_QUBIT_GATE_CSX = "csx"
    TWO_QUBIT_GATE_CU = "cu"
    TWO_QUBIT_GATE_RXX = "rxx"
    TWO_QUBIT_GATE_RYY = "ryy"
    TWO_QUBIT_GATE_RZZ = "rzz"
    TWO_QUBIT_GATE_RZX = "rzx"
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
        TWO_QUBIT_GATE_ISWAP,
        TWO_QUBIT_GATE_CU1,
        TWO_QUBIT_GATE_CP,
        TWO_QUBIT_GATE_CS,
        TWO_QUBIT_GATE_CSDG,
        TWO_QUBIT_GATE_CU3,
        TWO_QUBIT_GATE_ECR,
        TWO_QUBIT_GATE_DCX,
        TWO_QUBIT_GATE_CSX,
        TWO_QUBIT_GATE_CU,
        TWO_QUBIT_GATE_RXX,
        TWO_QUBIT_GATE_ECR,
        TWO_QUBIT_GATE_RZZ,
        TWO_QUBIT_GATE_DCX,
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
    DEVICE_MONITOR_PREFIX = "device_monitor_"
    DEVICE_MANAGER_PREFIX = "device_mgr_"

    # Transpiler
    TRANSPILER_CMSS = "cmss"
    TRANSPILER_HIGH_PERFORMANCE_CMSS = "high_performance_cmss"
    TRANSPILER_QISKIT = "qiskit"
    TRANSPILER_DUMMY = "dummy"
    TRANSPILER_CMSS_QUBO = "cmss_qubo"
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
    RESULTS_FETCH_MODE_SET = "set"
    RESULTS_FETCH_ASYNC_RETRIES = 3
    RESULTS_FETCH_ASYNC_TIMEOUT = 30

    # Profiling types
    PROFILING_TYPE_ALL = "all"
    PROFILING_TYPE_CODE = "code"
    PROFILING_TYPE_QUEUING = "queuing"
    PROFILING_TYPE_SCHEDULING = "scheduling"
    PROFILING_TYPE_DRIVER_PARSE = "driver:parse"
    PROFILING_TYPE_DRIVER_TRANSPILE = "driver:transpile"
    PROFILING_TYPE_DRIVER_RUN = "driver:run"
    PROFILING_TYPE_MACHINE = "machine"
    PROFILING_TYPES = [
        PROFILING_TYPE_ALL,
        PROFILING_TYPE_CODE,
        PROFILING_TYPE_QUEUING,
        PROFILING_TYPE_SCHEDULING,
        PROFILING_TYPE_DRIVER_PARSE,
        PROFILING_TYPE_DRIVER_TRANSPILE,
        PROFILING_TYPE_DRIVER_RUN,
        PROFILING_TYPE_MACHINE,
    ]
    PROFILING_INFO = {
        PROFILING_TYPE_ALL: {"alias_name": "使能所有性能评估类型"},
        PROFILING_TYPE_CODE: {"alias_name": "作业中单代码执行耗时"},
        PROFILING_TYPE_QUEUING: {"alias_name": "作业排队耗时"},
        PROFILING_TYPE_SCHEDULING: {"alias_name": "调度器耗时"},
        PROFILING_TYPE_DRIVER_PARSE: {"alias_name": "代码解析耗时"},
        PROFILING_TYPE_DRIVER_TRANSPILE: {"alias_name": "转译器耗时"},
        PROFILING_TYPE_DRIVER_RUN: {"alias_name": "后端运行耗时"},
        PROFILING_TYPE_MACHINE: {"alias_name": "量子计算机运行耗时"},
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

    # Code compression level
    DEFAULT_CODE_COMPRESSION_LEVEL = 0
    MIN_CODE_COMPRESSION_LEVEL = 0
    MAX_CODE_COMPRESSION_LEVEL = 9

    # job engine property
    DEFAULT_JOB_POOL_TYPE = "process"
    DEFAULT_POOL_CONCURRENCY = 1
    DEFAULT_JOB_TIMEOUT = 300
    DEFAULT_JOB_INTERVAL = 5

    # device monitor engine property
    DEFAULT_DEVICE_MONITOR_RETRIES = 100
    DEFAULT_DEVICE_MONITOR_RETRY_INTERVAL = 60
    DEFAULT_DEVICE_MONITOR_INTERVAL = 60

    # user management
    AUTH_MODE_KEY = "auth_mode"
    AUTH_MODE_NO = "no"
    AUTH_MODE_JWT = "jwt"
    AUTH_MODE_VIRTUAL_INSTANCE = "virtual_instance"
    AUTH_MODES = [AUTH_MODE_NO, AUTH_MODE_JWT, AUTH_MODE_VIRTUAL_INSTANCE]

    ADMIN_PROJECT_ID = "00000000-0000-4000-8000-000000000001"
    ADMIN_PROJECT_NAME = "admin project"
    DEFAULT_PROJECT_ID = "00000000-0000-4000-8000-000000000000"
    DEFAULT_PROJECT_NAME = "default project"
    ADMIN_USERNAME = "admin"
    DEFAULT_ADMIN_PASSWORD = _s("123456")
    DEFAULT_VIRTUAL_INSTANCE_PASSWORD = _s("111111")
    ANONYMOUS_USER_ID = "00000000-0000-4000-8000-000000000000"
    ANONYMOUS_USERNAME = "anonymous"
    INVALID_PROJECT_ID = "00000000-0000-0000-0000-000000000000"
    INVALID_USER_ID = "00000000-0000-0000-0000-000000000000"
    ENV_VAR_ACCESS_TOKEN = _s("QCOS_ACCESS_TOKEN")
    JWT_AUTH_AUDIENCE = "qcos-api"
    ROLE_ADMIN = "admin"
    ROLE_USER = "user"
    ROLE_ANY = "__any__"
    ALL_ROLES = [ROLE_ADMIN, ROLE_USER]

    # Job status
    JOB_STATUS_UNKNOWN = "UNKNOWN"
    JOB_STATUS_QUEUED = "QUEUED"
    JOB_STATUS_RUNNING = "RUNNING"
    JOB_STATUS_FAILED = "FAILED"
    JOB_STATUS_COMPLETED = "COMPLETED"
    JOB_STATUS_CANCELLING = "CANCELLING"
    JOB_STATUS_CANCELLED = "CANCELLED"
    JOB_STATUS_DELETING = "DELETING"
    JOB_STATUS_DELETED = "DELETED"
    JOB_STATUSES = [
        JOB_STATUS_UNKNOWN,
        JOB_STATUS_QUEUED,
        JOB_STATUS_RUNNING,
        JOB_STATUS_FAILED,
        JOB_STATUS_COMPLETED,
        JOB_STATUS_CANCELLING,
        JOB_STATUS_CANCELLED,
        JOB_STATUS_DELETING,
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
    DEFAULT_SHOTS = 10
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

    # Complete reconstruction bit threshold
    COMPLETE_RECONSTRUCTION_THRESHOLD = 32

    # Max memory for dynamic definition
    DD_MAX_MEMORY = 1024

    # --- Metrics constants ---
    # system metrics
    # system stats field names
    SYSTEM_HEALTHY = "system_healthy"
    HEARTBEAT_TIMESTAMP = "heartbeat_timestamp"
    # Component names
    COMPONENT_NAME_FASTAPI = "fastapi"
    COMPONENT_NAME_REDIS = "redis"
    COMPONENT_NAME_PREFECT = "prefect"
    COMPONENT_NAME_WORKER = "worker"
    COMPONENT_NAMES = [
        COMPONENT_NAME_FASTAPI,
        COMPONENT_NAME_REDIS,
        COMPONENT_NAME_PREFECT,
        COMPONENT_NAME_WORKER,
    ]

    # Component status
    COMPONENT_STATUS = "component_status"
    COMPONENT_STATUS_ONLINE = "online"
    COMPONENT_STATUS_OFFLINE = "offline"

    # Job metrics
    JOB_METRICS_FIELD_TOTAL = "total"
    JOB_METRICS_FIELD_COMPLETED = JOB_STATUS_COMPLETED.lower()
    JOB_METRICS_FIELD_FAILED = JOB_STATUS_FAILED.lower()
    JOB_METRICS_FIELD_RUNNING = JOB_STATUS_RUNNING.lower()
    JOB_METRICS_FIELD_QUEUED = JOB_STATUS_QUEUED.lower()
    JOB_METRICS_FIELD_CANCELLING = JOB_STATUS_CANCELLING.lower()
    JOB_METRICS_FIELD_CANCELLED = JOB_STATUS_CANCELLED.lower()
    JOB_METRICS_FIELD_DELETED = JOB_STATUS_DELETED.lower()
    JOB_METRICS_FIELD_UNKNOWN = JOB_STATUS_UNKNOWN.lower()

    # API metrics
    API_METRICS_REQUESTS_TOTAL = "api_requests_total"
    API_METRICS_REQUESTS_IN_PROGRESS = "api_requests_in_progress"
    API_METRICS_REQUESTS_DURATION = "api_request_duration"

    # API stats field names
    API_TOTAL_REQUESTS = "total_requests"
    API_LAST_HOUR_REQUESTS = "last_hour_requests"
    API_LAST_DAY_REQUESTS = "last_day_requests"

    DEFAULT_JOB_QUERY_INTERVAL = 5
    DEFAULT_JOB_WAIT_TIME = 604800


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
