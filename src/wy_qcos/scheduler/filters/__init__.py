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

from .base import BaseFilter, BaseFilterHandler
from .code_type import CodeTypeFilter
from .device_status import DeviceStatusFilter
from .device_group import DeviceGroupFilter
from .qubit_count import QubitCountFilter
from .tech_type import TechTypeFilter
from .gate_fidelity import GateFidelityFilter
from .queue_limit import QueueLimitFilter

# Default filter order (must filters first, then optional)
# Note: DeviceGroupFilter is injected by AutoScheduler with
# device_group_manager, not listed here as it needs runtime
# configuration.
DEFAULT_FILTERS = [
    CodeTypeFilter,
    DeviceStatusFilter,
    TechTypeFilter,
    QubitCountFilter,
    QueueLimitFilter,
    GateFidelityFilter,
]

# Filter registry for auto-discovery
FILTER_REGISTRY = {
    "CodeTypeFilter": CodeTypeFilter,
    "DeviceStatusFilter": DeviceStatusFilter,
    "DeviceGroupFilter": DeviceGroupFilter,
    "QubitCountFilter": QubitCountFilter,
    "TechTypeFilter": TechTypeFilter,
    "GateFidelityFilter": GateFidelityFilter,
    "QueueLimitFilter": QueueLimitFilter,
}
