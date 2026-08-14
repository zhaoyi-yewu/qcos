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
import os
from typing import Any

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.db.repositories.job import JobRepository
from wy_qcos.db.utils.db_utils import create_db_session
from wy_qcos.device.device_manager import DeviceManager
from wy_qcos.flavor.flavor_manager import FlavorManager
from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.errors import NoValidDeviceError
from wy_qcos.scheduler.filters import (
    BaseFilter,
    BaseFilterHandler,
    DEFAULT_FILTERS,
)
from wy_qcos.scheduler.request_spec import RequestSpec
from wy_qcos.scheduler.weighers import (
    BaseWeightHandler,
    BaseWeigher,
    DEFAULT_WEIGHERS,
)
from wy_qcos.task_manager.task_manager import TaskFlowManager

logger = logging.getLogger(__name__)


class AutoScheduler:
    """Auto scheduler using Filter + Weigher pattern.

    Inspired by OpenStack Nova FilterScheduler.

    1. Build DeviceState list from all devices
    2. Run filters to eliminate ineligible devices
    3. Run weighers to rank remaining devices
    4. Return the highest-weighted device name
    """

    def __init__(
        self,
        device_manager: DeviceManager,
        task_manager: TaskFlowManager,
        flavor_manager: FlavorManager,
        device_group_manager=None,
        db_engine=None,
        filter_handler: BaseFilterHandler | None = None,
        weight_handler: BaseWeightHandler | None = None,
        enabled_filters: list[str] | None = None,
        enabled_weighers: list[str] | None = None,
        transpiler_manager: Any = None,
    ):
        """Init AutoScheduler.

        Args:
            device_manager: device manager
            task_manager: task flow manager
            flavor_manager: flavor manager
            device_group_manager: device group manager
            db_engine: SQLAlchemy database engine used to query
                job load info from the qcos database. When None,
                load counts fall back to 0.
            filter_handler: filter handler (default uses
                DEFAULT_FILTERS; DeviceGroupFilter is included
                when dynamically discovered)
            weight_handler: weight handler (default uses
                DEFAULT_WEIGHERS)
            enabled_filters: list of filter class names to enable.
                When provided, filters are resolved from the
                dynamically discovered filter classes (scanned
                from scheduler/filters) by name. Duplicate names
                are skipped. When None or empty, DEFAULT_FILTERS
                are used. DeviceGroupFilter, when available in the
                discovered registry, is appended (deduplicated) so
                device group constraints are enforced.
            enabled_weighers: list of weigher class names to enable.
                When provided, weighers are resolved from the
                dynamically discovered weigher classes (scanned
                from scheduler/weighers) by name. When None or
                empty, DEFAULT_WEIGHERS are used.
            transpiler_manager: transpiler manager used to resolve
                transpiler instances for supported code types.
                When None, falls back to the driver's code types.
        """
        self._device_manager = device_manager
        self._task_manager = task_manager
        self._flavor_manager = flavor_manager
        self._device_group_manager = device_group_manager
        self._db_engine = db_engine
        self._transpiler_manager = transpiler_manager

        # dynamically discover filter/weigher classes by scanning
        # the scheduler/filters and scheduler/weighers directories
        # via Library.import_classes; the resulting name->class
        # mappings are used by _resolve_filter_classes /
        # _resolve_weigher_classes to resolve ENABLED_FILTERS /
        # ENABLED_WEIGHERS names from config
        self._filter_registry = self._load_filter_registry()
        self._weigher_registry = self._load_weigher_registry()

        if filter_handler is None:
            filter_classes = self._resolve_filter_classes(enabled_filters)
            filter_handler = BaseFilterHandler(
                filter_classes,
                device_group_manager=device_group_manager,
            )
        self._filter_handler = filter_handler

        if weight_handler is None:
            weigher_classes = self._resolve_weigher_classes(enabled_weighers)
            weight_handler = BaseWeightHandler(weigher_classes)
        self._weight_handler = weight_handler

    @staticmethod
    def _load_filter_registry():
        """Dynamically discover filter classes under scheduler/filters.

        Uses Library.import_classes to scan the filters directory and
        build a name->class mapping for all BaseFilter subclasses
        (excluding the base classes themselves).

        Returns:
            dict mapping filter class name to filter class
        """
        scheduler_dir = os.path.dirname(__file__)
        filters_dir = os.path.join(scheduler_dir, "filters")
        classes, _ = Library.import_classes(
            pkg_dir=filters_dir,
            base_module_name="wy_qcos.scheduler",
            base_dir=scheduler_dir,
            base_class=BaseFilter,
            excluded_class="^Base",
        )
        logger.info(f"Discovered filter classes: {list(classes.keys())}")
        return classes

    @staticmethod
    def _load_weigher_registry():
        """Dynamically discover weigher classes under scheduler/weighers.

        Uses Library.import_classes to scan the weighers directory and
        build a name->class mapping for all BaseWeigher subclasses
        (excluding the base classes themselves).

        Returns:
            dict mapping weigher class name to weigher class
        """
        scheduler_dir = os.path.dirname(__file__)
        weighers_dir = os.path.join(scheduler_dir, "weighers")
        classes, _ = Library.import_classes(
            pkg_dir=weighers_dir,
            base_module_name="wy_qcos.scheduler",
            base_dir=scheduler_dir,
            base_class=BaseWeigher,
            excluded_class="^Base",
        )
        logger.info(f"Discovered weigher classes: {list(classes.keys())}")
        return classes

    def _resolve_filter_classes(self, enabled_filters):
        """Resolve filter classes from the discovered registry.

        Args:
            enabled_filters: list of filter class names; when None or
                empty, DEFAULT_FILTERS are used

        Returns:
            list of filter classes; duplicates are skipped
        """
        if not enabled_filters:
            filter_classes = list(DEFAULT_FILTERS)
        else:
            filter_classes = []
            for name in enabled_filters:
                cls = self._filter_registry.get(name)
                if cls is None:
                    logger.warning(
                        f"Unknown filter '{name}' in enabled_filters, skipping"
                    )
                    continue
                if cls in filter_classes:
                    logger.warning(
                        f"Duplicate filter '{name}' in "
                        f"enabled_filters, skipping"
                    )
                    continue
                filter_classes.append(cls)
            if not filter_classes:
                logger.warning(
                    "No valid filters resolved from enabled_filters, "
                    "falling back to DEFAULT_FILTERS"
                )
                filter_classes = list(DEFAULT_FILTERS)

        filter_names = [
            getattr(c, "__name__", c.__class__.__name__)
            for c in filter_classes
        ]
        logger.info(f"AutoScheduler enabled filters: {filter_names}")
        return filter_classes

    def _resolve_weigher_classes(self, enabled_weighers):
        """Resolve weigher classes from the discovered registry.

        Args:
            enabled_weighers: list of weigher class names; when None
                or empty, DEFAULT_WEIGHERS are used

        Returns:
            list of weigher classes
        """
        if not enabled_weighers:
            weigher_classes = list(DEFAULT_WEIGHERS)
        else:
            weigher_classes = []
            for name in enabled_weighers:
                cls = self._weigher_registry.get(name)
                if cls is None:
                    logger.warning(
                        f"Unknown weigher '{name}' in "
                        f"enabled_weighers, skipping"
                    )
                    continue
                if cls in weigher_classes:
                    logger.warning(
                        f"Duplicate weigher '{name}' in "
                        f"enabled_weighers, skipping"
                    )
                    continue
                weigher_classes.append(cls)
            if not weigher_classes:
                logger.warning(
                    "No valid weighers resolved from enabled_weighers, "
                    "falling back to DEFAULT_WEIGHERS"
                )
                weigher_classes = list(DEFAULT_WEIGHERS)

        logger.info(
            f"AutoScheduler enabled weighers: "
            f"{[c.__name__ for c in weigher_classes]}"
        )
        return weigher_classes

    def schedule(self, request_spec: RequestSpec) -> str:
        """Execute auto scheduling.

        Args:
            request_spec: scheduling request spec

        Returns:
            selected device name

        Raises:
            NoValidDeviceError: if no device passes filters
        """
        # 1. Build device states
        device_states = self._build_device_states()

        if not device_states:
            raise NoValidDeviceError("No available devices")

        logger.info(
            f"Auto schedule: {len(device_states)} devices found, "
            f"spec: code_type={request_spec.code_type}, "
            f"num_qubits={request_spec.num_qubits}, "
            f"flavor_id={request_spec.flavor_id}"
        )

        # 2. Run filters
        filtered = self._filter_handler.get_filtered_objects(
            device_states, request_spec
        )

        if not filtered:
            raise NoValidDeviceError(
                "No device matches the scheduling requirements"
            )

        logger.info(
            f"Auto schedule: {len(filtered)} devices passed filters: "
            f"{[d.name for d in filtered]}"
        )

        # 3. Single device: return directly
        if len(filtered) == 1:
            logger.info(
                f"Auto schedule: only one device passed: {filtered[0].name}"
            )
            return filtered[0].name

        # 4. Run weighers
        weighed = self._weight_handler.get_weighed_objects(
            filtered, request_spec
        )

        best = weighed[0]
        result_str = ", ".join(f"{w.obj.name}={w.weight:.2f}" for w in weighed)
        logger.info(f"Auto schedule: weighed devices: {result_str}")
        logger.info(f"Auto schedule: selected device: {best.obj.name}")

        return best.obj.name

    def _build_device_states(self) -> list[DeviceState]:
        """Build DeviceState list from all devices.

        Returns:
            list of DeviceState objects with dynamic info populated.
        """
        devices = self._device_manager.get_devices()
        device_states = []
        for device in devices.values():
            # Resolve the device's transpiler instance (if a
            # transpiler manager is available) so that the
            # transpiler-declared supported code types take
            # precedence over the driver's declaration.
            transpiler = None
            if self._transpiler_manager is not None:
                transpiler_name = device.get_driver().get_transpiler()
                if transpiler_name:
                    transpiler = self._transpiler_manager.get_transpiler(
                        transpiler_name
                    )
            state = DeviceState.from_device(device, transpiler=transpiler)
            # Populate dynamic load info
            queued = self._get_queued_count(device.get_name())
            running = self._get_running_count(device.get_name())
            vendor_queued = 0
            vendor_running = 0
            state.set_load_info(queued, running, vendor_queued, vendor_running)
            device_states.append(state)
        return device_states

    def _get_queued_count(self, device_name: str) -> int:
        """Get queued job count for a device from qcos database.

        Queries the job table for jobs whose backend matches the
        given device and whose job_status is QUEUED.

        Args:
            device_name: device name

        Returns:
            number of queued jobs, returns 0 on error or when the
            database engine is not configured
        """
        return self._count_jobs_by_status(
            device_name, Constant.JOB_STATUS_QUEUED
        )

    def _get_running_count(self, device_name: str) -> int:
        """Get running job count for a device from qcos database.

        Queries the job table for jobs whose backend matches the
        given device and whose job_status is RUNNING.

        Args:
            device_name: device name

        Returns:
            number of running jobs, returns 0 on error or when the
            database engine is not configured
        """
        return self._count_jobs_by_status(
            device_name, Constant.JOB_STATUS_RUNNING
        )

    def _count_jobs_by_status(self, device_name: str, job_status: str) -> int:
        """Count jobs for a device filtered by job status.

        Args:
            device_name: device name (matches job.backend column)
            job_status: job status value to filter by

        Returns:
            count of matching jobs, returns 0 on error or when the
            database engine is not configured
        """
        if self._db_engine is None:
            logger.debug(
                f"db_engine not configured, skip counting "
                f"{job_status} jobs for {device_name}"
            )
            return 0
        try:
            with create_db_session(self._db_engine) as db_session:
                job_repo = JobRepository(db_session)
                return job_repo.get_jobs_count(
                    filters={
                        "backend": device_name,
                        "job_status": job_status,
                    }
                )
        except Exception as e:
            logger.warning(
                f"Failed to get {job_status} count for {device_name}: {e}"
            )
            return 0

    @staticmethod
    def build_request_spec(
        code_type: str = "",
        num_qubits: int = 0,
        flavor_id: str | None = None,
        extra_specs: dict | None = None,
        flavor_manager: FlavorManager | None = None,
    ) -> RequestSpec:
        """Build RequestSpec from job request parameters.

        Args:
            code_type: code type (qasm, qasm2, qasm3, qubo)
            num_qubits: number of qubits in source code
            flavor_id: flavor UUID string
            extra_specs: extra scheduling specs
            flavor_manager: flavor manager for looking up flavor specs

        Returns:
            RequestSpec instance
        """
        flavor_specs = {}
        if flavor_id and flavor_manager:
            flavor_specs = flavor_manager.get_flavor_specs(flavor_id)

        return RequestSpec(
            code_type=code_type if code_type else None,
            num_qubits=num_qubits,
            flavor_id=flavor_id,
            flavor_specs=flavor_specs,
            extra_specs=extra_specs or {},
        )
