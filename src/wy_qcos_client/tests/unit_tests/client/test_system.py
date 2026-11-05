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
#     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
#     MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Tests for wy_qcos_client.Client system/job/misc methods."""

import json
import uuid as uuid_lib
from unittest.mock import patch

import pytest

from wy_qcos_client.client import Client
from wy_qcos_client.common import errors
from wy_qcos_client.common.client_library import _s

client = Client()


class TestSystemMethods:
    """Cover ping/system_info/show_mem/gc_mem/trace_mem and workers."""

    @patch.object(Client, "call_json_rpc")
    def test_ping(self, mock_call):
        mock_call.return_value = (200, "OK", "text", "pong")
        ret = client.ping("hello")
        assert ret == (200, "OK", "text", "pong")
        mock_call.assert_called_once_with(
            client.system_url, "ping", {"message": "hello"}
        )

    @patch.object(Client, "call_json_rpc")
    def test_system_info(self, mock_call):
        mock_call.return_value = (200, "OK", "text", {"total_jobs": 1})
        ret = client.system_info()
        assert ret[0] == 200
        mock_call.assert_called_once_with(
            client.system_url, "system_info", body_data=None
        )

    @patch.object(Client, "call_json_rpc")
    def test_show_mem(self, mock_call):
        mock_call.return_value = (200, "OK", "text", {"rss_mb": 100})
        ret = client.show_mem()
        assert ret[0] == 200
        mock_call.assert_called_once_with(
            client.system_url, "show_mem", body_data=None
        )

    @patch.object(Client, "call_json_rpc")
    def test_gc_mem_default(self, mock_call):
        mock_call.return_value = (200, "OK", "text", {"collected": 1})
        ret = client.gc_mem()
        assert ret[0] == 200
        mock_call.assert_called_once_with(
            client.system_url, "gc_mem", {"generations": 2}
        )

    @patch.object(Client, "call_json_rpc")
    def test_gc_mem_generations(self, mock_call):
        mock_call.return_value = (200, "OK", "text", {"collected": 1})
        ret = client.gc_mem(generations=0)
        assert ret[0] == 200
        mock_call.assert_called_once_with(
            client.system_url, "gc_mem", {"generations": 0}
        )

    @patch.object(Client, "call_json_rpc")
    def test_trace_mem_default(self, mock_call):
        mock_call.return_value = (200, "OK", "text", "stats")
        ret = client.trace_mem()
        assert ret[0] == 200
        mock_call.assert_called_once_with(
            client.system_url,
            "trace_mem",
            {"action": "snapshot", "nframe": 25, "sort_count": False},
        )

    @patch.object(Client, "call_json_rpc")
    def test_trace_mem_custom(self, mock_call):
        mock_call.return_value = (200, "OK", "text", "stats")
        ret = client.trace_mem(action="stop", nframe=10, sort_count=True)
        assert ret[0] == 200
        mock_call.assert_called_once_with(
            client.system_url,
            "trace_mem",
            {"action": "stop", "nframe": 10, "sort_count": True},
        )

    @patch.object(Client, "call_json_rpc")
    def test_list_workers_no_filters(self, mock_call):
        mock_call.return_value = (200, "OK", "text", [])
        ret = client.list_workers()
        assert ret[0] == 200
        mock_call.assert_called_once_with(
            client.system_url,
            "list_workers",
            body_data=None,
            filters=None,
            pagination=None,
            sort=None,
            search=None,
        )

    @patch.object(Client, "call_json_rpc")
    def test_list_workers_with_filters(self, mock_call):
        mock_call.return_value = (200, "OK", "text", [])
        ret = client.list_workers(
            filters={"worker_status": "running"},
            pagination={"page": 1, "page_size": 10},
            sort=["-worker_name"],
            search="dummy",
        )
        assert ret[0] == 200
        kwargs = mock_call.call_args.kwargs
        assert kwargs["filters"] == {"worker_status": "running"}
        assert kwargs["pagination"] == {"page": 1, "page_size": 10}
        assert kwargs["sort"] == ["-worker_name"]
        assert kwargs["search"] == "dummy"

    @patch.object(Client, "call_json_rpc")
    def test_restart_worker(self, mock_call):
        mock_call.return_value = (200, "OK", "text", "restarted")
        ret = client.restart_worker(worker_name="worker1")
        assert ret[0] == 200
        mock_call.assert_called_once_with(
            client.system_url,
            "restart_worker",
            {"worker_name": "worker1"},
        )


