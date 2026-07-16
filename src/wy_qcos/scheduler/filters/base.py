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

logger = logging.getLogger(__name__)


class BaseFilter:
    """Base class for all filters.

    Subclasses must implement _filter_one() to decide whether a
    DeviceState passes the filter. Return True to keep the device.
    """

    def filter_all(
        self, list_obj: list[DeviceState], spec: RequestSpec
    ) -> list[DeviceState]:
        """Filter all devices.

        Args:
            list_obj: list of DeviceState objects
            spec: request spec

        Returns:
            list of DeviceState objects that pass the filter
        """
        return [obj for obj in list_obj if self._filter_one(obj, spec)]

    def _filter_one(self, obj: DeviceState, spec: RequestSpec) -> bool:
        """Check if a single device passes the filter.

        Args:
            obj: DeviceState object
            spec: request spec

        Returns:
            True if the device passes, False otherwise.
        """
        raise NotImplementedError

    def is_enabled(self, spec: RequestSpec) -> bool:
        """Whether this filter is enabled for the given spec.

        Override in subclasses to conditionally enable/disable.

        Args:
            spec: request spec

        Returns:
            True if enabled (default).
        """
        return True


class BaseFilterHandler:
    """Filter handler that chains multiple filters.

    Inspired by OpenStack Nova FilterHandler.
    """

    def __init__(self, filter_classes: list):
        """Init filter handler.

        Args:
            filter_classes: list of filter classes or instances.
                Classes are instantiated; instances are used directly.
        """
        self._filters = [
            cls if isinstance(cls, BaseFilter) else cls()
            for cls in filter_classes
        ]

    def get_filtered_objects(
        self, list_obj: list[DeviceState], spec: RequestSpec
    ) -> list[DeviceState]:
        """Run all enabled filters in order.

        Args:
            list_obj: list of DeviceState objects
            spec: request spec

        Returns:
            list of DeviceState objects that pass all filters
        """
        filtered = list(list_obj)
        for filter_instance in self._filters:
            if not filter_instance.is_enabled(spec):
                continue
            logger.debug(
                f"Running filter: {filter_instance.__class__.__name__}, "
                f"devices before: {[d.name for d in filtered]}"
            )
            filtered = filter_instance.filter_all(filtered, spec)
            if not filtered:
                logger.debug(
                    f"Filter {filter_instance.__class__.__name__} "
                    f"returned no devices"
                )
                break
        return filtered
