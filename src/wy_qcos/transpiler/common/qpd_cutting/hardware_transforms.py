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

"""Circuit transformations for hardware without dynamic-circuit support.

These transformations are deliberately opt-in.  Generating QPD experiments is
backend independent, while deferring measurements consumes additional qubits
and is therefore a hardware-specific policy.
"""

from __future__ import annotations

from qiskit import QuantumCircuit, QuantumRegister


def defer_qpd_measurements(
    circuit: QuantumCircuit,
    *,
    qpd_register_name: str = "qpd_measurements",
    ancilla_register_name: str = "qpd_ancilla",
) -> tuple[QuantumCircuit, int]:
    """Defer QPD measurements to the end of a circuit using ancillas.

    Each measurement written to the classical register named by
    ``qpd_register_name`` is replaced by a CNOT from the measured qubit to a
    fresh ancilla.  The ancillas are measured into the original classical bits
    at the end of the circuit.  This is the deferred-measurement construction
    used for static backends which cannot execute mid-circuit measurements.

    The input circuit is never modified.  The returned integer is the number
    of added ancillas.  Measurements targeting other classical registers are
    left unchanged.

    Reset removal is intentionally outside the scope of this transformation:
    a reset in the input raises :class:`ValueError`, because an internal reset
    cannot in general be removed without changing circuit semantics.

    Args:
        circuit: Circuit containing generated QPD measurements.
        qpd_register_name: Name of the QPD classical measurement register.
        ancilla_register_name: Name to use for the added quantum register.

    Returns:
        A transformed circuit and the number of added ancilla qubits.

    Raises:
        TypeError: If ``circuit`` is not a Qiskit ``QuantumCircuit``.
        ValueError: If the circuit contains a reset or the requested ancilla
            register name is already in use.
    """
    if not isinstance(circuit, QuantumCircuit):
        raise TypeError("circuit must be a qiskit.QuantumCircuit")
    if any(item.operation.name == "reset" for item in circuit.data):
        raise ValueError(
            "Cannot defer QPD measurements in a circuit containing reset; "
            "reset removal is not generally semantics-preserving"
        )

    qpd_clbits = {
        clbit
        for register in circuit.cregs
        if register.name == qpd_register_name
        for clbit in register
    }
    deferred_items = [
        item
        for item in circuit.data
        if item.operation.name == "measure"
        and item.clbits
        and item.clbits[0] in qpd_clbits
    ]
    if not deferred_items:
        return circuit.copy(), 0

    register_names = {
        register.name for register in (*circuit.qregs, *circuit.cregs)
    }
    if ancilla_register_name in register_names:
        raise ValueError(
            f"Register name {ancilla_register_name!r} is already in use"
        )

    transformed = circuit.copy_empty_like()
    ancillas = QuantumRegister(len(deferred_items), ancilla_register_name)
    transformed.add_register(ancillas)
    qubit_map = dict(
        zip(circuit.qubits, transformed.qubits[: circuit.num_qubits])
    )
    clbit_map = dict(zip(circuit.clbits, transformed.clbits))
    deferred: list[tuple[object, object]] = []

    for item in circuit.data:
        if (
            item.operation.name == "measure"
            and item.clbits
            and item.clbits[0] in qpd_clbits
        ):
            ancilla = ancillas[len(deferred)]
            transformed.cx(qubit_map[item.qubits[0]], ancilla)
            deferred.append((ancilla, clbit_map[item.clbits[0]]))
        else:
            transformed.append(
                item.operation,
                [qubit_map[qubit] for qubit in item.qubits],
                [clbit_map[clbit] for clbit in item.clbits],
            )

    for ancilla, clbit in deferred:
        transformed.measure(ancilla, clbit)
    return transformed, len(deferred)


def contains_mid_circuit_measurement(circuit: QuantumCircuit) -> bool:
    """Return whether a measurement/reset precedes a later quantum operation.

    Barriers after a measurement are ignored.  A reset is treated as a
    measurement boundary because it is also unsupported by many static
    hardware backends.
    """
    if not isinstance(circuit, QuantumCircuit):
        raise TypeError("circuit must be a qiskit.QuantumCircuit")

    measurement_seen = False
    for item in circuit.data:
        if item.operation.name in {"measure", "reset"}:
            measurement_seen = True
        elif measurement_seen and item.operation.name != "barrier":
            return True
    return False


__all__ = ["defer_qpd_measurements", "contains_mid_circuit_measurement"]
