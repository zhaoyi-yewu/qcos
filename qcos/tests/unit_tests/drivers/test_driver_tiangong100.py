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

import json
from unittest.mock import patch

import pytest

from qcos.common.library import Library
from qcos.drivers.qboson.driver_tiangong100 import DriverTiangong100

obj = DriverTiangong100()
obj.base_url = ''


class TestDriverTiangong100:
    @classmethod
    def setup_class(cls):
        cls.qasm_str = {
            "source_code":
                """
                OPENQASM 2.0;
                include "qelib1.inc";
                qreg q[5];
                creg c[5];
                h q[0];
                h q[0];
                x q[0];
                rx(1) q[0];
                measure q->c;
                """,
            "index": "index"}

    def test_init_driver(self):
        assert obj.init_driver() is None

    def test_validate_driver_configs(self):
        configs = {}
        success, err_msg = obj.validate_driver_configs(configs)
        assert success is False

    def test_close_driver(self):
        obj.close_driver()

    @patch.object(DriverTiangong100, "get_task_results")
    @patch.object(DriverTiangong100, "get_task_id")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(DriverTiangong100, "submit_tasks")
    @patch.object(DriverTiangong100, "upload_file")
    @patch.object(DriverTiangong100, "check_device_status")
    @patch.object(DriverTiangong100, "user_auth")
    @patch.object(Library, "is_valid_url")
    def test_run(self, mock_is_valid_url, mock_user_auth,
                 mock_check_device_status, mock_upload_file,
                 mock_submit_tasks, mock_loop_with_timeout,
                 mock_get_task_id, mock_get_task_results):

        mock_is_valid_url.return_value = False
        with pytest.raises(ValueError) as context:
            obj.run('1', 5, self.qasm_str, "gate_sequence")
        assert "Invalid URL [1]:" in str(context.value)

        mock_is_valid_url.return_value = True
        mock_user_auth.return_value = iter([False, '', ''])
        with pytest.raises(ValueError) as context:
            obj.run('1', 5, self.qasm_str, "gate_sequence")
        assert "Authorize failed [1]:" in str(context.value)

        mock_user_auth.return_value = iter([True, '', ''])
        mock_check_device_status.return_value = iter([False, 'no'])
        with pytest.raises(ValueError) as context:
            obj.run('1', 5, self.qasm_str, "gate_sequence")
        assert "no" in str(context.value)

        mock_user_auth.return_value = iter([True, '', ''])
        mock_check_device_status.return_value = iter([True, 'no'])
        mock_upload_file.return_value = iter([False, '', ''])
        with pytest.raises(ValueError) as context:
            obj.run('1', 5, self.qasm_str, "gate_sequence")
        assert "Failed to upload file [1]: " in str(context.value)

        mock_user_auth.return_value = iter([True, '', ''])
        mock_check_device_status.return_value = iter([True, 'no'])
        mock_upload_file.return_value = iter([True, '', {'creator': 'my',
                                                         'id': 'admin',
                                                         'name': 'empire'}])
        mock_submit_tasks.return_value = iter([False, ''])
        with pytest.raises(ValueError) as context:
            obj.run('1', 5, self.qasm_str, "gate_sequence")
        assert "Failed to submit task [1_index]: " in str(context.value)

        mock_user_auth.return_value = iter([True, '', ''])
        mock_check_device_status.return_value = iter([True, 'no'])
        mock_upload_file.return_value = iter([True, '', {'creator': 'my',
                                                         'id': 'admin',
                                                         'name': 'empire'}])
        mock_submit_tasks.return_value = iter([True, ''])
        mock_loop_with_timeout.return_value = iter([False, '', ''])
        with pytest.raises(ValueError) as context:
            obj.run('1', 5, self.qasm_str, "gate_sequence")
        assert "Failed to wait for task [1_index]: " in str(context.value)

        mock_user_auth.return_value = iter([True, '', ''])
        mock_check_device_status.return_value = iter([True, 'no'])
        mock_upload_file.return_value = iter([True, '', {'creator': 'my',
                                                         'id': 'admin',
                                                         'name': 'empire'}])
        mock_submit_tasks.return_value = iter([True, ''])
        mock_loop_with_timeout.return_value = iter([True, '', ''])
        mock_get_task_id.return_value = iter([False, '', {'id': 'admin'}])
        with pytest.raises(ValueError) as context:
            obj.run('1', 5, self.qasm_str, "gate_sequence")
        assert "Failed to get task id [1_index]: " in str(context.value)

        mock_user_auth.return_value = iter([True, '', ''])
        mock_check_device_status.return_value = iter([True, 'no'])
        mock_upload_file.return_value = iter([True, '', {'creator': 'my',
                                                         'id': 'admin',
                                                         'name': 'empire'}])
        mock_submit_tasks.return_value = iter([True, ''])
        mock_loop_with_timeout.return_value = iter([True, '', ''])
        mock_get_task_id.return_value = iter([True, '', {'id': 'admin'}])
        mock_get_task_results.return_value = iter([False, '', ''])
        with pytest.raises(ValueError) as context:
            obj.run('1', 5, self.qasm_str, "gate_sequence")
        assert "Failed to get task results [1]:" in str(context.value)

        mock_user_auth.return_value = iter([True, '', ''])
        mock_check_device_status.return_value = iter([True, 'no'])
        mock_upload_file.return_value = iter([True, '', {'creator': 'my',
                                                         'id': 'admin',
                                                         'name': 'empire'}])
        mock_submit_tasks.return_value = iter([True, ''])
        mock_loop_with_timeout.return_value = iter([True, '', ''])
        mock_get_task_id.return_value = iter([True, '', {'id': 'admin'}])
        mock_get_task_results.return_value = iter([True, '', ''])
        obj.run('1', 5, self.qasm_str, "gate_sequence")

    @patch.object(Library, "call_http_api")
    def test_user_auth(self, mock_call_http_api):
        mock_call_http_api.return_value = iter([200, '',
                                                '{"code": "Alice",'
                                                '"msg": "Bob"}', ''])
        success, err_msg, token = obj.user_auth("admin", "admin")
        assert success is False
        assert err_msg == "Bob"

        mock_call_http_api.return_value = iter([114514, '',
                                                '{"code": "Alice",'
                                                '"msg": "Bob"}', ''])
        success, err_msg, token = obj.user_auth("admin", "admin")
        assert success is False
        assert err_msg == ''

    @patch.object(Library, "call_http_api")
    def test_check_device_status(self, mock_call_http_api):
        mock_call_http_api.return_value = iter([200, '', '{"code": "0",'
                                                         '"msg": "Bob",'
                                                         '"data": {'
                                                         '"status": 0,'
                                                         '"status_desc": 666'
                                                         '}}', ''])
        success, err_msg = obj.check_device_status("233")
        assert success is False

    @patch.object(Library, "call_http_api")
    def test_upload_file(self, mock_call_http_api):
        mock_call_http_api.return_value = iter([200, '', '{"code": "0",'
                                                         '"msg": "Bob",'
                                                         '"data": {'
                                                         '"creator": "my",'
                                                         '"id": "admin",'
                                                         ' "name": "empire"'
                                                         '}}', ''])
        success, err_msg, file_info = obj.upload_file("1", '', self.qasm_str)
        assert success is True
        assert err_msg == ''
        assert file_info == {'creator': 'my', 'id': 'admin', 'name': 'empire'}

    @patch.object(Library, "call_http_api")
    def test_submit_tasks(self, mock_call_http_api):
        mock_call_http_api.return_value = iter([200, '', '{"code": "0",'
                                                         '"msg": "Bob"}', ''])
        success, err_msg = obj.submit_tasks([])
        assert success is True

    @patch.object(Library, "call_http_api")
    def test_get_task_id(self, mock_call_http_api):

        mock_call_http_api.return_value = iter([200, '', '{"code": "0",'
                                                         '"msg": "Bob",'
                                                         '"data": {}}', ''])
        success, err_msg, task_info = obj.get_task_id("tzeentch-001")
        assert success is False

    @patch.object(DriverTiangong100, "get_task_id")
    def test_check_task_status(self, mock_get_task_id):
        mock_get_task_id.return_value = iter([True, '', {"name": "empire"}])
        success = obj.check_task_status("1", [])
        assert success is False

    @patch.object(Library, "call_http_api")
    def test_get_task_results(self, mock_call_http_api):
        response = {
            "code": "0",
            "msg": "Bob",
            "data": {
                "out_data": [],
                "visual_data": []
            }
        }
        mock_call_http_api.return_value = iter([200, '',
                                                json.dumps(response), ''])
        success, err_msg, result = obj.get_task_results("1")
        assert success is True

    @patch.object(Library, "call_http_api")
    def test_delete_task(self, mock_call_http_api):

        mock_call_http_api.return_value = iter([200, '', '{"code": "0",'
                                                         '"msg": "Bob"}', ''])
        success, err_msg = obj.delete_task("1")
        assert success is True
