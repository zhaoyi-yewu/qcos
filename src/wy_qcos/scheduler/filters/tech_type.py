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

    Only enabled when spec.tech_type is specified (from flavor.specs).
    Matches the device's tech_type against the required value.
    """

    def is_enabled(self, spec: RequestSpec) -> bool:
        return spec.tech_type is not None

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        logger.debug(
            f"TechTypeFilter: device_name: {obj.name}. "
            f"obj.tech_type: {obj.tech_type}, "
            f"spec.tech_type: {spec.tech_type}"
        )

        if spec.tech_type is None:
            return True
        return obj.tech_type == spec.tech_type
