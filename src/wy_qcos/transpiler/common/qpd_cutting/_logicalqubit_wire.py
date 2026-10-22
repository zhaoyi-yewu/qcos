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

"""LogicalQubit Cloud execution adapter for wire-cut Z-basis fragments.

The LQCloud SDK accepts its own ``QuantumCircuit`` objects rather than
OpenQASM.  This adapter translates the lightweight local circuit model,
submits each fragment as an independent cloud task, and converts the returned
counts into the QPD-correlated expectations used by reconstruction.  LQCloud
does not accept multiple circuits in one ``backend.run`` call, so concurrency
is implemented by keeping a bounded number of single-circuit jobs in flight.
"""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np

from ._quarkstudio_wire import _counts_to_weighted_expectation
from ._wire_cutting_core import Operation
from ._wire_cutting_service import (
    CuttingExperimentBatch,
    CuttingExperimentResults,
)
from ._wire_cutting_workflow import FragmentExperiment


_LQCLOUD_SUBMISSION_PATCH_LOCK = threading.Lock()


def _is_missing_lqcloud_task(error: BaseException) -> bool:
    """Return whether an SDK error says an accepted task cannot be found."""
    message = str(error).lower()
    return "status poll failed" in message and (
        "http 404" in message or "任务不存在" in message
    )


def _is_idempotency_in_flight(value: object) -> bool:
    """Return whether an SDK response/error is an in-flight idempotency 409.

    LQCloud 0.5.1 returns the final response from ``request_with_retry`` after
    its retry budget is exhausted.  The provider raises ``JobError`` only
    after that helper returns, so the adapter must recognize both a response
    object and an exception to remain compatible with SDK revisions.
    """
    status_code = getattr(value, "status_code", None)
    response = getattr(value, "response", None)
    if status_code is None and response is not None:
        status_code = getattr(response, "status_code", None)

    message_parts = [str(value)]
    for candidate in (value, response):
        if candidate is None:
            continue
        text = getattr(candidate, "text", None)
        if text:
            message_parts.append(str(text))
        json_method = getattr(candidate, "json", None)
        if callable(json_method):
            try:
                message_parts.append(str(json_method()))
            except (TypeError, ValueError):
                pass

    message = " ".join(message_parts).lower()
    is_409 = (
        status_code == 409
        or "http 409" in message
        or "409 client error" in message
    )
    mentions_key = "idempotency" in message or "幂等" in message
    mentions_in_flight = any(
        marker in message
        for marker in (
            "in_flight",
            "in flight",
            "still being processed",
            "仍在处理",
            "正在处理",
        )
    )
    return is_409 and mentions_key and mentions_in_flight


def _lqcloud_release(version: str) -> tuple[int, int, int]:
    """Parse the three-part release number exposed by the LQCloud SDK."""
    release = version.split("+", 1)[0].split("-", 1)[0].split(".")
    try:
        parts = (release + ["0", "0"])[:3]
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return (0, 0, 0)


