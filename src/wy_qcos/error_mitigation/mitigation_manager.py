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

"""Mitigation manager: orchestrates the full error mitigation pipeline."""

from __future__ import annotations

import logging
from typing import Any

from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.error_mitigation.mitigation_base import MitigationBase
from wy_qcos.error_mitigation.mitigation_factory import MitigationFactory
from wy_qcos.error_mitigation.readout_mitigation import ReadoutMitigation
from wy_qcos.error_mitigation.zne_mitigation import ZNEMitigation

logger = logging.getLogger(__name__)


class MitigationManager:
    """Orchestrates the full error mitigation pipeline.

    Manages mitigation technique instances, validates device
    compatibility, transforms circuits, and post-processes results
    in the correct order.

    Pipeline order:
        1. DD (circuit transformation, before execution)
        2. ZNE (circuit variant generation, before execution)
        3. Hardware execution (original + variants + calibration)
        4. REM (result correction)
        5. ZNE (extrapolation)
        6. Clifford (observable correction)
    """

    def __init__(self):
        self._factory = MitigationFactory()
        self._techniques: dict[str, MitigationBase] = {}
        self._calibration_data: dict[str, Any] = {}

    def configure(self, error_mitigation_config: dict[str, Any]) -> None:
        """Configure mitigation techniques from user request.

        Args:
            error_mitigation_config: The "error_mitigation" field from
                the job submission request.
        """
        self._techniques.clear()

        for name, config in error_mitigation_config.items():
            if not isinstance(config, dict):
                continue
            if not config.get("enabled", False):
                continue
            try:
                technique = self._factory.create(
                    name, **{k: v for k, v in config.items() if k != "enabled"}
                )
                technique.set_config(config)
                self._techniques[name] = technique
                logger.info("Enabled mitigation: %s", name)
            except (ValueError, TypeError) as exc:
                logger.warning(
                    "Failed to create mitigation '%s': %s", name, exc
                )

    def validate_device(self, device_config: dict[str, Any]) -> tuple:
        """Validate all enabled techniques against device capabilities.

        Args:
            device_config: Device configuration dictionary.

        Returns:
            (is_valid, error_messages) tuple.
        """
        errors = []
        for name, technique in self._techniques.items():
            valid, msg = technique.validate_device(device_config)
            if not valid:
                errors.append(f"{name}: {msg}")

        if errors:
            return (False, "; ".join(errors))
        return (True, None)

    def has_enabled(self) -> bool:
        """Whether any mitigation technique is enabled."""
        return len(self._techniques) > 0

    def get_technique(self, name: str) -> MitigationBase | None:
        """Get a specific technique by name."""
        return self._techniques.get(name)

    def get_enabled_names(self) -> list[str]:
        """Get names of all enabled techniques."""
        return list(self._techniques.keys())

    def needs_calibration(self) -> list[str]:
        """Get names of techniques that need calibration."""
        return [
            name
            for name, tech in self._techniques.items()
            if tech.needs_calibration()
        ]

    def get_calibration_circuits(
        self,
        circuit: QuantumCircuit,
        target_qubits: list[int] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Generate calibration circuits for all techniques that need them.

        Args:
            circuit: The quantum circuit.
            target_qubits: Qubit indices for calibration.

        Returns:
            Dict mapping technique name to list of calibration circuits.
        """
        all_circuits: dict[str, list[dict[str, Any]]] = {}

        rem = self._techniques.get("readout") or self._techniques.get("rem")
        if rem and isinstance(rem, ReadoutMitigation):
            qubits = target_qubits or list(range(circuit.num_qubits))
            all_circuits["readout"] = rem.build_calibration_circuits(qubits)

        return all_circuits

    def store_calibration_data(
        self, technique_name: str, data: dict[str, Any]
    ) -> None:
        """Store calibration results for a technique.

        Args:
            technique_name: Technique identifier.
            data: Calibration data.
        """
        self._calibration_data[technique_name] = data

    def transform_circuit(
        self, circuit: QuantumCircuit
    ) -> list[dict[str, Any]]:
        """Apply circuit-level transformations (DD, ZNE).

        Execution order: DD first, then ZNE on the DD-modified circuit.

        Args:
            circuit: The transpiled quantum circuit.

        Returns:
            List of circuit variants to execute.
        """
        current_variants: list[dict[str, Any]] = [
            {"label": "original", "circuit": circuit, "scale_factor": 1}
        ]

        zne = self._techniques.get("zne")
        if zne and isinstance(zne, ZNEMitigation) and zne.enabled:
            expanded: list[dict[str, Any]] = []
            for variant in current_variants:
                zne_variants = zne.transform_circuit(variant["circuit"])
                for zv in zne_variants:
                    sf = zv.get("scale_factor", 1)
                    zv["label"] = "original" if sf == 1 else "scaled"
                    expanded.append(zv)
            current_variants = expanded

        return current_variants

    def postprocess_results(
        self,
        variant_results: dict[str, dict[str, int]],
        num_qubits: int,
        target_qubits: list[int] | None = None,
    ) -> dict[str, Any]:
        """Apply result-level post-processing in cascade order.

        Order: REM -> ZNE -> Clifford.

        Args:
            variant_results: {label: counts} from hardware execution.
            num_qubits: Number of qubits.
            target_qubits: Physical qubit indices.

        Returns:
            Final mitigated results with full metadata.
        """
        current_results = dict(variant_results)
        pipeline_metadata: dict[str, Any] = {
            "techniques_applied": [],
            "raw_results": dict(variant_results),
            "pipeline_steps": [],
        }

        rem = self._techniques.get("readout") or self._techniques.get("rem")
        if rem and isinstance(rem, ReadoutMitigation) and rem.enabled:
            calib = self._calibration_data.get("readout")
            rem_output = rem.postprocess(
                current_results,
                calibration=calib,
                num_qubits=num_qubits,
                target_qubits=target_qubits,
            )
            current_results = rem_output.get("results", current_results)
            pipeline_metadata["techniques_applied"].append("readout")
            pipeline_metadata["pipeline_steps"].append({
                "technique": "readout",
                "metadata": rem_output.get("metadata"),
            })

        zne = self._techniques.get("zne")
        if zne and isinstance(zne, ZNEMitigation) and zne.enabled:
            zne_output = zne.postprocess(
                current_results, num_qubits=num_qubits
            )
            extrapolated = zne_output.get("results", {}).get("extrapolated")
            if extrapolated is not None:
                current_results = {"extrapolated": extrapolated}
            pipeline_metadata["techniques_applied"].append("zne")
            pipeline_metadata["pipeline_steps"].append({
                "technique": "zne",
                "metadata": zne_output.get("metadata"),
            })

        return {
            "results": current_results,
            "mitigation_metadata": pipeline_metadata,
        }
