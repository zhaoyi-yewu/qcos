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

    # need details or not
    details: bool = Field(description="Details info needed or not")


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
    # tech type
    tech_type: str = Field(description="Technology type")
    # max qubits
    max_qubits: int = Field(description="Maximum number of qubits")
    # available_qubits qubits
    available_qubits: int | None = Field(
        default=None,
        description="Maximum number of available qubits",
    )
    # enable device monitor
    enable_device_monitor: bool = Field(
        default=False,
        description="Whether device monitor is enabled",
    )
    # device monitor worker status
    device_monitor_status: str = Field(
        default="unknown",
        description="Device monitor worker status",
    )
    # monitor polling interval (seconds)
    monitor_polling_interval: int = Field(
        default=60,
        description="Device monitor polling interval in seconds",
    )
    # enable device manager
    enable_device_manager: bool = Field(
        default=False,
        description="Whether device manager is enabled",
    )
    # device manager worker status
    device_manager_status: str = Field(
        default="unknown",
        description="Device manager worker status",
    )
    # configs
    configs: dict | None = Field(
        default=None, description="Device configurations"
    )
    # job count by job status (e.g. QUEUED, RUNNING, COMPLETED)
    job_count: dict = Field(
        default_factory=dict,
        description="Job count grouped by job status",
    )
    # device status last updated at
    last_updated_at: str | None = Field(
        default=None, description="Device status last updated at"
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

    # get device options detail
    details: dict | None = Field(
        default=None, description="Get Device Options Response details"
    )


class SetDeviceMaintainModeRequest(BaseModel):
    """Set Device Maintain Mode Request.

    Pydantic Model for Set Device Maintain Mode Request.
    """

    # device name
    device_name: str = Field(description="Device name")
    # maintain mode: on/off
    mode: str = Field(description="Maintain mode: on or off")


class SetDeviceMaintainModeResponse(BaseModel):
    """Set Device Maintain Mode Response.

    Pydantic Model for Set Device Maintain Mode Response.
    """

    # device name
    name: str = Field(description="Device name")
    # device status after operation
    status: str = Field(description="Device status after operation")


class SetDeviceRequest(BaseModel):
    """Set Device Request.

    Pydantic Model for Set Device Request. Allows updating device
    status, enable flag, and max qubits in a single call.

    """

    # device name
    device_name: str = Field(description="Device name")
    # device status: auto/online/offline/busy/calibrating/
    # maintain/unknown
    # None means no change; "auto" also means no change
    status: str | None = Field(
        default=None,
        description="Device status: auto, online, offline, busy, "
        "calibrating, maintain, unknown. "
        "None or 'auto' means no change",
    )
    # enable flag: true/false
    # None means no change
    enable: bool | None = Field(
        default=None,
        description="Enable or disable the device. None means no change",
    )
    # max qubits: "auto" or a positive integer string
    # None means no change
    max_qubits: str | None = Field(
        default=None,
        description="Max qubits: 'auto' to restore driver default, "
        "or a positive integer string. None means no change",
    )


class SetDeviceResponse(BaseModel):
    """Set Device Response.

    Pydantic Model for Set Device Response. Returns the device
    attributes after the operation.

    """

    # device name
    name: str = Field(description="Device name")
    # device status after operation
    status: str = Field(description="Device status after operation")
    # device enable flag after operation
    enable: bool = Field(description="Device enable flag after operation")
    # device max qubits after operation
    max_qubits: int = Field(description="Device max qubits after operation")