class LogicalQubitBatchExecutor:
    """Execute a collection of wire-QPD fragments through the LQCloud SDK."""

    MAX_IN_FLIGHT = 64

    def __init__(
        self,
        api_key: str,
        backend_name: str,
        shots: int,
        *,
        url: str = "https://cloud.logicalqubit.com",
        task_timeout: float | None = 43_200.0,
        poll_interval: float = 2.0,
        submission_timeout: float | None = 43_200.0,
        max_submission_attempts: int = 30,
        max_missing_task_polls: int = 3,
        max_task_resubmissions: int = 2,
        readout_correction: bool = False,
        route_to_topology: bool = True,
    ) -> None:
        if not api_key:
            raise ValueError("LogicalQubit API key must not be empty.")
        if not backend_name:
            raise ValueError("LogicalQubit backend_name must not be empty.")
        if not 1 <= shots <= 50_000:
            raise ValueError(
                "LogicalQubit shots must be between 1 and 50,000."
            )
        if task_timeout is not None and task_timeout <= 0:
            raise ValueError("task_timeout must be positive or None.")
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive.")
        if submission_timeout is not None and submission_timeout <= 0:
            raise ValueError("submission_timeout must be positive or None.")
        if max_submission_attempts < 1:
            raise ValueError("max_submission_attempts must be positive.")
        if max_missing_task_polls < 0:
            raise ValueError("max_missing_task_polls must be non-negative.")
        if max_task_resubmissions < 0:
            raise ValueError("max_task_resubmissions must be non-negative.")
        try:
            import lqcloud
            from lqcloud import LQCloudProvider, QuantumCircuit
        except ImportError as error:
            raise RuntimeError(
                "Install LogicalQubit Cloud support with "
                "`python -m pip install lqcloud==0.5.1`."
            ) from error
        sdk_version = getattr(lqcloud, "__version__", None)
        if sdk_version is not None and _lqcloud_release(sdk_version) < (
            0,
            5,
            1,
        ):
            raise RuntimeError(
                f"lqcloud>=0.5.1 is required, but {sdk_version} is installed. "
                "Version 0.5.1 safely retries HTTP 409 idempotency conflicts "
                "with the original Idempotency-Key. Upgrade with "
                "`python -m pip install --upgrade lqcloud==0.5.1`."
            )
        try:
            from lqcloud.provider import (
                cloud_provider as lqcloud_provider_module,
            )
        except ImportError as error:
            if sdk_version is not None:
                raise RuntimeError(
                    "The installed lqcloud package is incomplete; reinstall "
                    "it with `python -m pip install --force-reinstall "
                    "lqcloud==0.5.1`."
                ) from error
            # Unit-test doubles expose only the public SDK objects.
            lqcloud_provider_module = None

        self._QuantumCircuit = QuantumCircuit
        self._backend = LQCloudProvider(api_key=api_key, url=url).get_backend(
            backend_name
        )
        self._shots = shots
        self._task_timeout = task_timeout
        self._poll_interval = poll_interval
        self._submission_timeout = submission_timeout
        self._max_submission_attempts = max_submission_attempts
        self._max_missing_task_polls = max_missing_task_polls
        self._max_task_resubmissions = max_task_resubmissions
        self._readout_correction = readout_correction
        self._route_to_topology = route_to_topology
        self._coupling_map, self._physical_qubits = _backend_topology(
            self._backend
        )
        if route_to_topology and not self._coupling_map:
            raise ValueError(
                "LogicalQubit backend exposes no topology.coupling_map; "
                "cannot route CZ gates."
            )
        self._submitted = 0

        # Kept as an attribute so the retry shim can be exercised with a fake
        # SDK in unit tests without making network calls.
        self._lqcloud_provider_module = lqcloud_provider_module

    @property
    def submitted_tasks(self) -> int:
        """Number of single-circuit LQCloud jobs submitted."""
        return self._submitted

    @property
    def cache_hits(self) -> int:
        """LQCloud execution has no local result cache."""
        return 0

    def execute(
        self, batch: CuttingExperimentBatch
    ) -> CuttingExperimentResults:
        """Execute fragment circuits and reconstruct local responses."""
        groups: dict[tuple[int, int], list] = defaultdict(list)
        for experiment in batch.experiments:
            groups[(experiment.term_index, experiment.fragment_label)].append(
                experiment
            )

        work = []
        for key, group in sorted(groups.items()):
            fragment_experiment = group[0].fragment_experiment
            if any(
                item.fragment_experiment != fragment_experiment
                for item in group
            ):
                raise ValueError(
                    "Inconsistent fragment data in one LogicalQubit group."
                )
            if any(
                any(axis != "Z" for axis in item.observable.values())
                for item in group
            ):
                raise ValueError(
                    "LogicalQubit wire executor currently supports "
                    "Z-basis observables."
                )
            circuit = (
                _fragment_to_routed_lqcloud_circuit(
                    self._QuantumCircuit,
                    fragment_experiment,
                    self._coupling_map,
                    self._physical_qubits,
                )
                if self._route_to_topology
                else _fragment_to_lqcloud_circuit(
                    self._QuantumCircuit, fragment_experiment
                )
            )
            work.append((key, group, circuit))

        values: dict[tuple[int, int, int], float] = {}
        for start in range(0, len(work), self.MAX_IN_FLIGHT):
            chunk = work[start : start + self.MAX_IN_FLIGHT]
            results = self._run_individual_circuits([
                circuit for _, _, circuit in chunk
            ])
            for (_, group, _), result in zip(chunk, results, strict=True):
                if not result.success:
                    error_type = getattr(result, "error_type", None)
                    error_message = getattr(result, "error", None)
                    raise RuntimeError(
                        "LogicalQubit fragment failed: "
                        f"{error_type} {error_message}"
                    )
                counts = result.get_counts()
                for experiment in group:
                    qpd_cbits = tuple(
                        sorted(
                            experiment.fragment_experiment.terminal_measurements
                        )
                    )
                    observable_cbits = tuple(sorted(experiment.observable))
                    values[
                        (
                            experiment.term_index,
                            experiment.observable_index,
                            experiment.fragment_label,
                        )
                    ] = _counts_to_weighted_expectation(
                        counts, qpd_cbits, observable_cbits
                    )
        return CuttingExperimentResults(
            batch,
            tuple(
                values[
                    (
                        item.term_index,
                        item.observable_index,
                        item.fragment_label,
                    )
                ]
                for item in batch.experiments
            ),
        )

    def _run_individual_circuits(self, circuits: list) -> list:
        """Submit circuits and recover from transient missing-task responses.

        LQCloud occasionally accepts an asynchronous task and then briefly
        returns HTTP 404 while its status record is being propagated.  First
        poll the same job again; if it remains absent, resubmit only that
        circuit.  Results already obtained for sibling circuits are retained.
        """
        if not circuits:
            return []

        def submit(circuit):
            job = self._submit_with_extended_idempotency_retry(circuit)
            self._submitted += 1
            return job

        def await_result(job):
            for poll_retry in range(self._max_missing_task_polls + 1):
                try:
                    return job.result(
                        timeout=self._task_timeout,
                        wait=max(1, int(math.ceil(self._poll_interval))),
                        verbose=False,
                    )
                except Exception as error:
                    if (
                        not _is_missing_lqcloud_task(error)
                        or poll_retry >= self._max_missing_task_polls
                    ):
                        raise
                    delay = min(self._poll_interval * (2**poll_retry), 60.0)
                    print(
                        "LogicalQubit task was temporarily unavailable; "
                        f"polling it again in {delay:g}s "
                        f"({poll_retry + 1}/{self._max_missing_task_polls}).",
                        flush=True,
                    )
                    time.sleep(delay)

        def capture_result(job):
            try:
                return True, await_result(job)
            except Exception as error:
                return False, error

        jobs = [submit(circuit) for circuit in circuits]
        results = [None] * len(circuits)
        pending = list(range(len(circuits)))
        resubmissions = [0] * len(circuits)

        while pending:
            with ThreadPoolExecutor(
                max_workers=len(pending),
                thread_name_prefix="logicalqubit-result",
            ) as pool:
                outcomes = list(
                    pool.map(
                        capture_result, (jobs[index] for index in pending)
                    )
                )

            retry_indices = []
            for index, (succeeded, outcome) in zip(
                pending, outcomes, strict=True
            ):
                if succeeded:
                    results[index] = outcome
                    continue
                if (
                    not _is_missing_lqcloud_task(outcome)
                    or resubmissions[index] >= self._max_task_resubmissions
                ):
                    raise outcome
                resubmissions[index] += 1
                delay = min(
                    self._poll_interval * (2 ** (resubmissions[index] - 1)),
                    60.0,
                )
                print(
                    "LogicalQubit task is missing; resubmitting only its "
                    f"circuit in {delay:g}s "
                    f"({resubmissions[index]}/{self._max_task_resubmissions}).",
                    flush=True,
                )
                time.sleep(delay)
                jobs[index] = submit(circuits[index])
                retry_indices.append(index)
            pending = retry_indices

        return results

    def _submit_with_extended_idempotency_retry(self, circuit):
        """Wait out in-flight HTTP 409 responses with the original key.

        LQCloud 0.5.1 safely handles ``idempotency_in_flight`` responses, but
        its public API does not expose the request retry budget and the
        default retry window can be shorter than an overloaded server's
        submission latency.  Temporarily wrap the SDK request helper while
        ``backend.run`` creates the key and submits the circuit.  If an SDK
        retry round still ends in ``idempotency_in_flight``, call the helper
        again with the exact same arguments and key.  Never call
        ``backend.run`` again for this condition: doing so would create a new
        key and could duplicate a task already accepted by the server.
        """
        provider_module = self._lqcloud_provider_module
        if provider_module is None:
            return self._backend.run(
                circuit,
                shots=self._shots,
                readout_correction=self._readout_correction,
            )
        with _LQCLOUD_SUBMISSION_PATCH_LOCK:
            original_request = provider_module.request_with_retry

            def request_with_extended_retry(*args, **kwargs):
                method = kwargs.get("method", args[1] if len(args) > 1 else "")
                is_idempotent_post = (
                    str(method).upper() == "POST"
                    and kwargs.get("idempotency_key") is not None
                )
                if not is_idempotent_post:
                    return original_request(*args, **kwargs)

                kwargs["max_attempts"] = max(
                    int(kwargs.get("max_attempts", 0)),
                    self._max_submission_attempts,
                )
                started = time.monotonic()
                retry_round = 0
                while True:
                    try:
                        outcome = original_request(*args, **kwargs)
                    except Exception as error:
                        if not _is_idempotency_in_flight(error):
                            raise
                        outcome = error
                        caught_error = error
                    else:
                        caught_error = None
                        if not _is_idempotency_in_flight(outcome):
                            return outcome

                    elapsed = time.monotonic() - started
                    if (
                        self._submission_timeout is not None
                        and elapsed >= self._submission_timeout
                    ):
                        timeout_error = TimeoutError(
                            "LogicalQubit submission remained in-flight for "
                            f"{elapsed:.1f}s "
                            f"(limit={self._submission_timeout:g}s). "
                            "Every retry used the original Idempotency-Key; "
                            "check "
                            "the cloud job list before starting a new process."
                        )
                        if caught_error is not None:
                            raise timeout_error from caught_error
                        raise timeout_error

                    retry_round += 1
                    delay = min(
                        self._poll_interval * (2 ** min(retry_round - 1, 5)),
                        60.0,
                    )
                    if self._submission_timeout is not None:
                        delay = min(delay, self._submission_timeout - elapsed)
                    print(
                        "LogicalQubit submission is still being processed; "
                        "continuing with the same Idempotency-Key in "
                        f"{delay:g}s (extended retry round {retry_round}, "
                        f"elapsed {elapsed:.1f}s).",
                        flush=True,
                    )
                    time.sleep(delay)

            provider_module.request_with_retry = request_with_extended_retry
            try:
                return self._backend.run(
                    circuit,
                    shots=self._shots,
                    readout_correction=self._readout_correction,
                )
            finally:
                provider_module.request_with_retry = original_request

    def execute_qiskit_sampler_experiments(
        self,
        experiments: Mapping,
        *,
        name_prefix: str = "gate-cut",
        max_in_flight: int = 64,
    ) -> Mapping:
        """Execute addon-cutting circuits and return ordered SamplerV1 results.

        The portfolio examples use Qiskit's ``generate_cutting_experiments``
        interface rather than this package's canonical experiment batch.  This
        bridge preserves that interface while compiling every distinct circuit
        to the selected LogicalQubit backend topology and keeping at most
        ``max_in_flight`` single-circuit cloud jobs active at once.
        """
        del name_prefix  # LQCloud jobs do not accept a user-visible name.
        if max_in_flight < 1:
            raise ValueError("max_in_flight must be positive.")
        if not experiments or any(
            not circuits for circuits in experiments.values()
        ):
            raise ValueError(
                "Each partition must contain at least one circuit."
            )
        try:
            from qiskit import (
                ClassicalRegister,
                QuantumCircuit,
                QuantumRegister,
                qasm2,
                transpile,
            )
            from qiskit.primitives import SamplerResult
            from qiskit.transpiler import CouplingMap
        except ImportError as error:
            raise RuntimeError(
                "Qiskit is required to execute upstream cutting experiments."
            ) from error

        positions_by_signature: dict[tuple, list[tuple[object, int]]] = (
            defaultdict(list)
        )
        circuit_by_signature: dict[tuple, Any] = {}
        result_slots: dict[object, list[object | None]] = {
            label: [None] * len(circuits)
            for label, circuits in experiments.items()
        }
        for label, circuits in experiments.items():
            for index, circuit in enumerate(circuits):
                signature = _qiskit_circuit_signature(circuit)
                positions_by_signature[signature].append((label, index))
                circuit_by_signature.setdefault(signature, circuit)

        canonical_circuits = []
        signatures = list(circuit_by_signature)
        for signature in signatures:
            source = circuit_by_signature[signature]
            qreg = QuantumRegister(source.num_qubits, "q")
            cregs = [
                ClassicalRegister(register.size, f"c{index}")
                for index, register in enumerate(source.cregs)
            ]
            canonical = QuantumCircuit(qreg, *cregs)
            for instruction in source.data:
                canonical.append(
                    instruction.operation,
                    [
                        canonical.qubits[source.find_bit(qubit).index]
                        for qubit in instruction.qubits
                    ],
                    [
                        canonical.clbits[source.find_bit(cbit).index]
                        for cbit in instruction.clbits
                    ],
                )
            canonical_circuits.append(canonical)

        transpile_options: dict[str, Any] = {
            "optimization_level": 3,
            "seed_transpiler": 42,
            "num_processes": 1,
        }
        if self._route_to_topology:
            transpile_options.update(
                basis_gates=("u3", "cz"),
                coupling_map=CouplingMap(self._coupling_map),
                layout_method="sabre",
                routing_method="sabre",
            )
        else:
            transpile_options["basis_gates"] = ("u3", "cx")
        compiled = transpile(canonical_circuits, **transpile_options)

        signatures_by_qasm: dict[str, list[tuple]] = defaultdict(list)
        circuit_by_qasm = {}
        for signature, circuit in zip(signatures, compiled, strict=True):
            qasm = qasm2.dumps(circuit)
            signatures_by_qasm[qasm].append(signature)
            circuit_by_qasm.setdefault(qasm, circuit)

        qasms = list(circuit_by_qasm)
        print(
            f"Prepared {sum(len(v) for v in experiments.values())} logical "
            f"subexperiments as {len(qasms)} unique LogicalQubit circuit(s)."
        )
        quasi_by_qasm = {}
        in_flight_limit = min(self.MAX_IN_FLIGHT, max_in_flight)
        for start in range(0, len(qasms), in_flight_limit):
            chunk = qasms[start : start + in_flight_limit]
            lq_circuits = [
                _qiskit_to_lqcloud_circuit(
                    self._QuantumCircuit, circuit_by_qasm[qasm]
                )
                for qasm in chunk
            ]
            cloud_results = self._run_individual_circuits(lq_circuits)
            for qasm, result in zip(chunk, cloud_results, strict=True):
                if not result.success:
                    error_type = getattr(result, "error_type", None)
                    error_message = getattr(result, "error", None)
                    raise RuntimeError(
                        "LogicalQubit circuit failed: "
                        f"{error_type} {error_message}"
                    )
                quasi_by_qasm[qasm] = _counts_to_quasi_distribution(
                    result.get_counts()
                )

        for qasm, equivalent_signatures in signatures_by_qasm.items():
            quasi = quasi_by_qasm[qasm]
            for signature in equivalent_signatures:
                for label, index in positions_by_signature[signature]:
                    result_slots[label][index] = quasi

        results = {}
        for label, slots in result_slots.items():
            if any(slot is None for slot in slots):
                raise AssertionError(
                    f"Missing LogicalQubit result in partition {label!r}."
                )
            results[label] = SamplerResult(
                quasi_dists=list(slots),
                metadata=[{"shots": self._shots} for _ in slots],
            )
        return results