class TestSetDevice:
    """Cover set_device argument branches."""

    @patch.object(Client, "call_json_rpc")
    def test_set_device_no_optional_fields(self, mock_call):
        mock_call.return_value = (200, "OK", "text", "done")
        ret = client.set_device("dummy")
        assert ret[0] == 200
        mock_call.assert_called_once_with(
            client.device_url, "set_device", {"device_name": "dummy"}
        )

    @patch.object(Client, "call_json_rpc")
    def test_set_device_all_fields(self, mock_call):
        mock_call.return_value = (200, "OK", "text", "done")
        ret = client.set_device(
            "dummy",
            state="online",
            enable=True,
            max_qubits="auto",
            available_qubits=8,
        )
        assert ret[0] == 200
        mock_call.assert_called_once_with(
            client.device_url,
            "set_device",
            {
                "device_name": "dummy",
                "state": "online",
                "enable": True,
                "max_qubits": "auto",
                "available_qubits": 8,
            },
        )

    @patch.object(Client, "call_json_rpc")
    def test_set_device_partial_fields(self, mock_call):
        mock_call.return_value = (200, "OK", "text", "done")
        ret = client.set_device("dummy", state="offline", enable=False)
        assert ret[0] == 200
        mock_call.assert_called_once_with(
            client.device_url,
            "set_device",
            {"device_name": "dummy", "state": "offline", "enable": False},
        )


class TestSubmitJob:
    """Cover submit_job optional parameter branches."""

    @patch.object(Client, "call_json_rpc")
    def test_submit_job_minimal(self, mock_call):
        mock_call.return_value = (200, "OK", "text", {"job_id": "j1"})
        ret = client.submit_job("OPENQASM 2.0;")
        assert ret[0] == 200
        data = mock_call.call_args.args[2]
        assert data["source_code"] == "OPENQASM 2.0;"
        assert "backend" not in data
        assert "flavor_id" not in data
        assert "extra_specs" not in data
        assert "job_id" not in data
        assert "params" not in data
        assert "options" not in data

    @patch.object(Client, "call_json_rpc")
    def test_submit_job_all_optional(self, mock_call):
        job_uuid = str(uuid_lib.uuid4())
        flavor_uuid = uuid_lib.uuid4()
        mock_call.return_value = (200, "OK", "text", {"job_id": job_uuid})
        ret = client.submit_job(
            "OPENQASM 2.0;",
            backend="dummy",
            flavor_id=flavor_uuid,
            extra_specs={"min_qubits": 2},
            job_id=job_uuid,
            params={"k": "v"},
            options={"enable_wirecut": True},
            job_name="n",
            shots=128,
        )
        assert ret[0] == 200
        data = mock_call.call_args.args[2]
        assert data["backend"] == "dummy"
        assert data["flavor_id"] == str(flavor_uuid)
        assert data["extra_specs"] == {"min_qubits": 2}
        assert data["job_id"] == job_uuid
        assert data["params"] == {"k": "v"}
        assert data["options"] == {"enable_wirecut": True}
        assert data["job_name"] == "n"
        assert data["shots"] == 128


