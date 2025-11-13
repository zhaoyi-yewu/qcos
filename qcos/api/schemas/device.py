#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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


class GetDevicesRequest(BaseModel):
    """Get Devices Request
    Pydantic Model for Get Devices Request
    """


class GetDeviceRequest(BaseModel):
    """Get Device Request
    Pydantic Model for Get Device Request
    """

    # device name
    name: str


class GetDeviceResponse(BaseModel):
    """Get Device Response
    Pydantic Model for Get Device Response
    """

    # device name
    name: str
    # device alias name
    alias_name: str | None = None
    # description
    description: str | None = None
    # driver name
    driver_name: str
    # device enable
    enable: bool
    # device status
    status: str
    # tech type
    tech_type: str
    # max qubits
    max_qubits: int
    # configs
    configs: dict | None = None
