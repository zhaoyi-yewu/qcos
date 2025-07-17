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

class Constant:
    """
    Constants
    """
    # Code types
    CODE_TYPE_QASM = "qasm"
    CODE_TYPE_QASM2 = "qasm2"
    CODE_TYPE_QASM3 = "qasm3"
    CODE_TYPE_QUBO = "qubo"
    CODE_TYPES = [CODE_TYPE_QASM, CODE_TYPE_QASM2, CODE_TYPE_QASM3,
                  CODE_TYPE_QUBO]

    # Description string length
    MIN_DESCRIPTION_LENGTH = 1
    MAX_DESCRIPTION_LENGTH = 255

    # Quantum Gates
    # single-qubit gates
    SQ_GATE_X = "x"
    SQ_GATE_Y = "y"
    SQ_GATE_Z = "z"
    SQ_GATE_H = "h"
    SQ_GATE_S = "s"
    SQ_GATE_T = "t"
    SQ_GATE_RX = "rx"
    SQ_GATE_RY = "ry"
    SQ_GATE_RZ = "rz"
    SQ_GATE_SDG = "sdg"
    SQ_GATE_TDG = "tdg"
    SQ_GATE_U1 = "u1"
    SQ_GATE_U2 = "u2"
    SQ_GATE_U3 = "u3"
    SQ_GATE_LIST = [
        SQ_GATE_X,
        SQ_GATE_Y,
        SQ_GATE_Z,
        SQ_GATE_H,
        SQ_GATE_S,
        SQ_GATE_T,
        SQ_GATE_RX,
        SQ_GATE_RY,
        SQ_GATE_RZ,
        SQ_GATE_SDG,
        SQ_GATE_TDG,
        SQ_GATE_U1,
        SQ_GATE_U2,
        SQ_GATE_U3
    ]
    # double-qubit gates
    DQ_GATE_CH = "ch"
    DQ_GATE_CRX = "crx"
    DQ_GATE_CRY = "cry"
    DQ_GATE_CRZ = "crz"
    DQ_GATE_CX = "cx"
    DQ_GATE_CY = "cy"
    DQ_GATE_CZ = "cz"
    DQ_GATE_LIST = [
        DQ_GATE_CH,
        DQ_GATE_CRX,
        DQ_GATE_CRY,
        DQ_GATE_CRZ,
        DQ_GATE_CX,
        DQ_GATE_CY,
        DQ_GATE_CZ
    ]
    # triple-qubit gates
    TQ_GATE_CCX = "ccx"
    TQ_GATE_LIST = [
        TQ_GATE_CCX
    ]
    # all gate list
    ALL_GATE_LIST = SQ_GATE_LIST + DQ_GATE_LIST + TQ_GATE_LIST
    ALL_GATES = "all"

    # Drivers
    DRIVER_DUMMY = "dummy"
    DRIVERS = set()  # autofilled during driver registration

    # Transpiler
    TRANSPILER_CMSS = "cmss"
    TRANSPILER_TYPES = set()  # autofilled during plugin registration

    # Quantum computer tech type
    TECH_TYPE_NEUTRAL_ATOM = "neutral_atom"
    TECH_TYPE_ION_TRAP = "ion_trap"
    TECH_TYPE_SUPERCONDUCTING = "superconducting"
    TECH_TYPE_PHOTON = "photon"

    # Job types
    JOB_TYPE_ESTIMATION = "estimation"
    JOB_TYPE_SAMPLING = "sampling"
    JOB_TYPES = [JOB_TYPE_ESTIMATION, JOB_TYPE_SAMPLING]

    # Job scheduling policy
    JOB_SCHED_POLICY_PRIORITY = "priority"
    JOB_SCHED_POLICY_HIGH_RESPONSE_RATIO = "high_response_ratio"
    JOB_SCHED_POLICY_SHORTEST_JOB_FIRST = "shortest_job_first"
    JOB_SCHED_POLICY_TIME_PRECEDENCE = "time_precedence"
    JOB_SCHED_POLICY_PERIODIC = "periodic"
    JOB_SCHED_POLICY_DEPENDENT = "dependent"
    JOB_SCHED_POLICY_BATCH = "batch"
    JOB_SCHED_POLICY_REALTIME = "realtime"
    DEFAULT_JOB_SCHED_POLICY = JOB_SCHED_POLICY_TIME_PRECEDENCE
    JOB_SCHED_POLICIES = [JOB_SCHED_POLICY_PRIORITY,
                          JOB_SCHED_POLICY_HIGH_RESPONSE_RATIO,
                          JOB_SCHED_POLICY_SHORTEST_JOB_FIRST,
                          JOB_SCHED_POLICY_TIME_PRECEDENCE,
                          JOB_SCHED_POLICY_PERIODIC,
                          JOB_SCHED_POLICY_DEPENDENT,
                          JOB_SCHED_POLICY_BATCH,
                          JOB_SCHED_POLICY_REALTIME]

    # Results fetch mode
    RESULTS_FETCH_MODE_SYNC = "sync"
    RESULTS_FETCH_MODE_ASYNC = "async"
    RESULTS_FETCH_ASYNC_RETRIES = 3
    RESULTS_FETCH_ASYNC_TIMEOUT = 30

    # Profiling types
    PROFILING_TYPE_TRANSPILER = "transpiler"
    PROFILING_TYPE_SCHEDULER = "scheduler"
    PROFILING_TYPES = [PROFILING_TYPE_TRANSPILER, PROFILING_TYPE_SCHEDULER]

    # Callback types
    CALLBACK_TYPE_RESULTS = "results"
    CALLBACK_TYPES = [CALLBACK_TYPE_RESULTS]

    # Maximum jobs allowed in the system
    MAX_JOBS = 1000

    # Job priority
    DEFAULT_JOB_PRIORITY = 5
    MIN_JOB_PRIORITY = 1
    MAX_JOB_PRIORITY = 10
    MAX_JOB_WORKER = 1

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
    JOB_STATUSES = [JOB_STATUS_UNKNOWN, JOB_STATUS_QUEUED, JOB_STATUS_RUNNING,
                    JOB_STATUS_FAILED, JOB_STATUS_COMPLETED,
                    JOB_STATUS_CANCELLING, JOB_STATUS_CANCELLED,
                    JOB_STATUS_DELETED]

    # Prefect flow state
    PREFECT_STATE_SCHEDULED = "SCHEDULED"
    PREFECT_STATE_PENDING = "PENDING"
    PREFECT_STATE_LATE = "LATE"
    PREFECT_STATE_FAILED = "FAILED"
    PREFECT_STATE_COMPLETED = "COMPLETED"
    PREFECT_STATE_CRASHED = "CRASHED"

    # Prefect job log
    PREFECT_JOB_LOG_PATH = "/var/log/qcos/prefect-flow.log"
    PREFECT_JOB_LOG_ROTATION = "500 MB"
    PREFECT_JOB_LOG_RETENTION = "30 days"
    PREFECT_JOB_LOG_FORMAT = ("{time:YYYY-MM-DD HH:mm:ss} | {level} "
                              "| {name} | {message}")

    # Shots
    DEFAULT_SHOTS = 1
    MIN_SHOTS = 1
    MAX_SHOTS = 10240

    # Qubits
    DEFAULT_QUBITS = 1
    MIN_QUBITS = 1
    MAX_QUBITS = 1024

    # Optimization level
    DEFAULT_OPTIMIZATION_LEVEL = 0
    MIN_OPTIMIZATION_LEVEL = 0
    MAX_OPTIMIZATION_LEVEL = 3


class HttpHeaders:
    # headers
    DEFAULT_JSON_HEADERS = {"Content-Type": "application/json"}


class HttpMethod:
    """
    HTTP methods
    """
    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"


class HttpCode:
    """
    HTTP status codes
    """
    SUCCESS_OK = 200
    SUCCESS_CREATED = 201
    SUCCESS_ACCEPTED = 202
    SUCCESS_NO_CONTENT = 204
    BAD_REQUEST_ERROR = 400
    FORBIDDEN_ERROR = 403
    NOT_FOUND_ERROR = 404
    TIMEOUT_ERROR = 408
    CONFLICT_ERROR = 409
    INTERNAL_SERVER_ERROR = 500
