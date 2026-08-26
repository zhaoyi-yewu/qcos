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

from wy_qcos.common.flavor_constant import FlavorConstant
from wy_qcos.scheduler.request_spec import RequestSpec
from wy_qcos.scheduler.device_state import DeviceState
from wy_qcos.scheduler.filters.code_type import CodeTypeFilter
from wy_qcos.scheduler.filters.device_availability import (
    DeviceAvailabilityFilter,
)
from wy_qcos.scheduler.filters.device_name import DeviceNameFilter
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
    input_constrains=None,
    enable_circuit_aggregation=False,
    driver_options_schema=None,
    transpiler_options_schema=None,
):
    """Create a DeviceState for testing."""
    return DeviceState(
        device=None,
        name=name,
        status=status,
        enable=enable,
        max_qubits=max_qubits,
        available_qubits=max_qubits,
        tech_type=tech_type,
        supported_code_types=supported_code_types or ["qasm", "qasm2"],
        supported_basis_gates=None,
        details=details or {},
        queued_job_count=queued_job_count,
        running_job_count=running_job_count,
        max_queued_jobs=max_queued_jobs,
        input_constrains=input_constrains or {},
        enable_circuit_aggregation=enable_circuit_aggregation,
        driver_options_schema=driver_options_schema,
        transpiler_options_schema=transpiler_options_schema,
    )


