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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------


class Constant:
    """
    Constants
    """
    # Code types
    CODE_TYPE_QASM2 = "qasm2"
    CODE_TYPE_QASM3 = "qasm3"
    CODE_TYPE_QUBO = "qubo"
    CODE_TYPES = [CODE_TYPE_QASM2, CODE_TYPE_QASM3, CODE_TYPE_QUBO]

    # Drivers
    DRIVER_DUMMY = "DriverDummy"
    DRIVERS = set([DRIVER_DUMMY])  # autofilled during driver registration

    # Transpiler
    TRANSPILER_CMSS = "cmss"
    TRANSPILER_TYPES = [TRANSPILER_CMSS]

    # Job types
    JOB_TYPE_ESTIMATION = "estimation"
    JOB_TYPE_SAMPLING = "sampling"
    JOB_TYPES = [JOB_TYPE_ESTIMATION, JOB_TYPE_SAMPLING]

    # Job scheduling policy
    JOB_SCHEDULING_POLICY_PRIORITY = "priority"
    JOB_SCHEDULING_POLICY_HIGH_RESPONSE_RATIO = "high_response_ratio"
    JOB_SCHEDULING_POLICY_SHORTEST_JOB_FIRST = "shortest_job_first"
    JOB_SCHEDULING_POLICY_TIME_PRECEDENCE = "time_precedence"
    JOB_SCHEDULING_POLICY_PERIODIC = "periodic"
    JOB_SCHEDULING_POLICY_DEPENDENT = "dependent"
    JOB_SCHEDULING_POLICY_BATCH = "batch"
    JOB_SCHEDULING_POLICY_REALTIME = "realtime"
    DEFAULT_JOB_SCHEDULING_POLICY = JOB_SCHEDULING_POLICY_TIME_PRECEDENCE
    JOB_SCHEDULING_POLICIES = [JOB_SCHEDULING_POLICY_PRIORITY,
                               JOB_SCHEDULING_POLICY_HIGH_RESPONSE_RATIO,
                               JOB_SCHEDULING_POLICY_SHORTEST_JOB_FIRST,
                               JOB_SCHEDULING_POLICY_TIME_PRECEDENCE,
                               JOB_SCHEDULING_POLICY_PERIODIC,
                               JOB_SCHEDULING_POLICY_DEPENDENT,
                               JOB_SCHEDULING_POLICY_BATCH,
                               JOB_SCHEDULING_POLICY_REALTIME]

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
    DEFAULT_JOB_TIMEOUT = 60
    DEFAULT_JOB_INTERVAL = 5

    # Job status
    JOB_STATUS_UNKNOWN = "UNKNOWN"
    JOB_STATUS_QUEUED = "QUEUED"
    JOB_STATUS_RUNNING = "RUNNING"
    JOB_STATUS_FAILED = "FAILED"
    JOB_STATUS_COMPLETED = "COMPLETED"
    JOB_STATUS_CANCELLING = "CANCELLING"
    JOB_STATUS_CANCELLED = "CANCELLED"
    JOB_STATUSES = [JOB_STATUS_UNKNOWN, JOB_STATUS_QUEUED, JOB_STATUS_RUNNING,
                    JOB_STATUS_FAILED, JOB_STATUS_COMPLETED,
                    JOB_STATUS_CANCELLING, JOB_STATUS_CANCELLED]

    # Shots
    DEFAULT_SHOTS = 10
    MIN_SHOTS = 1
    MAX_SHOTS = 1000

    # Qubits
    DEFAULT_QUBITS = 1
    MIN_QUBITS = 1
    MAX_QUBITS = 1024

    # Optimization level
    DEFAULT_OPTIMIZATION_LEVEL = 0
    MIN_OPTIMIZATION_LEVEL = 0
    MAX_OPTIMIZATION_LEVEL = 3


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
