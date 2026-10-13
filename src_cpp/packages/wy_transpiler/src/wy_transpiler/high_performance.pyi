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

class OperationType:
    """Quantum operation type enum."""

    MEASURE: OperationType
    SINGLE_QUBIT_OPERATION: OperationType
    DOUBLE_QUBIT_OPERATION: OperationType
    TRIPLE_QUBIT_OPERATION: OperationType
    FOUR_QUBIT_OPERATION: OperationType
    FIVE_QUBIT_OPERATION: OperationType
    SYNC: OperationType
    MOVE: OperationType

    def __init__(self, value: int) -> None: ...

class BaseOperation:
    """Base quantum operation / IR element.

    Represents a single operation in a quantum circuit (gate, measure,
    sync, etc.). Returned by qasm_to_ir, accepted by optimize and
    transpile_from_ir.
    """

    name: str
    targets: list[int]
    arg_value: list[float]
    operation_type: OperationType

    def __init__(
        self,
        name: str,
        targets: list[int],
        arg_value: list[float] = ...,
        operation_type: OperationType = ...,
    ) -> None: ...

class TranspileResult:
    """Result of the all-in-one transpile function."""

    basis_gate_list: list[BaseOperation]
    num_qubits: int
    initial_mapping: list[int]
    final_mapping: list[int]

def qasm_to_ir(qasm_str: str) -> tuple[list[BaseOperation], int]:
    """Parse an OpenQASM string into an IR operation list.

    Args:
        qasm_str: OpenQASM 2.0/3.0 circuit string.

    Returns:
        (operation list, qubit count). Operations are BaseOperation.
    """

def to_qasm2(operations: list[BaseOperation], num_qubits: int = -1) -> str:
    """Convert an IR operation list to an OpenQASM 2.0 string.

    Args:
        operations: BaseOperation list (e.g. from qasm_to_ir or optimize).
        num_qubits: Force qubit count in output QASM. -1 = auto from ops.

    Returns:
        OpenQASM 2.0 circuit string.
    """

def to_qasm3(operations: list[BaseOperation], num_qubits: int = -1) -> str:
    """Convert an IR operation list to an OpenQASM 3.0 string.

    Args:
        operations: BaseOperation list (e.g. from qasm_to_ir or optimize).
        num_qubits: Force qubit count in output QASM. -1 = auto from ops.

    Returns:
        OpenQASM 3.0 circuit string.
    """

def optimize(
    ir: list[BaseOperation],
    opt_level: int = 1,
    verbose: bool = False,
    basis_gates: set[str] | None = None,
    num_threads: int = 1,
    fast_mode: bool = False,
) -> list[BaseOperation]:
    """Optimize an IR operation list with multiple optimization passes.

    opt_level:
        0 - No optimization
        1 - InverseCancellation + AdjacentPhaseOpt + Equivalence
        2 - Level 1 + HadamardReduction + RzCommute + CxCommute + PhasePoly
        3 - Level 2 + UnitarySynthesis

    Args:
        ir: Operation list to optimize.
        opt_level: Optimization level 0-3, default 1.
        verbose: Print optimization details, default False.
        basis_gates: Basis gate filter set, None = no filter.
        num_threads: Parallel threads. 1=serial, 0=auto, >1=explicit.
        fast_mode: True=run once, False=run until convergence.

    Returns:
        Optimized operation list.
    """

def optimize_qasm(
    qasm_str: str,
    opt_level: int = 1,
    basis_gates: set[str] | None = None,
) -> str:
    """Optimize a QASM circuit string and return the optimized QASM string.

    Parses the input QASM, runs optimization passes, and converts back
    to the same QASM version as the input — without routing or gate
    decomposition.

    Args:
        qasm_str: OpenQASM 2.0/3.0 circuit string.
        opt_level: Optimization level 0-3, default 1.
        basis_gates: Gate filter set. None = preserve original gate set.

    Returns:
        Optimized OpenQASM string (2.0 or 3.0).
    """

def qasm_stats(qasm_str: str) -> tuple[int, int]:
    """Compute circuit depth and gate count from a QASM string.

    Args:
        qasm_str: OpenQASM 2.0/3.0 circuit string.

    Returns:
        (depth, size) tuple. depth = circuit depth,
        size = number of quantum gates (excludes
        measure/reset/sync/move/barrier).
    """

