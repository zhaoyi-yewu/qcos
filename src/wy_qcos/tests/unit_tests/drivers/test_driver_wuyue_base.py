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

import json
import pytest

from unittest.mock import patch, MagicMock

from wy_qcos.common.constant import HttpCode
from wy_qcos.common.library import Library, _s
from wy_qcos.drivers.driver_wuyue_base import DriverWuyueBase


driver_wuyue_base = DriverWuyueBase()

# ruff: noqa: S105
driver_wuyue_base.password_secret = _s("test_password_secret")
driver_wuyue_base.password_pri_key = _s(
    "MIICeAIBADANBgkqhkiG9w0BAQEFAASCAmIwggJeAgEAAoGBAL+S1b9o7RbU0zhBdvV"
    "NijpIdCNMy3hx+G+H1rflVnhB0rE/4eNkTS5v3iDNMhhqBZKjAslyBcq6FQS55EgShH"
    "UeK4rXUPI8k0yfonxnemT/t7wI9nCgI9lb5HUffzj4B9RRlhmeqTuW8w9GEBoNQZxMD"
    "6sCn1zghWskrZrNhsjbAgMBAAECgYEAuWle0Mu3s8I1z5uki5QJdZFMPiIER8VeomtB"
    "SGiBgRCL35spgBBClvAUd4DBvFlYnWyBtQBTVLs2voU/yPWLFbZgKhRMBY1KbD8lgV6"
    "vVfMnZvLxsvt6HGAFNauOZ7JwnwaaLSNFSR+kApjSIh5rzrPufjQ5U+1TlQiebdXAFm"
    "kCQQDiWHedCvlrIAC7txgApzodRu6TjpnCk3+r+21FD75/uQDV3OcI6D8A+UkkP22Dm"
    "6ZR5FsHZgriN9s144H+omcHAkEA2KwhPBjh3C6mW/OPGhPLJwf7pCoJRT6Y+KME76kY"
    "bpBO99aEJqH8B3e7mEHGeZGyD3E0FODwbJvshqy4k68mjQJBAKlBfFiL700jBklYtfM"
    "vGa7w7tCajvJId+00O1asWkiKIEzMPluTyCFDSGV5pLwIdYvBViynKrZVDHA0q22tJZ"
    "sCQE98RezwC9tkWa8d2H9uh3ZYHV6J9UCryB5eX280DzxwQCf3UB+ECRsMN4uRhagPZ"
    "Mz5cGvAYTLWuJxnPIchF/kCQQDYtMa3+Yys8GjTe6gvkd6rQ7b6X3pTW2em8KfirlWe"
    "VAZtYs/MxYJZcuFy26lFA+DtO7Rg2GzhIKkUrzvqvgkQ"
)
driver_wuyue_base.password_pub_key = _s(
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC/ktW/aO0W1NM4QXb1TYo6SHQjTMt"
    "4cfhvh9a35VZ4QdKxP+HjZE0ub94gzTIYagWSowLJcgXKuhUEueRIEoR1HiuK11DyPJ"
    "NMn6J8Z3pk/7e8CPZwoCPZW+R1H384+AfUUZYZnqk7lvMPRhAaDUGcTA+rAp9c4IVrJ"
    "K2azYbI2wIDAQAB"
)