def _qiskit_circuit_signature(circuit) -> tuple:
    """Return a register-name-independent signature for a measured circuit."""
    if circuit.parameters:
        raise ValueError(
            "LogicalQubit cutting experiments must be fully parameter-bound."
        )
    return (
        circuit.num_qubits,
        tuple(register.size for register in circuit.cregs),
        tuple(
            (
                instruction.operation.name,
                tuple(
                    repr(parameter)
                    for parameter in instruction.operation.params
                ),
                tuple(
                    circuit.find_bit(qubit).index
                    for qubit in instruction.qubits
                ),
                tuple(
                    circuit.find_bit(cbit).index for cbit in instruction.clbits
                ),
            )
            for instruction in circuit.data
        ),
    )


def _qiskit_to_lqcloud_circuit(quantum_circuit_type, source):
    """Translate a topology-routed, terminally measured Qiskit circuit."""
    circuit = quantum_circuit_type(source.num_qubits, source.num_clbits)
    measurements: list[tuple[int, int]] = []
    measurement_started = False
    for instruction in source.data:
        operation = instruction.operation
        qubits = tuple(
            source.find_bit(qubit).index for qubit in instruction.qubits
        )
        if operation.name == "barrier":
            continue
        if operation.name == "measure":
            measurement_started = True
            if len(qubits) != 1 or len(instruction.clbits) != 1:
                raise ValueError(
                    "LogicalQubit requires one-qubit measurement instructions."
                )
            measurements.append((
                qubits[0],
                source.find_bit(instruction.clbits[0]).index,
            ))
            continue
        if measurement_started:
            raise ValueError(
                "LogicalQubit cutting circuits must use terminal measurements."
            )
        if operation.name in {"u", "u3"}:
            circuit.u(*(float(value) for value in operation.params), qubits[0])
        elif operation.name == "cx":
            circuit.cx(*qubits)
        elif operation.name == "cz":
            circuit.cz(*qubits)
        else:
            raise RuntimeError(
                f"Unexpected compiled LogicalQubit gate: {operation.name}."
            )
    if not measurements:
        raise ValueError(
            "LogicalQubit cutting circuits must contain measurements."
        )
    measured_qubits = tuple(sorted({qubit for qubit, _ in measurements}))
    circuit.barrier(*measured_qubits)
    for qubit, cbit in measurements:
        circuit.measure(qubit, cbit)
    return circuit


