#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.api.posiq.routes_jsonrpc.errors import (
    handle_error_bad_requests,
    BadRequestError,
    UnauthorizedError,
    handle_error_unauthorized,
    ForbiddenError,
    handle_error_forbidden,
    NotFoundError,
    handle_error_not_found,
    ConflictError,
    handle_error_conflict,
    InternalServerError,
    handle_error_internal_server,
    handle_error_not_implemented,
    ServiceUnavailableError,
    NotImplementedError,
    handle_error_service_unavailable,
)

module_name = "module_name"
func_name = "func_name"
results = [False, ["err_msg"]]


class TestError:
    def test_handle_error_bad_requests(self):
        with pytest.raises(BadRequestError) as e:
            handle_error_bad_requests(module_name, func_name, results)
        assert "BadRequestError" in str(e)

    def test_handle_error_unauthorized(self):
        with pytest.raises(UnauthorizedError) as e:
            handle_error_unauthorized(module_name, func_name, results)
        assert "UnauthorizedError" in str(e)

    def test_handle_error_forbidden(self):
        with pytest.raises(ForbiddenError) as e:
            handle_error_forbidden(module_name, func_name, results)
        assert "ForbiddenError" in str(e)

    def test_handle_error_not_found(self):
        with pytest.raises(NotFoundError) as e:
            handle_error_not_found(module_name, func_name, results)
        assert "NotFoundError" in str(e)

    def test_handle_error_conflict(self):
        with pytest.raises(ConflictError) as e:
            handle_error_conflict(module_name, func_name, results)
        assert "ConflictError" in str(e)

    def test_handle_error_internal_server(self):
        with pytest.raises(InternalServerError) as e:
            handle_error_internal_server(module_name, func_name, results)
        assert "InternalServerError" in str(e)

    def test_handle_error_not_implemented(self):
        with pytest.raises(NotImplementedError) as e:
            handle_error_not_implemented(module_name, func_name, results)
        assert "NotImplementedError" in str(e)

    def test_handle_error_service_unavailable(self):
        with pytest.raises(ServiceUnavailableError) as e:
            handle_error_service_unavailable(module_name, func_name, results)
        assert "ServiceUnavailableError" in str(e)
