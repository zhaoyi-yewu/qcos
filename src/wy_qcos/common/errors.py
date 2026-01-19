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


class BaseException(Exception):
    """Base exception."""

    def __init__(self, message):
        super().__init__(message)
        self.message = str(message)

    def get_error_code(self):
        """Get error code.

        Returns:
            error code
        """
        return self.error_code

    def get_err_msgs(self):
        return f"[{self.module_name}] {self.err_type}: {self.message}"


class GenericException(BaseException):
    """Generic exception."""

    module_name = "Generic"
    error_code = -10
    err_type = "Error"


class InvalidArguments(BaseException):
    """Invalid arguments."""

    module_name = "Generic"
    error_code = -11
    err_type = "Invalid arguments"


class NotFound(BaseException):
    """Not Found."""

    module_name = "Generic"
    error_code = -12
    err_type = "Not Found"


class WorkFlowError(BaseException):
    """Work Flow Error."""

    module_name = "Workflow"
    error_code = -13
    err_type = "Error"


class JobEngineDriverInitError(BaseException):
    """Job Engine: Driver Init Error."""

    module_name = "JobEngine"
    error_code = -100
    err_type = "Driver Init Error"


class JobEngineTranspilerInitError(BaseException):
    """Job Engine: Transpiler Init Error."""

    module_name = "JobEngine"
    error_code = -101
    err_type = "Transpiler Init Error"


class JobEngineParseError(BaseException):
    """Job Engine: Parse Error."""

    module_name = "JobEngine"
    error_code = -102
    err_type = "Parse Error"


class JobEngineTranspileError(BaseException):
    """Job Engine: Transpile Error."""

    module_name = "JobEngine"
    error_code = -103
    err_type = "Transpile Error"


class JobEngineDriverRunError(BaseException):
    """Job Engine: Driver Run Error."""

    module_name = "JobEngine"
    error_code = -104
    err_type = "Driver Run Error"


class JobEngineCheckWidthError(BaseException):
    """Job Engine: Check QUBO Matrix Bit Width Error."""

    module_name = "JobEngine"
    error_code = -105
    err_type = "Check QUBO Matrix Bit Width Error"


class JobEnginePrecisionTooHighError(BaseException):
    """Job Engine: Precision is too high.

    resulting in subqubo with too few bits for processing.
    """

    module_name = "JobEngine"
    error_code = -106
    err_type = "Precision is too high Error"


class JobEngineQubitLimitExceededError(BaseException):
    """Job Engine: Device Qubit Limit Exceeded Error."""

    module_name = "JobEngine"
    error_code = -107
    err_type = "Device Qubit Limit Exceeded Error"


class JobEngineCheckMatrixError(BaseException):
    """Job Engine: Check Matrix Error."""

    module_name = "JobEngine"
    error_code = -108
    err_type = "Check Matrix Error"


class JobEngineCircuitCuttingError(BaseException):
    """Job Engine: Circuit Cutting Error."""

    module_name = "JobEngine"
    error_code = -109
    err_type = "Circuit Cutting Error"


class JobEngineReconProbError(BaseException):
    """Job Engine: Reconstruct Probability Error."""

    module_name = "JobEngine"
    error_code = -110
    err_type = "Reconstruct Probability Error"


class JobEngineCompileError(BaseException):
    """Job Engine: Compile Error."""

    module_name = "JobEngine"
    error_code = -111
    err_type = "Compile Error"
