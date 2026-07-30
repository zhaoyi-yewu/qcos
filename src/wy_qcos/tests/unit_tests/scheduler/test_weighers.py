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

"""Unit tests for scheduler weighers and auto scheduler."""

import pytest
from unittest.mock import MagicMock, patch

from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.request_spec import RequestSpec
from wy_qcos.scheduler.weighers.device_load import DeviceLoadWeigher
from wy_qcos.scheduler.weighers.exec_time import AvgExecTimeWeigher
from wy_qcos.scheduler.weighers.base import BaseWeightHandler
from wy_qcos.scheduler.weighers import DEFAULT_WEIGHERS
from wy_qcos.scheduler.errors import NoValidDeviceError
from wy_qcos.scheduler.auto_scheduler import AutoScheduler


def make_device_state(
    name="device1",
    queued_job_count=0,
    running_job_count=0,
    avg_exec_time_per_qubit=0.0,
    status="online",
    enable=True,
    max_qubits=10,
    tech_type="superconducting",
    supported_code_types=None,
):
    """Create a DeviceState for testing."""
    return DeviceState(
        device=None,
        name=name,
        status=status,
        enable=enable,
        max_qubits=max_qubits,
        available_num_qubits=max_qubits,
        tech_type=tech_type,
        supported_code_types=supported_code_types or ["qasm"],
        supported_basis_gates=None,
        details={},
        queued_job_count=queued_job_count,
        running_job_count=running_job_count,
        max_queued_jobs=-1,
        avg_exec_time_per_qubit=avg_exec_time_per_qubit,
    )


def make_spec(
    code_type="qasm",
    num_qubits=0,
    flavor_specs=None,
    extra_specs=None,
):
    """Create a RequestSpec for testing."""
    return RequestSpec(
        code_type=code_type,
        num_qubits=num_qubits,
        flavor_id=None,
        flavor_specs=flavor_specs or {},
        extra_specs=extra_specs or {},
    )


class TestDeviceLoadWeigher:
    """Tests for DeviceLoadWeigher."""

    def test_weigh_idle_device(self):
        weigher = DeviceLoadWeigher()
        device = make_device_state(queued_job_count=0, running_job_count=0)
        spec = make_spec()
        weight = weigher._weigh_object(device, spec)
        assert weight == 0.0

    def test_weigh_busy_device(self):
        weigher = DeviceLoadWeigher()
        device = make_device_state(queued_job_count=5, running_job_count=3)
        spec = make_spec()
        weight = weigher._weigh_object(device, spec)
        assert weight == -8.0

    def test_weigh_less_busy_higher_weight(self):
        weigher = DeviceLoadWeigher()
        idle_device = make_device_state(
            name="idle", queued_job_count=0, running_job_count=0
        )
        busy_device = make_device_state(
            name="busy", queued_job_count=10, running_job_count=5
        )
        spec = make_spec()
        idle_weight = weigher._weigh_object(idle_device, spec)
        busy_weight = weigher._weigh_object(busy_device, spec)
        assert idle_weight > busy_weight


class TestAvgExecTimeWeigher:
    """Tests for AvgExecTimeWeigher."""

    def test_weigh_no_exec_time(self):
        weigher = AvgExecTimeWeigher()
        device = make_device_state(avg_exec_time_per_qubit=0.0)
        spec = make_spec()
        weight = weigher._weigh_object(device, spec)
        assert weight == 0.0

    def test_weigh_with_exec_time(self):
        weigher = AvgExecTimeWeigher()
        device = make_device_state(avg_exec_time_per_qubit=5.5)
        spec = make_spec()
        weight = weigher._weigh_object(device, spec)
        assert weight == -5.5

    def test_weigh_faster_device_higher(self):
        weigher = AvgExecTimeWeigher()
        fast_device = make_device_state(
            name="fast", avg_exec_time_per_qubit=1.0
        )
        slow_device = make_device_state(
            name="slow", avg_exec_time_per_qubit=10.0
        )
        spec = make_spec()
        fast_weight = weigher._weigh_object(fast_device, spec)
        slow_weight = weigher._weigh_object(slow_device, spec)
        assert fast_weight > slow_weight


class TestBaseWeightHandler:
    """Tests for BaseWeightHandler."""

    def test_weigh_objects_sorted_descending(self):
        handler = BaseWeightHandler(DEFAULT_WEIGHERS)
        devices = [
            make_device_state(
                name="busy",
                queued_job_count=10,
                running_job_count=5,
            ),
            make_device_state(
                name="idle",
                queued_job_count=0,
                running_job_count=0,
            ),
            make_device_state(
                name="medium",
                queued_job_count=3,
                running_job_count=2,
            ),
        ]
        spec = make_spec()
        result = handler.get_weighed_objects(devices, spec)
        assert result[0].obj.name == "idle"
        assert result[1].obj.name == "medium"
        assert result[2].obj.name == "busy"

    def test_weigh_single_device(self):
        handler = BaseWeightHandler(DEFAULT_WEIGHERS)
        devices = [
            make_device_state(name="only", queued_job_count=1),
        ]
        spec = make_spec()
        result = handler.get_weighed_objects(devices, spec)
        assert len(result) == 1
        assert result[0].obj.name == "only"


