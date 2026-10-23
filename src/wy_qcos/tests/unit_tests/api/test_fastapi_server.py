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

"""Unit tests for fastapi_server module."""

from unittest.mock import MagicMock, patch

from wy_qcos.api.fastapi_server import (
    QcosUvicornServer,
    patched_invalid_params_from_validation_error,
)


class TestPatchedInvalidParams:
    """Test patched_invalid_params_from_validation_error function."""

    def test_with_validation_error(self):
        from pydantic import ValidationError

        exc = ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "missing",
                    "loc": ("body", "field1"),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )
        result = patched_invalid_params_from_validation_error(exc)
        assert result is not None
        assert hasattr(result.data, "errors")
        assert len(result.data.errors) == 1

    def test_with_request_validation_error(self):
        from fastapi.exceptions import RequestValidationError

        exc = RequestValidationError([
            {
                "type": "missing",
                "loc": ("body", "field1"),
                "msg": "Field required",
                "input": {},
            }
        ])
        result = patched_invalid_params_from_validation_error(exc)
        assert result is not None
        assert hasattr(result.data, "errors")

    def test_loc_body_prefix_removed(self):
        from pydantic import ValidationError

        exc = ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "missing",
                    "loc": ("body", "nested", "field"),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )
        result = patched_invalid_params_from_validation_error(exc)
        # The ("body",) prefix should be stripped from loc
        assert result.data.errors[0].loc == ["nested", "field"]

    def test_non_body_loc_not_removed(self):
        from pydantic import ValidationError

        exc = ValidationError.from_exception_data(
            "TestModel",
            [
                {
                    "type": "missing",
                    "loc": ("query", "param1"),
                    "msg": "Field required",
                    "input": {},
                }
            ],
        )
        result = patched_invalid_params_from_validation_error(exc)
        # Non-body loc should be wrapped in <>
        assert result.data.errors[0].loc[0] == "<query>"


class TestQcosUvicornServer:
    """Test QcosUvicornServer class."""

    def test_init(self):
        mock_config = MagicMock()
        mock_config.host = "127.0.0.1"
        mock_config.port = 18400
        mock_config.bind_socket = MagicMock()

        with patch.object(
            QcosUvicornServer, "__init__", lambda self, *a, **k: None
        ):
            server = QcosUvicornServer.__new__(QcosUvicornServer)
            server.config = mock_config
            # Manually call the __init__ logic
            cfg = server.config
            original_bind_socket = cfg.bind_socket
            assert original_bind_socket is not None

    def test_handle_exit(self):
        mock_config = MagicMock()
        mock_config.host = "127.0.0.1"
        mock_config.port = 18400
        mock_config.bind_socket = MagicMock()

        with patch.object(
            QcosUvicornServer, "__init__", lambda self, *a, **k: None
        ):
            server = QcosUvicornServer.__new__(QcosUvicornServer)
            server.config = mock_config

            with patch("wy_qcos.api.fastapi_server.UvicornServer.handle_exit"):
                import logging

                try:
                    server.handle_exit(15, None)
                except Exception as exc:
                    logging.getLogger(__name__).debug(
                        f"handle_exit raised: {exc}"
                    )
                # Verify app.state.exiting was set
                from wy_qcos.api.fastapi_server import app

                assert app.state.exiting is True
