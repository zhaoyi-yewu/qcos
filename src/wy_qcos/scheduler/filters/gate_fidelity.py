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


class GateFidelityFilter(BaseFilter):
    """Filter devices by minimum gate fidelity.

    The filter supports two independent thresholds sourced from
    flavor.specs. ``gate_fidelity_1q_min`` checks the device's
    average 1-qubit gate fidelity (from ``single_qubit_prop``);
    ``gate_fidelity_2q_min`` checks the average 2-qubit gate
    fidelity (from ``double_qubit_prop``).

    The filter is enabled when either threshold is specified.
    Devices without fidelity data are not blocked.
    """

    def is_enabled(self, spec: RequestSpec) -> bool:
        return (
            spec.gate_fidelity_1q_min is not None
            or spec.gate_fidelity_2q_min is not None
        )

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        # 1-qubit gate fidelity check
        if spec.gate_fidelity_1q_min is not None:
            avg_fidelity_1q = obj.get_avg_1q_fidelity()
            logger.debug(
                f"GateFidelityFilter: device_name: {obj.name}, "
                f"avg_fidelity_1q: {avg_fidelity_1q}. "
                f"spec.gate_fidelity_1q_min: "
                f"{spec.gate_fidelity_1q_min}"
            )
            # If no fidelity data available (None), pass through
            if avg_fidelity_1q is not None:
                if avg_fidelity_1q < spec.gate_fidelity_1q_min:
                    return False
        # 2-qubit gate fidelity check
        if spec.gate_fidelity_2q_min is not None:
            avg_fidelity_2q = obj.get_avg_2q_fidelity()
            logger.debug(
                f"GateFidelityFilter: device_name: {obj.name}, "
                f"avg_fidelity_2q: {avg_fidelity_2q}. "
                f"spec.gate_fidelity_2q_min: "
                f"{spec.gate_fidelity_2q_min}"
            )
            # If no fidelity data available (None), pass through
            if avg_fidelity_2q is not None:
                if avg_fidelity_2q < spec.gate_fidelity_2q_min:
                    return False
        return True
