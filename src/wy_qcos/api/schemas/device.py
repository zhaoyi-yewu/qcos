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


class GetDevicesRequest(BaseModel):
    """Get Devices Request.

    Pydantic Model for Get Devices Request.
    """


class GetDeviceRequest(BaseModel):
    """Get Device Request.

    Pydantic Model for Get Device Request.
    """

    # device name
    name: str = Field(description="Device name")


class GetDeviceResponse(BaseModel):
    """Get Device Response.

    Pydantic Model for Get Device Response.
    """

    # device name
    name: str = Field(description="Device name")
    # device alias name
    alias_name: str | None = Field(
        default=None, description="Device alias name"
    )
    # description
    description: str | None = Field(default=None, description="Description")
    # driver name
    driver_name: str = Field(description="Driver name")
    # device enable
    enable: bool = Field(description="Device enable status")
    # device status
    status: str = Field(description="Device status")
    # tech type
    tech_type: str = Field(description="Technology type")
    # max qubits
    max_qubits: int = Field(description="Maximum number of qubits")
    # configs
    configs: dict | None = Field(
        default=None, description="Device configurations"
    )
