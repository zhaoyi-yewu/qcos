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
    available_qubits: int = -1
    tech_type: str = ""
    supported_code_types: list[str] = field(default_factory=list)
    supported_basis_gates: list[str] | None = None
    details: dict = field(default_factory=dict)
    # input constrains from driver (e.g. job_shots schema)
    input_constrains: dict = field(default_factory=dict)
    # whether the driver supports circuit aggregation
    enable_circuit_aggregation: bool = False
    # driver_options schema from the driver
    driver_options_schema: dict | None = None
    # transpiler_options schema from the driver
    transpiler_options_schema: dict | None = None

    # Dynamic load info (from Prefect)
    queued_job_count: int = 0
    running_job_count: int = 0
    vendor_queued_job_count: int = 0
    vendor_running_job_count: int = 0
    max_queued_jobs: int = -1

    # Historical statistics (from DB)  # TODO(zhaoyi): NOT IMPLEMENTED YET
    avg_exec_time_per_qubit: float = 0.0
    # overall availability rate (0.0-1.0): historical + current hour
    availability_total: float = 0.0
    # current-hour real-time availability rate (0.0-1.0)
    availability_hourly: float = 0.0

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
            available_qubits=driver.get_available_qubits(),
            tech_type=device.tech_type,
            supported_code_types=supported_code_types or [],
            supported_basis_gates=driver.get_supported_basis_gates(),
            details=device.details or {},
            max_queued_jobs=device.get_max_queued_jobs(),
            input_constrains=getattr(driver, "input_constrains", {}) or {},
            enable_circuit_aggregation=getattr(
                driver, "enable_circuit_aggregation", False
            ),
            driver_options_schema=getattr(
                driver, "driver_options_schema", None
            ),
            transpiler_options_schema=getattr(
                driver, "transpiler_options_schema", None
            ),
        )

    def set_load_info(
        self,
        queued_job_count: int,
        running_job_count: int,
        vendor_queued_job_count: int,
        vendor_running_job_count: int,
    ):
        """Set dynamic load info.

        Args:
            queued_job_count: queued job count
            running_job_count: running job count
            vendor_queued_job_count: queued job count in vendor
            vendor_running_job_count: running job count in vendor
        """
        self.queued_job_count = queued_job_count
        self.running_job_count = running_job_count
        self.vendor_queued_job_count = vendor_queued_job_count
        self.vendor_running_job_count = vendor_running_job_count

    def set_availability(
        self,
        availability_hourly: float | None = None,
        availability_total: float | None = None,
    ):
        """Set device availability rates.

        Each parameter is optional; when None (omitted) the
        corresponding field is left unchanged.

        Args:
            availability_hourly: current-hour real-time availability
                rate (0.0-1.0). None means no change.
            availability_total: overall availability rate (0.0-1.0),
                aggregated from historical and current-hour data.
                None means no change.
        """
        if availability_hourly is not None:
            self.availability_hourly = availability_hourly
        if availability_total is not None:
            self.availability_total = availability_total

    def get_avg_1q_fidelity(self) -> float | None:
        """Get average 1-qubit gate fidelity from device details.

        Extracts ``xeb_fidelity`` from each qubit entry in
        ``details["calibration"]["qubit_metrics"]`` and returns the
        arithmetic mean.

        Returns:
            Average fidelity (0.0-1.0), or None when no data.
        """
        calibration = self.details.get("calibration")
        if not isinstance(calibration, dict):
            return None
        qubit_metrics = calibration.get("qubit_metrics")
        if not isinstance(qubit_metrics, list) or not qubit_metrics:
            return None
        fidelities = []
        for qm in qubit_metrics:
            if isinstance(qm, dict):
                fidelity = qm.get("xeb_fidelity")
                if fidelity is not None:
                    fidelities.append(float(fidelity))
        if not fidelities:
            return None
        return sum(fidelities) / len(fidelities)

    def get_avg_2q_fidelity(self) -> float | None:
        """Get average 2-qubit gate fidelity from device details.

        Extracts ``cz_fidelity`` from each coupler entry in
        ``details["calibration"]["coupler_metrics"]`` and returns the
        arithmetic mean.

        Returns:
            Average fidelity (0.0-1.0), or None when no data.
        """
        calibration = self.details.get("calibration")
        if not isinstance(calibration, dict):
            return None
        coupler_metrics = calibration.get("coupler_metrics")
        if not isinstance(coupler_metrics, list) or not coupler_metrics:
            return None
        fidelities = []
        for cm in coupler_metrics:
            if isinstance(cm, dict):
                fidelity = cm.get("cz_fidelity")
                if fidelity is not None:
                    fidelities.append(float(fidelity))
        if not fidelities:
            return None
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
