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


class GetDevicesRequest(BaseModel):
    """
    Get Devices Request
    Pydantic Model for Get Devices Request
    """


class GetDeviceRequest(BaseModel):
    """
    Get Device Request
    Pydantic Model for Get Device Request
    """
    # device name
    name: str = None


class GetDeviceResponse(BaseModel):
    """
    Get Device Response
    Pydantic Model for Get Device Response
    """
    # device name
    name: str = None
    # device version
    version: Optional[str] = None
    # device driver
    driver: str = None
    # device description
    description: Optional[str] = None
    # device enable
    enable: bool = None
    # device tech_type
    tech_type: Optional[str] = None
    # device max_qubits
    max_qubits: int = None
    # enable transpiler
    enable_transpiler: Optional[bool] = None
    # device transpiler
    transpiler: Optional[str] = None
    # supported transpilers
    supported_transpilers: Optional[list] = None
    # enable circuit merge
    enable_circuit_merge: Optional[bool] = None
    # supported code types
    supported_code_types: Optional[list] = None
    # supported basis gates
    supported_basis_gates: Optional[list] = None
    # results fetch mode
    results_fetch_mode: Optional[str] = None
    # extra configs
    extra_configs: Optional[dict] = None
