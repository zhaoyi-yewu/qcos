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
from typing import Any

from wy_qcos.device.device import Device


@dataclass
class DeviceState:
    """Device state object for filters and weighers.

    Wraps a Device instance together with its dynamic load info,
    providing a unified interface for filter/weigher operations.
    """

    # Original Device instance
    device: Device
    name: str = ""
    status: str = ""
    enable: bool = False
    max_qubits: int = 0
    available_num_qubits: int = -1
    tech_type: str = ""
    supported_code_types: list[str] = field(default_factory=list)
    supported_basis_gates: list[str] | None = None
    details: dict = field(default_factory=dict)

    # Dynamic load info (from Prefect)
    queued_job_count: int = 0
    running_job_count: int = 0
    max_queued_jobs: int = -1

    # Historical statistics (from DB)
    avg_exec_time_per_qubit: float = 0.0

    @classmethod
    def from_device(
        cls, device: Device, transpiler: Any = None
    ) -> "DeviceState":
        """Build a DeviceState from a Device instance.

        Args:
            device: Device instance
            transpiler: optional TranspilerBase instance. When provided,
                its supported code types take precedence over the
                driver's; falls back to the driver when the
                transpiler returns None or an empty list.

        Returns:
            DeviceState instance with static fields populated.
            Dynamic fields default to zero and must be set later.
        """
        driver = device.get_driver()
        # Prefer transpiler-declared code types; fall back to driver
        supported_code_types = None
        if transpiler is not None:
            supported_code_types = transpiler.get_supported_code_types()
        if supported_code_types is None or len(supported_code_types) == 0:
            supported_code_types = driver.get_supported_code_types()
        return cls(
            device=device,
            name=device.get_name(),
            status=device.get_status(),
            enable=device.get_enable(),
            max_qubits=driver.get_max_qubits(),
            available_num_qubits=getattr(driver, "available_num_qubits", -1),
            tech_type=device.tech_type,
            supported_code_types=supported_code_types or [],
            supported_basis_gates=driver.get_supported_basis_gates(),
            details=device.details or {},
            max_queued_jobs=device.get_max_queued_jobs(),
        )

    def set_load_info(
        self,
        queued_job_count: int,
        running_job_count: int,
    ):
        """Set dynamic load info.

        Args:
            queued_job_count: queued job count
            running_job_count: running job count
        """
        self.queued_job_count = queued_job_count
        self.running_job_count = running_job_count

    def get_avg_1q_fidelity(self) -> float:
        """Get average 1-qubit gate fidelity from device details.

        Returns:
            Average fidelity, 0.0 if not available.
        """
        single_qubit_prop = self.details.get("single_qubit_prop", {})
        if not single_qubit_prop or not isinstance(single_qubit_prop, dict):
            return 0.0
        fidelities = []
        for prop in single_qubit_prop.values():
            if isinstance(prop, dict):
                fidelity = prop.get("single_qubit_gate_fidelity")
                if fidelity is not None:
                    fidelities.append(float(fidelity))
        if not fidelities:
            return 0.0
        return sum(fidelities) / len(fidelities)

    def get_avg_2q_fidelity(self) -> float:
        """Get average 2-qubit gate fidelity from device details.

        Returns:
            Average fidelity, 0.0 if not available.
        """
        double_qubit_prop = self.details.get("double_qubit_prop", {})
        if not double_qubit_prop or not isinstance(double_qubit_prop, dict):
            return 0.0
        fidelities = []
        for prop in double_qubit_prop.values():
            if isinstance(prop, dict):
                fidelity = prop.get("gate_fidelity")
                if fidelity is not None:
                    fidelities.append(float(fidelity))
        if not fidelities:
            return 0.0
        return sum(fidelities) / len(fidelities)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for logging/debugging.

        Returns:
            Dictionary representation.
        """
        return {
            "name": self.name,
            "status": self.status,
            "enable": self.enable,
            "max_qubits": self.max_qubits,
            "tech_type": self.tech_type,
            "supported_code_types": self.supported_code_types,
            "queued_job_count": self.queued_job_count,
            "running_job_count": self.running_job_count,
            "max_queued_jobs": self.max_queued_jobs,
            "avg_exec_time_per_qubit": self.avg_exec_time_per_qubit,
        }