class TestResolveHelpers:
    """Cover resolve_user_id / resolve_role_id / resolve_device_group_id."""

    def test_resolve_user_id_uuid_passthrough(self):
        uid = str(uuid_lib.uuid4())
        assert Client.resolve_user_id(client, uid) == uid

    @patch.object(Client, "get_users")
    def test_resolve_user_id_by_name_found(self, mock_get_users):
        uid = str(uuid_lib.uuid4())
        text = json.dumps({"result": {uid: {"user_name": "alice"}}})
        mock_get_users.return_value = (200, "OK", text, {})
        assert Client.resolve_user_id(client, "alice") == uid
        mock_get_users.assert_called_once_with(filters={"user_name": "alice"})

    @patch.object(Client, "get_users")
    def test_resolve_user_id_not_found(self, mock_get_users):
        text = json.dumps({"result": {}})
        mock_get_users.return_value = (200, "OK", text, {})
        with pytest.raises(errors.GenericException, match="not found"):
            Client.resolve_user_id(client, "ghost")

    @patch.object(Client, "get_users")
    def test_resolve_user_id_http_error(self, mock_get_users):
        mock_get_users.return_value = (500, "Server Error", "", None)
        with pytest.raises(errors.GenericException, match="Failed"):
            Client.resolve_user_id(client, "alice")

    @patch.object(Client, "get_users")
    def test_resolve_user_id_jsonrpc_error(self, mock_get_users):
        text = json.dumps({
            "error": {"message": "denied", "data": {"details": "no perm"}}
        })
        mock_get_users.return_value = (200, "OK", text, {})
        with pytest.raises(errors.GenericException, match="denied"):
            Client.resolve_user_id(client, "alice")

    def test_resolve_role_id_uuid_passthrough(self):
        rid = str(uuid_lib.uuid4())
        assert Client.resolve_role_id(client, rid) == rid

    @patch.object(Client, "get_roles")
    def test_resolve_role_id_by_name_found(self, mock_get_roles):
        rid = str(uuid_lib.uuid4())
        text = json.dumps({"result": {rid: {"role_name": "ops"}}})
        mock_get_roles.return_value = (200, "OK", text, {})
        assert Client.resolve_role_id(client, "ops") == rid
        mock_get_roles.assert_called_once_with(filters={"role_name": "ops"})

    @patch.object(Client, "get_roles")
    def test_resolve_role_id_not_found(self, mock_get_roles):
        text = json.dumps({"result": {}})
        mock_get_roles.return_value = (200, "OK", text, {})
        with pytest.raises(errors.GenericException, match="not found"):
            Client.resolve_role_id(client, "ghost")

    @patch.object(Client, "get_roles")
    def test_resolve_role_id_http_error(self, mock_get_roles):
        mock_get_roles.return_value = (502, "Bad Gateway", "", None)
        with pytest.raises(errors.GenericException, match="Failed"):
            Client.resolve_role_id(client, "ops")

    def test_resolve_device_group_id_uuid_passthrough(self):
        gid = str(uuid_lib.uuid4())
        assert Client.resolve_device_group_id(client, gid) == gid

    @patch.object(Client, "get_device_groups")
    def test_resolve_device_group_id_by_name(self, mock_get):
        gid = str(uuid_lib.uuid4())
        text = json.dumps({"result": [{"id": gid, "name": "grp"}]})
        mock_get.return_value = (200, "OK", text, {})
        assert Client.resolve_device_group_id(client, "grp") == gid
        mock_get.assert_called_once_with(filters={"group_name": "grp"})

    @patch.object(Client, "get_device_groups")
    def test_resolve_device_group_id_not_found(self, mock_get):
        text = json.dumps({"result": []})
        mock_get.return_value = (200, "OK", text, {})
        with pytest.raises(errors.GenericException, match="not found"):
            Client.resolve_device_group_id(client, "ghost")

    @patch.object(Client, "get_device_groups")
    def test_resolve_device_group_id_http_error(self, mock_get):
        mock_get.return_value = (503, "Unavailable", "", None)
        with pytest.raises(errors.GenericException, match="Failed"):
            Client.resolve_device_group_id(client, "grp")

    @patch.object(Client, "get_device_groups")
    def test_resolve_device_group_id_jsonrpc_error(self, mock_get):
        text = json.dumps({
            "error": {"message": "boom", "data": {"details": "why"}}
        })
        mock_get.return_value = (200, "OK", text, {})
        with pytest.raises(errors.GenericException, match="boom"):
            Client.resolve_device_group_id(client, "grp")


