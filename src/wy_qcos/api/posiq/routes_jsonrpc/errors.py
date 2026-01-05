#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

"""JSON-RPC/RestfulAPI error-code mappings.

Error codes mappings and descriptions:
.. code-block:: text

    +--------+----------+---------------------+-------------------------------+
    |err_code|http_code | Description         | Examples / Scenarios          |
    +========+==========+=====================+===============================+
    | 0      | 2XX      |Accepted / OK        |success                        |
    | -400   | 400      |Bad Request          |invalid params / request       |
    | -401   | 401      |Unauthorized         |unauthorized login / token     |
    | -403   | 403      |Forbidden            |unauthorized operations        |
    | -404   | 404      |Not Found            |resource not found             |
    | -409   | 409      |Conflict             |create duplicated resource name|
    |        |          |                     |resource deps not met          |
    | -500   | 500      |Internal Server Error|bug / exception                |
    | -501   | 501      |Not Implemented      |not implemented                |
    | -503   | 503      |Service Unavailable  |service offline                |
    +--------+----------+---------------------+-------------------------------+
"""

import fastapi_jsonrpc as jsonrpc
from pydantic import BaseModel

from wy_qcos.common.constant import HttpCode


class JsonRpcBaseError(jsonrpc.BaseError):
    """JsonRpc Base Error."""

    class DataModel(BaseModel):
        """Data Model."""

        details: str


class BadRequestError(JsonRpcBaseError):
    """Bad Request Error."""

    CODE = -HttpCode.BAD_REQUEST_ERROR
    MESSAGE = "Bad Request"


class UnauthorizedError(JsonRpcBaseError):
    """Unauthorized Error."""

    CODE = -HttpCode.UNAUTHORIZED_ERROR
    MESSAGE = "Unauthorized"


class ForbiddenError(JsonRpcBaseError):
    """Forbidden Error."""

    CODE = -HttpCode.FORBIDDEN_ERROR
    MESSAGE = "Forbidden"


class NotFoundError(JsonRpcBaseError):
    """Not Found Error."""

    CODE = -HttpCode.NOT_FOUND_ERROR
    MESSAGE = "Not Found"


class ConflictError(JsonRpcBaseError):
    """Conflict Error."""

    CODE = -HttpCode.CONFLICT_ERROR
    MESSAGE = "Conflict"


class InternalServerError(JsonRpcBaseError):
    """Internal Server Error."""

    CODE = -HttpCode.INTERNAL_SERVER_ERROR
    MESSAGE = "Internal Server Error"


class NotImplementedError(JsonRpcBaseError):
    """Not Implemented Error."""

    CODE = -HttpCode.NOT_IMPLEMENTED_ERROR
    MESSAGE = "Not Implemented"


class ServiceUnavailableError(JsonRpcBaseError):
    """Service Unavailable Error."""

    CODE = -HttpCode.SERVICE_UNAVAILABLE_ERROR
    MESSAGE = "Service Unavailable"


def handle_errors(err_cls, module_name, func_name, results, param_name, code):
    """Handle errors.

    Args:
        err_cls: error class
        module_name: module name
        func_name: function name
        results: results for jsonrpc
        param_name: name of the param
        code: error code
    """
    success, err_msg = results
    if success is False:
        param_str = ""
        if param_name:
            param_str = f"{param_name}: "

        details = f"{param_str}{err_msg}"
        if isinstance(err_msg, list):
            details = f"{param_str}{';'.join(err_msg)}"

        error = err_cls(data={"details": details})
        if code:
            error.CODE = code
        error.MESSAGE = f"[{module_name}] Failed to {func_name}"
        raise error


def handle_error_bad_requests(
    module_name, func_name, results, param_name=None, code=None
):
    """Handle bad_requests error.

    Args:
        module_name: module name
        func_name: function name
        results: results for jsonrpc
        param_name: name of the param (Default value = None)
        code: error code (Default value = None)
    """
    return handle_errors(
        BadRequestError, module_name, func_name, results, param_name, code
    )


def handle_error_unauthorized(
    module_name, func_name, results, param_name=None, code=None
):
    """Handle unauthorized error.

    Args:
        module_name: module name
        func_name: function name
        results: results for jsonrpc
        param_name: name of the param (Default value = None)
        code: error code (Default value = None)
    """
    return handle_errors(
        UnauthorizedError, module_name, func_name, results, param_name, code
    )


def handle_error_forbidden(
    module_name, func_name, results, param_name=None, code=None
):
    """Handle forbidden error.

    Args:
        module_name: module name
        func_name: function name
        results: results for jsonrpc
        param_name: name of the param (Default value = None)
        code: error code (Default value = None)
    """
    return handle_errors(
        ForbiddenError, module_name, func_name, results, param_name, code
    )


def handle_error_not_found(
    module_name, func_name, results, param_name=None, code=None
):
    """Handle forbidden error.

    Args:
        module_name: module name
        func_name: function name
        results: results for jsonrpc
        param_name: name of the param (Default value = None)
        code: error code (Default value = None)
    """
    return handle_errors(
        NotFoundError, module_name, func_name, results, param_name, code
    )


def handle_error_conflict(
    module_name, func_name, results, param_name=None, code=None
):
    """Handle conflict error.

    Args:
        module_name: module name
        func_name: function name
        results: results for jsonrpc
        param_name: name of the param (Default value = None)
        code: error code (Default value = None)
    """
    return handle_errors(
        ConflictError, module_name, func_name, results, param_name, code
    )


def handle_error_internal_server(
    module_name, func_name, results, param_name=None, code=None
):
    """Handle internal server error.

    Args:
        module_name: module name
        func_name: function name
        results: results for jsonrpc
        param_name: name of the param (Default value = None)
        code: error code (Default value = None)
    """
    return handle_errors(
        InternalServerError, module_name, func_name, results, param_name, code
    )


def handle_error_not_implemented(
    module_name, func_name, results, param_name=None, code=None
):
    """Handle not implemented error.

    Args:
        module_name: module name
        func_name: function name
        results: results for jsonrpc
        param_name: name of the param (Default value = None)
        code: error code (Default value = None)
    """
    return handle_errors(
        NotImplementedError, module_name, func_name, results, param_name, code
    )


def handle_error_service_unavailable(
    module_name, func_name, results, param_name=None, code=None
):
    """Handle service unavailable error.

    Args:
        module_name: module name
        func_name: function name
        results: results for jsonrpc
        param_name: name of the param (Default value = None)
        code: error code (Default value = None)
    """
    return handle_errors(
        ServiceUnavailableError,
        module_name,
        func_name,
        results,
        param_name,
        code,
    )
