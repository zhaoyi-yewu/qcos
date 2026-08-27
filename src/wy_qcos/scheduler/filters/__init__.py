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
from .device_availability import DeviceAvailabilityFilter
from .device_name import DeviceNameFilter
from .device_status import DeviceStatusFilter
from .device_group import DeviceGroupFilter
from .qubit_count import QubitCountFilter
from .tech_type import TechTypeFilter
from .gate_fidelity import GateFidelityFilter
from .queue_limit import QueueLimitFilter

# Default filter order (must filters first, then optional)
# All filters share the same initialization interface via
# BaseFilterHandler, which injects device_group_manager into every
# instance. Filters that don't need it simply ignore it.
DEFAULT_FILTERS = [
    CodeTypeFilter,
    DeviceStatusFilter,
    TechTypeFilter,
    QubitCountFilter,
    QueueLimitFilter,
    GateFidelityFilter,
    DeviceAvailabilityFilter,
    DeviceNameFilter,
    DeviceGroupFilter,
]
