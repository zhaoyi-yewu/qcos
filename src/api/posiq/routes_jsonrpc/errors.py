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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import fastapi_jsonrpc as jsonrpc
from pydantic import BaseModel


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
        details: None


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
        details: None
