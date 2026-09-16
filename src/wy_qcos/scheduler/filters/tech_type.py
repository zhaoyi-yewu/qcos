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


class TechTypeFilter(BaseFilter):
    """Filter devices by technology type.

    Only enabled when ``qc:tech_types`` is specified in flavor or
    extra_specs. Matches the device's tech_type against any of the
    required values (comma-separated list supported).
    """

    def is_enabled(self, spec: RequestSpec) -> bool:
        return bool(spec.tech_types)

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        required = spec.tech_types
        logger.debug(
            f"TechTypeFilter: device_name: {obj.name}. "
            f"obj.tech_type: {obj.tech_type}, "
            f"spec.tech_types: {required}"
        )

        if not required:
            return True
        return obj.tech_type in required
