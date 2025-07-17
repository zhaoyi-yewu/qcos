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

from pydantic import BaseModel


class PingRequest(BaseModel):
    """
    Ping Request
    Pydantic Model for Ping Request
    """
    # message
    message: str = None


class PongResponse(BaseModel):
    """
    Pong Response
    Pydantic Model for Pong Response
    """
    # message
    message: str = None


class VersionRequest(BaseModel):
    """
    Version Request
    Pydantic Model for Version Request
    """


class VersionResponse(BaseModel):
    """
    Version Response
    Pydantic Model for Version Response
    """
    # version
    version: str
    api_version: str
    supported_api_versions: list[dict]
    platform_version: str
