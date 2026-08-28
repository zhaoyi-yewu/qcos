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

from dataclasses import dataclass, field

from wy_qcos.common.flavor_constant import FlavorConstant


def _parse_csv(value) -> list:
    """Parse a comma-separated string or list into a list of str.

    None/empty -> []. Non-string non-list -> []. Whitespace
    around each item is stripped; empty items are dropped.
    """
    if value is None:
        return []
    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        return []
    return [str(x).strip() for x in items if str(x).strip()]


@dataclass
class RequestSpec:
    """Schedule request spec for filters and weighers.

    Aggregates job info, flavor specs and extra specs.
    extra_specs overrides flavor specs for the same key.
    """

    # --- from job request ---
    code_type: str | None = None
    num_qubits: int = 0
    shots: int | None = None
    circuit_aggregation: str | None = None
    driver_options: dict | None = None
    transpiler_options: dict | None = None

    # --- from flavor ---
    flavor_id: str | None = None
    flavor_specs: dict = field(default_factory=dict)

    # --- from extra_specs (user custom) ---
    extra_specs: dict = field(default_factory=dict)

    @property
    def min_qubits(self) -> int | None:
        """Minimum qubits required (from flavor or extra_specs)."""
        spec_key = FlavorConstant.FS_KEY_MIN_QUBITS
        val = self.extra_specs.get(spec_key, self.flavor_specs.get(spec_key))
        return val

    @property
    def max_qubits(self) -> int | None:
        """Maximum qubits allowed (extra_specs overrides flavor)."""
        spec_key = FlavorConstant.FS_KEY_MAX_QUBITS
        val = self.extra_specs.get(spec_key, self.flavor_specs.get(spec_key))
        return val

    @property
    def tech_type(self) -> str | None:
        """Technology type from flavor or extra_specs.

        Sourced under the ``qc:tech_types`` key. extra_specs
        overrides flavor. Stored as a comma-separated string, the
        first value is returned for single-value matching in
        ``TechTypeFilter``; use ``tech_types`` for the full list.
        """
        spec_key = FlavorConstant.FS_KEY_TECH_TYPES
        val = self.extra_specs.get(spec_key, self.flavor_specs.get(spec_key))
        return val

    @property
    def tech_types(self) -> list[str]:
        """Technology types list from flavor or extra_specs.

        Sourced under the ``qc:tech_types`` key. The value may be a
        comma-separated string or a list. Returns a list (possibly
        empty).
        """
        raw = self.tech_type
        return _parse_csv(raw)

    @property
    def code_types(self) -> list[str]:
        """Allowed code types from flavor or extra_specs.

        Sourced under the ``qcos:code_types`` key. The value may be a
        comma-separated string or a list. Returns a list (possibly
        empty). When non-empty, CodeTypeFilter uses this list to
        override the job's code_type for matching.
        """
        spec_key = FlavorConstant.FS_KEY_CODE_TYPES
        val = self.extra_specs.get(spec_key, self.flavor_specs.get(spec_key))
        return _parse_csv(val)

    @property
    def devices(self) -> list[str]:
        """Whitelist of device names from flavor or extra_specs.

        Sourced under the ``qcos:devices`` key. The value may be a
        comma-separated string or a list. ``all`` means no
        restriction. Returns a list (possibly empty).
        """
        spec_key = FlavorConstant.FS_KEY_DEVICES
        val = self.extra_specs.get(spec_key, self.flavor_specs.get(spec_key))
        return _parse_csv(val)

    @property
    def exclude_devices(self) -> list[str]:
        """Blacklist of device names from flavor or extra_specs.

        Sourced under the ``qcos:exclude_devices`` key. The value may
        be a comma-separated string or a list. Returns a list
        (possibly empty).
        """
        spec_key = FlavorConstant.FS_KEY_EXCLUDE_DEVICES
        val = self.extra_specs.get(spec_key, self.flavor_specs.get(spec_key))
        return _parse_csv(val)

    @property
    def device_groups(self) -> list[str] | None:
        """Device group references from extra_specs or flavor.

        Sourced under the ``qc:device_groups`` key. extra_specs
        overrides flavor. The value may be a comma-separated string
        or a list. Returns a list, or None when neither source
        specifies the key (so DeviceGroupFilter can distinguish
        "disabled" from "empty").
        """
        spec_key = FlavorConstant.FS_KEY_GATE_DEVICE_GROUPS
        if spec_key in self.extra_specs:
            parsed = _parse_csv(self.extra_specs.get(spec_key))
            return parsed if parsed else None
        val = self.flavor_specs.get(spec_key)
        if val is None:
            return None
        if isinstance(val, (list, tuple, set)):
            result = [str(x) for x in val if str(x).strip()]
            return result if result else None
        parsed = _parse_csv(val)
        return parsed if parsed else None

    @property
    def gate_fidelity_1q_min(self) -> float | None:
        """Minimum 1-qubit gate fidelity from flavor specs."""
        spec_key = FlavorConstant.FS_KEY_GATE_FIDELITY_1Q_MIN
        return self.flavor_specs.get(spec_key)

    @property
    def gate_fidelity_2q_min(self) -> float | None:
        """Minimum 2-qubit gate fidelity from flavor specs."""
        spec_key = FlavorConstant.FS_KEY_GATE_FIDELITY_2Q_MIN
        return self.flavor_specs.get(spec_key)

    @property
    def device_availability(self) -> float | None:
        """Minimum device availability (availability rate) required.

        Sourced from flavor or extra_specs under the
        ``qc:device_availability`` key (a float in [0.0, 1.0]).
        extra_specs overrides flavor.
        """
        spec_key = FlavorConstant.FS_KEY_DEVICE_AVAILABILITY
        val = self.extra_specs.get(spec_key, self.flavor_specs.get(spec_key))
        return val

    @property
    def has_scheduling_constraints(self) -> bool:
        """Whether any scheduling constraint is specified."""
        return (
            self.flavor_specs is not None and len(self.flavor_specs) > 0
        ) or (self.extra_specs is not None and len(self.extra_specs) > 0)

    @staticmethod
    def validate_extra_specs(extra_specs: dict) -> tuple[bool, str | None]:
        """Validate that extra_specs keys are supported.

        Each key in extra_specs must be one of the recognized
        scheduling spec keys. Returns (True, None) on success,
        (False, error_msg) when an unsupported key is found.
        """
        if not extra_specs:
            return True, None
        allowed = {
            FlavorConstant.FS_KEY_MIN_QUBITS,
            FlavorConstant.FS_KEY_MAX_QUBITS,
            FlavorConstant.FS_KEY_GATE_FIDELITY_1Q_MIN,
            FlavorConstant.FS_KEY_GATE_FIDELITY_2Q_MIN,
            FlavorConstant.FS_KEY_GATE_DEVICE_GROUPS,
            FlavorConstant.FS_KEY_DEVICE_AVAILABILITY,
            FlavorConstant.FS_KEY_TECH_TYPES,
            FlavorConstant.FS_KEY_CODE_TYPES,
            FlavorConstant.FS_KEY_DEVICES,
            FlavorConstant.FS_KEY_EXCLUDE_DEVICES,
        }
        for key in extra_specs:
            if key not in allowed:
                return (
                    False,
                    f"Unsupported extra_specs field: '{key}'. "
                    f"Allowed fields: {sorted(allowed)}",
                )
        return True, None
