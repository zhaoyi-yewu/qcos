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


from pydantic import BaseModel


class GetDriversRequest(BaseModel):
    """Get Drivers Request.

    Pydantic Model for Get Drivers Request.
    """


class GetDriverRequest(BaseModel):
    """Get Driver Request.

    Pydantic Model for Get Driver Request.
    """

    # driver name
    name: str


class GetDriverResponse(BaseModel):
    """Get Driver Response.

    Pydantic Model for Get Driver Response.
    """

    # driver name
    name: str
    # driver alias name
    alias_name: str | None = None
    # driver version
    version: str
    # driver description
    description: str
    # tech_type
    tech_type: str
    # max_qubits
    max_qubits: int
    # enable transpiler
    enable_transpiler: bool
    # transpiler
    transpiler: str | None
    # supported transpilers
    supported_transpilers: list
    # enable circuit aggregation
    enable_circuit_aggregation: bool
    # supported code types
    supported_code_types: list
    # supported basis gates
    supported_basis_gates: list | None
    # results fetch mode
    results_fetch_mode: str
