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

from pydantic import BaseModel, Field


class GetVersionRequest(BaseModel):
    """Get Version Request.

    Pydantic Model for Get Version Request.
    """


class GetVersionResponse(BaseModel):
    """Get Version Response.

    Pydantic Model for Get Version Response.
    """

    # version
    version: str = Field(..., description="version")
    api_version: str = Field(..., description="api version")
    supported_api_versions: list[dict] = Field(
        ..., description="supported api versions"
    )
    platform_version: str = Field(..., description="platform version")
    capabilities: dict = Field(..., description="capabilities")
