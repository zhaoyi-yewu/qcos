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

import pytest

from wy_qcos.common.errors import (
    BaseException,
    GenericException,
    InvalidArguments,
    NotFound,
    WorkFlowError,
    JobEngineDriverInitError,
    JobEngineTranspilerInitError,
    JobEngineParseError,
    JobEngineTranspileError,
    JobEngineDriverRunError,
    JobEngineCheckWidthError,
    JobEnginePrecisionTooHighError,
    JobEngineQubitLimitExceededError,
    JobEngineCheckMatrixError,
    JobEngineCircuitCuttingError,
    JobEngineReconProbError,
    JobEngineCompileError,
)


class TestBaseException:
    """Test BaseException class."""

    def test_base_exception_initialization(self):
        """Test BaseException initialization."""
        message = "Test error message"
        exc = BaseException(message)
        assert exc.message == message
        assert str(exc) == message

    def test_base_exception_get_error_code(self):
        """Test BaseException get_error_code method."""
        exc = BaseException("test")
        with pytest.raises(AttributeError):
            exc.get_error_code()

    def test_base_exception_get_err_msgs(self):
        """Test BaseException get_err_msgs method."""
        exc = BaseException("test message")
        # Should raise AttributeError because BaseException doesn't have
        # module_name, err_type attributes
        with pytest.raises(AttributeError):
            exc.get_err_msgs()


class TestGenericException:
    """Test GenericException class."""

    def test_generic_exception_initialization(self):
        """Test GenericException initialization."""
        message = "Generic error"
        exc = GenericException(message)
        assert exc.message == message
        assert exc.error_code == -10
        assert exc.module_name == "Generic"
        assert exc.err_type == "Error"

    def test_generic_exception_get_error_code(self):
        """Test GenericException get_error_code."""
        exc = GenericException("test")
        assert exc.get_error_code() == -10

    def test_generic_exception_get_err_msgs(self):
        """Test GenericException get_err_msgs."""
        exc = GenericException("test message")
        msgs = exc.get_err_msgs()
        assert "[Generic]" in msgs
        assert "Error" in msgs
        assert "test message" in msgs


class TestInvalidArguments:
    """Test InvalidArguments exception."""

    def test_invalid_arguments_initialization(self):
        """Test InvalidArguments initialization."""
        message = "Invalid argument error"
        exc = InvalidArguments(message)
        assert exc.message == message
        assert exc.error_code == -11
        assert exc.module_name == "Generic"
        assert exc.err_type == "Invalid arguments"

    def test_invalid_arguments_get_error_code(self):
        """Test InvalidArguments get_error_code."""
        exc = InvalidArguments("test")
        assert exc.get_error_code() == -11

    def test_invalid_arguments_get_err_msgs(self):
        """Test InvalidArguments get_err_msgs."""
        exc = InvalidArguments("bad param")
        msgs = exc.get_err_msgs()
        assert "[Generic]" in msgs
        assert "Invalid arguments" in msgs
        assert "bad param" in msgs


class TestNotFound:
    """Test NotFound exception."""

    def test_not_found_initialization(self):
        """Test NotFound initialization."""
        message = "Resource not found"
        exc = NotFound(message)
        assert exc.message == message
        assert exc.error_code == -12
        assert exc.module_name == "Generic"
        assert exc.err_type == "Not Found"

    def test_not_found_get_error_code(self):
        """Test NotFound get_error_code."""
        exc = NotFound("test")
        assert exc.get_error_code() == -12

    def test_not_found_get_err_msgs(self):
        """Test NotFound get_err_msgs."""
        exc = NotFound("resource missing")
        msgs = exc.get_err_msgs()
        assert "[Generic]" in msgs
        assert "Not Found" in msgs
        assert "resource missing" in msgs


class TestWorkFlowError:
    """Test WorkFlowError exception."""

    def test_workflow_error_initialization(self):
        """Test WorkFlowError initialization."""
        message = "Workflow error"
        exc = WorkFlowError(message)
        assert exc.message == message
        assert exc.error_code == -13
        assert exc.module_name == "Workflow"
        assert exc.err_type == "Error"

    def test_workflow_error_get_error_code(self):
        """Test WorkFlowError get_error_code."""
        exc = WorkFlowError("test")
        assert exc.get_error_code() == -13

    def test_workflow_error_get_err_msgs(self):
        """Test WorkFlowError get_err_msgs."""
        exc = WorkFlowError("workflow failed")
        msgs = exc.get_err_msgs()
        assert "[Workflow]" in msgs
        assert "Error" in msgs
        assert "workflow failed" in msgs