def _counts_to_quasi_distribution(counts: Mapping[str, int]):
    """Normalize LogicalQubit's big-endian counts for SamplerV1."""
    try:
        from qiskit.result import QuasiDistribution
    except ImportError as error:  # pragma: no cover - guarded by the caller
        raise RuntimeError(
            "Qiskit is required to construct sampler results."
        ) from error
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("LogicalQubit returned no measurement shots.")
    probabilities: dict[int, float] = {}
    for bitstring, count in counts.items():
        bits = bitstring.replace(" ", "")
        if not bits or any(bit not in "01" for bit in bits):
            raise ValueError(
                f"Unexpected LogicalQubit count key: {bitstring!r}."
            )
        if not isinstance(count, int) or count < 0:
            raise ValueError(
                f"Unexpected LogicalQubit count value: {count!r}."
            )
        outcome = int(bits, 2)
        probabilities[outcome] = (
            probabilities.get(outcome, 0.0) + count / total
        )
    return QuasiDistribution(probabilities)


def _fragment_to_lqcloud_circuit(
    quantum_circuit_type, experiment: FragmentExperiment
):
    """Translate a prepared, all-Z fragment to LQCloud."""
    fragment = experiment.fragment
    circuit = quantum_circuit_type(fragment.num_qubits, fragment.num_qubits)
    for qubit, state in sorted(experiment.preparations.items()):
        _append_qpd_preparation(circuit, qubit, state)
    for operation in fragment.operations:
        _append_operation(circuit, operation)
    for qubit, axis in sorted(experiment.terminal_measurements.items()):
        _append_pauli_measurement_rotation(circuit, qubit, axis)
    # LQCloud requires a barrier immediately before readout and will inject
    # reset operations itself at submission time.
    circuit.barrier(*range(fragment.num_qubits))
    circuit.measure(
        list(range(fragment.num_qubits)), list(range(fragment.num_qubits))
    )
    return circuit


