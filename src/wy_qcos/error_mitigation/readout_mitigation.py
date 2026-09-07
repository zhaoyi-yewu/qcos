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

"""Readout error mitigation (REM).

Calibrates per-qubit 2x2 confusion matrices by preparing |0> and |1>
states and measuring, then applies pseudo-inverse correction to
measurement probabilities.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.gate_operation import GateOperation
from wy_qcos.common.cmss.base_operation import OperationType
from wy_qcos.common.cmss.measure import Measure
from wy_qcos.error_mitigation.mitigation_base import MitigationBase
from wy_qcos.error_mitigation.utils import (
    counts_to_probabilities,
    counts_to_samples,
    clip_and_normalize,
    expectation_from_probabilities,
    marginal_samples,
    samples_to_probabilities,
)

logger = logging.getLogger(__name__)

MAX_GLOBAL_MATRIX_QUBITS = 15


def build_local_confusion_matrix(
    per_qubit_confusion: Dict[int, np.ndarray],
    target_qubits: Sequence[int],
) -> np.ndarray:
    """Build Kronecker product of per-qubit confusion matrices.

    Args:
        per_qubit_confusion: Mapping from qubit index to its 2x2 confusion matrix.
        target_qubits: Qubit indices to tensor together.

    Returns:
        Kronecker product confusion matrix of shape (2^k, 2^k).

    Raises:
        ValueError: If target_qubits is empty.
    """
    if not target_qubits:
        raise ValueError("target_qubits is empty")
    mats = [per_qubit_confusion[q] for q in target_qubits]
    out = mats[0]
    for m in mats[1:]:
        out = np.kron(out, m)
    return out


def mitigate_readout(
    probabilities: np.ndarray, confusion_matrix: np.ndarray
) -> np.ndarray:
    """Apply pseudo-inverse readout mitigation.

    Args:
        probabilities: Raw probability vector.
        confusion_matrix: Readout confusion matrix.

    Returns:
        Mitigated probability vector (clipped and renormalized).

    Raises:
        ValueError: If confusion_matrix is not square.
    """
    if confusion_matrix.shape[0] != confusion_matrix.shape[1]:
        raise ValueError("confusion_matrix must be square")
    pinv = np.linalg.pinv(confusion_matrix)
    mitigated = pinv @ probabilities
    return clip_and_normalize(mitigated)


def build_confusion_matrix_from_counts(
    counts_list: List[Dict[str, int]], num_qubits: int
) -> np.ndarray:
    """Build confusion matrix from calibration measurement counts.

    Each entry in counts_list corresponds to one prepared basis state.
    Column i of the matrix = probability distribution when state i was prepared.

    Args:
        counts_list: List of measurement count dicts, one per prepared state.
        num_qubits: Number of qubits (1 for per-qubit calibration).

    Returns:
        Confusion matrix of shape (2**num_qubits, 2**num_qubits).
    """
    dim = 2**num_qubits
    mat = np.zeros((dim, dim), dtype=float)
    for i, counts in enumerate(counts_list):
        if i < dim:
            probs = counts_to_probabilities(counts, num_qubits)
            mat[:, i] = probs
    return mat


def expectation_from_samples_unbiased(
    local_samples: np.ndarray,
    local_confusion_matrices: Sequence[np.ndarray],
) -> float:
    """Unbiased readout-mitigated parity estimator from samples.

    Avoids building the full 2^k marginal when support size k is large.

    Args:
        local_samples: 2-D array of shape (nshots, k) with 0/1 outcomes.
        local_confusion_matrices: Sequence of k 2x2 confusion matrices.

    Returns:
        Unbiased readout-mitigated parity expectation value.

    Raises:
        ValueError: If inputs are invalid.
    """
    if local_samples.ndim != 2:
        raise ValueError("local_samples must be 2D (nshots, k)")
    k = local_samples.shape[1]
    if k == 0:
        return 1.0
    if len(local_confusion_matrices) != k:
        raise ValueError(
            "local_confusion_matrices length must equal number of columns"
        )
    if local_samples.shape[0] == 0:
        return 0.0

    scores = np.ones(local_samples.shape[0], dtype=float)
    norms = np.ones(local_samples.shape[0], dtype=float)
    for i, cm in enumerate(local_confusion_matrices):
        cm_arr = np.asarray(cm, dtype=float)
        if cm_arr.shape != (2, 2):
            raise ValueError("each confusion matrix must be (2, 2)")
        inv = np.linalg.pinv(cm_arr)
        bits = local_samples[:, i]
        w = inv[0] - inv[1]
        n = inv[0] + inv[1]
        scores *= np.where(bits == 0, w[0], w[1])
        norms *= np.where(bits == 0, n[0], n[1])

    mask = norms != 0
    if not np.any(mask):
        return 0.0
    return float((scores[mask] / norms[mask]).mean())


def mitigate_observable_from_samples(
    samples: np.ndarray,
    support: Sequence[int],
    per_qubit: Dict[int, np.ndarray],
    target_qubits_group: Sequence[int],
    marginal_max_support: int = 10,
) -> float:
    """Compute readout-mitigated observable from samples with adaptive strategy.

    Uses exact marginal mitigation for small support (<=threshold),
    and the unbiased estimator for large support.

    Args:
        samples: Measurement samples (nshots, num_qubits).
        support: Logical qubit indices of non-identity Pauli terms.
        per_qubit: Per-qubit 2x2 confusion matrices.
        target_qubits_group: Physical qubit indices for the measurement group.
        marginal_max_support: Max support for exact marginal method.

    Returns:
        Readout-mitigated expectation value.
    """
    if not support:
        return 1.0
    support_phys = [target_qubits_group[i] for i in support]
    if len(support) <= marginal_max_support:
        local_cm = build_local_confusion_matrix(per_qubit, support_phys)
        local_samp = marginal_samples(samples, list(support))
        local_probs = samples_to_probabilities(local_samp, len(support))
        local_probs_rem = mitigate_readout(local_probs, local_cm)
        return expectation_from_probabilities(local_probs_rem, support)
    local_samples = marginal_samples(samples, list(support))
    local_cm_list = [per_qubit[q] for q in support_phys]
    return expectation_from_samples_unbiased(local_samples, local_cm_list)


class ReadoutMitigation(MitigationBase):
    """Readout error mitigation technique.

    Corrects measurement errors by calibrating per-qubit confusion matrices
    and applying pseudo-inverse correction to measurement probabilities.
    """

    def __init__(
        self,
        calibration_shots: int = 8192,
        cache_ttl: int = 43200,
    ):
        """Initialize readout mitigation.

        Args:
            calibration_shots: Number of shots for calibration circuits.
            cache_ttl: Calibration cache time-to-live in seconds.
        """
        super().__init__("readout")
        self._calibration_shots = calibration_shots
        self._cache_ttl = cache_ttl
        self._calibration_data: Optional[Dict[str, Any]] = None

    def set_config(self, config: Dict[str, Any]) -> None:
        super().set_config(config)
        self._calibration_shots = config.get(
            "calibration_shots", self._calibration_shots
        )
        self._cache_ttl = config.get("cache_ttl", self._cache_ttl)

    def needs_calibration(self) -> bool:
        return True

    def validate_device(self, device_config: Dict[str, Any]) -> tuple:
        return (True, None)

    def build_calibration_circuits(
        self, target_qubits: List[int]
    ) -> List[Dict[str, Any]]:
        """Build per-qubit calibration circuits.

        For each qubit, generates two circuits:
        - Prepare |0> (no gate) and measure
        - Prepare |1> (X gate) and measure

        Args:
            target_qubits: Qubit indices to calibrate.

        Returns:
            List of calibration circuit descriptors.
        """
        circuits = []
        for q in target_qubits:
            num_qubits = q + 1
            for prepared_state in ("0", "1"):
                qc = QuantumCircuit(num_qubits, 1)
                if prepared_state == "1":
                    qc.append(
                        GateOperation(
                            "x",
                            targets=[q],
                            operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
                        )
                    )
                qc.append(Measure(targets=[q]))
                circuits.append({
                    "qubit": q,
                    "prepared_state": prepared_state,
                    "circuit": qc,
                    "shots": self._calibration_shots,
                })
        return circuits

    def process_calibration_results(
        self,
        calibration_results: Dict[int, Dict[str, Dict[str, int]]],
        target_qubits: List[int],
    ) -> Dict[str, Any]:
        """Process calibration measurement results into confusion matrices.

        Args:
            calibration_results: {qubit: {"0": counts_0, "1": counts_1}}
            target_qubits: Qubit indices that were calibrated.

        Returns:
            Calibration data with per-qubit confusion matrices.
        """
        per_qubit_confusion: Dict[int, np.ndarray] = {}
        for q in target_qubits:
            if q in calibration_results:
                counts_0 = calibration_results[q].get("0", {})
                counts_1 = calibration_results[q].get("1", {})
                per_qubit_confusion[q] = build_confusion_matrix_from_counts(
                    [counts_0, counts_1], num_qubits=1
                )
        self._calibration_data = {
            "per_qubit_confusion": per_qubit_confusion,
            "target_qubits": target_qubits,
        }
        return self._calibration_data

    def postprocess(
        self,
        results: Dict[str, Dict[str, int]],
        calibration: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Apply readout mitigation to measurement results.

        Args:
            results: Dict mapping variant label to counts.
            calibration: Calibration data with per_qubit_confusion.
            **kwargs: Must include "num_qubits" and optionally "target_qubits".

        Returns:
            Mitigated results with metadata.
        """
        calib = calibration or self._calibration_data
        if calib is None:
            logger.warning("No calibration data available, skipping REM")
            return {
                "results": results,
                "metadata": {"technique": "readout", "applied": False},
            }

        per_qubit_cm = calib.get("per_qubit_confusion", {})
        if not per_qubit_cm:
            return {
                "results": results,
                "metadata": {"technique": "readout", "applied": False},
            }

        num_qubits = kwargs.get("num_qubits")
        target_qubits = kwargs.get("target_qubits", calib.get("target_qubits"))

        mitigated_results = {}
        metadata_list = []

        for label, counts in results.items():
            if num_qubits is None:
                sample_key = next(iter(counts))
                num_qubits = len(sample_key)

            if target_qubits is None:
                target_qubits = list(range(num_qubits))

            if num_qubits <= MAX_GLOBAL_MATRIX_QUBITS:
                probs = counts_to_probabilities(counts, num_qubits)
                active_qubits = [q for q in target_qubits if q in per_qubit_cm]
                if not active_qubits:
                    mitigated_results[label] = counts
                    metadata_list.append({"label": label, "applied": False})
                    continue
                local_cm = build_local_confusion_matrix(
                    per_qubit_cm, active_qubits
                )
                cond = np.linalg.cond(local_cm)
                if cond > 1e6:
                    logger.warning(
                        "Confusion matrix condition number %.2e is too high "
                        "for qubits %s, skipping REM",
                        cond,
                        active_qubits,
                    )
                    mitigated_results[label] = counts
                    metadata_list.append({
                        "label": label,
                        "applied": False,
                        "warning": "singular_confusion_matrix",
                    })
                    continue

                mitigated_probs = mitigate_readout(probs, local_cm)
                total_counts = sum(counts.values())
                mitigated_counts = {}
                for idx, p in enumerate(mitigated_probs):
                    bitstring = format(idx, f"0{num_qubits}b")
                    c = round(p * total_counts)
                    if c > 0:
                        mitigated_counts[bitstring] = c

                max_correction = float(np.max(np.abs(mitigated_probs - probs)))
                mitigated_results[label] = mitigated_counts
                metadata_list.append({
                    "label": label,
                    "applied": True,
                    "max_correction": max_correction,
                    "condition_number": float(cond),
                })
            else:
                mitigated_results[label] = counts
                metadata_list.append({
                    "label": label,
                    "applied": False,
                    "reason": "too_many_qubits_for_global_matrix",
                })

        return {
            "results": mitigated_results,
            "metadata": {
                "technique": "readout",
                "variants": metadata_list,
                "calibration_qubits": list(per_qubit_cm.keys()),
            },
        }
