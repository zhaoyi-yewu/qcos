#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You may use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Zero-noise extrapolation (ZNE).

Scales circuit noise by *folding* CZ gates, executes the original circuit
plus one or more noise-scaled variants, and extrapolates the measurement
probabilities back to the zero-noise limit.

Noise scaling
-------------
``apply_zne_cz_folding`` supports arbitrary real scale factors in
``[1, 3]`` (and odd-integer factors beyond) by *partially* folding a
fraction of the CZ gates: a folded CZ is replaced by three consecutive
CZ gates (``CZ * CZ * CZ == CZ`` unitarily) which amplifies the physical
gate noise.  Folding ``k`` of ``n`` CZ gates yields scale ``1 + 2*k/n``.
Keeping the maximum scale small (``<= 3``) keeps the circuit in the
perturbative noise regime where extrapolation is valid; large scales
(e.g. 5) saturate the signal on real hardware and make extrapolation
unreliable.

Extrapolation
-------------
Several methods are supported:

    - "polynomial": least-squares polynomial fit (default, degree 1).
      A degree-1 fit through several points is robust to shot noise and
      matches the near-linear noise response in the small-scale regime.
    - "richardson": exact Richardson cancellation (n points cancel noise
      terms up to order n-1).  Sensitive to shot noise.
    - "linear": two-point linear extrapolation.
    - "exponential": fit ``a + b*exp(c*lambda)`` and evaluate at 0
      (matches depolarising noise).

