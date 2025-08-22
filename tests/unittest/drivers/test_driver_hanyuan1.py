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

from unittest.mock import patch

import pytest

from qcos.common.library import Library
from qcos.drivers.cascoldatom.driver_hanyuan1 import DriverHanyuan1

obj = DriverHanyuan1()


class TestDriverHanyuan1:
    def test_init_driver(self):
        assert obj.init_driver() is None

    def test_close_driver(self):
        assert obj.close_driver() is None

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs(self, mock_validate_schema):
        mock_validate_schema.return_value = iter([True, ''])
        success, err_msg = obj.validate_driver_configs()
        assert success == True

        mock_validate_schema.return_value = iter([False, ''])
        success, err_msg = obj.validate_driver_configs()
        assert success == False

    @patch.object(DriverHanyuan1, "get_task_results")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(DriverHanyuan1, "submit_task")
    def test_run(self, mock_submit_task, mock_loop_with_timeout,
                 mock_get_task_results):
        qasm_str = {
            "source_code":
                '''
                OPENQASM 2.0;
                include "qelib1.inc";
                qreg q[5];
                creg c[5];
                h q[0];
                h q[0];
                x q[0];
                rx(1) q[0];
                measure q->c;
                ''',
            "index": "index",
            "transpile_results": "transpile_results"
        }
        mock_submit_task.return_value = iter([False, ''])
        with pytest.raises(ValueError) as context:
            obj.run('1', 5, qasm_str, "gate_sequence")
        assert "Failed to submit task [1]:" in str(context.value)

        mock_submit_task.return_value = iter([True, ''])
        mock_loop_with_timeout.return_value = iter([False, '', ''])
        with pytest.raises(ValueError) as context:
            obj.run('1', 5, qasm_str, "gate_sequence")
        assert "Failed to wait for task [1]:" in str(context.value)

        mock_submit_task.return_value = iter([True, ''])
        mock_loop_with_timeout.return_value = iter([True, '', ''])
        mock_get_task_results.return_value = iter([False, '', ''])
        with pytest.raises(ValueError) as context:
            obj.run('1', 5, qasm_str, "gate_sequence")
        assert "Failed to get task results [1]: " in str(
            context.value)

        mock_submit_task.return_value = iter([True, ''])
        mock_loop_with_timeout.return_value = iter([True, '', ''])
        mock_get_task_results.return_value = iter([True, '', ''])
        obj.run('1', 5, qasm_str, "gate_sequence")

    def test_print_api_response(self):
        obj.verbose = True
        assert obj.print_api_response("156", "no reason", "edit") is None

    def test_check_task_status(self):
        assert obj.check_task_status("1", 1, []) is False

    def test_get_task_results(self):
        success, err_msg, result = obj.get_task_results("1", 1)
        assert success == True

    def test_submit_task(self):
        obj.submit_task("1", 5, [], "gate_sequence", 10, 1)

    @patch.object(Library, "call_http_api")
    def test_call_json_rpc(self, mock_call_http_api):
        mock_call_http_api.return_value = iter([True, ''])
        obj.call_json_rpc(obj.base_url, '', {"job_id": "1"})
