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

    All filters share a uniform initialization interface. The
    set_device_group_manager() method is called by AutoScheduler
    on every filter instance during initialization; filters that do
    not need the device_group_manager simply ignore it (the default
    no-op implementation here).
    """

    def set_device_group_manager(self, manager):
        """Set the device group manager on this filter.

        Called by AutoScheduler on every filter instance during
        initialization. Override in subclasses that need access to
        the device group manager (e.g. DeviceGroupFilter).

        Args:
            manager: DeviceGroupManager instance
        """
        pass

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

    def __init__(
        self,
        filter_classes: list,
        device_group_manager=None,
    ):
        """Init filter handler.

        All filter classes are instantiated uniformly (no special
        constructor arguments). After instantiation, the
        device_group_manager (when provided) is injected into every
        filter instance via set_device_group_manager(), so filters
        that need it (e.g. DeviceGroupFilter) can access it.

        Args:
            filter_classes: list of filter classes or instances.
                Classes are instantiated; instances are used directly.
            device_group_manager: device group manager injected
                into every filter instance after instantiation.
                Defaults to None (no injection).
        """
        self._filters = []
        # last per-filter status produced by get_filtered_objects,
        # mapping filter class name -> bool (True if the filter left
        # at least one device). Consumers (e.g. AutoScheduler) can
        # inspect this attribute after a filtering run.
        self.last_filter_status: dict[str, bool] = {}
        for cls in filter_classes:
            if isinstance(cls, BaseFilter):
                instance = cls
            else:
                instance = cls()
            if device_group_manager is not None:
                instance.set_device_group_manager(device_group_manager)
            self._filters.append(instance)

    def get_filtered_objects(
        self,
        list_obj: list[DeviceState],
        spec: RequestSpec,
        run_all_filters: bool = False,
    ) -> tuple[list[DeviceState], str | None, list[DeviceState] | None]:
        """Run all enabled filters in order and return the survivors.

        When run_all_filters is False (default), the method stops
        early as soon as no devices remain (backward-compatible
        behavior with respect to the filtered list).

        When run_all_filters is True, all enabled filters are run
        regardless of intermediate results so that the per-filter
        status is complete.

        The per-filter status (class name -> bool) is stored on
        ``self.last_filter_status`` for callers that need to
        distinguish failure reasons (e.g. QubitCountFilter).

        Args:
            list_obj: list of DeviceState objects
            spec: request spec
            run_all_filters: if True, run all filters even when no
                devices remain

        Returns:
            A tuple ``(filtered_devices, last_failed_filter_name,
            last_filtered_devices_snapshot)``.

            - filtered_devices: list of DeviceState objects that
              passed all filters.
            - last_failed_filter_name: name of the filter that
              emptied the list, or None.
            - last_filtered_devices: snapshot of devices that
              passed the last successful filter, or None.
        """
        filtered = list(list_obj)
        filter_status: dict[str, bool] = {}
        last_failed_filter = None
        last_filtered_devices = None
        for filter_instance in self._filters:
            if not filter_instance.is_enabled(spec):
                continue
            filter_name = filter_instance.__class__.__name__
            before_count = len(filtered)
            logger.info(
                f"Running filter: {filter_name}, "
                f"devices before: {before_count}"
            )
            if not filtered and not run_all_filters:
                break
            filtered = filter_instance.filter_all(filtered, spec)
            after_count = len(filtered)
            if after_count < before_count:
                removed = before_count - after_count
                logger.info(
                    f"Filter {filter_name} removed {removed} "
                    f"device(s), {after_count} remaining"
                )
            if not filtered:
                filter_status[filter_name] = False
                logger.info(
                    f"Filter {filter_name} returned no devices, "
                    f"scheduling will fail"
                )
                last_failed_filter = filter_name
                if not run_all_filters:
                    break
            else:
                filter_status[filter_name] = True
                last_filtered_devices = filtered
        self.last_filter_status = filter_status
        return filtered, last_failed_filter, last_filtered_devices
