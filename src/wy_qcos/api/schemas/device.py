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
    # need details or not
    details: bool = Field(description="Details info needed or not")


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
    # device status timestamp
    timestamp: str = Field(description="Device status timestamp")
    # tech type
    tech_type: str = Field(description="Technology type")
    # max qubits
    max_qubits: int = Field(description="Maximum number of qubits")
    # configs
    configs: dict | None = Field(
        default=None, description="Device configurations"
    )
    # details info
    details: dict | None = Field(default=None, description="Details info")


class CalibrateDeviceRequest(BaseModel):
    """Calibrate Device.

    Pydantic Model for Get Calibrate Device.
    """

    # device name
    device_name: str = Field(description="Device name")
    # method
    method: str = Field(description="method name")
    # calibrate options
    options: dict | None = Field(default=None, description="Calibrate Options")


class CalibrateDeviceResponse(BaseModel):
    """Get Calibrate Device Response.

    Pydantic Model for Get Calibrate Device Response.
    """

    # calibrate response detail
    details: dict | None = Field(
        default=None, description="Calibrate Response details"
    )


class GetCalibrateResultRequest(BaseModel):
    """Get Calibrate Result Request.

    Pydantic Model for Get Calibrate Result.
    """

    # device name
    device_name: str = Field(description="Device name")
    # method
    method: str = Field(description="method name")


class GetCalibrateResultResponse(BaseModel):
    """Get Calibrate Result Response.

    Pydantic Model for Get Calibrate Result.
    """

    # get calibrate result detail
    details: dict | None = Field(
        default=None, description="Calibrate Response details"
    )


class SetDeviceOptionsRequest(BaseModel):
    """Set Device Options.

    Pydantic Model for Set Device Options.
    """

    # device name
    device_name: str = Field(description="Device name")
    # method
    method: str = Field(description="method name")
    # set options
    options: dict | None = Field(default=None, description="Device Options")


class SetDeviceOptionsResponse(BaseModel):
    """Set Device Options Response.

    Pydantic Model for Set Device Options Response.
    """

    # calibrate response detail
    details: dict | None = Field(
        default=None, description="Set Device Options Response details"
    )


class GetDeviceOptionsRequest(BaseModel):
    """Get Device Options Request.

    Pydantic Model for Get Device Options Request.
    """

    # device name
    device_name: str = Field(description="Device name")
    # method
    method: str = Field(description="method name")


class GetDeviceOptionsResponse(BaseModel):
    """Get Device Options Response.

    Pydantic Model for Get Device Options Response.
    """

    # get calibrate result detail
    details: dict | None = Field(
        default=None, description="Get Device Options Response details"
    )
