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

"""
JSON-RPC/RestfulAPI error-code mappings

==============================================================================
|err_code|http_code | Description         | Examples / Scenarios             |
==============================================================================
| 0      | 2XX      |Accepted/OK          |success                           |
| -400   | 400      |Bad Request          |invalid params / request          |
| -401   | 401      |Unauthorized         |unauthorized login / token        |
| -403   | 403      |Forbidden            |unauthorized operations           |
| -404   | 404      |Not Found            |resource not found                |
| -409   | 409      |Conflict             |create duplicated resource name/id|
|        |          |                     |resource deps not met             |
| -500   | 500      |Internal Server Error|bug / exception                   |
| -501   | 501      |Not Implemented      |not implemented                   |
| -503   | 503      |Service Unavailable  |service offline                   |
==============================================================================
"""

import fastapi_jsonrpc as jsonrpc
from pydantic import BaseModel


class JsonRpcBaseError(jsonrpc.BaseError):
    """
    JsonRpc Base Error
    """

    class DataModel(BaseModel):
        """
        Data Model
        """
        details: str


class BadRequestError(JsonRpcBaseError):
    """
    Bad Request Error
    """
    CODE = -400
    MESSAGE = "Bad Request"


class UnauthorizedError(JsonRpcBaseError):
    """
    Unauthorized Error
    """
    CODE = -401
    MESSAGE = "Unauthorized"


class ForbiddenError(JsonRpcBaseError):
    """
    Forbidden Error
    """
    CODE = -403
    MESSAGE = "Forbidden"


class NotFoundError(JsonRpcBaseError):
    """
    Not Found Error
    """
    CODE = -404
    MESSAGE = "Not Found"


class ConflictError(JsonRpcBaseError):
    """
    Conflict Error
    """
    CODE = -409
    MESSAGE = "Conflict"


class InternalServerError(JsonRpcBaseError):
    """
    Internal Server Error
    """
    CODE = -500
    MESSAGE = "Internal Server Error"


class NotImplementedError(JsonRpcBaseError):
    """
    Not Implemented Error
    """
    CODE = -501
    MESSAGE = "Not Implemented"


class ServiceUnavailableError(JsonRpcBaseError):
    """
    Service Unavailable Error
    """
    CODE = -503
    MESSAGE = "Service Unavailable"


def handle_errors(err_cls, module_name, func_name, results, param_name, code):
    """
    Handle errors

    :param err_cls: error class
    :param module_name: module name
    :param func_name: function name
    :param results: results for jsonrpc
    :param param_name: name of the param
    :param code: error code
    """
    success, err_msg = results
    if success is False:
        param_str = ""
        if param_name:
            param_str = f"{param_name}: "

        details = f"{param_str}{err_msg}"
        if isinstance(err_msg, list):
            details = f"{param_str}{';'.join(err_msg)}"

        error = err_cls(
            data={"details": details}
        )
        if code:
            error.CODE = code
        error.MESSAGE = f"[{module_name}] Failed to {func_name}"
        raise error


@staticmethod
def handle_error_bad_requests(
        module_name, func_name, results, param_name=None, code=None):
    """
    Handle bad_requests error

    :param module_name: module name
    :param func_name: function name
    :param results: results for jsonrpc
    :param param_name: name of the param
    :param code: error code
    """
    return handle_errors(
        BadRequestError,
        module_name,
        func_name,
        results,
        param_name,
        code)


def handle_error_unauthorized(
        module_name, func_name, results, param_name=None, code=None):
    """
    Handle unauthorized error

    :param module_name: module name
    :param func_name: function name
    :param results: results for jsonrpc
    :param param_name: name of the param
    :param code: error code
    """
    return handle_errors(
        UnauthorizedError,
        module_name,
        func_name,
        results,
        param_name,
        code)


def handle_error_forbidden(
        module_name, func_name, results, param_name=None, code=None):
    """
    Handle forbidden error

    :param module_name: module name
    :param func_name: function name
    :param results: results for jsonrpc
    :param param_name: name of the param
    :param code: error code
    """
    return handle_errors(
        ForbiddenError,
        module_name,
        func_name,
        results,
        param_name,
        code)


def handle_error_not_found(
        module_name, func_name, results, param_name=None, code=None):
    """
    Handle forbidden error

    :param module_name: module name
    :param func_name: function name
    :param results: results for jsonrpc
    :param param_name: name of the param
    :param code: error code
    """
    return handle_errors(
        NotFoundError,
        module_name,
        func_name,
        results,
        param_name,
        code)


def handle_error_conflict(
        module_name, func_name, results, param_name=None, code=None):
    """
    Handle conflict error

    :param module_name: module name
    :param func_name: function name
    :param results: results for jsonrpc
    :param param_name: name of the param
    :param code: error code
    """
    return handle_errors(
        ConflictError,
        module_name,
        func_name,
        results,
        param_name,
        code)


def handle_error_internal_server(
        module_name, func_name, results, param_name=None, code=None):
    """
    Handle internal server error

    :param module_name: module name
    :param func_name: function name
    :param results: results for jsonrpc
    :param param_name: name of the param
    :param code: error code
    """
    return handle_errors(
        InternalServerError,
        module_name,
        func_name,
        results,
        param_name,
        code)


def handle_error_not_implemented(
        module_name, func_name, results, param_name=None, code=None):
    """
    Handle not implemented error

    :param module_name: module name
    :param func_name: function name
    :param results: results for jsonrpc
    :param param_name: name of the param
    :param code: error code
    """
    return handle_errors(
        NotImplementedError,
        module_name,
        func_name,
        results,
        param_name,
        code)


def handle_error_service_unavailable(
        module_name, func_name, results, param_name=None, code=None):
    """
    Handle service unavailable error

    :param module_name: module name
    :param func_name: function name
    :param results: results for jsonrpc
    :param param_name: name of the param
    :param code: error code
    """
    return handle_errors(
        ServiceUnavailableError,
        module_name,
        func_name,
        results,
        param_name,
        code)