class TestJobEngineDriverInitError:
    """Test JobEngineDriverInitError exception."""

    def test_driver_init_error_initialization(self):
        """Test JobEngineDriverInitError initialization."""
        message = "Driver init error"
        exc = JobEngineDriverInitError(message)
        assert exc.message == message
        assert exc.error_code == -100
        assert exc.module_name == "JobEngine"
        assert exc.err_type == "Driver Init Error"

    def test_driver_init_error_get_error_code(self):
        """Test JobEngineDriverInitError get_error_code."""
        exc = JobEngineDriverInitError("test")
        assert exc.get_error_code() == -100

    def test_driver_init_error_get_err_msgs(self):
        """Test JobEngineDriverInitError get_err_msgs."""
        exc = JobEngineDriverInitError("failed to init driver")
        msgs = exc.get_err_msgs()
        assert "[JobEngine]" in msgs
        assert "Driver Init Error" in msgs
        assert "failed to init driver" in msgs


class TestJobEngineTranspilerInitError:
    """Test JobEngineTranspilerInitError exception."""

    def test_transpiler_init_error_initialization(self):
        """Test JobEngineTranspilerInitError initialization."""
        message = "Transpiler init error"
        exc = JobEngineTranspilerInitError(message)
        assert exc.message == message
        assert exc.error_code == -101
        assert exc.module_name == "JobEngine"
        assert exc.err_type == "Transpiler Init Error"

    def test_transpiler_init_error_get_error_code(self):
        """Test JobEngineTranspilerInitError get_error_code."""
        exc = JobEngineTranspilerInitError("test")
        assert exc.get_error_code() == -101


class TestJobEngineParseError:
    """Test JobEngineParseError exception."""

    def test_parse_error_initialization(self):
        """Test JobEngineParseError initialization."""
        message = "Parse error"
        exc = JobEngineParseError(message)
        assert exc.message == message
        assert exc.error_code == -102
        assert exc.module_name == "JobEngine"
        assert exc.err_type == "Parse Error"

    def test_parse_error_get_error_code(self):
        """Test JobEngineParseError get_error_code."""
        exc = JobEngineParseError("test")
        assert exc.get_error_code() == -102


class TestJobEngineTranspileError:
    """Test JobEngineTranspileError exception."""

    def test_transpile_error_initialization(self):
        """Test JobEngineTranspileError initialization."""
        message = "Transpile error"
        exc = JobEngineTranspileError(message)
        assert exc.message == message
        assert exc.error_code == -103
        assert exc.module_name == "JobEngine"
        assert exc.err_type == "Transpile Error"

    def test_transpile_error_get_error_code(self):
        """Test JobEngineTranspileError get_error_code."""
        exc = JobEngineTranspileError("test")
        assert exc.get_error_code() == -103


class TestJobEngineDriverRunError:
    """Test JobEngineDriverRunError exception."""

    def test_driver_run_error_initialization(self):
        """Test JobEngineDriverRunError initialization."""
        message = "Driver run error"
        exc = JobEngineDriverRunError(message)
        assert exc.message == message
        assert exc.error_code == -104
        assert exc.module_name == "JobEngine"
        assert exc.err_type == "Driver Run Error"

    def test_driver_run_error_get_error_code(self):
        """Test JobEngineDriverRunError get_error_code."""
        exc = JobEngineDriverRunError("test")
        assert exc.get_error_code() == -104


class TestJobEngineCheckWidthError:
    """Test JobEngineCheckWidthError exception."""

    def test_check_width_error_initialization(self):
        """Test JobEngineCheckWidthError initialization."""
        message = "Check width error"
        exc = JobEngineCheckWidthError(message)
        assert exc.message == message
        assert exc.error_code == -105
        assert exc.module_name == "JobEngine"
        assert exc.err_type == "Check QUBO Matrix Bit Width Error"

    def test_check_width_error_get_error_code(self):
        """Test JobEngineCheckWidthError get_error_code."""
        exc = JobEngineCheckWidthError("test")
        assert exc.get_error_code() == -105


