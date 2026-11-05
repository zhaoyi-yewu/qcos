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

"""Tests for Client auth token storage branches and AI REST methods."""

import os
from unittest.mock import MagicMock, patch

import pytest

from wy_qcos_client.client import Client, SSL
from wy_qcos_client.common import errors
from wy_qcos_client.common.client_library import _s


client = Client()


def _mock_response(status_code=200, json_data=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_data
    return resp


class TestLoginTokenStorage:
    """Cover login() token-storing branches."""

    def setup_method(self):
        client.access_token = None

    def teardown_method(self):
        client.access_token = None
        os.environ.pop("QCOS_ACCESS_TOKEN", None)
        os.environ.pop("QCOS_REFRESH_TOKEN", None)

    @patch.object(Client, "call_json_rpc")
    def test_login_stores_tokens(self, mock_call):
        mock_call.return_value = (
            200,
            "OK",
            "text",
            {"access_token": _s("at"), "refresh_token": _s("rt")},
        )
        status, _r, _t, _res = client.login("u", "p")
        assert status == 200
        assert client.access_token == _s("at")
        assert os.environ["QCOS_ACCESS_TOKEN"] == _s("at")
        assert os.environ["QCOS_REFRESH_TOKEN"] == _s("rt")

    @patch.object(Client, "call_json_rpc")
    def test_login_non_dict_result(self, mock_call):
        mock_call.return_value = (200, "OK", "text", None)
        status, _r, _t, _res = client.login("u", "p")
        assert status == 200
        assert client.access_token is None

    @patch.object(Client, "call_json_rpc")
    def test_login_object_with_get(self, mock_call):
        obj = {"access_token": _s("at2"), "refresh_token": _s("rt2")}

        class Wrapper:
            def get(self, key, default=None):
                return obj.get(key, default)

        mock_call.return_value = (200, "OK", "text", Wrapper())
        status, _r, _t, _res = client.login("u", "p")
        assert status == 200
        assert client.access_token == _s("at2")

    @patch.object(Client, "call_json_rpc")
    def test_login_missing_tokens(self, mock_call):
        mock_call.return_value = (200, "OK", "text", {"foo": "bar"})
        status, _r, _t, _res = client.login("u", "p")
        assert status == 200
        assert client.access_token is None

    @patch.object(Client, "call_json_rpc")
    def test_login_failure_no_store(self, mock_call):
        mock_call.return_value = (
            401,
            "Unauthorized",
            "text",
            {"access_token": "at"},
        )
        status, _r, _t, _res = client.login("u", "p")
        assert status == 401
        assert client.access_token is None

    @patch.object(Client, "call_json_rpc")
    def test_login_token_store_exception_swallowed(self, mock_call):
        # result whose .get raises -> warning path, no crash
        class Bad:
            def get(self, *a, **kw):
                raise RuntimeError("boom")

        mock_call.return_value = (200, "OK", "text", Bad())
        status, _r, _t, _res = client.login("u", "p")
        assert status == 200

    @patch.object(Client, "call_json_rpc")
    def test_logout_clears_token(self, mock_call):
        mock_call.return_value = (200, "OK", "text", {})
        client.set_token("tok")
        status, _r, _t, _res = client.logout()
        assert status == 200
        assert client.get_token() is None

    @patch.object(Client, "call_json_rpc")
    def test_logout_failure_keeps_token(self, mock_call):
        mock_call.return_value = (500, "Server Error", "text", {})
        client.set_token("tok")
        status, _r, _t, _res = client.logout()
        assert status == 500
        assert client.get_token() == "tok"


class TestRefreshToken:
    """Cover refresh_token() branches."""

    def teardown_method(self):
        os.environ.pop("QCOS_REFRESH_TOKEN", None)

    def test_refresh_token_missing_env(self):
        os.environ.pop("QCOS_REFRESH_TOKEN", None)
        status, reason, _t, result = client.refresh_token()
        assert status == 401
        assert "No refresh token" in str(result)

    @patch.object(Client, "call_json_rpc")
    def test_refresh_token_stores_new_tokens(self, mock_call):
        os.environ["QCOS_REFRESH_TOKEN"] = _s("old-rt")
        mock_call.return_value = (
            200,
            "OK",
            "text",
            {"access_token": _s("new-at"), "refresh_token": _s("new-rt")},
        )
        status, _r, _t, _res = client.refresh_token()
        assert status == 200
        assert client.get_token() == _s("new-at")
        assert os.environ["QCOS_REFRESH_TOKEN"] == _s("new-rt")

    @patch.object(Client, "call_json_rpc")
    def test_refresh_token_object_result(self, mock_call):
        os.environ["QCOS_REFRESH_TOKEN"] = _s("old-rt")

        class Wrapper:
            def get(self, key, default=None):
                return {
                    "access_token": _s("oat"),
                    "refresh_token": _s("ort"),
                }.get(key, default)

        mock_call.return_value = (200, "OK", "text", Wrapper())
        status, _r, _t, _res = client.refresh_token()
        assert status == 200
        assert client.get_token() == _s("oat")

    @patch.object(Client, "call_json_rpc")
    def test_refresh_token_non_dict_result(self, mock_call):
        os.environ["QCOS_REFRESH_TOKEN"] = _s("old-rt")
        client.set_token("prev")
        try:
            mock_call.return_value = (200, "OK", "text", None)
            status, _r, _t, _res = client.refresh_token()
            assert status == 200
            # non-dict result stores nothing; previous token preserved
            assert client.get_token() == "prev"
        finally:
            client.clear_token()

    @patch.object(Client, "call_json_rpc")
    def test_refresh_token_failure(self, mock_call):
        os.environ["QCOS_REFRESH_TOKEN"] = _s("old-rt")
        client.set_token("prev")
        mock_call.return_value = (401, "Unauthorized", "text", {})
        status, _r, _t, _res = client.refresh_token()
        assert status == 401
        assert client.get_token() == "prev"


class TestClearToken:
    def test_clear_token(self):
        client.set_token("x")
        client.clear_token()
        assert client.get_token() is None


class TestAiUrl:
    def test_ai_url_property(self):
        assert client.ai_url.endswith("/v1/ai")


class TestAiHelpers:
    """Cover _ai_headers / _ai_verify / _ai_cert branches."""

    def teardown_method(self):
        SSL.use_ssl = False
        SSL.ca_file = None
        SSL.cert_file = None
        SSL.key_file = None

    def test_ai_headers_plain(self):
        os.environ.pop("QCOS_ACCESS_TOKEN", None)
        os.environ.pop("QCOS_VIRTUAL_INSTANCE_ID", None)
        client.access_token = None
        client.request_headers = None
        headers = client._ai_headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers
        assert "Accept" not in headers

    def test_ai_headers_sse(self):
        headers = client._ai_headers(accept_sse=True)
        assert headers["Accept"] == "text/event-stream"

    def test_ai_headers_with_token(self):
        client.access_token = _s("tok")
        try:
            headers = client._ai_headers()
        finally:
            client.access_token = None
        assert headers["Authorization"] == "Bearer " + _s("tok")

    def test_ai_headers_env_token(self):
        client.access_token = None
        with patch.dict("os.environ", {"QCOS_ACCESS_TOKEN": _s("envtok")}):
            headers = client._ai_headers()
        assert headers["Authorization"] == "Bearer " + _s("envtok")

    def test_ai_headers_env_virtual_instance(self):
        with patch.dict("os.environ", {"QCOS_VIRTUAL_INSTANCE_ID": "vi-9"}):
            headers = client._ai_headers()
        assert headers["x-qcos-virtual-instance-id"] == "vi-9"

    def test_ai_headers_custom_request_headers(self):
        client.request_headers = {"X-Custom": "1"}
        try:
            headers = client._ai_headers()
        finally:
            client.request_headers = None
        assert headers["X-Custom"] == "1"

    def test_ai_verify_no_ssl(self):
        SSL.use_ssl = False
        assert client._ai_verify() is False

    def test_ai_verify_ssl_with_ca(self):
        SSL.use_ssl = True
        SSL.ca_file = "ca.pem"
        assert client._ai_verify() == "ca.pem"

    def test_ai_verify_ssl_without_ca(self):
        SSL.use_ssl = True
        SSL.ca_file = None
        assert client._ai_verify() is False

    def test_ai_cert_no_ssl(self):
        SSL.use_ssl = False
        assert client._ai_cert() is None

    def test_ai_cert_ssl_full(self):
        SSL.use_ssl = True
        SSL.cert_file = "cert.pem"
        SSL.key_file = "key.pem"
        assert client._ai_cert() == ("cert.pem", "key.pem")

    def test_ai_cert_ssl_partial(self):
        SSL.use_ssl = True
        SSL.cert_file = "cert.pem"
        SSL.key_file = None
        assert client._ai_cert() is None


class TestAiChatStream:
    @patch("wy_qcos_client.client.requests.post")
    def test_chat_stream_success(self, mock_post):
        resp = _mock_response(200, None, "ok")
        mock_post.return_value = resp
        ret = client.ai_chat_stream("hi", session_id="s1")
        assert ret is resp
        args, kwargs = mock_post.call_args
        assert args[0].endswith("/v1/ai/chat")
        assert kwargs["stream"] is True
        payload = kwargs["json"]
        assert payload["message"] == "hi"
        assert payload["session_id"] == "s1"
        assert payload["enable_rag"] is True

    @patch("wy_qcos_client.client.requests.post")
    def test_chat_stream_failure_raises(self, mock_post):
        resp = _mock_response(500, None, "server error")
        mock_post.return_value = resp
        with pytest.raises(errors.GenericException, match="500"):
            client.ai_chat_stream("hi")
        resp.close.assert_called()

    @patch("wy_qcos_client.client.requests.post")
    def test_chat_stream_custom_timeout(self, mock_post):
        resp = _mock_response(200, None, "ok")
        mock_post.return_value = resp
        client.ai_chat_stream("hi", timeout=5)
        assert mock_post.call_args.kwargs["timeout"] == 5


class TestAiSessions:
    @patch("wy_qcos_client.client.requests.get")
    def test_list_sessions_success(self, mock_get):
        mock_get.return_value = _mock_response(200, [{"session_id": "s1"}], "")
        ret = client.ai_list_sessions()
        assert ret == [{"session_id": "s1"}]
        assert mock_get.call_args.args[0].endswith("/v1/ai/sessions")

    @patch("wy_qcos_client.client.requests.get")
    def test_list_sessions_failure(self, mock_get):
        mock_get.return_value = _mock_response(404, None, "nf")
        with pytest.raises(errors.GenericException, match="404"):
            client.ai_list_sessions()

    @patch("wy_qcos_client.client.requests.post")
    def test_create_session_success(self, mock_post):
        mock_post.return_value = _mock_response(
            200, {"session_id": "s2", "title": "t"}, ""
        )
        ret = client.ai_create_session(title="t")
        assert ret["session_id"] == "s2"
        assert mock_post.call_args.kwargs["json"] == {"title": "t"}

    @patch("wy_qcos_client.client.requests.post")
    def test_create_session_failure(self, mock_post):
        mock_post.return_value = _mock_response(500, None, "err")
        with pytest.raises(errors.GenericException, match="500"):
            client.ai_create_session()

    @patch("wy_qcos_client.client.requests.get")
    def test_get_session_success(self, mock_get):
        mock_get.return_value = _mock_response(
            200, {"session": {}, "messages": []}, ""
        )
        ret = client.ai_get_session("s1")
        assert ret["messages"] == []
        assert mock_get.call_args.args[0].endswith("/v1/ai/sessions/s1")

    @patch("wy_qcos_client.client.requests.get")
    def test_get_session_failure(self, mock_get):
        mock_get.return_value = _mock_response(404, None, "nf")
        with pytest.raises(errors.GenericException, match="404"):
            client.ai_get_session("s1")

    @patch("wy_qcos_client.client.requests.delete")
    def test_delete_session_success(self, mock_delete):
        mock_delete.return_value = _mock_response(
            200, {"status": "deleted"}, ""
        )
        ret = client.ai_delete_session("s1")
        assert ret["status"] == "deleted"
        assert mock_delete.call_args.args[0].endswith("/v1/ai/sessions/s1")

    @patch("wy_qcos_client.client.requests.delete")
    def test_delete_session_failure(self, mock_delete):
        mock_delete.return_value = _mock_response(500, None, "err")
        with pytest.raises(errors.GenericException, match="500"):
            client.ai_delete_session("s1")


class TestClientInitSsl:
    def test_init_with_ssl_sets_https_urls(self):
        c = Client(use_ssl=True)
        assert c.version_url.startswith("https://")
        assert c.auth_url.startswith("https://")

    def test_init_plain_http_urls(self):
        c = Client()
        assert c.version_url.startswith("http://")
        assert c.version_url.endswith("/version")

    def test_init_sets_ssl_fields(self):
        SSL.use_ssl = False
        Client(
            use_ssl=True,
            ssl_certfile="cert",
            ssl_keyfile="key",
            ssl_cafile="ca",
        )
        assert SSL.use_ssl is True
        assert SSL.cert_file == "cert"
        assert SSL.key_file == "key"
        assert SSL.ca_file == "ca"
        # reset for other tests
        SSL.use_ssl = False
        SSL.cert_file = None
        SSL.key_file = None
        SSL.ca_file = None
