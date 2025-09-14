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

from typing import Optional

from pydantic import BaseModel


class GetTranspilersRequest(BaseModel):
    """Get Transpilers Request
    Pydantic Model for Get Transpilers Request
    """


class GetTranspilerRequest(BaseModel):
    """Get Transpiler Request
    Pydantic Model for Get Transpiler Request
    """
    # transpiler name
    name: str = None


class GetTranspilerResponse(BaseModel):
    """Get Transpiler Response
    Pydantic Model for Get Transpiler Response
    """
    # transpiler name
    name: str = None
    # transpiler alias name
    alias_name: str = None
    # version
    version: str = None
    # enable this transpiler or not
    enable: bool = True
    # supported code types
    supported_code_types: list = []
    # transpiler_options
    transpiler_options: Optional[dict] = None
    # transpiler_options schema
    transpiler_options_schema: Optional[dict] = None
