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
from wy_qcos.scheduler.filters.base import BaseFilter
from wy_qcos.scheduler.request_spec import RequestSpec

logger = logging.getLogger(__name__)

# extra_properties key for device group reference
DEVICE_GROUP_SPEC_KEY = "qc:device_groups"


class DeviceGroupFilter(BaseFilter):
    """Filter devices by device group membership.

    Checks if the flavor's extra_properties contains a
    'qc:device_groups' reference. If so, only devices that belong
    to the referenced group (by name or UUID) pass the filter.

    The device_group_manager is set by AutoScheduler before
    filtering.
    """

    def __init__(self, device_group_manager=None):
        """Init DeviceGroupFilter.

        Args:
            device_group_manager: DeviceGroupManager instance for
                looking up group members
        """
        self._device_group_manager = device_group_manager

    def set_device_group_manager(self, manager):
        """Set device group manager.

        Args:
            manager: DeviceGroupManager instance
        """
        self._device_group_manager = manager

    def is_enabled(self, spec: RequestSpec) -> bool:
        """Check if this filter is enabled for the given spec.

        Enabled when flavor_specs contains 'qc:device_groups'.

        Args:
            spec: request spec

        Returns:
            True if the filter should be applied.
        """
        group_ref = spec.flavor_specs.get(DEVICE_GROUP_SPEC_KEY)
        return group_ref is not None

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        """Check if a single device passes the filter.

        Args:
            obj: DeviceState object
            spec: request spec

        Returns:
            True if the device is in the referenced group,
            False otherwise. Returns True if filter is disabled.
        """
        group_ref = spec.flavor_specs.get(DEVICE_GROUP_SPEC_KEY)
        if not group_ref:
            return True

        if self._device_group_manager is None:
            logger.warning(
                "DeviceGroupFilter enabled but device_group_manager is None"
            )
            return True

        device_names = self._device_group_manager.get_device_names_by_group(
            group_ref
        )
        if not device_names:
            logger.warning(f"No devices found for group: {group_ref}")
            return False

        return obj.name in device_names
