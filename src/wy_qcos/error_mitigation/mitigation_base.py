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

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit


class MitigationBase(ABC):
    """Abstract base class for error mitigation techniques.

    Provides the interface for calibration, circuit transformation,
    and result post-processing used by all mitigation strategies.
    """

    def __init__(self, name: str):
        self._name = name
        self._enabled = False
        self._config: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_config(self, config: Dict[str, Any]) -> None:
        """Set configuration for this mitigation technique.

        Args:
            config: Configuration dictionary.
        """
        self._config = config
        self._enabled = config.get("enabled", False)

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()

    def needs_calibration(self) -> bool:
        """Whether this technique requires calibration data before execution.

        Returns:
            True if calibration is needed, False otherwise.
        """
        return False

    def calibrate(
        self,
        circuit: QuantumCircuit,
        device_id: str,
        target_qubits: Optional[List[int]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run calibration procedure.

        Default implementation returns empty dict (no calibration needed).

        Args:
            circuit: The quantum circuit to calibrate for.
            device_id: Target device identifier.
            target_qubits: Qubit indices to calibrate.
            **kwargs: Additional keyword arguments.

        Returns:
            Calibration data dictionary.
        """
        return {}

    def transform_circuit(
        self, circuit: QuantumCircuit
    ) -> List[Dict[str, Any]]:
        """Transform the circuit for this mitigation technique.

        Default implementation returns the original circuit unchanged.

        Args:
            circuit: The quantum circuit to transform.

        Returns:
            List of circuit variants to execute. Each variant is a dict with:
                - "label": str, variant identifier
                - "circuit": QuantumCircuit, the variant circuit
                - "scale_factor": int or float, noise scale (1.0 = original)
        """
        return [{"label": "original", "circuit": circuit, "scale_factor": 1}]

    @abstractmethod
    def postprocess(
        self,
        results: Dict[str, Dict[str, int]],
        calibration: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Post-process raw measurement results.

        Args:
            results: Dict mapping variant label to counts dict.
                     e.g. {"original": {"00": 500, "11": 500}}
            calibration: Optional calibration data.
            **kwargs: Additional keyword arguments.

        Returns:
            Dict with mitigated results and metadata:
                - "probabilities": corrected probability array or counts dict
                - "metadata": correction metadata
        """
        raise NotImplementedError(
            "postprocess() must be implemented by subclass"
        )

    def validate_device(self, device_config: Dict[str, Any]) -> tuple:
        """Validate that the device supports this technique.

        Args:
            device_config: Device configuration dictionary.

        Returns:
            Tuple of (is_valid: bool, error_message: str or None).
        """
        return (True, None)
