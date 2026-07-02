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


@dataclass
class RequestSpec:
    """Schedule request spec for filters and weighers.

    Aggregates job info, flavor specs and extra specs.
    extra_specs overrides flavor specs for the same key.
    """

    # --- from job request ---
    job_id: str
    code_type: str = ""
    num_qubits: int = 0

    # --- from flavor ---
    flavor_id: str | None = None
    flavor_specs: dict = field(default_factory=dict)

    # --- from extra_specs (user custom) ---
    extra_specs: dict = field(default_factory=dict)

    @property
    def min_qubits(self) -> int | None:
        """Minimum qubits required (from flavor or extra_specs)."""
        val = self.extra_specs.get(
            "min_qubits", self.flavor_specs.get("min_qubits")
        )
        return val

    @property
    def max_qubits(self) -> int | None:
        """Maximum qubits allowed (extra_specs overrides flavor)."""
        val = self.extra_specs.get(
            "max_qubits", self.flavor_specs.get("max_qubits")
        )
        return val

    @property
    def tech_type(self) -> str | None:
        """Technology type from flavor specs."""
        return self.flavor_specs.get("tech_type")

    @property
    def gate_fidelity_2q_min(self) -> float | None:
        """Minimum 2-qubit gate fidelity from flavor specs."""
        return self.flavor_specs.get("gate_fidelity_2q_min")

    @property
    def has_scheduling_constraints(self) -> bool:
        """Whether any scheduling constraint is specified."""
        return (
            self.flavor_specs is not None and len(self.flavor_specs) > 0
        ) or (self.extra_specs is not None and len(self.extra_specs) > 0)
