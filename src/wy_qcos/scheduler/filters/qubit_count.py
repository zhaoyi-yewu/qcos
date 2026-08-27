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


class QubitCountFilter(BaseFilter):
    """Filter devices by qubit count requirements.

    Checks that the device's max_qubits/available_num_qubits is >= the job's
    required num_qubits, and that the job's num_qubits is >= the flavor's
    min_qubits (if specified).
    """

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        logger.debug(
            f"QubitCountFilter: device_name: {obj.name}. "
            f"obj.max_qubits: {obj.max_qubits}, "
            f"obj.available_num_qubits: {obj.available_num_qubits}, "
            f"spec.num_qubits: {spec.num_qubits}, "
            f"spec.min_qubits: {spec.min_qubits}, "
            f"spec.max_qubits: {spec.max_qubits}"
        )

        # Check job qubit count fits in device
        # Check max_qubits
        if spec.num_qubits > 0:
            if obj.max_qubits < spec.num_qubits:
                return False
        # Check min_qubits from flavor/extra_specs
        if spec.min_qubits is not None:
            if obj.max_qubits < spec.min_qubits:
                return False
        # Check max_qubits upper bound from extra_specs
        if spec.max_qubits is not None:
            if obj.max_qubits > spec.max_qubits:
                return False

        # Check available_qubits
        if obj.available_num_qubits >= 0:
            if spec.num_qubits > 0:
                if obj.available_num_qubits < spec.num_qubits:
                    return False
            # Check min_qubits from flavor/extra_specs
            if spec.min_qubits is not None:
                if obj.available_num_qubits < spec.min_qubits:
                    return False
            # Check max_qubits upper bound from extra_specs
            if spec.max_qubits is not None:
                if obj.available_num_qubits > spec.max_qubits:
                    return False

        return True
