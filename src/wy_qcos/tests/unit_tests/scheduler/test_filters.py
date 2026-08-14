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

"""Unit tests for scheduler filters."""

from wy_qcos.scheduler.request_spec import RequestSpec
from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.filters.code_type import CodeTypeFilter
from wy_qcos.scheduler.filters.device_status import DeviceStatusFilter
from wy_qcos.scheduler.filters.qubit_count import QubitCountFilter
from wy_qcos.scheduler.filters.tech_type import TechTypeFilter
from wy_qcos.scheduler.filters.gate_fidelity import GateFidelityFilter
from wy_qcos.scheduler.filters.queue_limit import QueueLimitFilter
from wy_qcos.scheduler.filters.base import BaseFilterHandler
from wy_qcos.scheduler.filters import DEFAULT_FILTERS


def make_device_state(
    name="device1",
    status="online",
    enable=True,
    max_qubits=10,
    tech_type="superconducting",
    supported_code_types=None,
    details=None,
    queued_job_count=0,
    running_job_count=0,
    max_queued_jobs=-1,
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
        supported_code_types=supported_code_types or ["qasm", "qasm2"],
        supported_basis_gates=None,
        details=details or {},
        queued_job_count=queued_job_count,
        running_job_count=running_job_count,
        max_queued_jobs=max_queued_jobs,
    )


def make_spec(
    code_type="qasm",
    num_qubits=0,
    flavor_specs=None,
    extra_specs=None,
    flavor_id=None,
):
    """Create a RequestSpec for testing."""
    return RequestSpec(
        code_type=code_type,
        num_qubits=num_qubits,
        flavor_id=flavor_id,
        flavor_specs=flavor_specs or {},
        extra_specs=extra_specs or {},
    )


class TestCodeTypeFilter:
    """Tests for CodeTypeFilter."""

    def test_filter_matching_code_type(self):
        filter_obj = CodeTypeFilter()
        device = make_device_state(supported_code_types=["qasm", "qasm2"])
        spec = make_spec(code_type="qasm")
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_non_matching_code_type(self):
        filter_obj = CodeTypeFilter()
        device = make_device_state(supported_code_types=["qasm"])
        spec = make_spec(code_type="qubo")
        assert filter_obj._filter_one(device, spec) is False

    def test_filter_empty_code_type(self):
        filter_obj = CodeTypeFilter()
        device = make_device_state()
        spec = make_spec(code_type="")
        assert filter_obj._filter_one(device, spec) is True


class TestDeviceStatusFilter:
    """Tests for DeviceStatusFilter."""

    def test_filter_online(self):
        filter_obj = DeviceStatusFilter()
        device = make_device_state(status="online", enable=True)
        spec = make_spec()
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_busy(self):
        filter_obj = DeviceStatusFilter()
        device = make_device_state(status="busy", enable=True)
        spec = make_spec()
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_offline(self):
        filter_obj = DeviceStatusFilter()
        device = make_device_state(status="offline", enable=True)
        spec = make_spec()
        assert filter_obj._filter_one(device, spec) is False

    def test_filter_disabled(self):
        filter_obj = DeviceStatusFilter()
        device = make_device_state(enable=False)
        spec = make_spec()
        assert filter_obj._filter_one(device, spec) is False


class TestQubitCountFilter:
    """Tests for QubitCountFilter."""

    def test_filter_sufficient_qubits(self):
        filter_obj = QubitCountFilter()
        device = make_device_state(max_qubits=20)
        spec = make_spec(num_qubits=10)
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_insufficient_qubits(self):
        filter_obj = QubitCountFilter()
        device = make_device_state(max_qubits=5)
        spec = make_spec(num_qubits=10)
        assert filter_obj._filter_one(device, spec) is False

    def test_filter_no_qubit_requirement(self):
        filter_obj = QubitCountFilter()
        device = make_device_state(max_qubits=5)
        spec = make_spec(num_qubits=0)
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_min_qubits_from_flavor(self):
        filter_obj = QubitCountFilter()
        device = make_device_state(max_qubits=10)
        spec = make_spec(flavor_specs={"min_qubits": 16})
        assert filter_obj._filter_one(device, spec) is False

    def test_filter_max_qubits_from_extra_specs(self):
        filter_obj = QubitCountFilter()
        device = make_device_state(max_qubits=200)
        spec = make_spec(extra_specs={"max_qubits": 100})
        assert filter_obj._filter_one(device, spec) is False