def transpile_from_qasm(
    qasm_string: str,
    supp_basis_gates: list[str],
    opt_level: int = 1,
    coupling_list: list[tuple[int, int]] = ...,
    edge_fidelities: list[float] = ...,
    single_qubit_fidelities: list[float] = ...,
    layout_method: str = "vf2_layout",
    target_bits: list[int] = ...,
    num_threads: int = 0,
    fast_mode: bool = True,
    fidelity_threshold: float = -1.0,
    fidelity_weight: float = 0.5,
) -> TranspileResult:
    """All-in-one: parse QASM, optimize, route, decompose.

    Compiles a QASM string into a basis gate sequence supported by
    the target hardware. Includes parsing, optimization, layout
    mapping, routing, and gate decomposition.

    Args:
        qasm_string: OpenQASM circuit string.
        supp_basis_gates: Supported basis gate names for the target hardware.
        opt_level: Optimization level 0-3, default 1.
        coupling_list: Physical qubit coupling edges [(q0, q1), ...].
            Empty list skips routing.
        edge_fidelities: Edge fidelities corresponding to coupling_list.
            Empty list = not used.
        single_qubit_fidelities: Single-qubit fidelity array indexed by
            physical qubit ID. Empty list = not used.
        layout_method: Initial layout method, "vf2_layout" or "dense_layout".
        target_bits: Target physical qubit IDs. When non-empty, all-1q
            circuits map to these qubits.
        num_threads: Optimization threads. 0=auto, 1=serial, >1=explicit.
        fast_mode: True=run pass list once, default True.
        fidelity_threshold: Edges below this fidelity are filtered.
            Negative = adaptive (mean - std, clamped to [0.3, 0.9]).
        fidelity_weight: DenseLayout fidelity weight in [0, 1].
            0.0 = pure density, 1.0 = pure fidelity.

    Returns:
        TranspileResult with basis_gate_list, num_qubits,
        initial_mapping, and final_mapping.
    """

def transpile_from_ir(
    ir_ops: list[BaseOperation],
    num_qubits: int,
    supp_basis_gates: list[str],
    opt_level: int = 1,
    coupling_list: list[tuple[int, int]] = ...,
    edge_fidelities: list[float] = ...,
    single_qubit_fidelities: list[float] = ...,
    layout_method: str = "vf2_layout",
    target_bits: list[int] = ...,
    num_threads: int = 0,
    fast_mode: bool = False,
    fidelity_threshold: float = -1.0,
    fidelity_weight: float = 0.5,
) -> TranspileResult:
    """Transpile a pre-parsed IR (skip QASM parse step).

    Same pipeline as transpile_from_qasm but skips the QASM parsing
    step. The caller provides the already-parsed operation list and
    the logical qubit count directly.

    Args:
        ir_ops: Pre-parsed operation list (IR), e.g. from qasm_to_ir.
        num_qubits: Number of logical qubits in the circuit.
        supp_basis_gates: Supported basis gate names for the target hardware.
        opt_level: Optimization level 0-3, default 1.
        coupling_list: Physical qubit coupling edges [(q0, q1), ...].
            Empty list skips routing.
        edge_fidelities: Edge fidelities corresponding to coupling_list.
            Empty list = not used.
        single_qubit_fidelities: Single-qubit fidelity array indexed by
            physical qubit ID. Empty list = not used.
        layout_method: Initial layout method, "vf2_layout" or "dense_layout".
        target_bits: Target physical qubit IDs. When non-empty, all-1q
            circuits map to these qubits.
        num_threads: Optimization threads. 0=auto, 1=serial, >1=explicit.
        fast_mode: True=run pass list once, default False.
        fidelity_threshold: Edges below this fidelity are filtered.
            Negative = adaptive (mean - std, clamped to [0.3, 0.9]).
        fidelity_weight: DenseLayout fidelity weight in [0, 1].
            0.0 = pure density, 1.0 = pure fidelity.

    Returns:
        TranspileResult with basis_gate_list, num_qubits,
        initial_mapping, and final_mapping.
    """