@pytest.mark.driver
class TestDriverWuyueBase:
    """Test suite for DriverWuyueBase class."""

    @pytest.mark.smoke
    @patch.object(DriverWuyueBase, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_submit_tasks_success(
        self, mock_call_http_api, mock_decrypt_by_private_key
    ):
        """Test submit_tasks with successful response."""
        mock_response = {"code": 1, "msg": "Success", "data": "encrypted_data"}
        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )
        mock_decrypt_by_private_key.return_value = mock_response
        success, err_msg = driver_wuyue_base.submit_tasks("test_data")
        assert success is True
        assert err_msg == ""

    @patch.object(DriverWuyueBase, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_submit_tasks_failure(
        self, mock_call_http_api, mock_decrypt_by_private_key
    ):
        """Test submit_tasks with failed response."""
        mock_response = {"code": 0, "msg": "Err", "data": "encrypted_data"}
        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )

        mock_decrypt_by_private_key.return_value = mock_response
        success, err_msg = driver_wuyue_base.submit_tasks("test_data")
        assert success is False
        assert err_msg == "Err"

    @patch.object(Library, "call_http_api")
    def test_submit_tasks_http_error(self, mock_call_http_api):
        """Test submit_tasks with HTTP error."""
        mock_call_http_api.return_value = (
            HttpCode.TIMEOUT_ERROR,
            "Timeout",
            None,
            MagicMock(),
        )

        success, err_msg = driver_wuyue_base.submit_tasks("test_data")
        assert success is False
        assert err_msg == "Timeout"

    def test_prepare_sign(self):
        """Test prepare_sign method."""
        test_data = {
            "key1": "value1",
            "key2": ["list1", "list2"],
            "key3": None,
        }

        sign = driver_wuyue_base.prepare_sign(test_data)
        assert len(sign) == 32
        assert sign == "f72fa9e9e1ba2a17827baf279be2b63b"

    def test_decrypt_by_private_key(self):
        """Test decrypt_by_private_key method."""
        test_data = {"test": "data"}
        encrypted = driver_wuyue_base.encrypt_by_public_key(test_data)

        decrypted = driver_wuyue_base.decrypt_by_private_key(encrypted)
        assert decrypted == test_data

    def test_prepare_submit_data(self):
        """Test prepare_submit_data method."""
        job_id = "test_job_id"
        src_code = "test_src_code"
        shots = 100
        data_index = "1"

        submit_data = driver_wuyue_base.prepare_submit_data(
            job_id, src_code, shots, data_index
        )
        assert len(submit_data) == 344

    def test_validate_driver_configs_invalid_port(self):
        """Test validate_driver_configs with invalid port."""
        test_configs = {
            "ip_address": "100.100.100.2",
            "port": "invalid port",
            "client_id": "test_client_id",
            "eng_code": "test_eng_code",
            "password_secret": "test_password_secret",
            "password_pub_key": "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC/ktW/a"
            "O0W1NM4QXb1TYo6SHQjTMt4cfhvh9a35VZ4QdKxP+HjZE"
            "0ub94gzTIYagWSowLJcgXKuhUEueRIEoR1HiuK11DyPJN"
            "Mn6J8Z3pk/7e8CPZwoCPZW+R1H384+AfUUZYZnqk7lvMP"
            "RhAaDUGcTA+rAp9c4IVrJK2azYbI2wIDAQAB",
            "password_pri_key": "",
        }

        success, err_msg = driver_wuyue_base.validate_driver_configs(
            test_configs
        )
        assert success is False
        assert err_msg is not None

    def test_validate_driver_configs_success(self):
        """Test validate_driver_configs with valid configs."""
        test_configs = {
            "ip_address": "100.100.100.2",
            "port": 12345,
            "client_id": "test_client_id",
            "eng_code": "test_eng_code",
            "password_secret": "test_password_secret",
            "password_pub_key": "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC/ktW/a"
            "O0W1NM4QXb1TYo6SHQjTMt4cfhvh9a35VZ4QdKxP+HjZE"
            "0ub94gzTIYagWSowLJcgXKuhUEueRIEoR1HiuK11DyPJN"
            "Mn6J8Z3pk/7e8CPZwoCPZW+R1H384+AfUUZYZnqk7lvMP"
            "RhAaDUGcTA+rAp9c4IVrJK2azYbI2wIDAQAB",
            "password_pri_key": "",
            "max_job_wait_time": 10000,
            "job_query_interval": 10,
        }

        success, err_msg = driver_wuyue_base.validate_driver_configs(
            test_configs
        )
        assert success is True
        assert err_msg is None
        assert driver_wuyue_base.ip_addr == "100.100.100.2"
        assert driver_wuyue_base.port == 12345
        assert driver_wuyue_base.client_id == "test_client_id"
        assert driver_wuyue_base.eng_code == "test_eng_code"
        assert driver_wuyue_base.password_secret == _s("test_password_secret")
        assert driver_wuyue_base.password_pub_key == _s(
            "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC/ktW/aO0W1NM4QXb1TYo6"
            "SHQjTMt4cfhvh9a35VZ4QdKxP+HjZE0ub94gzTIYagWSowLJcgXKuhUEueRI"
            "EoR1HiuK11DyPJNMn6J8Z3pk/7e8CPZwoCPZW+R1H384+AfUUZYZnqk7lvMP"
            "RhAaDUGcTA+rAp9c4IVrJK2azYbI2wIDAQAB"
        )
        assert driver_wuyue_base.password_pri_key == ""
        assert driver_wuyue_base.max_job_wait_time == 10000
        assert driver_wuyue_base.job_query_interval == 10

    def test_validate_driver_configs_missing_required_fields(self):
        """Test validate_driver_configs with missing required fields."""
        test_configs = {
            "ip_address": "test_ip",
            # Missing port
            "client_id": "test_client",
            # Missing eng_code
            "password_secret": "test_password_secret",
            # Missing pwd_pub_key
            # Missing pwd_pri_key
        }

        success, err_msg = driver_wuyue_base.validate_driver_configs(
            test_configs
        )
        assert success is False
        assert err_msg is not None

    @patch.object(DriverWuyueBase, "decrypt_by_private_key")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(Library, "call_http_api")
    def test_run_task_failed(
        self,
        mock_call_http_api,
        mock_loop_with_timeout,
        mock_decrypt_by_private_key,
    ):
        """Test run method when task fails."""
        # Setup mock for submit_tasks
        mock_response = {"code": 1, "msg": "Success", "data": "encrypted_data"}

        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )

        # Setup mock for loop_with_timeout to return failure status
        mock_loop_with_timeout.return_value = (
            False,
            "Timeout error",
            {"task_status": driver_wuyue_base.task_status_failed},
        )

        mock_decrypt_by_private_key.return_value = mock_response
        job_id = "test_job"
        num_qubits = 2
        data = {
            "index": "test_index",
            "source_code": "test_code",
            "transpile_results": [],
        }
        data_type = "qasm2"
        shots = 1

        exception_raised = False
        exception_msg = ""

        try:
            driver_wuyue_base.run(job_id, num_qubits, data, data_type, shots)
        except ValueError as e:
            exception_raised = True
            exception_msg = str(e)

        assert exception_raised is True
        assert (
            exception_msg
            == "Failed to wait for task [test_job]: Timeout error"
        )

    @patch.object(Library, "loop_with_timeout")
    @patch.object(Library, "call_http_api")
    def test_run_http_error(self, mock_call_http_api, mock_loop_with_timeout):
        """Test run method with HTTP error during submission."""
        # Setup mock for submit_tasks to return HTTP error
        mock_call_http_api.return_value = (
            HttpCode.NOT_IMPLEMENTED_ERROR,
            "not implement error",
            None,
            MagicMock(),
        )

        job_id = "test_job"
        num_qubits = 2
        data = {
            "index": "test_index",
            "source_code": "test_code",
            "transpile_results": [],
        }
        data_type = "qasm2"
        shots = 1

        exception_raised = False
        exception_msg = ""

        try:
            driver_wuyue_base.run(job_id, num_qubits, data, data_type, shots)
        except ValueError as e:
            exception_raised = True
            exception_msg = str(e)

        assert exception_raised is True
        assert exception_msg == "Failed to submit task: not implement error"

    @patch.object(DriverWuyueBase, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_check_task_status_success(
        self, mock_call_http_api, mock_decrypt_by_private_key
    ):
        """Test check_task_status with successful status check."""
        mock_response = {
            "code": 1,
            "msg": "Success",
            "data": [
                {
                    "taskStatus": driver_wuyue_base.task_status_completed,
                    "outData": {"lineResult": "test_result"},
                }
            ],
        }
        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )
        mock_decrypt_by_private_key.return_value = mock_response
        success, err_msg, task_status = driver_wuyue_base.check_task_status(
            "test_task_id", [driver_wuyue_base.task_status_completed]
        )
        assert success is True
        assert err_msg == ""
        assert task_status == driver_wuyue_base.task_status_completed

    @patch.object(DriverWuyueBase, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_check_task_status_failure(
        self, mock_call_http_api, mock_decrypt_by_private_key
    ):
        """Test check_task_status with failed status check."""
        mock_response = {
            "code": 0,
            "msg": "Error",
            "data": [{"taskStatus": driver_wuyue_base.task_status_queuing}],
        }
        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )
        mock_decrypt_by_private_key.return_value = mock_response
        success, err_msg, task_status = driver_wuyue_base.check_task_status(
            "test_task_id", [driver_wuyue_base.task_status_completed]
        )
        assert success is False
        assert err_msg is not None
        assert task_status == driver_wuyue_base.task_status_failed

    @patch.object(DriverWuyueBase, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_get_task_results_success(
        self, mock_call_http_api, mock_decrypt_by_private_key
    ):
        """Test get_task_results with successful result retrieval."""
        test_result = {"00": 10, "01": 11, "10": 9, "11": 0}
        mock_response = {
            "code": 1,
            "msg": "Success",
            "data": [
                {
                    "taskStatus": driver_wuyue_base.task_status_completed,
                    "outData": {
                        "lineResult": test_result,
                        "grid": "grid_info",
                        "optimization": "optimization",
                    },
                    "execEndTime": 12345,
                    "execStartTime": 12333,
                    "timeConsume": "2.00",
                }
            ],
        }
        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )

        mock_decrypt_by_private_key.return_value = mock_response
        success, err_msg, results, machine_time_info = (
            driver_wuyue_base.get_task_results("test_task_id")
        )
        assert success is True
        assert err_msg == ""
        assert len(results) == 3
        assert results["line_results"]["00"] == 10
        assert results["line_results"]["01"] == 11
        assert results["line_results"]["10"] == 9
        assert results["grid_info"] == "grid_info"
        assert results["optimized_circuit"] == "optimization"
        assert machine_time_info["time_consume"] == "2.00"
        assert machine_time_info["exec_end_time"] == 12345
        assert machine_time_info["exec_start_time"] == 12333

    @patch.object(Library, "call_http_api")
    def test_get_task_results_http_error(self, mock_call_http_api):
        """Test get_task_results with HTTP error."""
        mock_call_http_api.return_value = (
            HttpCode.CONFLICT_ERROR,
            "conflict error",
            None,
            MagicMock(),
        )

        exception_raised = False
        exception_msg = ""
        try:
            driver_wuyue_base.get_task_results("test_task_id")
        except ValueError as e:
            exception_raised = True
            exception_msg = str(e)

        assert exception_raised is True
        assert "conflict error" in exception_msg

    def test_init_driver(self):
        """Test init_driver method."""
        driver_wuyue_base.init_driver()

    def test_close_driver(self):
        """Test close_driver method."""
        driver_wuyue_base.close_driver()

    def test_fetch_cfg(self):
        """Test fetch_configs method."""
        driver_wuyue_base.fetch_configs()

    def test_cancel(self):
        """Test cancel method."""
        driver_wuyue_base.cancel("123")

    def test_format_item(self):
        """Test format_item method."""
        test_item = "test_string"
        result = driver_wuyue_base.format_item(test_item)
        assert result == '"test_string"'

        test_item = 123
        result = driver_wuyue_base.format_item(test_item)
        assert result == "123"

    def test_prepare_query_task_data(self):
        """Test prepare_query_task_data method."""
        task_id = "test_task_id"
        driver_wuyue_base.client_id = "test_client_id"
        driver_wuyue_base.eng_code = "test_eng_code"
        query_data = driver_wuyue_base.prepare_query_task_data(task_id)
        assert len(query_data) == 344

    def test_convert_code_with_valid_transpile_results(self):
        """Test convert_code with valid transpile results."""
        num_qubits = 2
        src_code = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            "qreg q[2];\nh q[0];\ncx q[0],q[1];"
        )
        transpile_results = []

        result = driver_wuyue_base.convert_code(
            num_qubits, src_code, transpile_results
        )
        assert result == src_code

    def test_convert_code_with_invalid_transpile_results(self):
        """Test convert_code with invalid transpile results."""
        num_qubits = 2
        src_code = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            "qreg q[2];\nh q[0];\ncx q[0],q[1];"
        )
        transpile_results = [
            "invalid",
            "operations",
        ]  # Non-BaseOperation items

        result = driver_wuyue_base.convert_code(
            num_qubits, src_code, transpile_results
        )
        assert result == src_code

    def test_convert_code_with_non_list_transpile_results(self):
        """Test convert_code with non-list transpile results."""
        num_qubits = 2
        src_code = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            "qreg q[2];\nh q[0];\ncx q[0],q[1];"
        )
        transpile_results = "not a list"  # Non-list input

        result = driver_wuyue_base.convert_code(
            num_qubits, src_code, transpile_results
        )
        assert result == src_code

    def test_convert_code_with_valid_base_operations(self):
        """Test convert_code with valid BaseOperation instances."""
        num_qubits = 2
        src_code = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            "qreg q[2];\nh q[0];\ncx q[0],q[1];"
        )
        transpile_results = []  # Empty list of BaseOperation instances

        result = driver_wuyue_base.convert_code(
            num_qubits, src_code, transpile_results
        )
        assert result == src_code

    def test_convert_code_edge_case_empty_qasm(self):
        """Test convert_code with empty QASM code."""
        num_qubits = 0
        src_code = ""
        transpile_results = []

        result = driver_wuyue_base.convert_code(
            num_qubits, src_code, transpile_results
        )
        assert result == src_code

    def test_convert_code_edge_case_none_transpile_results(self):
        """Test convert_code with None transpile results."""
        num_qubits = 2
        src_code = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            "qreg q[2];\nh q[0];\ncx q[0],q[1];"
        )
        transpile_results = None

        result = driver_wuyue_base.convert_code(
            num_qubits, src_code, transpile_results
        )
        assert result == src_code

    @patch.object(DriverWuyueBase, "decrypt_by_private_key")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(Library, "call_http_api")
    def test_run_success(
        self,
        mock_call_http_api,
        mock_loop_with_timeout,
        mock_decrypt_by_private_key,
    ):
        """Test run method with successful task execution."""
        # Setup mock for submit_tasks
        mock_response = {"code": 1, "msg": "Success", "data": "encrypted_data"}

        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )

        # Setup mock for loop_with_timeout
        mock_loop_with_timeout.return_value = (
            True,
            None,
            driver_wuyue_base.task_status_completed,
        )

        # Setup mock for get_task_results
        mock_get_results = MagicMock(
            return_value=(
                True,
                None,
                {"result": "test_result"},
                {"exec_end_time": 12345},
            )
        )
        mock_decrypt_by_private_key.return_value = mock_response
        driver_wuyue_base.get_task_results = mock_get_results
        job_id = "test_job"
        num_qubits = 2
        data = {
            "index": "test_index",
            "source_code": "test_code",
            "transpile_results": [],
        }
        data_type = "qasm2"
        shots = 100

        exception_raised = False
        exception_msg = None
        try:
            driver_wuyue_base.run(job_id, num_qubits, data, data_type, shots)
        except ValueError as e:
            exception_raised = True
            exception_msg = str(e)
            print(exception_msg)

        assert exception_raised is False
        assert exception_msg is None

    @patch.object(DriverWuyueBase, "get_device_info")
    def test_fetch_running_info_success(self, mock_get_device_info):
        driver = DriverWuyueBase()
        mock_get_device_info.return_value = (
            True,
            None,
            {
                "horizontalRelaxationTime": 132,
                "doubleFidelity": 0.9,
                "singleFidelity": 0.95,
                "tweezersNum": 200,
            },
        )
        result = driver.fetch_running_info()
        assert "details" in result
        assert result["details"]["horizontalRelaxationTime"] == 132
        assert result["details"]["doubleFidelity"] == 0.9
        assert result["details"]["singleFidelity"] == 0.95
        assert result["details"]["tweezersNum"] == 200

    @patch.object(DriverWuyueBase, "get_device_info")
    def test_fetch_running_info_exception(self, mock_get_device_info):
        driver = DriverWuyueBase()
        mock_get_device_info.return_value = (False, "test error", None)
        result = driver.fetch_running_info()
        assert result["details"] == {}

    @patch.object(DriverWuyueBase, "update_device_info")
    @patch.object(DriverWuyueBase, "update_device_info_schema")
    @patch.object(DriverWuyueBase, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_get_device_info(
        self,
        mock_call_http_api,
        mock_decrypt_by_private_key,
        mock_update_device_info_schema,
        mock_update_device_info,
    ):
        """Test get_device_info method with successful response."""
        mock_schema = {
            "horizontalRelaxationTime": int,
            "tweezersNum": int,
            "singleFidelity": float,
            "doubleFidelity": float,
        }
        mock_update_device_info_schema.return_value = mock_schema

        mock_data = {
            "horizontalRelaxationTime": 132,
            "tweezersNum": 200,
            "singleFidelity": 0.95,
            "doubleFidelity": 0.9,
        }
        mock_response = {"code": 1, "msg": "Success", "data": mock_data}

        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )
        mock_decrypt_by_private_key.return_value = mock_response

        mock_device_info = {
            "horizontalRelaxationTime": 132,
            "tweezersNum": 200,
            "singleFidelity": 0.95,
            "doubleFidelity": 0.9,
        }
        mock_update_device_info.return_value = mock_device_info

        success, err_msg, device_info = driver_wuyue_base.get_device_info()
        assert success is True
        assert err_msg == ""
        assert device_info["horizontalRelaxationTime"] == 132
        assert device_info["tweezersNum"] == 200
        assert device_info["singleFidelity"] == 0.95
        assert device_info["doubleFidelity"] == 0.9

    def test_construct_machine_time_info(self):
        driver = DriverWuyueBase()
        data = {
            "execStartTime": 12345,
            "execEndTime": None,
            "timeConsume": "2.00",
        }
        machine_time_info = driver.construct_machine_time_info(data)
        assert machine_time_info["exec_start_time"] == 12345
        assert machine_time_info["exec_end_time"] is None
        assert machine_time_info["time_consume"] == "2.00"