class TestJobEnginePrecisionTooHighError:
    """Test JobEnginePrecisionTooHighError exception."""

    def test_precision_too_high_error_initialization(self):
        """Test JobEnginePrecisionTooHighError initialization."""
        message = "Precision too high"
        exc = JobEnginePrecisionTooHighError(message)
        assert exc.message == message
        assert exc.error_code == -106
        assert exc.module_name == "JobEngine"
        assert exc.err_type == "Precision is too high Error"

    def test_precision_too_high_error_get_error_code(self):
        """Test JobEnginePrecisionTooHighError get_error_code."""
        exc = JobEnginePrecisionTooHighError("test")
        assert exc.get_error_code() == -106


class TestJobEngineQubitLimitExceededError:
    """Test JobEngineQubitLimitExceededError exception."""

    def test_qubit_limit_exceeded_error_initialization(self):
        """Test JobEngineQubitLimitExceededError initialization."""
        message = "Qubit limit exceeded"
        exc = JobEngineQubitLimitExceededError(message)
        assert exc.message == message
        assert exc.error_code == -107
        assert exc.module_name == "JobEngine"
        assert exc.err_type == "Device Qubit Limit Exceeded Error"

    def test_qubit_limit_exceeded_error_get_error_code(self):
        """Test JobEngineQubitLimitExceededError get_error_code."""
        exc = JobEngineQubitLimitExceededError("test")
        assert exc.get_error_code() == -107


class TestJobEngineCheckMatrixError:
    """Test JobEngineCheckMatrixError exception."""

    def test_check_matrix_error_initialization(self):
        """Test JobEngineCheckMatrixError initialization."""
        message = "Check matrix error"
        exc = JobEngineCheckMatrixError(message)
        assert exc.message == message
        assert exc.error_code == -108
        assert exc.module_name == "JobEngine"
        assert exc.err_type == "Check Matrix Error"

    def test_check_matrix_error_get_error_code(self):
        """Test JobEngineCheckMatrixError get_error_code."""
        exc = JobEngineCheckMatrixError("test")
        assert exc.get_error_code() == -108


class TestJobEngineCircuitCuttingError:
    """Test JobEngineCircuitCuttingError exception."""

    def test_circuit_cutting_error_initialization(self):
        """Test JobEngineCircuitCuttingError initialization."""
        message = "Circuit cutting error"
        exc = JobEngineCircuitCuttingError(message)
        assert exc.message == message
        assert exc.error_code == -109
        assert exc.module_name == "JobEngine"
        assert exc.err_type == "Circuit Cutting Error"

    def test_circuit_cutting_error_get_error_code(self):
        """Test JobEngineCircuitCuttingError get_error_code."""
        exc = JobEngineCircuitCuttingError("test")
        assert exc.get_error_code() == -109


class TestJobEngineReconProbError:
    """Test JobEngineReconProbError exception."""

    def test_recon_prob_error_initialization(self):
        """Test JobEngineReconProbError initialization."""
        message = "Reconstruct probability error"
        exc = JobEngineReconProbError(message)
        assert exc.message == message
        assert exc.error_code == -110
        assert exc.module_name == "JobEngine"
        assert exc.err_type == "Reconstruct Probability Error"

    def test_recon_prob_error_get_error_code(self):
        """Test JobEngineReconProbError get_error_code."""
        exc = JobEngineReconProbError("test")
        assert exc.get_error_code() == -110


class TestJobEngineCompileError:
    """Test JobEngineCompileError exception."""

    def test_compile_error_initialization(self):
        """Test JobEngineCompileError initialization."""
        message = "Compile error"
        exc = JobEngineCompileError(message)
        assert exc.message == message
        assert exc.error_code == -111
        assert exc.module_name == "JobEngine"
        assert exc.err_type == "Compile Error"

    def test_compile_error_get_error_code(self):
        """Test JobEngineCompileError get_error_code."""
        exc = JobEngineCompileError("test")
        assert exc.get_error_code() == -111

    def test_compile_error_get_err_msgs(self):
        """Test JobEngineCompileError get_err_msgs."""
        exc = JobEngineCompileError("compilation failed")
        msgs = exc.get_err_msgs()
        assert "[JobEngine]" in msgs
        assert "Compile Error" in msgs
        assert "compilation failed" in msgs
