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

from wy_qcos.common.flavor_constant import FlavorConstant
from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.request_spec import RequestSpec
from .base import BaseFilter

logger = logging.getLogger(__name__)


class DeviceNameFilter(BaseFilter):
    """Filter devices by whitelist and blacklist of device names.

    Combines two extra_specs properties into a single filter:

    - ``qcos:devices`` (whitelist): when non-empty, only devices whose
      name is in the list pass. The special value ``all`` means no
      restriction.
    - ``qcos:exclude_devices`` (blacklist): when non-empty, devices
      whose name is in the list are filtered out.

    Enabled when either property is specified. A device passes only if
    it is not excluded AND (whitelist is empty/``all`` or its name is
    in the whitelist).
    """

    def is_enabled(self, spec: RequestSpec) -> bool:
        return bool(spec.devices) or bool(spec.exclude_devices)

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        # 1. blacklist check (exclude_devices)
        excluded = spec.exclude_devices
        if excluded and obj.name in excluded:
            logger.debug(
                f"DeviceNameFilter: device_name: {obj.name}, "
                f"in blacklist: {excluded}, passed: False"
            )
            return False

        # 2. whitelist check (devices)
        whitelist = spec.devices
        if not whitelist:
            return True

        # "all" means no restriction
        if FlavorConstant.DEVICE_NAME_ALL in whitelist:
            return True

        passed = obj.name in whitelist
        logger.debug(
            f"DeviceNameFilter: device_name: {obj.name}, "
            f"whitelist: {whitelist}, passed: {passed}"
        )
        return passed