class TestAutoScheduler:
    """Tests for AutoScheduler."""

    def test_schedule_no_devices(self):
        device_manager = MagicMock()
        device_manager.get_devices.return_value = {}
        task_manager = MagicMock()
        flavor_manager = MagicMock()

        scheduler = AutoScheduler(device_manager, task_manager, flavor_manager)
        spec = make_spec()

        with pytest.raises(NoValidDeviceError):
            scheduler.schedule(spec)

    def test_schedule_single_device_passes(self):
        device = MagicMock()
        device.get_name.return_value = "device1"
        device.get_status.return_value = "online"
        device.get_enable.return_value = True
        device.get_max_queued_jobs.return_value = -1
        device.tech_type = "superconducting"
        device.details = {}
        driver = MagicMock()
        driver.get_max_qubits.return_value = 10
        driver.available_num_qubits = 10
        driver.get_supported_code_types.return_value = ["qasm"]
        driver.get_supported_basis_gates.return_value = None
        device.get_driver.return_value = driver

        device_manager = MagicMock()
        device_manager.get_devices.return_value = {"device1": device}
        task_manager = MagicMock()
        task_manager.convert_to_prefect_states.return_value = []
        task_manager.get_flow_runs_with_filters.return_value = []
        flavor_manager = MagicMock()

        scheduler = AutoScheduler(device_manager, task_manager, flavor_manager)
        spec = make_spec(code_type="qasm")

        result = scheduler.schedule(spec)
        assert result == "device1"

    def test_schedule_multiple_devices_picks_least_busy(self):
        devices = {}
        for name, queue_count in [
            ("busy_device", 10),
            ("idle_device", 0),
        ]:
            device = MagicMock()
            device.get_name.return_value = name
            device.get_status.return_value = "online"
            device.get_enable.return_value = True
            device.get_max_queued_jobs.return_value = -1
            device.tech_type = "superconducting"
            device.details = {}
            driver = MagicMock()
            driver.get_max_qubits.return_value = 20
            driver.available_num_qubits = 20
            driver.get_supported_code_types.return_value = ["qasm"]
            driver.get_supported_basis_gates.return_value = None
            device.get_driver.return_value = driver
            devices[name] = device

        device_manager = MagicMock()
        device_manager.get_devices.return_value = devices

        # Job load counts are read from the qcos database. The
        # DeviceLoadWeigher only cares about queued_job_count, so the
        # running count is mocked as 0 for all devices.
        device_queue_map = {
            "busy_device": 10,
            "idle_device": 0,
        }

        def mock_get_jobs_count(filters=None):
            backend = (filters or {}).get("backend", "")
            job_status = (filters or {}).get("job_status", "")
            if job_status == "QUEUED":
                return device_queue_map.get(backend, 0)
            return 0

        fake_repo = MagicMock()
        fake_repo.get_jobs_count.side_effect = mock_get_jobs_count
        fake_session = MagicMock()
        fake_session.__enter__ = MagicMock(return_value=fake_session)
        fake_session.__exit__ = MagicMock(return_value=False)

        task_manager = MagicMock()
        flavor_manager = MagicMock()

        with (
            patch(
                "wy_qcos.scheduler.auto_scheduler.create_db_session",
                return_value=fake_session,
            ),
            patch(
                "wy_qcos.scheduler.auto_scheduler.JobRepository",
                return_value=fake_repo,
            ),
        ):
            scheduler = AutoScheduler(
                device_manager,
                task_manager,
                flavor_manager,
                db_engine=MagicMock(),
            )
            spec = make_spec(code_type="qasm")

            result = scheduler.schedule(spec)

        assert result == "idle_device"

    def test_schedule_no_device_passes_filters(self):
        device = MagicMock()
        device.get_name.return_value = "device1"
        device.get_status.return_value = "offline"
        device.get_enable.return_value = True
        device.get_max_queued_jobs.return_value = -1
        device.tech_type = "superconducting"
        device.details = {}
        driver = MagicMock()
        driver.get_max_qubits.return_value = 10
        driver.available_num_qubits = 10
        driver.get_supported_code_types.return_value = ["qasm"]
        driver.get_supported_basis_gates.return_value = None
        device.get_driver.return_value = driver

        device_manager = MagicMock()
        device_manager.get_devices.return_value = {"device1": device}
        task_manager = MagicMock()
        task_manager.convert_to_prefect_states.return_value = []
        task_manager.get_flow_runs_with_filters.return_value = []
        flavor_manager = MagicMock()

        scheduler = AutoScheduler(device_manager, task_manager, flavor_manager)
        spec = make_spec(code_type="qasm")

        with pytest.raises(NoValidDeviceError):
            scheduler.schedule(spec)

    def test_build_request_spec_with_flavor(self):
        flavor_manager = MagicMock()
        flavor_manager.get_flavor_specs.return_value = {
            "min_qubits": 16,
            "tech_type": "superconducting",
        }

        spec = AutoScheduler.build_request_spec(
            code_type="qasm",
            num_qubits=5,
            flavor_id="test-flavor-id",
            extra_specs={"max_qubits": 100},
            flavor_manager=flavor_manager,
        )

        assert spec.code_type == "qasm"
        assert spec.num_qubits == 5
        assert spec.flavor_id == "test-flavor-id"
        assert spec.min_qubits == 16
        assert spec.tech_type == "superconducting"
        assert spec.max_qubits == 100