Adaptive point pruning
----------------------
Before extrapolation ``postprocess`` discards scale points whose
measurement is *saturated* (near the maximally-mixed distribution, i.e.
the signal has collapsed) or *non-monotonic* (noise did not increase with
scale).  When fewer than two trustworthy points remain it returns the
un-extrapolated scale-1 result, so ZNE degrades gracefully and never
amplifies noise on circuits it cannot help.
"""

from __future__ import annotations

import copy
import logging
import random
import re
from typing import Any
from collections.abc import Sequence

import numpy as np

from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.base_operation import BaseOperation
from wy_qcos.error_mitigation.mitigation_base import MitigationBase
from wy_qcos.error_mitigation.utils import (
    counts_to_probabilities,
    clip_and_normalize,
    expectation_from_probabilities,
)

logger = logging.getLogger(__name__)

# Matches variant labels of the form "zne_s<scale>", e.g. zne_s1, zne_s1.5.
_SCALE_LABEL_RE = re.compile(r"^zne_s(\d+(?:\.\d+)?)$")

# Supported extrapolation method names.
_EXTRAPOLATION_METHODS = (
    "richardson",
    "linear",
    "polynomial",
    "exponential",
)


def apply_zne_cz_scaling(
    circuit: QuantumCircuit, scale: int
) -> QuantumCircuit:
    """Fold CZ gates to scale circuit noise by an odd factor.

    Each CZ gate is replaced by ``scale`` consecutive CZ gates.  Because
    ``CZ * CZ = I``, an odd number of CZ gates is logically equivalent to
    a single CZ while amplifying the gate noise by ``scale``.

    Args:
        circuit: The quantum circuit to transform.
        scale: Positive odd integer noise scale factor (1, 3, 5, ...).

    Returns:
        New circuit with each CZ gate folded ``scale`` times.

    Raises:
        ValueError: If ``scale`` is not a positive odd integer.
    """
    if scale < 1 or scale % 2 == 0:
        raise ValueError(
            f"ZNE scale factor must be a positive odd integer, got {scale}"
        )
    if scale == 1:
        return circuit
    new_ops: list[BaseOperation] = []
    for op in circuit.get_operations():
        new_ops.append(op)
        if op.name == "cz":
            for _ in range(scale - 1):
                new_ops.append(copy.deepcopy(op))
    return QuantumCircuit.from_ir(new_ops, circuit.num_qubits)


def apply_zne_cz_folding(
    circuit: QuantumCircuit, scale: float
) -> QuantumCircuit:
    """Fold CZ gates to scale circuit noise by an arbitrary factor.

    Generalises :func:`apply_zne_cz_scaling` to real scale factors in
    ``[1, 3]`` by *partially* folding a fraction of the CZ gates: each
    folded CZ is replaced by three consecutive CZ gates (``CZ * CZ * CZ``
    is unitarily a single CZ), adding two extra noisy CZ gates.  Folding
    ``k`` of ``n`` CZ gates yields an effective scale of ``1 + 2*k/n``.

    For an odd-integer ``scale`` (1, 3, 5, ...) this delegates to
    :func:`apply_zne_cz_scaling` (every gate folded ``scale`` times), so
    legacy configurations keep their exact behaviour.

    Args:
        circuit: The quantum circuit to transform.
        scale: Noise scale factor ``>= 1``.  Values in ``[1, 3]`` use
            partial folding; odd integers ``> 3`` use full per-gate
            folding.

    Returns:
        New circuit with CZ gates folded to approximate ``scale``.

    Raises:
        ValueError: If ``scale`` is less than 1.
    """
    scale = float(scale)
    if scale < 1.0:
        raise ValueError(f"ZNE scale factor must be >= 1, got {scale}")
    if abs(scale - 1.0) < 1e-12:
        return circuit
    ops = list(circuit.get_operations())
    cz_pos = [i for i, op in enumerate(ops) if op.name == "cz"]
    n = len(cz_pos)
    if n == 0:
        return circuit
    # Odd-integer scales use full per-gate folding (exact, legacy path).
    if scale == int(scale) and int(scale) % 2 == 1:
        return apply_zne_cz_scaling(circuit, int(scale))
    # Partial folding: fold k of n CZ gates into triples (+2 each),
    # capped at full tripling (scale ~3).  Achieved scale = 1 + 2*k/n.
    target_extra = int(round((scale - 1.0) * n))
    target_extra = max(0, min(target_extra, 2 * n))
    num_fold = target_extra // 2
    fold_set = set(cz_pos[:num_fold])
    new_ops: list[BaseOperation] = []
    for i, op in enumerate(ops):
        new_ops.append(op)
        if i in fold_set:
            new_ops.append(copy.deepcopy(op))
            new_ops.append(copy.deepcopy(op))
    return QuantumCircuit.from_ir(new_ops, circuit.num_qubits)


def apply_zne_cz_tripling(circuit: QuantumCircuit) -> QuantumCircuit:
    """Apply CZ gate tripling for ZNE noise scaling (scale factor 3).

    Backwards-compatible alias for :func:`apply_zne_cz_scaling`.

    Args:
        circuit: The quantum circuit to transform.

    Returns:
        New circuit with each CZ gate tripled.
    """
    return apply_zne_cz_scaling(circuit, 3)


def count_cz_gates(circuit: QuantumCircuit) -> int:
    """Count the number of CZ gates in a circuit.

    Args:
        circuit: The quantum circuit.

    Returns:
        Number of CZ gates.
    """
    return sum(1 for op in circuit.get_operations() if op.name == "cz")


# Gate names that are self-inverse (G^dag = G) and thus safe to fold by
# repetition (G G G is logically G).  ZNE folding replaces a gate with
# ``G G^dag G``; for self-inverse gates this is three identical copies.
_SELF_INVERSE_GATES = frozenset({
    "cz",
    "cx",
    "x",
    "y",
    "z",
    "h",
    "s",
    "t",
    "sdg",
    "tdg",
})


def _is_foldable(op: BaseOperation) -> bool:
    """Whether ``op`` can be noise-scaled by gate folding."""
    return op.name in _SELF_INVERSE_GATES


def fold_gates(
    circuit: QuantumCircuit,
    scale: float,
    *,
    strategy: str = "left",
    gate_names: Sequence[str] | None = None,
    seed: int | None = None,
) -> QuantumCircuit:
    """Fold gates to scale circuit noise by an arbitrary factor.

    Generalised gate folding following mitiq's ``fold_gates_at_random``
    family.  Each folded gate ``G`` is replaced by ``G G G`` (for
    self-inverse gates this is ``G * G^dag * G``), so folding one gate
    once adds two noisy copies and raises the scale by ``2 / n`` where
    ``n`` is the number of foldable gates.

    The ``strategy`` controls *which* gates receive the extra partial fold
    needed to reach a non-odd-integer scale:

    - ``"left"``:  the first gates (deterministic, legacy behaviour).
    - ``"right"``: the last gates.
    - ``"random"``: a random subset (mitiq default) -- avoids systematic
      bias toward the circuit's leading gates.

    Args:
        circuit: The quantum circuit to transform.
        scale: Noise scale factor ``>= 1``.
        strategy: ``"left"``, ``"right"`` or ``"random"``.
        gate_names: Restrict folding to these gate names.  Defaults to
            all self-inverse two-qubit gates (CZ/CX), matching the
            legacy CZ-only intent while allowing CX devices.
        seed: RNG seed for the ``"random"`` strategy.

    Returns:
        New circuit with gates folded to approximate ``scale``.

    Raises:
        ValueError: If ``scale < 1`` or ``strategy`` is unknown.
    """
    scale = float(scale)
    if scale < 1.0:
        raise ValueError(f"ZNE scale factor must be >= 1, got {scale}")
    if abs(scale - 1.0) < 1e-12:
        return circuit
    if strategy not in ("left", "right", "random"):
        raise ValueError(
            f"Unknown folding strategy '{strategy}', expected "
            "left/right/random"
        )

    ops = list(circuit.get_operations())
    if gate_names is not None:
        foldable_idx = [
            i for i, op in enumerate(ops) if op.name in set(gate_names)
        ]
    else:
        foldable_idx = [i for i, op in enumerate(ops) if _is_foldable(op)]
    n = len(foldable_idx)
    if n == 0:
        return circuit

    # Each gate folded k times -> scale 1 + 2k/n.  Start every gate at
    # num_uniform = floor((scale-1)/2) folds (nearest odd-integer scale),
    # then add one extra fold to a subset to hit the fractional part --
    # mitiq's _create_fold_mask greedy approach.
    num_uniform = int((scale - 1.0) // 2.0)
    num_extra = int(round((scale - 1.0 - 2.0 * num_uniform) * n / 2.0))
    num_extra = max(0, min(num_extra, n))

    if strategy == "right":
        extra_idx = set(foldable_idx[n - num_extra :])
    elif strategy == "random":
        rng = random.Random(seed)
        shuffled = foldable_idx[:]
        rng.shuffle(shuffled)
        extra_idx = set(shuffled[:num_extra])
    else:  # left
        extra_idx = set(foldable_idx[:num_extra])

    new_ops: list[BaseOperation] = []
    for i, op in enumerate(ops):
        new_ops.append(op)
        if i in foldable_idx:
            folds = num_uniform + (1 if i in extra_idx else 0)
            for _ in range(folds):
                # G G^dag G == G G G for self-inverse gates.
                new_ops.append(copy.deepcopy(op))
                new_ops.append(copy.deepcopy(op))
    return QuantumCircuit.from_ir(new_ops, circuit.num_qubits)


def zne_linear_extrapolate(
    probs_1: np.ndarray, probs_3: np.ndarray
) -> np.ndarray:
    """Richardson linear extrapolation from noise scale 1 and 3 to zero.

    Formula: ``(3 * probs_1 - probs_3) / 2``

    Kept for backwards compatibility.  New code should use
    :func:`extrapolate_to_zero`, which generalises to any number of scale
    factors and any supported method.

    Args:
        probs_1: Probabilities or expectation at noise scale 1.
        probs_3: Probabilities or expectation at noise scale 3.

    Returns:
        Linearly extrapolated zero-noise probabilities.
    """
    return (3.0 * probs_1 - probs_3) / 2.0


def _entropy(probs: np.ndarray) -> float:
    """Shannon entropy (base-2) of a probability vector."""
    p = np.asarray(probs, dtype=float)
    p = p[p > 1e-12]
    if p.size == 0:
        return 0.0
    return float(-np.sum(p * np.log2(p)))  # type: ignore[operator]


def _prune_scale_points(
    points: list[tuple[float, np.ndarray]],
    num_qubits: int,
) -> list[tuple[float, np.ndarray]]:
    """Drop saturated / non-monotonic trailing scale points.

    ZNE is valid only while the measurement grows noisier (more uniform)
    with scale.  Once the largest scale collapses to near the
    maximally-mixed distribution the signal is lost and that point carries
    no extrapolation information; including it would curve-fit pure noise.
    Points are dropped from the high end until the surviving set is
    monotonic in entropy and the top point still carries signal.

    Args:
        points: ``(scale, probs)`` sorted ascending by scale.
        num_qubits: Number of measured qubits (sets the uniform peak).

    Returns:
        Pruned list (a copy); never longer than ``points``.
    """
    if len(points) <= 2:
        return list(points)
    dim = 1 << num_qubits
    uniform_peak = 1.0 / dim
    pruned = list(points)
    while len(pruned) >= 2:
        _hi_scale, hi_p = pruned[-1]
        hi_peak = float(np.max(hi_p))
        hi_ent = _entropy(hi_p)
        # Saturation: top point ~ maximally mixed -> no signal left.
        if hi_peak < 1.5 * uniform_peak:
            logger.info(
                "ZNE pruning scale=%.4g: near-uniform (peak=%.4f), dropping",
                pruned[-1][0],
                hi_peak,
            )
            pruned.pop()
            continue
        # Monotonicity: noise must grow (entropy must not decrease) with
        # scale.  A tolerance avoids shot-noise false positives.
        sec_ent = _entropy(pruned[-2][1])
        if hi_ent < sec_ent - 0.25:
            logger.info(
                "ZNE pruning scale=%.4g: non-monotonic entropy "
                "(%.4f < %.4f), dropping",
                pruned[-1][0],
                hi_ent,
                sec_ent,
            )
            pruned.pop()
            continue
        break
    return pruned


def richardson_coefficients(
    scale_factors: Sequence[float],
) -> np.ndarray:
    """Richardson extrapolation coefficients for the given scale factors.

    Finds coefficients ``c_i`` such that ``sum(c_i) = 1`` and
    ``sum(c_i * lambda_i**k) = 0`` for ``k = 1 .. n-1``.  Applying them
    to the noisy estimates cancels noise terms up to order ``n-1`` and
    yields the zero-noise estimate.

    For two points this reduces to the linear formula
    ``(lambda2*y1 - lambda1*y2) / (lambda2 - lambda1)``.

    Args:
        scale_factors: Noise scale factors ``lambda_i``.

    Returns:
        Coefficient vector of length ``n``.
    """
    scales = np.asarray(scale_factors, dtype=float)
    n = scales.size
    if n == 1:
        return np.ones(1)
    # Solve V^T c = e0, where V is the Vandermonde matrix (increasing
    # powers) and e0 = [1, 0, ..., 0]: the constant moment is 1 and every
    # higher moment is cancelled.
    matrix = np.vander(scales, N=n, increasing=True).T
    rhs = np.zeros(n)
    rhs[0] = 1.0
    return np.linalg.solve(matrix, rhs)


def extrapolate_to_zero(
    scale_factors: Sequence[float],
    probs_matrix: np.ndarray,
    method: str = "richardson",
    polynomial_degree: int | None = None,
) -> np.ndarray:
    """Extrapolate per-element probabilities to the zero-noise limit.

    Args:
        scale_factors: Noise scale factors, length ``n``.
        probs_matrix: Array of shape ``(n, dim)``; row ``i`` is the
            probability vector measured at ``scale_factors[i]``.
        method: One of ``richardson``, ``linear``, ``polynomial``,
            ``exponential``.
        polynomial_degree: Polynomial degree for the ``polynomial``
            method.  Defaults to ``n - 1`` (interpolating); a lower degree
            gives a least-squares fit that suppresses shot noise.

    Returns:
        Extrapolated probability vector of length ``dim``.  Not clipped
        or renormalised.

    Raises:
        ValueError: If ``method`` is unknown.
    """
    scales = np.asarray(scale_factors, dtype=float)
    probs_matrix = np.asarray(probs_matrix, dtype=float)
    if probs_matrix.ndim == 1:
        probs_matrix = probs_matrix.reshape(1, -1)
    n = scales.size
    if probs_matrix.shape[0] != n:
        raise ValueError(
            "scale_factors (" + str(n) + ") and probs_matrix rows "
            "(" + str(probs_matrix.shape[0]) + ") disagree"
        )

    if method == "richardson":
        coeffs = richardson_coefficients(scales)
        return coeffs @ probs_matrix

    if method == "linear":
        if n < 2:
            return probs_matrix[0].copy()
        l1, l2 = scales[0], scales[1]
        y1, y2 = probs_matrix[0], probs_matrix[1]
        return (l2 * y1 - l1 * y2) / (l2 - l1)

    if method == "polynomial":
        degree = polynomial_degree if polynomial_degree is not None else n - 1
        degree = max(0, min(int(degree), n - 1))
        # np.polyfit returns coefficients highest-power first; the value
        # at lambda=0 is the constant term (last row).
        coeffs = np.polyfit(scales, probs_matrix, degree)
        return coeffs[-1]

    if method == "exponential":
        return _exponential_extrapolate(scales, probs_matrix)

    raise ValueError(
        "Unknown ZNE extrapolation method '"
        + method
        + "'. Expected one of: "
        + str(_EXTRAPOLATION_METHODS)
    )


def _exponential_extrapolate(
    scales: np.ndarray, probs_matrix: np.ndarray
) -> np.ndarray:
    """Fit ``a + b*exp(c*lambda)`` per element and evaluate at ``lambda=0``.

    The decay rate ``c`` is constrained to be non-positive so the model
    describes a signal relaxing toward an asymptote as noise grows, which
    also keeps ``exp`` from overflowing.  Elements whose nonlinear fit
    does not converge fall back to a degree-1 polynomial fit.
    """
    import warnings

    from scipy.optimize import curve_fit

    dim = probs_matrix.shape[1]
    result = np.zeros(dim)

    def model(lam, a, b, c):
        return a + b * np.exp(c * lam)

    # c <= 0 prevents overflow and matches decaying-noise physics; a is a
    # probability asymptote and b the zero-noise offset.
    lower = np.array([-0.5, -1.5, -10.0])
    upper = np.array([1.5, 1.5, 0.0])

    for j in range(dim):
        y = probs_matrix[:, j]
        a0 = float(np.clip(y[-1], -0.4, 1.4))
        b0 = float(np.clip(y[0] - a0, -1.4, 1.4))
        c0 = -0.3
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                popt, _ = curve_fit(
                    model,
                    scales,
                    y,
                    p0=[a0, b0, c0],
                    bounds=(lower, upper),
                    maxfev=2000,
                )
            value = float(model(0.0, *popt))
            if not np.isfinite(value):
                raise RuntimeError("non-finite fit")
            result[j] = value
        except (RuntimeError, ValueError, np.linalg.LinAlgError):
            fallback = np.polyfit(scales, y, 1)
            result[j] = fallback[-1]
    return result


def _probs_to_counts(
    probs: np.ndarray, total_counts: int, num_qubits: int
) -> dict[str, int]:
    """Convert a probability vector to integer counts.

    Distributes ``total_counts`` shots across bitstrings according to
    ``probs`` and adjusts the largest bin so the totals match exactly.

    Args:
        probs: Probability vector of length ``2**num_qubits``.
        total_counts: Total number of shots.
        num_qubits: Number of measured qubits.

    Returns:
        Counts dictionary (only non-zero entries).
    """
    probs = np.asarray(probs, dtype=float)
    counts = np.round(probs * total_counts).astype(int)
    diff = total_counts - int(counts.sum())
    if diff != 0 and counts.size:
        idx = int(np.argmax(probs))
        counts[idx] += diff
    result: dict[str, int] = {}
    for idx, c in enumerate(counts):
        if c > 0:
            result[format(idx, f"0{num_qubits}b")] = int(c)
    return result


class ZNEMitigation(MitigationBase):
    """Zero-noise extrapolation mitigation technique.

    Generates one circuit variant per noise scale factor by folding CZ
    gates, executes them, and extrapolates the measurement probabilities
    back to the zero-noise limit.

    Configuration (via ``set_config`` or the constructor):

        - ``scale_factors``: noise scale factors, e.g. ``[1, 2, 3]``.
          Floats in ``[1, 3]`` use partial CZ folding; odd integers
          ``> 1`` fold every CZ gate that many times.
        - ``extrapolation_method``: ``polynomial`` (default),
          ``richardson``, ``linear`` or ``exponential``.
        - ``polynomial_degree``: degree for the ``polynomial`` method
          (default 1 -- a robust linear least-squares fit).
        - ``enable_fallback``: fall back to scale-1 when extrapolation
          diverges (default ``True``).
        - ``fallback_threshold``: maximum total negative probability mass
          tolerated before falling back (default ``0.15``).
        - ``scale_factor``: legacy single value, treated as
          ``[1, scale]``.
    """

    DEFAULT_SCALE_FACTORS: tuple[float, ...] = (1.0, 2.0, 3.0)
    DEFAULT_METHOD: str = "polynomial"
    DEFAULT_POLYNOMIAL_DEGREE: int = 1
    DEFAULT_FOLDING_STRATEGY: str = "left"

    _fold_gate_names: tuple[str, ...] | None

    def __init__(
        self,
        scale_factors: Sequence[float] | None = None,
        extrapolation_method: str = DEFAULT_METHOD,
        polynomial_degree: int | None = None,
        enable_fallback: bool = True,
        fallback_threshold: float = 0.15,
        scale_factor: float | None = None,
        folding_strategy: str = DEFAULT_FOLDING_STRATEGY,
        folding_seed: int | None = None,
        fold_gate_names: Sequence[str] | None = None,
    ):
        """Initialise ZNE mitigation.

        Args:
            scale_factors: Noise scale factors.  Defaults to ``(1, 2, 3)``.
            extrapolation_method: Extrapolation method name.
            polynomial_degree: Degree for the polynomial method.
            enable_fallback: Whether to fall back on divergence.
            fallback_threshold: Max negative mass before fallback.
            scale_factor: Legacy single scale factor; equivalent to
                ``scale_factors=(1, scale_factor)``.
            folding_strategy: Which gates get the partial fold for
                fractional scales -- ``"left"`` (default, legacy),
                ``"right"`` or ``"random"`` (mitiq default, unbiased).
            folding_seed: RNG seed for the ``"random"`` strategy.
            fold_gate_names: Gate names eligible for folding.  Defaults
                to all self-inverse two-qubit gates; restricting to
                ``["cz"]`` reproduces the legacy CZ-only behaviour.
        """
        super().__init__("zne")
        if scale_factors is not None:
            self._scale_factors = tuple(float(s) for s in scale_factors)
        elif scale_factor is not None:
            self._scale_factors = (1.0, float(scale_factor))
        else:
            self._scale_factors = tuple(self.DEFAULT_SCALE_FACTORS)
        self._extrapolation_method = extrapolation_method
        self._polynomial_degree = polynomial_degree
        if (
            self._polynomial_degree is None
            and self._extrapolation_method == "polynomial"
        ):
            self._polynomial_degree = self.DEFAULT_POLYNOMIAL_DEGREE
        self._enable_fallback = enable_fallback
        self._fallback_threshold = fallback_threshold
        self._scale_factor = max(self._scale_factors)
        self._folding_strategy = folding_strategy
        self._folding_seed = folding_seed
        # Default to CZ-only so the out-of-the-box behaviour is identical
        # to the legacy apply_zne_cz_folding; widen via fold_gate_names.
        self._fold_gate_names = (
            ("cz",) if fold_gate_names is None else tuple(fold_gate_names)
        )

    def set_config(self, config: dict[str, Any]) -> None:
        """Set configuration from a dictionary."""
        super().set_config(config)
        if config.get("scale_factors"):
            self._scale_factors = tuple(
                float(s) for s in config["scale_factors"]
            )
        elif config.get("scale_factor"):
            self._scale_factors = (1.0, float(config["scale_factor"]))
        self._extrapolation_method = config.get(
            "extrapolation_method", self._extrapolation_method
        )
        self._polynomial_degree = config.get(
            "polynomial_degree", self._polynomial_degree
        )
        if (
            self._polynomial_degree is None
            and self._extrapolation_method == "polynomial"
        ):
            self._polynomial_degree = self.DEFAULT_POLYNOMIAL_DEGREE
        self._enable_fallback = config.get(
            "enable_fallback", self._enable_fallback
        )
        self._fallback_threshold = config.get(
            "fallback_threshold", self._fallback_threshold
        )
        self._folding_strategy = config.get(
            "folding_strategy", self._folding_strategy
        )
        self._folding_seed = config.get("folding_seed", self._folding_seed)
        if "fold_gate_names" in config:
            gns = config["fold_gate_names"]
            self._fold_gate_names = None if gns is None else tuple(gns)
        self._scale_factor = max(self._scale_factors)

    def validate_device(self, device_config: dict[str, Any]) -> tuple:
        """Validate that the device exposes a CZ gate."""
        basis_gates = device_config.get("basis_gates", [])
        if "cz" not in [g.lower() for g in basis_gates]:
            return (
                False,
                "ZNE requires CZ gate in device basis gates. "
                f"Available: {basis_gates}",
            )
        return (True, None)

    def transform_circuit(
        self, circuit: QuantumCircuit
    ) -> list[dict[str, Any]]:
        """Generate original and noise-scaled circuit variants.

        Args:
            circuit: The original transpiled circuit.

        Returns:
            List of circuit variants, one per configured scale factor.
        """
        cz_count = count_cz_gates(circuit)
        if cz_count == 0:
            logger.info("No CZ gates found in circuit, ZNE has no effect")
            return [
                {
                    "label": "zne_s1",
                    "circuit": circuit,
                    "scale_factor": 1,
                }
            ]

        use_legacy = (
            self._folding_strategy == "left"
            and self._fold_gate_names == ("cz",)
        )
        variants: list[dict[str, Any]] = []
        for scale in self._scale_factors:
            if use_legacy:
                scaled = apply_zne_cz_folding(circuit, float(scale))
            else:
                scaled = fold_gates(
                    circuit,
                    float(scale),
                    strategy=self._folding_strategy,
                    gate_names=self._fold_gate_names,
                    seed=self._folding_seed,
                )
            achieved = count_cz_gates(scaled) / cz_count if cz_count else 1.0
            variants.append({
                "label": f"zne_s{achieved:g}",
                "circuit": scaled,
                "scale_factor": float(scale),
            })
            logger.info(
                "ZNE variant zne_s%.4g: %d CZ -> %d CZ (scale %.3f, %s)",
                achieved,
                cz_count,
                count_cz_gates(scaled),
                achieved,
                "legacy" if use_legacy else self._folding_strategy,
            )
        return variants

    def _parse_scale(self, label: str) -> float | None:
        """Extract the noise scale factor from a variant label."""
        match = _SCALE_LABEL_RE.match(label)
        if match:
            return float(match.group(1))
        if label == "original":
            return 1.0
        if label == "scaled":
            return float(self._scale_factor) if self._scale_factor else 3.0
        return None

    def postprocess(
        self,
        results: dict[str, dict[str, int]],
        calibration: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Apply ZNE extrapolation to measurement results.

        Two extrapolation modes are supported (mitiq offers only the
        expectation-value mode; the probability mode is kept as default
        for backwards-compatible counts output):

        - **Probability mode (default):** extrapolate each bitstring's
          probability to zero noise, returning ``mitigated`` counts.
        - **Expectation-value mode:** pass ``observable=[q0, q1, ...]`` to
          reduce each scale's counts to a single Z-parity expectation via
          :func:`utils.expectation_from_probabilities`, extrapolate that
          scalar to zero noise, and return it under the
          ``"expectation_value"`` key.  Scalar extrapolation is the
          mitiq standard and is statistically more stable than
          per-element probability extrapolation.

        Args:
            results: Dict mapping variant label to counts.  Labels of the
                form ``zne_s<scale>`` are parsed; legacy ``original`` and
                ``scaled`` labels are also accepted.
            calibration: Not used by ZNE.
            **kwargs: ``num_qubits`` and optional ``observable`` (a list
                of qubit indices for the Z-parity observable).

        Returns:
            Extrapolated results with metadata.
        """
        num_qubits = kwargs.get("num_qubits")
        if num_qubits is None:
            for counts in results.values():
                if counts:
                    num_qubits = len(next(iter(counts)))
                    break
        if num_qubits is None:
            num_qubits = 1

        observable = kwargs.get("observable")

        # Collect (scale, probs); keep the first occurrence of each scale
        # and remember the scale-1 counts for the shot total / fallback.
        points: list[tuple[float, np.ndarray]] = []
        seen: set[float] = set()
        scale1_counts: dict[str, int] | None = None
        scale1_probs: np.ndarray | None = None
        for label, counts in results.items():
            scale = self._parse_scale(label)
            if scale is None or counts is None or scale in seen:
                continue
            seen.add(scale)
            probs = counts_to_probabilities(counts, num_qubits)
            points.append((scale, probs))
            if abs(scale - 1.0) < 1e-9:
                scale1_counts = counts
                scale1_probs = probs

        if scale1_counts is None or scale1_probs is None:
            logger.warning("No scale-1 results found for ZNE")
            return {
                "results": results,
                "metadata": {"technique": "zne", "applied": False},
            }

        total_counts = sum(scale1_counts.values())
        points.sort(key=lambda item: item[0])

        if observable is not None:
            # Expectation-value mode (mitiq standard): fit the scalar
            # observable value vs scale directly.  Distribution-entropy
            # pruning does not apply -- a more uniform distribution as
            # noise grows is the *signal* the fit rides on, not a
            # collapse to discard.  Only require >= 2 points.
            if len(points) < 2:
                return {
                    "results": {
                        "expectation_value": float(
                            expectation_from_probabilities(
                                scale1_probs, list(observable)
                            )
                        ),
                        "expectation_value_raw": float(
                            expectation_from_probabilities(
                                scale1_probs, list(observable)
                            )
                        ),
                    },
                    "metadata": {
                        "technique": "zne",
                        "applied": False,
                        "mode": "expectation_value",
                        "reason": "insufficient_scale_points",
                        "scale_factors": [float(s) for s, _ in points],
                    },
                }
            scales = np.array([p[0] for p in points], dtype=float)
            probs_matrix = np.vstack([p[1] for p in points])
            return self._extrapolate_expectation(
                scales,
                probs_matrix,
                self._extrapolation_method,
                observable,
                scale1_probs,
                total_counts,
                num_qubits,
            )

        # Drop saturated / non-monotonic trailing points so extrapolation
        # never curve-fits collapsed measurements.
        pruned = _prune_scale_points(points, num_qubits)

        if len(pruned) < 2:
            logger.info(
                "Fewer than 2 trustworthy ZNE points (%d after "
                "pruning of %d), skipping extrapolation",
                len(pruned),
                len(points),
            )
            return {
                "results": {
                    "extrapolated": _probs_to_counts(
                        scale1_probs, total_counts, num_qubits
                    )
                },
                "metadata": {
                    "technique": "zne",
                    "applied": False,
                    "reason": "insufficient_scale_points",
                    "scale_factors": [float(s) for s, _ in points],
                    "pruned_to": len(pruned),
                },
            }

        scales = np.array([p[0] for p in pruned], dtype=float)
        probs_matrix = np.vstack([p[1] for p in pruned])
        method = self._extrapolation_method

        extrapolated = extrapolate_to_zero(
            scales, probs_matrix, method, self._polynomial_degree
        )
        extrapolated = np.asarray(extrapolated, dtype=float).ravel()

        neg_mass = float(-np.sum(np.minimum(extrapolated, 0.0)))  # type: ignore[operator]
        finite = bool(np.all(np.isfinite(extrapolated)))
        used_fallback = False
        if not finite or (
            self._enable_fallback and neg_mass > self._fallback_threshold
        ):
            logger.warning(
                "ZNE extrapolation unstable (method=%s, "
                "neg_mass=%.3f, finite=%s); falling back to scale-1",
                method,
                neg_mass,
                finite,
            )
            extrapolated = scale1_probs
            used_fallback = True

        extrapolated = clip_and_normalize(extrapolated)
        delta = float(np.mean(np.abs(extrapolated - scale1_probs)))
        mitigated_counts = _probs_to_counts(
            extrapolated, total_counts, num_qubits
        )

        return {
            "results": {"extrapolated": mitigated_counts},
            "metadata": {
                "technique": "zne",
                "applied": True,
                "scale_factors": [float(s) for s in scales],
                "extrapolation_method": method,
                "polynomial_degree": self._polynomial_degree,
                "mean_delta": delta,
                "negative_mass": neg_mass,
                "fallback": used_fallback,
                "fallback_threshold": self._fallback_threshold,
                "pruned_points": len(points) - len(pruned),
            },
        }

    def _extrapolate_expectation(
        self,
        scales: np.ndarray,
        probs_matrix: np.ndarray,
        method: str,
        observable: Any,
        scale1_probs: np.ndarray,
        total_counts: int,
        num_qubits: int,
    ) -> dict[str, Any]:
        """Expectation-value ZNE (mitiq standard).

        Reduces each scale's probability vector to a single Z-parity
        expectation over ``observable`` qubits, fits the (scale,
        expectation) pairs to ``method``, and evaluates at zero noise.
        Scalar extrapolation is statistically more stable than
        per-element probability extrapolation.
        """
        support = list(observable)
        expectations = np.array(
            [
                expectation_from_probabilities(probs_matrix[i], support)
                for i in range(scales.size)
            ],
            dtype=float,
        )
        raw_exp1 = float(expectations[0]) if scales.size else 0.0

        extrapolated: float = float(
            np.asarray(
                extrapolate_to_zero(
                    [float(s) for s in scales],
                    expectations.reshape(-1, 1),
                    method,
                    self._polynomial_degree,
                )
            ).ravel()[0]
        )

        finite = bool(np.isfinite(extrapolated))
        # Expectation values are bounded in [-1, 1]; a divergent fit
        # (out of range) triggers fallback to the scale-1 value.
        used_fallback = False
        if not finite or (
            self._enable_fallback and abs(extrapolated) > 1.0 + 1e-9
        ):
            logger.warning(
                "ZNE expectation extrapolation unstable (method=%s, "
                "value=%.4f, finite=%s); falling back to scale-1",
                method,
                extrapolated,
                finite,
            )
            extrapolated = raw_exp1
            used_fallback = True
        extrapolated = float(np.clip(extrapolated, -1.0, 1.0))

        return {
            "results": {
                "expectation_value": extrapolated,
                "expectation_value_raw": raw_exp1,
            },
            "metadata": {
                "technique": "zne",
                "applied": True,
                "mode": "expectation_value",
                "observable": support,
                "scale_factors": [float(s) for s in scales],
                "extrapolation_method": method,
                "polynomial_degree": self._polynomial_degree,
                "expectations": [float(e) for e in expectations],
                "fallback": used_fallback,
                "fallback_threshold": self._fallback_threshold,
            },
        }
