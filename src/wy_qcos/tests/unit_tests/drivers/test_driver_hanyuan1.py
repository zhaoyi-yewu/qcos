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
import requests
from unittest.mock import patch, MagicMock

from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos.common.library import Library
from wy_qcos.drivers.cascoldatom.driver_hanyuan1 import DriverHanyuan1


driver_hanyuan1 = DriverHanyuan1()
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 5
data = {"index": 0, "source_code": None, "transpile_results": []}
data_type = DriverHanyuan1.DATA_TYPE_GATE_SEQUENCE
shots = 1024


@pytest.mark.driver
class TestDriverHanyuan1:
    def test_init(self):
        assert driver_hanyuan1.version == "0.0.1"
        assert driver_hanyuan1.alias_name == "中科酷原-汉原1 中性原子驱动"
        assert driver_hanyuan1.description == "中科酷原-汉原1 中性原子驱动"
        assert driver_hanyuan1.transpiler == Constant.TRANSPILER_CMSS
        assert driver_hanyuan1.tech_type == Constant.TECH_TYPE_NEUTRAL_ATOM
        assert driver_hanyuan1.supported_basis_gates == [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
        ]
        assert driver_hanyuan1.supported_transpilers == [
            Constant.TRANSPILER_CMSS
        ]
        assert driver_hanyuan1.enable_circuit_aggregation is True
        assert driver_hanyuan1.max_qubits == 10
        assert driver_hanyuan1.use_zmq is False

    @patch.object(DriverHanyuan1, "init_zerorpc_client")
    @patch.object(DriverHanyuan1, "init_base_url")
    @patch.object(DriverHanyuan1, "set_device_status")
    def test_init_driver_with_zmq(
        self, mock_set_status, mock_init_url, mock_init_zmq
    ):
        driver = DriverHanyuan1()
        driver.set_configs({
            "use_zmq": True,
            "zmq_ip_address": "127.0.0.1",
            "zmq_port": 18403,
        })
        driver.init_driver()
        mock_init_zmq.assert_called_once()
        mock_set_status.assert_called_once()

    @patch.object(DriverHanyuan1, "init_base_url")
    @patch.object(DriverHanyuan1, "set_device_status")
    def test_init_driver_without_zmq(self, mock_set_status, mock_init_url):
        driver = DriverHanyuan1()
        driver.set_configs({
            "use_zmq": False,
            "ip_address": "127.0.0.1",
            "port": 18402,
        })
        driver.init_driver()
        mock_init_url.assert_called_once()
        mock_set_status.assert_called_once()

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs_success(self, mock_validate):
        driver = DriverHanyuan1()
        configs = {
            "ip_address": "127.0.0.1",
            "port": 18402,
            "callback_baseurl": "http://test.com",
            "transpiler": {
                "qpu_configs": {
                    "qubits": 10,
                    "storage_area": ["q0", "q1"],
                    "operate_area": ["q0"],
                    "coupler_map": {"q0": ["q1"]},
                    "readout_error": {"q0": 0.01},
                }
            },
        }
        mock_validate.return_value = (True, [])
        success, err_msg = driver.validate_driver_configs(configs)
        assert success is True
        assert err_msg is None

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs_failure(self, mock_validate):
        driver = DriverHanyuan1()
        configs = {}
        mock_validate.return_value = (False, ["error"])
        success, err_msg = driver.validate_driver_configs(configs)
        assert success is False
        assert "error" in err_msg

    def test_close_driver(self):
        driver = DriverHanyuan1()
        mock_client = MagicMock()
        driver.zerorpc_clients = [mock_client]
        driver.close_driver()
        mock_client.close.assert_called_once()
        assert driver.zerorpc_clients == []

    def test_close_driver_with_exception(self):
        driver = DriverHanyuan1()
        mock_client = MagicMock()
        mock_client.close.side_effect = Exception("test")
        driver.zerorpc_clients = [mock_client]
        driver.close_driver()
        assert driver.zerorpc_clients == []

    def test_get_formatted_timestamp(self):
        driver = DriverHanyuan1()
        timestamp = driver.get_formatted_timestamp()
        assert isinstance(timestamp, str)
        assert len(timestamp) > 0

    @patch.object(DriverHanyuan1, "_execute_task_workflow")
    @patch.object(Library, "create_uuid")
    def test_fetch_configs(self, mock_uuid, mock_workflow):
        driver = DriverHanyuan1()
        mock_uuid.return_value = "test-uuid"
        mock_workflow.return_value = {"test": "config"}
        result = driver.fetch_configs()
        assert "qpu_configs" in result
        mock_workflow.assert_called_once()

    @patch.object(DriverHanyuan1, "_get_task_status")
    @patch("time.sleep")
    @patch("time.time")
    def test_check_task_status_completed(
        self, mock_time, mock_sleep, mock_get_status
    ):
        driver = DriverHanyuan1()
        mock_time.side_effect = [0, 1]
        mock_get_status.return_value = driver.task_status_completed
        success, err_msg = driver._check_task_status(
            job_id, "test", 0, timeout=10, interval=1
        )
        assert success is True
        assert err_msg is None

    @patch.object(DriverHanyuan1, "_get_task_status")
    @patch("time.sleep")
    @patch("time.time")
    def test_check_task_status_unknown(
        self, mock_time, mock_sleep, mock_get_status
    ):
        driver = DriverHanyuan1()
        mock_time.side_effect = [0, 1]
        mock_get_status.return_value = driver.task_status_unknown
        success, err_msg = driver._check_task_status(
            job_id, "test", 0, timeout=10, interval=1
        )
        assert success is False
        assert err_msg is not None

    @patch.object(DriverHanyuan1, "_get_task_status")
    @patch("time.sleep")
    @patch("time.time")
    def test_check_task_status_timeout(
        self, mock_time, mock_sleep, mock_get_status
    ):
        driver = DriverHanyuan1()
        mock_time.side_effect = [0, 2000]
        mock_get_status.return_value = driver.task_status_running
        success, err_msg = driver._check_task_status(
            job_id, "test", 0, timeout=10, interval=1
        )
        assert success is False
        assert "timed out" in err_msg

    @patch.object(DriverHanyuan1, "get_task_results")
    @patch.object(DriverHanyuan1, "_check_task_status")
    @patch.object(DriverHanyuan1, "submit_task")
    def test_execute_task_workflow_success(
        self, mock_submit, mock_check, mock_get_results
    ):
        driver = DriverHanyuan1()
        mock_submit.return_value = (True, None)
        mock_check.return_value = (True, None)
        mock_get_results.return_value = (True, None, {"result": "test"})
        result = driver._execute_task_workflow(job_id, "test")
        assert result == {"result": "test"}

    @patch.object(DriverHanyuan1, "submit_task")
    def test_execute_task_workflow_submit_failure(self, mock_submit):
        driver = DriverHanyuan1()
        mock_submit.return_value = (False, "submit error")
        with pytest.raises(ValueError) as exc_info:
            driver._execute_task_workflow(job_id, "test")
        assert "Failed to submit task" in str(exc_info.value)

    @patch.object(DriverHanyuan1, "_execute_task_workflow")
    def test_run(self, mock_workflow):
        driver = DriverHanyuan1()
        mock_workflow.return_value = {"result": "test"}
        driver.run(job_id, num_qubits, data, data_type, shots)
        mock_workflow.assert_called_once()

    @patch.object(DriverHanyuan1, "set_task")
    def test_cancel_success(self, mock_set_task):
        driver = DriverHanyuan1()
        mock_set_task.return_value = (True, None, {})
        success, err_msg = driver.cancel(job_id)
        assert success is True
        assert err_msg is None

    @patch.object(DriverHanyuan1, "set_task")
    def test_cancel_failure(self, mock_set_task):
        driver = DriverHanyuan1()
        mock_set_task.return_value = (False, "error", None)
        success, err_msg = driver.cancel(job_id)
        assert success is False
        assert err_msg == "error"

    @patch.object(DriverHanyuan1, "set_task")
    def test_cancel_exception(self, mock_set_task):
        driver = DriverHanyuan1()
        mock_set_task.side_effect = Exception("test error")
        success, err_msg = driver.cancel(job_id)
        assert success is False
        assert "test error" in err_msg

    def test_init_base_url(self):
        driver = DriverHanyuan1()
        driver.init_base_url("127.0.0.1", 18402)
        assert driver.server_host == "127.0.0.1"
        assert driver.server_port == 18402
        assert "http://127.0.0.1:18402/api/v1/job" in driver.base_url

    @patch("zerorpc.Client")
    def test_init_zerorpc_client(self, mock_client_class):
        driver = DriverHanyuan1()
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        driver.init_zerorpc_client("127.0.0.1", 18403, pool_size=2)
        assert driver.server_host == "127.0.0.1"
        assert driver.server_port == 18403
        assert len(driver.zerorpc_clients) == 2
        assert mock_client.connect.call_count == 2

    def test_get_zerorpc_client(self):
        driver = DriverHanyuan1()
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        driver.zerorpc_clients = [mock_client1, mock_client2]
        client = driver._get_zerorpc_client()
        assert client in [mock_client1, mock_client2]

    def test_get_zerorpc_client_empty(self):
        driver = DriverHanyuan1()
        driver.zerorpc_clients = []
        client = driver._get_zerorpc_client()
        assert client is None

    def test_print_api_response(self):
        driver = DriverHanyuan1()
        driver.verbose = True
        driver.print_api_response(200, "OK", "text", {"result": "test"})
        # Should not raise exception

    @patch.object(DriverHanyuan1, "_get_zerorpc_client")
    def test_call_zerorpc_rpc_success(self, mock_get_client):
        driver = DriverHanyuan1()
        mock_client = MagicMock()
        mock_method = MagicMock(
            return_value={"error": False, "result": "test"}
        )
        mock_client.submit_task = mock_method
        mock_get_client.return_value = mock_client
        status, reason, text, result = driver.call_zerorpc_rpc(
            "submit_task", {"test": "data"}
        )
        assert status == HttpCode.SUCCESS_OK
        assert result == "test"

    @patch.object(DriverHanyuan1, "_get_zerorpc_client")
    def test_call_zerorpc_rpc_no_client(self, mock_get_client):
        driver = DriverHanyuan1()
        mock_get_client.return_value = None
        status, reason, text, result = driver.call_zerorpc_rpc(
            "submit_task", {}
        )
        assert status == -1
        assert "not initialized" in reason

    @patch.object(DriverHanyuan1, "_get_zerorpc_client")
    def test_call_zerorpc_rpc_unknown_method(self, mock_get_client):
        driver = DriverHanyuan1()
        # Create a mock client that returns None for unknown attributes

        class MockClient:
            def __getattr__(self, name):
                return None

        mock_client = MockClient()
        mock_get_client.return_value = mock_client
        status, reason, text, result = driver.call_zerorpc_rpc(
            "unknown_method", {}
        )
        assert status == -1
        assert "Unknown method" in reason

    @patch.object(DriverHanyuan1, "_get_zerorpc_client")
    def test_call_zerorpc_rpc_timeout(self, mock_get_client):
        driver = DriverHanyuan1()
        mock_client = MagicMock()
        mock_method = MagicMock(side_effect=Exception("timeout"))
        mock_client.submit_task = mock_method
        mock_get_client.return_value = mock_client
        status, reason, text, result = driver.call_zerorpc_rpc(
            "submit_task", {}
        )
        assert status == -1
        assert "timeout" in reason.lower()

    @patch.object(Library, "call_http_api")
    def test_call_json_rpc_success(self, mock_call_http):
        driver = DriverHanyuan1()
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "test"}
        mock_call_http.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            "text",
            mock_response,
        )
        status, reason, text, result = driver.call_json_rpc(
            "http://test.com", "test_method", {"data": "test"}
        )
        assert status == HttpCode.SUCCESS_OK
        assert result == {"result": "test"}

    @patch.object(Library, "call_http_api")
    def test_call_json_rpc_connection_error(self, mock_call_http):
        driver = DriverHanyuan1()
        mock_call_http.side_effect = requests.exceptions.ConnectionError(
            "connection failed"
        )
        status, reason, text, result = driver.call_json_rpc(
            "http://test.com", "test_method"
        )
        assert status == -1
        assert "Connection error" in reason

    def test_build_request_data_gate_sequence(self):
        driver = DriverHanyuan1()
        mock_gate = MagicMock()
        mock_gate.name = "rx"
        mock_gate.targets = [0]
        mock_gate.arg_value = 1.0
        data = [mock_gate]
        result = driver._build_request_data(
            job_id,
            "gate_sequence",
            num_qubits=2,
            data=data,
            shots=100,
        )
        assert result["job_id"] == job_id
        assert result["data_type"] == "gate_sequence"
        assert result["qubit_num"] == 2
        assert result["shots"] == 100
        assert "data" in result
        assert "timestamp" in result

    def test_build_request_data_gate_sequence_dict(self):
        driver = DriverHanyuan1()
        mock_gate = MagicMock()
        mock_gate.name = "ry"
        mock_gate.targets = [1]
        mock_gate.arg_value = 0.5
        data = {"basis_gate_list": [mock_gate]}
        result = driver._build_request_data(
            job_id,
            "gate_sequence",
            num_qubits=2,
            data=data,
            shots=100,
        )
        assert result["data_type"] == "gate_sequence"
        assert len(result["data"]) == 1

    def test_build_request_data_gate_sequence_no_data(self):
        driver = DriverHanyuan1()
        with pytest.raises(ValueError) as exc_info:
            driver._build_request_data(job_id, "gate_sequence", data=None)
        assert "requires data parameter" in str(exc_info.value)

    def test_build_request_data_qu_topo(self):
        driver = DriverHanyuan1()
        result = driver._build_request_data(job_id, "qu_topo")
        assert result["job_id"] == job_id
        assert result["data_type"] == "qu_topo"

    def test_build_request_data_cancel_task(self):
        driver = DriverHanyuan1()
        result = driver._build_request_data(job_id, "cancel_task")
        assert result["job_id"] == job_id
        assert result["data_type"] == "cancel_task"

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    def test_submit_task_zmq_success(self, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_zerorpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {"error": False},
        )
        success, err_msg = driver.submit_task(
            job_id, "gate_sequence", num_qubits, [], shots
        )
        assert success is True

    @patch.object(DriverHanyuan1, "call_json_rpc")
    def test_submit_task_jsonrpc_success(self, mock_jsonrpc):
        driver = DriverHanyuan1()
        driver.use_zmq = False
        driver.base_url = "http://test.com"
        mock_jsonrpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {"result": "success"},
        )
        success, err_msg = driver.submit_task(
            job_id, "gate_sequence", num_qubits, [], shots
        )
        assert success is True

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    def test_submit_task_zmq_failure(self, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_zerorpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {"error": True, "message": "error"},
        )
        success, err_msg = driver.submit_task(
            job_id, "gate_sequence", num_qubits, [], shots
        )
        assert success is False

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    def test_submit_task_exception(self, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_zerorpc.side_effect = Exception("test error")
        success, err_msg = driver.submit_task(
            job_id, "gate_sequence", num_qubits, [], shots
        )
        assert success is False
        assert "test error" in err_msg

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    def test_get_task_status_zmq_success(self, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_zerorpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {"status": "completed"},
        )
        status = driver._get_task_status(job_id, "test", 0)
        assert status == "completed"

    @patch.object(DriverHanyuan1, "call_json_rpc")
    def test_get_task_status_jsonrpc_success(self, mock_jsonrpc):
        driver = DriverHanyuan1()
        driver.use_zmq = False
        driver.base_url = "http://test.com"
        mock_jsonrpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {"result": {"status": "running"}},
        )
        status = driver._get_task_status(job_id, "test", 0)
        assert status == "running"

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    def test_get_task_status_failure(self, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_zerorpc.return_value = (-1, "Error", None, None)
        status = driver._get_task_status(job_id, "test", 0)
        assert status is None

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    def test_get_task_results_zmq_success(self, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_zerorpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {"status": "success", "result": {"data": "test"}},
        )
        success, err_msg, results = driver.get_task_results(job_id, "test", 0)
        assert success is True
        assert results == {"data": "test"}

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    def test_get_task_results_zmq_no_result(self, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_zerorpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {"status": "success", "result": None},
        )
        success, err_msg, results = driver.get_task_results(job_id, "test", 0)
        assert success is False
        assert "no task results" in err_msg

    @patch.object(DriverHanyuan1, "call_json_rpc")
    def test_get_task_results_jsonrpc_success(self, mock_jsonrpc):
        driver = DriverHanyuan1()
        driver.use_zmq = False
        driver.base_url = "http://test.com"
        mock_jsonrpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {
                "result": {
                    "status": "success",
                    "result": {"data": "test"},
                }
            },
        )
        success, err_msg, results = driver.get_task_results(job_id, "test", 0)
        assert success is True
        assert results == {"data": "test"}

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    def test_set_task_zmq_success(self, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_zerorpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {"status": "success"},
        )
        success, err_msg, result = driver.set_task(job_id, "cancel_task")
        assert success is True
        assert err_msg is None

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    def test_set_task_zmq_failed(self, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_zerorpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {"status": "failed", "message": "error"},
        )
        success, err_msg, result = driver.set_task(job_id, "cancel_task")
        assert success is False
        assert err_msg == "error"

    @patch.object(DriverHanyuan1, "call_json_rpc")
    def test_set_task_jsonrpc_success(self, mock_jsonrpc):
        driver = DriverHanyuan1()
        driver.use_zmq = False
        driver.base_url = "http://test.com"
        mock_jsonrpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {"result": {"status": "success"}},
        )
        success, err_msg, result = driver.set_task(job_id, "cancel_task")
        assert success is True

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    @patch.object(Library, "create_uuid")
    def test_get_device_info_zmq_success(self, mock_uuid, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_uuid.return_value = job_id
        mock_zerorpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {
                "status": "success",
                "device_info": {
                    "device_status": "online",
                    "topo_data": {"qubits": 5},
                },
            },
        )
        success, err_msg, result = driver.get_device_info()
        assert success is True
        assert err_msg is None
        assert result["status"] == "success"

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    @patch.object(Library, "create_uuid")
    def test_get_device_info_zmq_failed(self, mock_uuid, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_uuid.return_value = job_id
        mock_zerorpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {"status": "failed", "message": "error"},
        )
        success, err_msg, result = driver.get_device_info()
        assert success is False
        assert err_msg == "error"

    @patch.object(DriverHanyuan1, "call_json_rpc")
    @patch.object(Library, "create_uuid")
    def test_get_device_info_jsonrpc_success(self, mock_uuid, mock_jsonrpc):
        driver = DriverHanyuan1()
        driver.use_zmq = False
        driver.base_url = "http://test.com"
        mock_uuid.return_value = job_id
        mock_jsonrpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {
                "result": {
                    "status": "success",
                    "device_info": {
                        "device_status": "online",
                        "topo_data": {"qubits": 5},
                    },
                }
            },
        )
        success, err_msg, result = driver.get_device_info()
        assert success is True
        assert err_msg is None
        assert result["status"] == "success"

    @patch.object(DriverHanyuan1, "call_json_rpc")
    @patch.object(Library, "create_uuid")
    def test_get_device_info_jsonrpc_failed(self, mock_uuid, mock_jsonrpc):
        driver = DriverHanyuan1()
        driver.use_zmq = False
        driver.base_url = "http://test.com"
        mock_uuid.return_value = job_id
        mock_jsonrpc.return_value = (
            HttpCode.SUCCESS_OK,
            "OK",
            None,
            {"result": {"status": "failed", "message": "error"}},
        )
        success, err_msg, result = driver.get_device_info()
        assert success is False
        assert err_msg == "error"

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    @patch.object(Library, "create_uuid")
    def test_get_device_info_request_failed(self, mock_uuid, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_uuid.return_value = job_id
        mock_zerorpc.return_value = (-1, "Connection error", None, None)
        success, err_msg, result = driver.get_device_info()
        assert success is False
        assert "Connection error" in err_msg

    @patch.object(DriverHanyuan1, "call_zerorpc_rpc")
    @patch.object(Library, "create_uuid")
    def test_get_device_info_exception(self, mock_uuid, mock_zerorpc):
        driver = DriverHanyuan1()
        driver.use_zmq = True
        mock_uuid.return_value = job_id
        mock_zerorpc.side_effect = Exception("test error")
        success, err_msg, result = driver.get_device_info()
        assert success is False
        assert "test error" in err_msg

    @patch.object(DriverHanyuan1, "get_device_info")
    def test_fetch_running_info_success(self, mock_get_device_info):
        driver = DriverHanyuan1()
        mock_get_device_info.return_value = (
            True,
            None,
            {
                "device_info": {
                    "device_status": "online",
                    "topo_data": {
                        "storage_area": ["q0", "q1"],
                        "readout_error": {"q0": 0.01, "q1": 0.02},
                    },
                }
            },
        )
        result = driver.fetch_running_info()
        assert result["status"] == "online"
        assert "details" in result
        assert "single_qubit_prop" in result["details"]

    @patch.object(DriverHanyuan1, "get_device_info")
    def test_fetch_running_info_exception(self, mock_get_device_info):
        driver = DriverHanyuan1()
        mock_get_device_info.return_value = (False, "test error", None)
        result = driver.fetch_running_info()
        assert result["status"] == "offline"
        assert result["details"] == {}