class TestTechTypeFilter:
    """Tests for TechTypeFilter."""

    def test_is_enabled_when_tech_type_set(self):
        filter_obj = TechTypeFilter()
        spec = make_spec(flavor_specs={"tech_type": "superconducting"})
        assert filter_obj.is_enabled(spec) is True

    def test_is_disabled_when_no_tech_type(self):
        filter_obj = TechTypeFilter()
        spec = make_spec()
        assert filter_obj.is_enabled(spec) is False

    def test_filter_matching_tech_type(self):
        filter_obj = TechTypeFilter()
        device = make_device_state(tech_type="superconducting")
        spec = make_spec(flavor_specs={"tech_type": "superconducting"})
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_non_matching_tech_type(self):
        filter_obj = TechTypeFilter()
        device = make_device_state(tech_type="ion_trap")
        spec = make_spec(flavor_specs={"tech_type": "superconducting"})
        assert filter_obj._filter_one(device, spec) is False


class TestGateFidelityFilter:
    """Tests for GateFidelityFilter."""

    def test_is_enabled_when_fidelity_set(self):
        filter_obj = GateFidelityFilter()
        spec = make_spec(flavor_specs={"gate_fidelity_2q_min": 0.99})
        assert filter_obj.is_enabled(spec) is True

    def test_is_disabled_when_no_fidelity(self):
        filter_obj = GateFidelityFilter()
        spec = make_spec()
        assert filter_obj.is_enabled(spec) is False

    def test_filter_fidelity_meets_threshold(self):
        filter_obj = GateFidelityFilter()
        details = {
            "double_qubit_prop": {
                "q1": {"gate_fidelity": 0.998},
                "q2": {"gate_fidelity": 0.999},
            }
        }
        device = make_device_state(details=details)
        spec = make_spec(flavor_specs={"gate_fidelity_2q_min": 0.995})
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_fidelity_below_threshold(self):
        filter_obj = GateFidelityFilter()
        details = {
            "double_qubit_prop": {
                "q1": {"gate_fidelity": 0.98},
                "q2": {"gate_fidelity": 0.99},
            }
        }
        device = make_device_state(details=details)
        spec = make_spec(flavor_specs={"gate_fidelity_2q_min": 0.995})
        assert filter_obj._filter_one(device, spec) is False

    def test_filter_no_fidelity_data(self):
        filter_obj = GateFidelityFilter()
        device = make_device_state(details={})
        spec = make_spec(flavor_specs={"gate_fidelity_2q_min": 0.995})
        assert filter_obj._filter_one(device, spec) is True


class TestQueueLimitFilter:
    """Tests for QueueLimitFilter."""

    def test_filter_no_limit(self):
        filter_obj = QueueLimitFilter()
        device = make_device_state(max_queued_jobs=-1, queued_job_count=100)
        spec = make_spec()
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_under_limit(self):
        filter_obj = QueueLimitFilter()
        device = make_device_state(max_queued_jobs=10, queued_job_count=5)
        spec = make_spec()
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_at_limit(self):
        filter_obj = QueueLimitFilter()
        device = make_device_state(max_queued_jobs=10, queued_job_count=10)
        spec = make_spec()
        assert filter_obj._filter_one(device, spec) is False

    def test_filter_zero_limit_with_jobs(self):
        filter_obj = QueueLimitFilter()
        device = make_device_state(max_queued_jobs=0, queued_job_count=1)
        spec = make_spec()
        assert filter_obj._filter_one(device, spec) is False

    def test_filter_zero_limit_no_jobs(self):
        filter_obj = QueueLimitFilter()
        device = make_device_state(max_queued_jobs=0, queued_job_count=0)
        spec = make_spec()
        assert filter_obj._filter_one(device, spec) is True


class TestBaseFilterHandler:
    """Tests for BaseFilterHandler."""

    def test_filter_chain_all_pass(self):
        handler = BaseFilterHandler(DEFAULT_FILTERS)
        devices = [
            make_device_state(name="d1", status="online", enable=True),
            make_device_state(name="d2", status="online", enable=True),
        ]
        spec = make_spec(code_type="qasm")
        result = handler.get_filtered_objects(devices, spec)
        assert len(result) == 2

    def test_filter_chain_some_filtered(self):
        handler = BaseFilterHandler(DEFAULT_FILTERS)
        devices = [
            make_device_state(
                name="d1",
                status="online",
                enable=True,
                supported_code_types=["qasm"],
            ),
            make_device_state(
                name="d2",
                status="offline",
                enable=True,
                supported_code_types=["qasm"],
            ),
        ]
        spec = make_spec(code_type="qasm")
        result = handler.get_filtered_objects(devices, spec)
        assert len(result) == 1
        assert result[0].name == "d1"

    def test_filter_chain_all_filtered(self):
        handler = BaseFilterHandler(DEFAULT_FILTERS)
        devices = [
            make_device_state(name="d1", status="offline"),
        ]
        spec = make_spec(code_type="qasm")
        result = handler.get_filtered_objects(devices, spec)
        assert len(result) == 0
