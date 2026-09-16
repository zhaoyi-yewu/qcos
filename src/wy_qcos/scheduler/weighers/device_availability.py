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
from .base import BaseWeigher

logger = logging.getLogger(__name__)


class DeviceAvailabilityWeigher(BaseWeigher):
    """Weigh devices by availability rate.

    Combines two availability signals:

    - ``availability_total``: historical aggregated rate (0.0-1.0),
      sourced from ``device_availability_hourly`` plus current-hour counts.
    - ``availability_hourly``: current-hour real-time rate
      (0.0-1.0), sourced from the in-memory ``DeviceAvailabilityCollector``.

    The weight is::

        0.1 * availability_hourly + availability_total

    multiplied by the weigher ``multiplier``. Higher weight = more
    preferred. The overall rate dominates; the current-hour rate
    acts as a small real-time bias.
    """

    multiplier: float = 1.0

    def _weigh_object(self, obj: DeviceState, spec: RequestSpec) -> float:
        logger.debug(
            f"DeviceAvailabilityWeigher: device_name: {obj.name}, "
            f"multiplier: {self.multiplier}. "
            f"availability_total: {obj.availability_total}, "
            f"availability_hourly: {obj.availability_hourly}"
        )
        return float(0.1 * obj.availability_hourly) + float(
            obj.availability_total
        )
