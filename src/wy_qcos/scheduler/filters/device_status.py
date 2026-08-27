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

import logging

from wy_qcos.device.device import Device
from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.request_spec import RequestSpec
from .base import BaseFilter

logger = logging.getLogger(__name__)


class DeviceStatusFilter(BaseFilter):
    """Filter devices by online status.

    Only enabled devices with status online or busy are eligible.
    Devices that are disabled, offline, disconnected, calibrating,
    or in maintain mode are filtered out.
    """

    # Statuses that allow job submission
    _ALLOWED_STATUSES = [
        Device.DEVICE_STATUS_ONLINE,
        Device.DEVICE_STATUS_BUSY,
    ]

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        logger.debug(
            f"DeviceStatusFilter: device_name: {obj.name}. "
            f"obj.enable: {obj.enable}, "
            f"obj.status: {obj.status}, "
            f"allowed_statuses: {self._ALLOWED_STATUSES}"
        )

        if not obj.enable:
            return False

        return obj.status in self._ALLOWED_STATUSES
