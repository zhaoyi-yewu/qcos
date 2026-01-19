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


class GetDriversRequest(BaseModel):
    """Get Drivers Request.

    Pydantic Model for Get Drivers Request.
    """


class GetDriverRequest(BaseModel):
    """Get Driver Request.

    Pydantic Model for Get Driver Request.
    """

    # driver name
    name: str = Field(description="Driver name")


class GetDriverResponse(BaseModel):
    """Get Driver Response.

    Pydantic Model for Get Driver Response.
    """

    # driver name
    name: str = Field(description="Driver name")
    # driver alias name
    alias_name: str | None = Field(
        default=None, description="Driver alias name"
    )
    # driver version
    version: str = Field(description="Driver version")
    # driver description
    description: str = Field(description="Driver description")
    # tech_type
    tech_type: str = Field(description="Technology type")
    # max_qubits
    max_qubits: int = Field(description="Maximum number of qubits")
    # enable transpiler
    enable_transpiler: bool = Field(description="Enable transpiler")
    # transpiler
    transpiler: str | None = Field(default=None, description="Transpiler")
    # supported transpilers
    supported_transpilers: list = Field(description="Supported transpilers")
    # enable circuit aggregation
    enable_circuit_aggregation: bool = Field(
        description="Enable circuit aggregation"
    )
    # supported code types
    supported_code_types: list = Field(description="Supported code types")
    # supported basis gates
    supported_basis_gates: list | None = Field(
        default=None, description="Supported basis gates"
    )
    # results fetch mode
    results_fetch_mode: str = Field(description="Results fetch mode")
