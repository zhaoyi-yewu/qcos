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

from prefect.client.schemas.objects import StateType

from wy_qcos.common.constant import Constant
from wy_qcos.drivers.device_manager import DeviceManager
from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.errors import NoValidDeviceError
from wy_qcos.scheduler.flavor_manager import FlavorManager
from wy_qcos.scheduler.filters import BaseFilterHandler, DEFAULT_FILTERS
from wy_qcos.scheduler.request_spec import RequestSpec
from wy_qcos.scheduler.weighers import BaseWeightHandler, DEFAULT_WEIGHERS
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
        filter_handler: BaseFilterHandler | None = None,
        weight_handler: BaseWeightHandler | None = None,
    ):
        """Init AutoScheduler.

        Args:
            device_manager: device manager
            task_manager: task flow manager
            flavor_manager: flavor manager
            filter_handler: filter handler (default uses DEFAULT_FILTERS)
            weight_handler: weight handler (default uses DEFAULT_WEIGHERS)
        """
        self._device_manager = device_manager
        self._task_manager = task_manager
        self._flavor_manager = flavor_manager

        if filter_handler is None:
            filter_handler = BaseFilterHandler(DEFAULT_FILTERS)
        self._filter_handler = filter_handler

        if weight_handler is None:
            weight_handler = BaseWeightHandler(DEFAULT_WEIGHERS)
        self._weight_handler = weight_handler

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
            state = DeviceState.from_device(device)
            # Populate dynamic load info
            queued = self._get_queued_count(device.get_name())
            running = self._get_running_count(device.get_name())
            state.set_load_info(queued, running)
            device_states.append(state)
        return device_states

    def _get_queued_count(self, device_name: str) -> int:
        """Get queued job count for a device.

        Args:
            device_name: device name

        Returns:
            number of queued (scheduled + pending) jobs
        """
        try:
            wait_states = self._task_manager.convert_to_prefect_states(
                Constant.PREFECT_WAIT_STATES
            )
            pool_name = f"{Constant.WORK_POOL_DEVICE_PREFIX}{device_name}"
            flows = self._task_manager.get_flow_runs_with_filters(
                states=wait_states, pool_name=pool_name
            )
            return len(flows)
        except Exception as e:
            logger.warning(
                f"Failed to get queued count for {device_name}: {e}"
            )
            return 0

    def _get_running_count(self, device_name: str) -> int:
        """Get running job count for a device.

        Args:
            device_name: device name

        Returns:
            number of running jobs
        """
        try:
            pool_name = f"{Constant.WORK_POOL_DEVICE_PREFIX}{device_name}"
            flows = self._task_manager.get_flow_runs_with_filters(
                states=[StateType.RUNNING], pool_name=pool_name
            )
            return len(flows)
        except Exception as e:
            logger.warning(
                f"Failed to get running count for {device_name}: {e}"
            )
            return 0

    @staticmethod
    def build_request_spec(
        job_id: str,
        code_type: str = "",
        num_qubits: int = 0,
        flavor_id: str | None = None,
        extra_specs: dict | None = None,
        flavor_manager: FlavorManager | None = None,
    ) -> RequestSpec:
        """Build RequestSpec from job request parameters.

        Args:
            job_id: job ID
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
            job_id=job_id,
            code_type=code_type.lower() if code_type else "",
            num_qubits=num_qubits,
            flavor_id=flavor_id,
            flavor_specs=flavor_specs,
            extra_specs=extra_specs or {},
        )