def make_spec(
    code_type="qasm",
    num_qubits=0,
    shots=None,
    circuit_aggregation=None,
    driver_options=None,
    transpiler_options=None,
    flavor_specs=None,
    extra_specs=None,
    flavor_id=None,
):
    """Create a RequestSpec for testing."""
    return RequestSpec(
        code_type=code_type,
        num_qubits=num_qubits,
        shots=shots,
        circuit_aggregation=circuit_aggregation,
        driver_options=driver_options,
        transpiler_options=transpiler_options,
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
        key = FlavorConstant.FS_KEY_MIN_QUBITS
        spec = make_spec(flavor_specs={key: 16})
        assert filter_obj._filter_one(device, spec) is False

    def test_filter_max_qubits_from_extra_specs(self):
        filter_obj = QubitCountFilter()
        device = make_device_state(max_qubits=200)
        key = FlavorConstant.FS_KEY_MAX_QUBITS
        spec = make_spec(extra_specs={key: 100})
        assert filter_obj._filter_one(device, spec) is False


class TestTechTypeFilter:
    """Tests for TechTypeFilter."""

    def test_is_enabled_when_tech_type_set(self):
        filter_obj = TechTypeFilter()
        spec = make_spec(flavor_specs={"qc:tech_types": "superconducting"})
        assert filter_obj.is_enabled(spec) is True

    def test_is_disabled_when_no_tech_type(self):
        filter_obj = TechTypeFilter()
        spec = make_spec()
        assert filter_obj.is_enabled(spec) is False

    def test_filter_matching_tech_type(self):
        filter_obj = TechTypeFilter()
        device = make_device_state(tech_type="superconducting")
        spec = make_spec(flavor_specs={"qc:tech_types": "superconducting"})
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_non_matching_tech_type(self):
        filter_obj = TechTypeFilter()
        device = make_device_state(tech_type="ion_trap")
        spec = make_spec(flavor_specs={"qc:tech_types": "superconducting"})
        assert filter_obj._filter_one(device, spec) is False

    def test_filter_matching_one_of_multiple(self):
        filter_obj = TechTypeFilter()
        device = make_device_state(tech_type="ion_trap")
        spec = make_spec(
            flavor_specs={"qc:tech_types": "superconducting,ion_trap"}
        )
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_non_matching_one_of_multiple(self):
        filter_obj = TechTypeFilter()
        device = make_device_state(tech_type="neutral_atom")
        spec = make_spec(
            flavor_specs={"qc:tech_types": "superconducting,ion_trap"}
        )
        assert filter_obj._filter_one(device, spec) is False


class TestGateFidelityFilter:
    """Tests for GateFidelityFilter."""

    def test_is_enabled_when_2q_fidelity_set(self):
        filter_obj = GateFidelityFilter()
        key = FlavorConstant.FS_KEY_GATE_FIDELITY_2Q_MIN
        spec = make_spec(flavor_specs={key: 0.99})
        assert filter_obj.is_enabled(spec) is True

    def test_is_enabled_when_1q_fidelity_set(self):
        filter_obj = GateFidelityFilter()
        key = FlavorConstant.FS_KEY_GATE_FIDELITY_1Q_MIN
        spec = make_spec(flavor_specs={key: 0.99})
        assert filter_obj.is_enabled(spec) is True

    def test_is_disabled_when_no_fidelity(self):
        filter_obj = GateFidelityFilter()
        spec = make_spec()
        assert filter_obj.is_enabled(spec) is False

    def test_filter_2q_fidelity_meets_threshold(self):
        filter_obj = GateFidelityFilter()
        details = {
            "calibration": {
                "coupler_metrics": [
                    {"qubits": [0, 1], "cz_fidelity": 0.998},
                    {"qubits": [1, 2], "cz_fidelity": 0.999},
                ]
            }
        }
        device = make_device_state(details=details)
        key = FlavorConstant.FS_KEY_GATE_FIDELITY_2Q_MIN
        spec = make_spec(flavor_specs={key: 0.995})
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_2q_fidelity_below_threshold(self):
        filter_obj = GateFidelityFilter()
        details = {
            "calibration": {
                "coupler_metrics": [
                    {"qubits": [0, 1], "cz_fidelity": 0.98},
                    {"qubits": [1, 2], "cz_fidelity": 0.99},
                ]
            }
        }
        device = make_device_state(details=details)
        key = FlavorConstant.FS_KEY_GATE_FIDELITY_2Q_MIN
        spec = make_spec(flavor_specs={key: 0.995})
        assert filter_obj._filter_one(device, spec) is False

    def test_filter_1q_fidelity_meets_threshold(self):
        filter_obj = GateFidelityFilter()
        details = {
            "calibration": {
                "qubit_metrics": [
                    {"qubit_id": 0, "xeb_fidelity": 0.999},
                    {"qubit_id": 1, "xeb_fidelity": 0.998},
                ]
            }
        }
        device = make_device_state(details=details)
        key = FlavorConstant.FS_KEY_GATE_FIDELITY_1Q_MIN
        spec = make_spec(flavor_specs={key: 0.995})
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_1q_fidelity_below_threshold(self):
        filter_obj = GateFidelityFilter()
        details = {
            "calibration": {
                "qubit_metrics": [
                    {"qubit_id": 0, "xeb_fidelity": 0.98},
                    {"qubit_id": 1, "xeb_fidelity": 0.99},
                ]
            }
        }
        device = make_device_state(details=details)
        key = FlavorConstant.FS_KEY_GATE_FIDELITY_1Q_MIN
        spec = make_spec(flavor_specs={key: 0.995})
        assert filter_obj._filter_one(device, spec) is False

    def test_filter_no_fidelity_data(self):
        filter_obj = GateFidelityFilter()
        device = make_device_state(details={})
        key = FlavorConstant.FS_KEY_GATE_FIDELITY_2Q_MIN
        spec = make_spec(flavor_specs={key: 0.995})
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_both_1q_and_2q_pass(self):
        filter_obj = GateFidelityFilter()
        details = {
            "calibration": {
                "qubit_metrics": [
                    {"qubit_id": 0, "xeb_fidelity": 0.999},
                ],
                "coupler_metrics": [
                    {"qubits": [0, 1], "cz_fidelity": 0.998},
                ],
            }
        }
        device = make_device_state(details=details)
        key1 = FlavorConstant.FS_KEY_GATE_FIDELITY_1Q_MIN
        key2 = FlavorConstant.FS_KEY_GATE_FIDELITY_2Q_MIN
        spec = make_spec(flavor_specs={key1: 0.995, key2: 0.995})
        assert filter_obj._filter_one(device, spec) is True

    def test_filter_1q_pass_2q_fail(self):
        filter_obj = GateFidelityFilter()
        details = {
            "calibration": {
                "qubit_metrics": [
                    {"qubit_id": 0, "xeb_fidelity": 0.999},
                ],
                "coupler_metrics": [
                    {"qubits": [0, 1], "cz_fidelity": 0.98},
                ],
            }
        }
        device = make_device_state(details=details)
        key1 = FlavorConstant.FS_KEY_GATE_FIDELITY_1Q_MIN
        key2 = FlavorConstant.FS_KEY_GATE_FIDELITY_2Q_MIN
        spec = make_spec(flavor_specs={key1: 0.995, key2: 0.995})
        assert filter_obj._filter_one(device, spec) is False


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


class TestDeviceAvailabilityFilter:
    """Tests for DeviceAvailabilityFilter."""

    def _make_device(self, availability_total=0.0):
        """Create a DeviceState with availability set."""
        state = make_device_state()
        state.set_availability(availability_total=availability_total)
        return state

    def test_not_enabled_when_no_threshold(self):
        """Filter is disabled when device_availability not specified."""
        filter_obj = DeviceAvailabilityFilter()
        spec = make_spec()
        assert filter_obj.is_enabled(spec) is False

    def test_enabled_when_threshold_specified(self):
        """Filter is enabled when device_availability is set."""
        filter_obj = DeviceAvailabilityFilter()
        spec = make_spec(
            flavor_specs={FlavorConstant.FS_KEY_DEVICE_AVAILABILITY: 0.9}
        )
        assert filter_obj.is_enabled(spec) is True

    def test_device_meets_threshold(self):
        """Device with availability >= threshold passes."""
        filter_obj = DeviceAvailabilityFilter()
        device = self._make_device(availability_total=0.95)
        spec = make_spec(
            flavor_specs={FlavorConstant.FS_KEY_DEVICE_AVAILABILITY: 0.9}
        )
        assert filter_obj._filter_one(device, spec) is True

    def test_device_below_threshold(self):
        """Device with availability < threshold is filtered out."""
        filter_obj = DeviceAvailabilityFilter()
        device = self._make_device(availability_total=0.5)
        spec = make_spec(
            flavor_specs={FlavorConstant.FS_KEY_DEVICE_AVAILABILITY: 0.9}
        )
        assert filter_obj._filter_one(device, spec) is False

    def test_device_no_availability_blocked_when_threshold_set(self):
        """Device with availability_total=0.0 blocked when threshold set."""
        filter_obj = DeviceAvailabilityFilter()
        device = self._make_device(availability_total=0.0)
        spec = make_spec(
            flavor_specs={FlavorConstant.FS_KEY_DEVICE_AVAILABILITY: 0.9}
        )
        assert filter_obj._filter_one(device, spec) is False

    def test_extra_specs_overrides_flavor(self):
        """extra_specs device_availability overrides flavor."""
        filter_obj = DeviceAvailabilityFilter()
        device = self._make_device(availability_total=0.8)
        spec = make_spec(
            flavor_specs={FlavorConstant.FS_KEY_DEVICE_AVAILABILITY: 0.9},
            extra_specs={FlavorConstant.FS_KEY_DEVICE_AVAILABILITY: 0.7},
        )
        # extra_specs (0.7) overrides flavor (0.9), device passes
        assert filter_obj._filter_one(device, spec) is True


class TestDeviceNameFilter:
    """Tests for DeviceNameFilter (whitelist + blacklist)."""

    # --- enable/disable ---

    def test_is_disabled_when_no_devices_and_no_exclude(self):
        filter_obj = DeviceNameFilter()
        spec = make_spec()
        assert filter_obj.is_enabled(spec) is False

    def test_is_enabled_when_devices_set(self):
        filter_obj = DeviceNameFilter()
        spec = make_spec(flavor_specs={"qcos:devices": "dev1,dev2"})
        assert filter_obj.is_enabled(spec) is True

    def test_is_enabled_when_exclude_set(self):
        filter_obj = DeviceNameFilter()
        spec = make_spec(flavor_specs={"qcos:exclude_devices": "dev1"})
        assert filter_obj.is_enabled(spec) is True

    # --- whitelist ---

    def test_device_in_whitelist(self):
        filter_obj = DeviceNameFilter()
        device = make_device_state(name="dev1")
        spec = make_spec(flavor_specs={"qcos:devices": "dev1,dev2"})
        assert filter_obj._filter_one(device, spec) is True

    def test_device_not_in_whitelist(self):
        filter_obj = DeviceNameFilter()
        device = make_device_state(name="dev3")
        spec = make_spec(flavor_specs={"qcos:devices": "dev1,dev2"})
        assert filter_obj._filter_one(device, spec) is False

    def test_all_means_no_restriction(self):
        filter_obj = DeviceNameFilter()
        device = make_device_state(name="dev_any")
        spec = make_spec(flavor_specs={"qcos:devices": "all"})
        assert filter_obj._filter_one(device, spec) is True

    def test_whitelist_only_disabled_returns_true(self):
        filter_obj = DeviceNameFilter()
        device = make_device_state(name="dev1")
        spec = make_spec()
        assert filter_obj._filter_one(device, spec) is True

    def test_extra_specs_overrides_flavor(self):
        filter_obj = DeviceNameFilter()
        device = make_device_state(name="dev3")
        spec = make_spec(
            flavor_specs={"qcos:devices": "dev1,dev2"},
            extra_specs={"qcos:devices": "dev3,dev4"},
        )
        assert filter_obj._filter_one(device, spec) is True

    # --- blacklist ---

    def test_device_in_blacklist(self):
        filter_obj = DeviceNameFilter()
        device = make_device_state(name="dev1")
        spec = make_spec(flavor_specs={"qcos:exclude_devices": "dev1,dev2"})
        assert filter_obj._filter_one(device, spec) is False

    def test_device_not_in_blacklist(self):
        filter_obj = DeviceNameFilter()
        device = make_device_state(name="dev3")
        spec = make_spec(flavor_specs={"qcos:exclude_devices": "dev1,dev2"})
        assert filter_obj._filter_one(device, spec) is True

    # --- whitelist + blacklist combined ---

    def test_whitelist_passes_but_blacklist_excludes(self):
        """Device in whitelist but also in blacklist is excluded."""
        filter_obj = DeviceNameFilter()
        device = make_device_state(name="dev1")
        spec = make_spec(
            flavor_specs={
                "qcos:devices": "dev1,dev2",
                "qcos:exclude_devices": "dev1",
            }
        )
        assert filter_obj._filter_one(device, spec) is False

    def test_whitelist_and_blacklist_both_pass(self):
        """Device in whitelist and not in blacklist passes."""
        filter_obj = DeviceNameFilter()
        device = make_device_state(name="dev2")
        spec = make_spec(
            flavor_specs={
                "qcos:devices": "dev1,dev2",
                "qcos:exclude_devices": "dev1",
            }
        )
        assert filter_obj._filter_one(device, spec) is True

    def test_blacklist_overrides_whitelist_all(self):
        """Even with devices=all, blacklist still excludes."""
        filter_obj = DeviceNameFilter()
        device = make_device_state(name="dev1")
        spec = make_spec(
            flavor_specs={
                "qcos:devices": "all",
                "qcos:exclude_devices": "dev1",
            }
        )
        assert filter_obj._filter_one(device, spec) is False


class TestCodeTypeFilterOverride:
    """Tests for CodeTypeFilter qcos:code_types override."""

    def test_code_types_override_matches(self):
        filter_obj = CodeTypeFilter()
        device = make_device_state(supported_code_types=["qasm", "qasm2"])
        spec = make_spec(
            code_type="qubo",
            flavor_specs={"qcos:code_types": "qasm"},
        )
        assert filter_obj._filter_one(device, spec) is True

    def test_code_types_override_no_match(self):
        filter_obj = CodeTypeFilter()
        device = make_device_state(supported_code_types=["qasm"])
        spec = make_spec(
            code_type="qasm",
            flavor_specs={"qcos:code_types": "qubo"},
        )
        assert filter_obj._filter_one(device, spec) is False

    def test_code_types_multiple_match_one(self):
        filter_obj = CodeTypeFilter()
        device = make_device_state(supported_code_types=["qasm2"])
        spec = make_spec(flavor_specs={"qcos:code_types": "qasm,qasm2"})
        assert filter_obj._filter_one(device, spec) is True

    def test_no_code_types_falls_back_to_job_code_type(self):
        filter_obj = CodeTypeFilter()
        device = make_device_state(supported_code_types=["qasm", "qasm2"])
        spec = make_spec(code_type="qasm")
        assert filter_obj._filter_one(device, spec) is True


class TestInputConstraintsFilter:
    """Tests for InputConstraintsFilter."""

    def test_shots_none_passes(self):
        """Shots is None: always passes."""
        from schema import And, Schema

        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(
            input_constrains={
                "job_shots": Schema(And(int, lambda x: 1024 <= x <= 102400))
            }
        )
        spec = make_spec(shots=None)
        assert filter_obj._filter_one(device, spec) is True

    def test_no_constraint_passes(self):
        """Driver declares no job_shots constraint: passes."""
        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(input_constrains={})
        spec = make_spec(shots=100)
        assert filter_obj._filter_one(device, spec) is True

    def test_constraint_none_passes(self):
        """job_shots constraint value is None: passes."""
        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(input_constrains={"job_shots": None})
        spec = make_spec(shots=100)
        assert filter_obj._filter_one(device, spec) is True

    def test_shots_valid_passes(self):
        """Shots satisfy the schema: passes."""
        from schema import And, Schema

        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(
            input_constrains={
                "job_shots": Schema(
                    And(
                        int,
                        lambda x: 1024 <= x <= 102400,
                        lambda x: x % 1024 == 0,
                    )
                )
            }
        )
        spec = make_spec(shots=2048)
        assert filter_obj._filter_one(device, spec) is True

    def test_shots_invalid_filtered(self):
        """Shots violate the schema: filtered out."""
        from schema import And, Schema

        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(
            input_constrains={
                "job_shots": Schema(
                    And(
                        int,
                        lambda x: 1024 <= x <= 102400,
                        lambda x: x % 1024 == 0,
                    )
                )
            }
        )
        spec = make_spec(shots=100)
        assert filter_obj._filter_one(device, spec) is False

    def test_shots_out_of_range_filtered(self):
        """Shots in range but not multiple of 1024: filtered out."""
        from schema import And, Schema

        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(
            input_constrains={
                "job_shots": Schema(
                    And(
                        int,
                        lambda x: 1024 <= x <= 102400,
                        lambda x: x % 1024 == 0,
                    )
                )
            }
        )
        spec = make_spec(shots=2000)
        assert filter_obj._filter_one(device, spec) is False


class TestInputConstraintsCircuitAggregation:
    """Tests for InputConstraintsFilter circuit_aggregation check."""

    def test_aggregation_enabled_any_value_passes(self):
        """enable_circuit_aggregation=True: any value passes."""
        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(enable_circuit_aggregation=True)
        spec = make_spec(circuit_aggregation="internal")
        assert filter_obj._filter_one(device, spec) is True

    def test_aggregation_disabled_none_passes(self):
        """enable_circuit_aggregation=False: None passes."""
        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(enable_circuit_aggregation=False)
        spec = make_spec(circuit_aggregation=None)
        assert filter_obj._filter_one(device, spec) is True

    def test_aggregation_disabled_none_string_passes(self):
        """enable_circuit_aggregation=False: 'None' string passes."""
        from wy_qcos.common.constant import Constant
        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(enable_circuit_aggregation=False)
        spec = make_spec(circuit_aggregation=Constant.AGGREGATION_TYPE_NONE)
        assert filter_obj._filter_one(device, spec) is True

    def test_aggregation_disabled_internal_filtered(self):
        """enable_circuit_aggregation=False: 'internal' filtered out."""
        from wy_qcos.common.constant import Constant
        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(enable_circuit_aggregation=False)
        spec = make_spec(
            circuit_aggregation=Constant.AGGREGATION_TYPE_INTERNAL
        )
        assert filter_obj._filter_one(device, spec) is False

    def test_aggregation_disabled_external_filtered(self):
        """enable_circuit_aggregation=False: 'external' filtered out."""
        from wy_qcos.common.constant import Constant
        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(enable_circuit_aggregation=False)
        spec = make_spec(
            circuit_aggregation=Constant.AGGREGATION_TYPE_EXTERNAL
        )
        assert filter_obj._filter_one(device, spec) is False


class TestInputConstraintsDriverOptions:
    """Tests for InputConstraintsFilter driver_options check."""

    def test_driver_options_none_passes(self):
        """driver_options is None: passes."""
        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(driver_options_schema={"sleep": int})
        spec = make_spec(driver_options=None)
        assert filter_obj._filter_one(device, spec) is True

    def test_no_schema_passes(self):
        """Driver declares no driver_options_schema: passes."""
        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(driver_options_schema=None)
        spec = make_spec(driver_options={"sleep": 10})
        assert filter_obj._filter_one(device, spec) is True

    def test_valid_driver_options_passes(self):
        """driver_options matching schema: passes."""
        from schema import Optional

        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(
            driver_options_schema={
                Optional("sleep"): int,
                Optional("compute_fidelity"): bool,
            }
        )
        spec = make_spec(
            driver_options={"sleep": 10, "compute_fidelity": True}
        )
        assert filter_obj._filter_one(device, spec) is True

    def test_invalid_driver_options_filtered(self):
        """driver_options with wrong type: filtered out."""
        from schema import Optional

        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(
            driver_options_schema={
                Optional("sleep"): int,
                Optional("compute_fidelity"): bool,
            }
        )
        spec = make_spec(driver_options={"sleep": "not_an_int"})
        assert filter_obj._filter_one(device, spec) is False

    def test_extra_keys_filtered(self):
        """driver_options with extra unknown keys: filtered out."""
        from schema import Optional

        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(
            driver_options_schema={
                Optional("sleep"): int,
            }
        )
        spec = make_spec(driver_options={"unknown_key": 1})
        assert filter_obj._filter_one(device, spec) is False


class TestInputConstraintsTranspilerOptions:
    """Tests for InputConstraintsFilter transpiler_options check."""

    def test_transpiler_options_none_passes(self):
        """transpiler_options is None: passes."""
        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(
            transpiler_options_schema={"optimization_level": int}
        )
        spec = make_spec(transpiler_options=None)
        assert filter_obj._filter_one(device, spec) is True

    def test_no_transpiler_schema_passes(self):
        """Driver declares no transpiler_options_schema: passes."""
        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(transpiler_options_schema=None)
        spec = make_spec(transpiler_options={"optimization_level": 1})
        assert filter_obj._filter_one(device, spec) is True

    def test_empty_transpiler_schema_passes(self):
        """Driver declares empty transpiler_options_schema: passes."""
        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(transpiler_options_schema={})
        spec = make_spec(transpiler_options={"optimization_level": 1})
        assert filter_obj._filter_one(device, spec) is True

    def test_valid_transpiler_options_passes(self):
        """transpiler_options matching schema: passes."""
        from schema import Optional

        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(
            transpiler_options_schema={
                "optimization_level": (
                    Optional("optimization_level", default=1),
                    int,
                ),
                "layout_method": (Optional("layout_method"), str),
            }
        )
        spec = make_spec(
            transpiler_options={
                "optimization_level": 2,
                "layout_method": "dense",
            }
        )
        assert filter_obj._filter_one(device, spec) is True

    def test_invalid_transpiler_options_filtered(self):
        """transpiler_options with wrong type: filtered out."""
        from schema import Optional

        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(
            transpiler_options_schema={
                "optimization_level": (
                    Optional("optimization_level"),
                    int,
                ),
            }
        )
        spec = make_spec(
            transpiler_options={"optimization_level": "not_an_int"}
        )
        assert filter_obj._filter_one(device, spec) is False

    def test_transpiler_extra_keys_filtered(self):
        """transpiler_options with extra unknown keys: filtered out."""
        from schema import Optional

        from wy_qcos.scheduler.filters.input_constraints import (
            InputConstraintsFilter,
        )

        filter_obj = InputConstraintsFilter()
        device = make_device_state(
            transpiler_options_schema={
                "optimization_level": (
                    Optional("optimization_level"),
                    int,
                ),
            }
        )
        spec = make_spec(transpiler_options={"unknown_key": 1})
        assert filter_obj._filter_one(device, spec) is False