class TestCallJsonRpcHeaders:
    """Cover header assembly branches in call_json_rpc."""

    @patch("wy_qcos_client.client.ClientLibrary.call_http_api")
    @patch.object(Client, "print_api_response")
    def test_token_from_env_and_instance(self, mock_print, mock_call_http_api):
        mock_call_http_api.return_value = [-1, "reason", "text", "result"]
        client.access_token = _s("instance-token")
        with patch.dict(
            "os.environ",
            {"QCOS_ACCESS_TOKEN": _s("env-token")},
        ):
            client.call_json_rpc("http://127.0.0.1", "get", {})
        headers = mock_call_http_api.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer " + _s("instance-token")

    @patch("wy_qcos_client.client.ClientLibrary.call_http_api")
    @patch.object(Client, "print_api_response")
    def test_token_from_env_only(self, mock_print, mock_call_http_api):
        mock_call_http_api.return_value = [-1, "reason", "text", "result"]
        client.access_token = None
        with patch.dict(
            "os.environ",
            {"QCOS_ACCESS_TOKEN": "env-token"},
            clear=False,
        ):
            client.call_json_rpc("http://127.0.0.1", "get", {})
        headers = mock_call_http_api.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer env-token"

    @patch("wy_qcos_client.client.ClientLibrary.call_http_api")
    @patch.object(Client, "print_api_response")
    def test_virtual_instance_header(self, mock_print, mock_call_http_api):
        mock_call_http_api.return_value = [-1, "reason", "text", "result"]
        with patch.dict(
            "os.environ",
            {"QCOS_VIRTUAL_INSTANCE_ID": "vi-123"},
            clear=False,
        ):
            client.call_json_rpc("http://127.0.0.1", "get", {})
        headers = mock_call_http_api.call_args.kwargs["headers"]
        assert headers["x-qcos-virtual-instance-id"] == "vi-123"

    @patch("wy_qcos_client.client.ClientLibrary.call_http_api")
    @patch.object(Client, "print_api_response")
    def test_custom_request_headers(self, mock_print, mock_call_http_api):
        mock_call_http_api.return_value = [-1, "reason", "text", "result"]
        client.request_headers = {"x-qcos-virtual-instance-id": "custom"}
        try:
            client.call_json_rpc("http://127.0.0.1", "get", {})
        finally:
            client.request_headers = None
        headers = mock_call_http_api.call_args.kwargs["headers"]
        assert headers["x-qcos-virtual-instance-id"] == "custom"

    @patch("wy_qcos_client.client.ClientLibrary.call_http_api")
    @patch.object(Client, "print_api_response")
    def test_query_object_assembly(self, mock_print, mock_call_http_api):
        mock_call_http_api.return_value = [-1, "reason", "text", "result"]
        client.call_json_rpc(
            "http://127.0.0.1",
            "get",
            {"a": 1},
            filters={"name": "x"},
            pagination={"page": 2},
            sort=["-created_at"],
            fields=["id"],
            search="kw",
        )
        json_payload = mock_call_http_api.call_args.kwargs["json"]
        assert json_payload["params"]["body"] == {"a": 1}
        assert json_payload["params"]["query"] == {
            "filters": {"name": "x"},
            "pagination": {"page": 2},
            "sort": ["-created_at"],
            "fields": ["id"],
            "search": "kw",
        }

    @patch("wy_qcos_client.client.ClientLibrary.call_http_api")
    @patch.object(Client, "print_api_response")
    def test_invalid_env_timeout_returns_error(
        self, mock_print, mock_call_http_api
    ):
        """Non-integer QCOS_CLIENT_TIMEOUT short-circuits with -1."""
        Client.timeout = 600
        Client.timeout_from_cli = False
        with patch.dict("os.environ", {"QCOS_CLIENT_TIMEOUT": "not-a-number"}):
            status, reason, _text, _res = client.call_json_rpc(
                "http://127.0.0.1", "get", {}
            )
        assert status == -1
        assert "Invalid QCOS_CLIENT_TIMEOUT" in reason

    @patch("wy_qcos_client.client.ClientLibrary.call_http_api")
    @patch.object(Client, "print_api_response")
    def test_connection_error(self, mock_print, mock_call_http_api):
        import requests

        mock_call_http_api.side_effect = requests.exceptions.ConnectionError(
            "refused"
        )
        status, reason, _text, _res = client.call_json_rpc(
            "http://127.0.0.1", "get", {}
        )
        assert status == -1
        assert "Connection error" in reason

    @patch("wy_qcos_client.client.ClientLibrary.call_http_api")
    @patch.object(Client, "print_api_response")
    def test_generic_exception(self, mock_print, mock_call_http_api):
        mock_call_http_api.side_effect = ValueError("boom")
        status, reason, _text, _res = client.call_json_rpc(
            "http://127.0.0.1", "get", {}
        )
        assert status == -1
        assert reason == "boom"

    def test_print_api_response_verbose(self, capsys):
        Client.verbose = True
        try:
            Client.print_api_response(200, "OK", "body", "res")
            out = capsys.readouterr().out
        finally:
            Client.verbose = False
        assert "status_code: 200" in out
        assert "reason: OK" in out

    def test_print_api_response_quiet(self, capsys):
        Client.verbose = False
        Client.print_api_response(200, "OK", "body", "res")
        assert capsys.readouterr().out == ""
