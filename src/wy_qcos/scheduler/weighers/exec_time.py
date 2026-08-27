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


class AvgExecTimeWeigher(BaseWeigher):
    """Weigh devices by historical average execution time per qubit.

    Devices with shorter average execution time get higher weight.
    Weight = -(avg_exec_time_per_qubit)

    Only enabled when devices have execution time data.
    """

    multiplier = 1.0

    def _weigh_object(self, obj: DeviceState, spec: RequestSpec) -> float:
        logger.debug(
            f"AvgExecTimeWeigher: device_name: {obj.name}, "
            f"multiplier: {self.multiplier}. "
            f"avg_exec_time_per_qubit: {obj.avg_exec_time_per_qubit}"
        )

        if obj.avg_exec_time_per_qubit <= 0:
            return 0.0
        return float(-obj.avg_exec_time_per_qubit)
