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


class GetTranspilersRequest(BaseModel):
    """Get Transpilers Request.

    Pydantic Model for Get Transpilers Request.
    """


class GetTranspilerRequest(BaseModel):
    """Get Transpiler Request.

    Pydantic Model for Get Transpiler Request.
    """

    # transpiler name
    name: str = Field(..., description="transpiler name")


class GetTranspilerResponse(BaseModel):
    """Get Transpiler Response.

    Pydantic Model for Get Transpiler Response.
    """

    # transpiler name
    name: str = Field(..., description="transpiler name")
    # transpiler alias name
    alias_name: str | None = Field(None, description="transpiler alias name")
    # version
    version: str | None = Field(None, description="version")
    # enable this transpiler or not
    enable: bool = Field(True, description="enable this transpiler or not")
    # supported code types
    supported_code_types: list = Field(
        default_factory=list, description="supported code types"
    )
    # transpiler_options
    transpiler_options: dict | None = Field(
        None, description="transpiler_options"
    )
    # transpiler_options schema
    transpiler_options_schema: dict | None = Field(
        None, description="transpiler_options schema"
    )