def _backend_topology(backend) -> tuple[tuple[tuple[int, int], ...], int]:
    """Read the SDK's physical coupling map without guessing a layout."""
    config = getattr(backend, "config", None)
    if callable(config):
        config = config()
    if not isinstance(config, Mapping):
        return (), 0
    topology = config.get("topology")
    if not isinstance(topology, Mapping):
        return (), 0
    raw_edges = topology.get("coupling_map", ())
    edges: set[tuple[int, int]] = set()
    for edge in raw_edges:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            continue
        left, right = int(edge[0]), int(edge[1])
        if left != right:
            # CZ is symmetric, while Qiskit's coupling map is directed.
            edges.update(((left, right), (right, left)))
    qubits = config.get("qubits", topology.get("qubits", 0))
    if not isinstance(qubits, int):
        qubits = 0
    return tuple(sorted(edges)), max(
        qubits, max((max(edge) + 1 for edge in edges), default=0)
    )


def _fragment_to_routed_lqcloud_circuit(
    quantum_circuit_type,
    experiment: FragmentExperiment,
    coupling_edges: tuple[tuple[int, int], ...],
    physical_qubits: int,
):
    """Route a fragment on the backend and retain U3/CZ gates.

    The routed Qiskit circuit uses physical-wire indexes.  The LQCloud circuit
    deliberately has the backend's full width so those indexes remain exact;
    only the fragment's output wires are measured, avoiding a 100-qubit
    readout payload for a 13--24 qubit fragment.
    """
    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit.transpiler import CouplingMap
    except ImportError as error:
        raise RuntimeError(
            "Install qiskit to topology-route LogicalQubit fragments."
        ) from error
    fragment = experiment.fragment
    source = QuantumCircuit(fragment.num_qubits)
    for fragment_operation in fragment.operations:
        source.unitary(
            fragment_operation.matrix, list(fragment_operation.qubits)
        )
    routed = transpile(
        source,
        basis_gates=("u3", "cz"),
        coupling_map=CouplingMap(coupling_edges),
        optimization_level=3,
        seed_transpiler=42,
    )
    layout = routed.layout
    if layout is None:
        raise RuntimeError(
            "Qiskit did not return a physical layout for the "
            "LogicalQubit fragment."
        )
    initial = tuple(layout.initial_index_layout()[: fragment.num_qubits])
    final = tuple(layout.final_index_layout()[: fragment.num_qubits])
    if physical_qubits < routed.num_qubits:
        physical_qubits = routed.num_qubits
    circuit = quantum_circuit_type(physical_qubits, fragment.num_qubits)
    for local_qubit, state in sorted(experiment.preparations.items()):
        _append_qpd_preparation(circuit, initial[local_qubit], state)
    for instruction in routed.data:
        routed_operation = instruction.operation
        qubits = tuple(
            routed.find_bit(qubit).index for qubit in instruction.qubits
        )
        if routed_operation.name in {"barrier", "delay", "id"}:
            continue
        if routed_operation.name in {"u", "u3"}:
            circuit.u(
                *(float(value) for value in routed_operation.params),
                qubits[0],
            )
        elif routed_operation.name == "rz":
            circuit.rz(float(routed_operation.params[0]), qubits[0])
        elif routed_operation.name == "cz":
            circuit.cz(*qubits)
        else:
            raise RuntimeError(
                "Unexpected routed LogicalQubit gate: "
                f"{routed_operation.name}."
            )
    for local_qubit, physical_qubit in enumerate(final):
        axis = experiment.terminal_measurements.get(local_qubit, "Z")
        _append_pauli_measurement_rotation(circuit, physical_qubit, axis)
    circuit.barrier(*final)
    circuit.measure(list(final), list(range(fragment.num_qubits)))
    return circuit


