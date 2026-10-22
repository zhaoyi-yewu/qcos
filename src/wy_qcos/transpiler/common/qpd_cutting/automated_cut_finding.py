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

# Modified for wuyue_cutting: represent an unreportably large squared sampling
# overhead as infinity instead of discarding an otherwise valid cut plan with
# OverflowError. This is required for honest preflight analysis of large cuts.

"""Function for automatically finding locations for gate and wire cuts."""

from __future__ import annotations

from typing import cast, Any
from dataclasses import dataclass
from math import sqrt
from sys import float_info

from qiskit.circuit import QuantumCircuit, CircuitInstruction

from .instructions import CutWire
from .cutting_decomposition import cut_gates
from .cut_finding.optimization_settings import OptimizationSettings
from .cut_finding.disjoint_subcircuits_state import DisjointSubcircuitsState
from .cut_finding.circuit_interface import SimpleGateList
from .cut_finding.lo_cuts_optimizer import LOCutsOptimizer
from .cut_finding.cco_utils import qc_to_cco_circuit


def find_cuts(
    circuit: QuantumCircuit,
    optimization: OptimizationParameters,
    constraints: DeviceConstraints,
) -> tuple[QuantumCircuit, dict[str, float]]:
    """Find circuit cuts that satisfy the optimization and device constraints.

    Args:
        circuit: The circuit to cut. The input circuit may not contain gates
            acting on more than two qubits.
        optimization: Options for controlling optimizer behavior. Currently,
            the optimal cuts are chosen using Dijkstra's best-first search
            algorithm.
        constraints: Constraints on how the circuit may be partitioned
    Returns:
        A circuit containing :class:`.BaseQPDGate` instances. The subcircuits
        resulting from cutting these gates will be runnable on the devices
        meeting the ``constraints``.

        A metadata dictionary:
            - cuts: Length-2 tuples describing cuts in the output circuit.
              The tuples are formatted as ``(cut_type: str, cut_id: int)``. The
              cut ID is the index of the cut gate or wire in the output
              circuit's ``data`` field.
            - sampling_overhead: The sampling overhead from cutting the gates
              and wires.
            - minimum_reached: Whether the search conclusively found the cost
              function minimum. ``minimum_reached = False`` could also mean
              that the returned cost was the lowest possible cost but the
              search could not run long enough to prove it.

    Raises:
        ValueError: The circuit contains a gate acting on more than 2 qubits.
    """
    circuit_cco = qc_to_cco_circuit(circuit)
    interface = SimpleGateList(circuit_cco)

    opt_settings = OptimizationSettings(
        seed=optimization.seed,
        max_gamma=optimization.max_gamma,
        max_backjumps=optimization.max_backjumps,
        gate_lo=optimization.gate_lo,
        wire_lo=optimization.wire_lo,
    )

    # Hard-code the optimizer to an LO-only optimizer
    optimizer = LOCutsOptimizer(interface, opt_settings, constraints)

    # Find cut locations
    opt_out = optimizer.optimize()

    wire_cut_actions = []
    gate_ids = []

    opt_out = cast(DisjointSubcircuitsState, opt_out)
    opt_out.actions = cast(list, opt_out.actions)
    for action in opt_out.actions:
        if action.action.get_name() == "CutTwoQubitGate":
            gate_ids.append(action.gate_spec.instruction_id)
        else:
            # The cut-finding optimizer currently only supports 4 cutting
            # actions: {CutTwoQubitGate + these 3 wire cut types}
            if action.action.get_name() not in (
                "CutLeftWire",
                "CutRightWire",
                "CutBothWires",
            ):
                raise RuntimeError(
                    f"Unsupported cut action: {action.action.get_name()}."
                )
            wire_cut_actions.append(action)

    # First, replace all gates to cut with BaseQPDGate instances.
    # This assumes each gate to cut is replaced 1-to-1 with a QPD gate.
    # This may not hold in the future as we stop treating gate cuts
    # individually.
    circ_out = cut_gates(circuit, gate_ids)[0]

    # Insert all the wire cuts
    counter = 0
    for action in sorted(wire_cut_actions, key=lambda a: a[1][0]):
        inst_id = action.gate_spec.instruction_id
        # action.args[0][0] will be either 1 (control) or 2 (target)
        qubit_id = action.args[0][0] - 1
        circ_out.data.insert(
            inst_id + counter,
            CircuitInstruction(
                CutWire(), [circuit.data[inst_id].qubits[qubit_id]], []
            ),
        )
        counter += 1

        if action.action.get_name() == "CutBothWires":
            # There should be two wires specified in the action in this case
            if len(action.args) != 2:
                raise RuntimeError(
                    "CutBothWires action must identify exactly two wires."
                )
            qubit_id2 = action.args[1][0] - 1
            circ_out.data.insert(
                inst_id + counter,
                CircuitInstruction(
                    CutWire(), [circuit.data[inst_id].qubits[qubit_id2]], []
                ),
            )
            counter += 1

    # Return metadata describing the cut scheme
    metadata: dict[str, Any] = {"cuts": []}
    for i, inst in enumerate(circ_out.data):
        if inst.operation.name == "qpd_2q":
            metadata["cuts"].append(("Gate Cut", i))
        elif inst.operation.name == "cut_wire":
            metadata["cuts"].append(("Wire Cut", i))
    gamma = float(opt_out.upper_bound_gamma())
    metadata["sampling_overhead"] = (
        gamma * gamma if gamma <= sqrt(float_info.max) else float("inf")
    )
    metadata["minimum_reached"] = optimizer.minimum_reached()

    return circ_out, metadata


@dataclass
class OptimizationParameters:
    """Specify parameters that control the optimization.

    If either ``max_backjumps`` or ``max_gamma`` is exceeded, the search
    terminates but returns the result of a greedy best-first search. This gives
    an *upper bound* on gamma.
    """

    #: Seed for NumPy generators in the best-first search priority queue.
    seed: int | None = OptimizationSettings().seed

    #: Maximum gamma value before the search terminates.
    max_gamma: float = OptimizationSettings().max_gamma

    #: Maximum backjumps before termination; ``None`` means no restriction.
    max_backjumps: None | int = OptimizationSettings().max_backjumps

    #: Bool indicating whether or not to allow LO gate cuts while finding cuts.
    gate_lo: bool = OptimizationSettings().gate_lo

    #: Bool indicating whether or not to allow LO wire cuts while finding cuts.
    wire_lo: bool = OptimizationSettings().wire_lo


@dataclass
class DeviceConstraints:
    """Specify the required qubit count per subcircuit."""

    qubits_per_subcircuit: int

    def __post_init__(self):
        """Post-init method for data class."""
        if self.qubits_per_subcircuit < 1:
            raise ValueError(
                "qubits_per_subcircuit must be a positive definite integer."
            )

    def get_qpu_width(self) -> int:
        """Return the number of qubits per subcircuit."""
        return self.qubits_per_subcircuit
