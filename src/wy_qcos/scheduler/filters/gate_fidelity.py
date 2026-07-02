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

from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.request_spec import RequestSpec
from .base import BaseFilter


class GateFidelityFilter(BaseFilter):
    """Filter devices by minimum 2-qubit gate fidelity.

    Only enabled when spec.gate_fidelity_2q_min is specified (from
    flavor.specs). Checks that the device's average 2-qubit gate
    fidelity meets the threshold.
    """

    def is_enabled(self, spec: RequestSpec) -> bool:
        return spec.gate_fidelity_2q_min is not None

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        if spec.gate_fidelity_2q_min is None:
            return True
        avg_fidelity = obj.get_avg_2q_fidelity()
        # If no fidelity data available, do not block the device
        if avg_fidelity <= 0.0:
            return True
        return avg_fidelity >= spec.gate_fidelity_2q_min
