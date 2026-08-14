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


class CodeTypeFilter(BaseFilter):
    """Filter devices by supported code type.

    Matches the job's code_type (qasm, qasm2, qasm3, qubo) against
    the device driver's supported_code_types.
    """

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        logger.debug(
            f"CodeTypeFilter: device_name: {obj.name}. "
            f"obj.supported_code_types: {obj.supported_code_types}, "
            f"spec.code_type: {spec.code_type}"
        )

        if not spec.code_type:
            return True
        return spec.code_type in obj.supported_code_types
