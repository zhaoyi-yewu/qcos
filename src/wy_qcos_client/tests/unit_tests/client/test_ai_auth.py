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
    """Create a mocked HTTP response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_data
    return resp


class TestLoginTokenStorage:
    """Cover login() token-storing branches."""

    def setup_method(self):
        """Provide a clean access token state."""
        client.access_token = None

    def teardown_method(self):
        """Clear client and environment tokens after each test."""
        client.access_token = None
        os.environ.pop("QCOS_ACCESS_TOKEN", None)
        os.environ.pop("QCOS_REFRESH_TOKEN", None)

    @patch.object(Client, "call_json_rpc")
    def test_login_stores_tokens(self, mock_call):
        """Test storing access and refresh tokens after login."""
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
        """Test login with a non-dictionary result."""
        mock_call.return_value = (200, "OK", "text", None)
        status, _r, _t, _res = client.login("u", "p")
        assert status == 200
        assert client.access_token is None

    @patch.object(Client, "call_json_rpc")
    def test_login_object_with_get(self, mock_call):
        """Test login with a result object supporting get."""
        obj = {"access_token": _s("at2"), "refresh_token": _s("rt2")}

        class Wrapper:
            """Wrap a dictionary as a login result object."""

            def get(self, key, default=None):
                """Return a value from the wrapped login result."""
                return obj.get(key, default)

        mock_call.return_value = (200, "OK", "text", Wrapper())
        status, _r, _t, _res = client.login("u", "p")
        assert status == 200
        assert client.access_token == _s("at2")

    @patch.object(Client, "call_json_rpc")
    def test_login_missing_tokens(self, mock_call):
        """Test login with tokens missing from the result."""
        mock_call.return_value = (200, "OK", "text", {"foo": "bar"})
        status, _r, _t, _res = client.login("u", "p")
        assert status == 200
        assert client.access_token is None

    @patch.object(Client, "call_json_rpc")
    def test_login_failure_no_store(self, mock_call):
        """Test that failed login does not store tokens."""
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
        """Test swallowing an exception during login token storage."""

        # result whose .get raises -> warning path, no crash
        class Bad:
            """Provide a result object whose getter raises an exception."""

            def get(self, *a, **kw):
                """Raise an error during token retrieval."""
                raise RuntimeError("boom")

        mock_call.return_value = (200, "OK", "text", Bad())
        status, _r, _t, _res = client.login("u", "p")
        assert status == 200

    @patch.object(Client, "call_json_rpc")
    def test_logout_clears_token(self, mock_call):
        """Test clearing the token after successful logout."""
        mock_call.return_value = (200, "OK", "text", {})
        client.set_token("tok")
        status, _r, _t, _res = client.logout()
        assert status == 200
        assert client.get_token() is None

    @patch.object(Client, "call_json_rpc")
    def test_logout_failure_keeps_token(self, mock_call):
        """Test keeping the token after failed logout."""
        mock_call.return_value = (500, "Server Error", "text", {})
        client.set_token("tok")
        status, _r, _t, _res = client.logout()
        assert status == 500
        assert client.get_token() == "tok"


class TestRefreshToken:
    """Cover refresh_token() branches."""

    def teardown_method(self):
        """Clear the refresh token environment state."""
        os.environ.pop("QCOS_REFRESH_TOKEN", None)

    def test_refresh_token_missing_env(self):
        """Test rejecting token refresh without an environment token."""
        os.environ.pop("QCOS_REFRESH_TOKEN", None)
        status, reason, _t, result = client.refresh_token()
        assert status == 401
        assert "No refresh token" in str(result)

    @patch.object(Client, "call_json_rpc")
    def test_refresh_token_stores_new_tokens(self, mock_call):
        """Test storing new tokens after a successful refresh."""
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
        """Test refreshing tokens from an object result."""
        os.environ["QCOS_REFRESH_TOKEN"] = _s("old-rt")

        class Wrapper:
            """Provide token values through a result object interface."""

            def get(self, key, default=None):
                """Return an access or refresh token value."""
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
        """Test preserving the token for a non-dictionary refresh result."""
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
        """Test preserving the token after a failed refresh."""
        os.environ["QCOS_REFRESH_TOKEN"] = _s("old-rt")
        client.set_token("prev")
        mock_call.return_value = (401, "Unauthorized", "text", {})
        status, _r, _t, _res = client.refresh_token()
        assert status == 401
        assert client.get_token() == "prev"


class TestClearToken:
    """Tests for Client token clearing."""

    def test_clear_token(self):
        """Test clearing the client token."""
        client.set_token("x")
        client.clear_token()
        assert client.get_token() is None


class TestAiUrl:
    """Tests for the Client AI URL property."""

    def test_ai_url_property(self):
        """Test the AI URL property."""
        assert client.ai_url.endswith("/v1/ai")


class TestAiHelpers:
    """Cover _ai_headers / _ai_verify / _ai_cert branches."""

    def teardown_method(self):
        """Clear SSL state after each test."""
        SSL.use_ssl = False
        SSL.ca_file = None
        SSL.cert_file = None
        SSL.key_file = None

    def test_ai_headers_plain(self):
        """Test building plain AI request headers."""
        os.environ.pop("QCOS_ACCESS_TOKEN", None)
        os.environ.pop("QCOS_VIRTUAL_INSTANCE_ID", None)
        client.access_token = None
        client.request_headers = None
        headers = client._ai_headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers
        assert "Accept" not in headers

    def test_ai_headers_sse(self):
        """Test adding the server-sent events Accept header."""
        headers = client._ai_headers(accept_sse=True)
        assert headers["Accept"] == "text/event-stream"

    def test_ai_headers_with_token(self):
        """Test adding the instance access token to AI headers."""
        client.access_token = _s("tok")
        try:
            headers = client._ai_headers()
        finally:
            client.access_token = None
        assert headers["Authorization"] == "Bearer " + _s("tok")

    def test_ai_headers_env_token(self):
        """Test adding the environment access token to AI headers."""
        client.access_token = None
        with patch.dict("os.environ", {"QCOS_ACCESS_TOKEN": _s("envtok")}):
            headers = client._ai_headers()
        assert headers["Authorization"] == "Bearer " + _s("envtok")

    def test_ai_headers_env_virtual_instance(self):
        """Test adding the environment virtual instance ID to AI headers."""
        with patch.dict("os.environ", {"QCOS_VIRTUAL_INSTANCE_ID": "vi-9"}):
            headers = client._ai_headers()
        assert headers["x-qcos-virtual-instance-id"] == "vi-9"

    def test_ai_headers_custom_request_headers(self):
        """Test adding custom request headers to AI headers."""
        client.request_headers = {"X-Custom": "1"}
        try:
            headers = client._ai_headers()
        finally:
            client.request_headers = None
        assert headers["X-Custom"] == "1"

    def test_ai_verify_no_ssl(self):
        """Test disabling certificate verification when SSL is disabled."""
        SSL.use_ssl = False
        assert client._ai_verify() is False

    def test_ai_verify_ssl_with_ca(self):
        """Test using the CA file for SSL verification."""
        SSL.use_ssl = True
        SSL.ca_file = "ca.pem"
        assert client._ai_verify() == "ca.pem"

    def test_ai_verify_ssl_without_ca(self):
        """Test disabling verification when SSL has no CA file."""
        SSL.use_ssl = True
        SSL.ca_file = None
        assert client._ai_verify() is False

    def test_ai_cert_no_ssl(self):
        """Test returning no client certificate when SSL is disabled."""
        SSL.use_ssl = False
        assert client._ai_cert() is None

    def test_ai_cert_ssl_full(self):
        """Test returning the SSL client certificate and key."""
        SSL.use_ssl = True
        SSL.cert_file = "cert.pem"
        SSL.key_file = "key.pem"
        assert client._ai_cert() == ("cert.pem", "key.pem")

    def test_ai_cert_ssl_partial(self):
        """Test returning no certificate for partial SSL credentials."""
        SSL.use_ssl = True
        SSL.cert_file = "cert.pem"
        SSL.key_file = None
        assert client._ai_cert() is None


class TestAiChatStream:
    """Tests for Client AI chat streaming."""

    @patch("wy_qcos_client.client.requests.post")
    def test_chat_stream_success(self, mock_post):
        """Test streaming an AI chat request successfully."""
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
        """Test raising an exception for a failed AI chat stream."""
        resp = _mock_response(500, None, "server error")
        mock_post.return_value = resp
        with pytest.raises(errors.GenericException, match="500"):
            client.ai_chat_stream("hi")
        resp.close.assert_called()

    @patch("wy_qcos_client.client.requests.post")
    def test_chat_stream_custom_timeout(self, mock_post):
        """Test passing a custom timeout to an AI chat stream."""
        resp = _mock_response(200, None, "ok")
        mock_post.return_value = resp
        client.ai_chat_stream("hi", timeout=5)
        assert mock_post.call_args.kwargs["timeout"] == 5

    @patch("wy_qcos_client.client.requests.post")
    def test_chat_stream_omits_model_id_by_default(self, mock_post):
        """Legacy request shape: no model_id key unless selected."""
        mock_post.return_value = _mock_response(200, None, "ok")
        client.ai_chat_stream("hi")
        payload = mock_post.call_args.kwargs["json"]
        assert "model_id" not in payload

    @patch("wy_qcos_client.client.requests.post")
    def test_chat_stream_includes_explicit_model_id(self, mock_post):
        """Test including an explicit model ID in an AI chat request."""
        mock_post.return_value = _mock_response(200, None, "ok")
        client.ai_chat_stream("hi", model_id="kimi-k3")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["model_id"] == "kimi-k3"


class TestAiModels:
    """Tests for Client AI model listing."""

    @patch("wy_qcos_client.client.requests.get")
    def test_list_models_success(self, mock_get):
        """Test listing AI models successfully."""
        data = {
            "default_model_id": "a",
            "models": [
                {
                    "id": "a",
                    "display_name": "A",
                    "model": "m-a",
                    "supports_vision": True,
                }
            ],
        }
        mock_get.return_value = _mock_response(200, data, "")
        ret = client.ai_list_models()
        assert ret["default_model_id"] == "a"
        assert ret["models"][0]["supports_vision"] is True
        assert mock_get.call_args.args[0].endswith("/v1/ai/models")

    @patch("wy_qcos_client.client.requests.get")
    def test_list_models_failure(self, mock_get):
        """Test raising an exception when listing AI models fails."""
        mock_get.return_value = _mock_response(404, None, "nf")
        with pytest.raises(errors.GenericException, match="404"):
            client.ai_list_models()


class TestAiSessions:
    """Tests for Client AI session management."""

    @patch("wy_qcos_client.client.requests.get")
    def test_list_sessions_success(self, mock_get):
        """Test listing AI sessions successfully."""
        mock_get.return_value = _mock_response(200, [{"session_id": "s1"}], "")
        ret = client.ai_list_sessions()
        assert ret == [{"session_id": "s1"}]
        assert mock_get.call_args.args[0].endswith("/v1/ai/sessions")

    @patch("wy_qcos_client.client.requests.get")
    def test_list_sessions_failure(self, mock_get):
        """Test raising an exception when listing AI sessions fails."""
        mock_get.return_value = _mock_response(404, None, "nf")
        with pytest.raises(errors.GenericException, match="404"):
            client.ai_list_sessions()

    @patch("wy_qcos_client.client.requests.post")
    def test_create_session_success(self, mock_post):
        """Test creating an AI session successfully."""
        mock_post.return_value = _mock_response(
            200, {"session_id": "s2", "title": "t"}, ""
        )
        ret = client.ai_create_session(title="t")
        assert ret["session_id"] == "s2"
        assert mock_post.call_args.kwargs["json"] == {"title": "t"}

    @patch("wy_qcos_client.client.requests.post")
    def test_create_session_failure(self, mock_post):
        """Test raising an exception when creating an AI session fails."""
        mock_post.return_value = _mock_response(500, None, "err")
        with pytest.raises(errors.GenericException, match="500"):
            client.ai_create_session()

    @patch("wy_qcos_client.client.requests.get")
    def test_get_session_success(self, mock_get):
        """Test getting an AI session successfully."""
        mock_get.return_value = _mock_response(
            200, {"session": {}, "messages": []}, ""
        )
        ret = client.ai_get_session("s1")
        assert ret["messages"] == []
        assert mock_get.call_args.args[0].endswith("/v1/ai/sessions/s1")

    @patch("wy_qcos_client.client.requests.get")
    def test_get_session_failure(self, mock_get):
        """Test raising an exception when getting an AI session fails."""
        mock_get.return_value = _mock_response(404, None, "nf")
        with pytest.raises(errors.GenericException, match="404"):
            client.ai_get_session("s1")

    @patch("wy_qcos_client.client.requests.delete")
    def test_delete_session_success(self, mock_delete):
        """Test deleting an AI session successfully."""
        mock_delete.return_value = _mock_response(
            200, {"status": "deleted"}, ""
        )
        ret = client.ai_delete_session("s1")
        assert ret["status"] == "deleted"
        assert mock_delete.call_args.args[0].endswith("/v1/ai/sessions/s1")

    @patch("wy_qcos_client.client.requests.delete")
    def test_delete_session_failure(self, mock_delete):
        """Test raising an exception when deleting an AI session fails."""
        mock_delete.return_value = _mock_response(500, None, "err")
        with pytest.raises(errors.GenericException, match="500"):
            client.ai_delete_session("s1")


class TestClientInitSsl:
    """Tests for Client SSL initialization."""

    def test_init_with_ssl_sets_https_urls(self):
        """Test using HTTPS URLs when SSL is enabled."""
        c = Client(use_ssl=True)
        assert c.version_url.startswith("https://")
        assert c.auth_url.startswith("https://")

    def test_init_plain_http_urls(self):
        """Test using plain HTTP URLs by default."""
        c = Client()
        assert c.version_url.startswith("http://")
        assert c.version_url.endswith("/version")

    def test_init_sets_ssl_fields(self):
        """Test setting global SSL fields during initialization."""
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