def _append_qpd_preparation(circuit, qubit: int, state: np.ndarray) -> None:
    known = {
        "zero": np.array([1, 0], dtype=complex),
        "one": np.array([0, 1], dtype=complex),
        "plus": np.array([1, 1], dtype=complex) / np.sqrt(2),
        "minus": np.array([1, -1], dtype=complex) / np.sqrt(2),
        "iplus": np.array([1, 1j], dtype=complex) / np.sqrt(2),
        "iminus": np.array([1, -1j], dtype=complex) / np.sqrt(2),
    }
    name = next(
        (key for key, value in known.items() if np.allclose(state, value)),
        None,
    )
    operations = {
        "zero": (),
        "one": ("x",),
        "plus": ("h",),
        "minus": ("x", "h"),
        "iplus": ("h", "s"),
        "iminus": ("x", "h", "s"),
    }
    if name is None:
        raise ValueError(
            "The QPD preparation is not in the supported six-state basis."
        )
    for operation in operations[name]:
        getattr(circuit, operation)(qubit)


def _append_pauli_measurement_rotation(circuit, qubit: int, axis: str) -> None:
    if axis == "Z":
        return
    if axis == "X":
        circuit.h(qubit)
        return
    if axis == "Y":
        circuit.sdg(qubit)
        circuit.h(qubit)
        return
    raise ValueError(f"Unsupported Pauli axis: {axis!r}.")


def _append_operation(circuit, operation: Operation) -> None:
    """Map native operations while retaining arbitrary one-qubit SU(2)."""
    matrix = np.asarray(operation.matrix, dtype=complex)
    qubits = operation.qubits
    if len(qubits) == 1:
        # LQCloud serializes numerical SU(2) matrices as one native operation,
        # preserving the desired U-gate depth reduction.
        circuit.su2(matrix, qubits[0])
        return
    if len(qubits) != 2:
        raise ValueError(
            "LogicalQubit adapter supports only one- and two-qubit operations."
        )
    first, second = qubits
    cx = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]])
    cz = np.diag([1, 1, 1, -1])
    swap = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
    if np.allclose(matrix, cx):
        circuit.cx(first, second)
    elif np.allclose(matrix, cz):
        circuit.cz(first, second)
    elif np.allclose(matrix, swap):
        circuit.swap(first, second)
    else:
        raise ValueError(
            "LogicalQubit adapter cannot serialize this two-qubit unitary."
        )
