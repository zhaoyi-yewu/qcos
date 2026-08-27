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

from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.request_spec import RequestSpec
from .base import BaseFilter

logger = logging.getLogger(__name__)


class DeviceAvailabilityFilter(BaseFilter):
    """Filter devices by minimum availability (availability rate).

    The availability threshold is sourced from flavor or extra_specs
    under the ``qc:device_availability`` key (a float in [0.0, 1.0]).
    Devices whose ``availability`` is lower than the threshold are
    filtered out.

    The filter is enabled only when the threshold is specified.
    Devices with no availability data (``availability == 0.0``) are not
    blocked when the threshold is not set; when set, a device with
    no availability data is treated as not meeting the requirement.
    """

    def is_enabled(self, spec: RequestSpec) -> bool:
        return spec.device_availability is not None

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        threshold = spec.device_availability
        if threshold is None:
            # is_enabled() guards this path; treat as pass-through
            return True
        logger.debug(
            f"DeviceAvailabilityFilter: device_name: {obj.name}. "
            f"obj.availability_total: {obj.availability_total}, "
            f"spec.device_availability: {threshold}"
        )
        # When the device has no availability data (0.0) and a
        # threshold is required, treat it as not meeting the
        # requirement.
        if obj.availability_total < threshold:
            return False
        return True
