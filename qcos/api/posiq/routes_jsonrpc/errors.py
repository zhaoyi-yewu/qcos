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

import fastapi_jsonrpc as jsonrpc
from pydantic import BaseModel


@staticmethod
def handle_invalid_params(results):
    """
    Handle invalid params

    :param results: results for jsonrpc
    """
    success, err_msg = results
    if success is False:
        raise InvalidParams(data={"details": "\n".join(err_msg)})


@staticmethod
def handle_submit_error(err_msg):
    """
    Handle submit error

    :param err_msg: error msg from task manager
    """

    raise JobSubmitError(data={"details": err_msg})


@staticmethod
def handle_get_status_error(err_msg):
    """
    Handle get status error

    :param err_msg: error msg from task manager
    """

    raise JobGetStatusError(data={"details": err_msg})


@staticmethod
def handle_get_results_error(err_msg):
    """
    Handle get results error

    :param err_msg: error msg from task manager
    """

    raise JobGetResultsError(data={"details": err_msg})


@staticmethod
def handle_list_error(err_msg):
    """
    Handle get results error

    :param err_msg: error msg from task manager
    """

    raise JobListError(data={"details": err_msg})


@staticmethod
def handle_cancel_error(err_msg):
    """
    Handle cancel job error

    :param err_msg: error msg from task manager
    """

    raise JobCancelError(data={"details": err_msg})


@staticmethod
def handle_job_error(err_msg):
    """
    Handle job error

    :param err_msg: error msg
    """

    raise JobError(data={"details": err_msg})


@staticmethod
def handle_device_error(err_msg):
    """
    Handle device error

    :param err_msg: error msg
    """

    raise DeviceError(data={"details": err_msg})


class UnknownError(jsonrpc.BaseError):
    """
    Unknown Error
    """
    CODE = -1
    MESSAGE = "Unknown error"

    class DataModel(BaseModel):
        """
        Data Model
        """
        details: str


class InvalidParams(jsonrpc.BaseError):
    """
    Invalid Params Error
    """
    CODE = -2
    MESSAGE = "Invalid params"

    class DataModel(BaseModel):
        """
        Data Model
        """
        details: str


class JobError(jsonrpc.BaseError):
    """
    Job Error
    """
    CODE = -10
    MESSAGE = "Job error"

    class DataModel(BaseModel):
        """
        Data Model
        """
        details: str


class DeviceError(jsonrpc.BaseError):
    """
    Device Error
    """
    CODE = -20
    MESSAGE = "Device error"

    class DataModel(BaseModel):
        """
        Data Model
        """
        details: str


class JobSubmitError(jsonrpc.BaseError):
    """
    Job Submit Error
    """
    CODE = -100
    MESSAGE = "Job submit error"

    class DataModel(BaseModel):
        """
        Data Model
        """
        details: str


class JobGetStatusError(jsonrpc.BaseError):
    """
    Job Get Status Error
    """
    CODE = -101
    MESSAGE = "Job get status error"

    class DataModel(BaseModel):
        """
        Data Model
        """
        details: str


class JobGetResultsError(jsonrpc.BaseError):
    """
    Job Get Result Error
    """
    CODE = -102
    MESSAGE = "Job get results error"

    class DataModel(BaseModel):
        """
        Data Model
        """
        details: str


class JobListError(jsonrpc.BaseError):
    """
    Job List Error
    """
    CODE = -103
    MESSAGE = "Job list error"

    class DataModel(BaseModel):
        """
        Data Model
        """
        details: str


class JobCancelError(jsonrpc.BaseError):
    """
    Job Cancel Error
    """
    CODE = -104
    MESSAGE = "Job cancel error"

    class DataModel(BaseModel):
        """
        Data Model
        """
        details: str
