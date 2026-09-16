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

from wy_qcos.common.constant import Constant
from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.filters.base import BaseFilter
from wy_qcos.scheduler.request_spec import RequestSpec

logger = logging.getLogger(__name__)


class DeviceGroupFilter(BaseFilter):
    """Filter devices by device group membership.

    Checks if the flavor's extra_properties contains a
    'qc:device_groups' reference. If so, only devices that belong
    to the referenced group (by name or UUID) pass the filter.

    The device_group_manager is set by AutoScheduler via
    set_device_group_manager() during filter initialization.
    """

    def __init__(self):
        """Init DeviceGroupFilter.

        The device_group_manager is injected later via
        set_device_group_manager() by AutoScheduler, keeping the
        initialization interface uniform across all filters.
        """
        self._device_group_manager = None

    def set_device_group_manager(self, manager):
        """Set the device group manager on this filter.

        Args:
            manager: DeviceGroupManager instance
        """
        self._device_group_manager = manager

    def is_enabled(self, spec: RequestSpec) -> bool:
        """Check if this filter is enabled for the given spec.

        Enabled when extra_specs or flavor_specs contains
        'qc:device_groups'. extra_specs takes precedence.

        Args:
            spec: request spec

        Returns:
            True if the filter should be applied.
        """
        return spec.device_groups is not None

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        """Check if a single device passes the filter.

        Args:
            obj: DeviceState object
            spec: request spec

        Returns:
            True if the device is in the referenced group,
            False otherwise. Returns True if filter is disabled.
        """
        device_groups = spec.device_groups
        if not device_groups:
            return True

        if self._device_group_manager is None:
            logger.warning(
                "DeviceGroupFilter enabled but device_group_manager is None"
            )
            return True

        device_set = set()
        for device_group in device_groups:
            device_names = (
                self._device_group_manager.get_device_names_by_group(
                    device_group
                )
            )
            device_set.update(device_names)

        if not device_set:
            logger.warning(
                f"No devices found for groups: {', '.join(device_groups)}"
            )
            return False

        logger.debug(
            f"DeviceGroupFilter: device_name: {obj.name}. "
            f"obj.name: {obj.name}, "
            f"device_set: {device_set}"
        )

        if Constant.DEVICE_GROUP_DN_ALL in device_set:
            return True

        return obj.name in device_set
