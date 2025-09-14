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
    """Get Devices Request
    Pydantic Model for Get Devices Request
    """


class GetDeviceRequest(BaseModel):
    """Get Device Request
    Pydantic Model for Get Device Request
    """
    # device name
    name: str = None


class GetDeviceResponse(BaseModel):
    """Get Device Response
    Pydantic Model for Get Device Response
    """
    # device name
    name: str = None
    # device alias name
    alias_name: str = None
    # description
    description: Optional[str] = None
    # driver name
    driver_name: str = None
    # device enable
    enable: bool = None
    # device status
    status: str = None
    # configs
    configs: Optional[dict] = None
