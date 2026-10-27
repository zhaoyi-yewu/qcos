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

"""QuarkStudio execution adapter for wire-cut Z-basis experiments.

The public :class:`QuarkStudioBatchExecutor` batches compatible experiments
by QPD term and fragment, serializes them to OpenQASM 2, then polls and
converts QuarkStudio counts into QPD-correlated expectations.  Problem
construction and command-line entry points belong in ``examples/``.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
import uuid
from collections import defaultdict
from collections.abc import Hashable, Iterable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any, Protocol, cast

import numpy as np

from ._wire_cutting_service import (
    CuttingExperimentBatch,
    CuttingExperimentResults,
)
from ._wire_cutting_core import Operation
from ._wire_cutting_workflow import FragmentExperiment


class _RetryableQuarkStudioRequestError(RuntimeError):
    """A result request that may succeed when retried."""


class _UnavailableQuarkStudioTaskError(RuntimeError):
    """A QuarkStudio task whose result can no longer be retrieved."""


def _result_indicates_unavailable_task(result: Mapping[str, object]) -> bool:
    """Return whether a successful HTTP response says that a task has expired.

    An empty result is QuarkStudio's normal response while a task is still
    running, so expiry is determined separately via ``/task/status``.
    """
    if not result:
        return False
    status = result.get("status")
    if isinstance(status, str):
        normalized_status = status.casefold()
        if normalized_status in {
            "not found",
            "not_found",
            "expired",
            "deleted",
            "unknown",
        }:
            return True
        if any(
            marker in normalized_status
            for marker in (
                "not found",
                "not exist",
                "does not exist",
                "no such task",
                "expired",
            )
        ):
            return True
    text = " ".join(
        str(result[field])
        for field in ("error", "message", "detail", "reason")
        if result.get(field) is not None
    ).casefold()
    return any(
        marker in text
        for marker in (
            "not found",
            "not exist",
            "does not exist",
            "no such task",
            "task expired",
            "result expired",
        )
    )


class QuarkStudioTaskCache(Protocol):
    """Distributed cache contract for one executable QuarkStudio task."""

    def get_result(self, key: str) -> Mapping[str, int] | None:
        """Return completed measurement counts for ``key`` when available."""

    def claim(self, key: str, lease_seconds: int) -> bool:
        """Atomically claim a task key for submission."""

    def record_task(self, key: str, task_id: str, lease_seconds: int) -> None:
        """Associate a submitted task ID with this owner's claim."""

    def task_id(self, key: str) -> str | None:
        """Return the task ID currently owned by another process, if known."""

    def recover_task(self, key: str, task_id: str, lease_seconds: int) -> bool:
        """Take over a task only if ``task_id`` is still its recorded ID."""

    def complete(
        self, key: str, counts: Mapping[str, int], ttl_seconds: int
    ) -> None:
        """Store completed counts and release this owner's in-flight claim."""

    def abandon(self, key: str) -> None:
        """Release this owner's claim after a submission failure."""


class RedisQuarkStudioTaskCache:
    """Redis cache for completed counts and in-flight QuarkStudio task claims.

    A result is reusable only for an identical canonical task key.  The key is
    built by :class:`QuarkStudioBatchExecutor` from QASM, backend settings,
    compiler options, and the measurement interpretation.  Redis' ``SET NX``
    claim prevents independent worker processes from submitting the same task
    concurrently; a lease keeps a crashed worker from blocking the key
    forever.
    """

    _SCHEMA_VERSION = 1
    _FLIGHT_SCHEMA_VERSION = 2

    def __init__(
        self, url: str, *, namespace: str = "qiskit-addon-cutting"
    ) -> None:
        if not url:
            raise ValueError("Redis cache URL must not be empty.")
        if not namespace:
            raise ValueError("Redis cache namespace must not be empty.")
        try:
            import redis
        except ImportError as error:
            raise RuntimeError(
                "Install the optional Redis client to enable QuarkStudio "
                "task caching: "
                "`python -m pip install redis`."
            ) from error
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._prefix = (
            f"{namespace}:quarkstudio-task-cache:v{self._SCHEMA_VERSION}"
        )
        self._owner = uuid.uuid4().hex

    def get_result(self, key: str) -> Mapping[str, int] | None:
        """Return validated completed counts for a cache key."""
        raw = self._client.get(self._result_key(key))
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
            counts = payload["counts"]
            if not isinstance(counts, dict) or not all(
                isinstance(bitstring, str) and isinstance(count, int)
                for bitstring, count in counts.items()
            ):
                raise ValueError("invalid counts payload")
        except (
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            raise RuntimeError(
                f"Invalid Redis result entry for QuarkStudio task key {key}."
            ) from error
        return counts

    def claim(self, key: str, lease_seconds: int) -> bool:
        """Claim a task key with Redis' atomic ``SET NX`` primitive."""
        payload = json.dumps(
            {"owner": self._owner, "task_id": None}, separators=(",", ":")
        )
        return bool(
            self._client.set(
                self._flight_key(key), payload, nx=True, ex=lease_seconds
            )
        )

    def record_task(self, key: str, task_id: str, lease_seconds: int) -> None:
        """Publish a task ID without overwriting another process' lease."""
        script = """
        local raw = redis.call('GET', KEYS[1])
        if not raw then return 0 end
        local entry = cjson.decode(raw)
        if entry.owner ~= ARGV[1] then return 0 end
        entry.task_id = ARGV[2]
        redis.call('SET', KEYS[1], cjson.encode(entry), 'XX', 'EX', ARGV[3])
        return 1
        """
        if not self._client.eval(
            script,
            1,
            self._flight_key(key),
            self._owner,
            task_id,
            lease_seconds,
        ):
            raise RuntimeError(
                "Lost the Redis task-submission lease before recording "
                "its task ID."
            )

    def task_id(self, key: str) -> str | None:
        """Return the task ID published by the submitting worker."""
        raw = self._client.get(self._flight_key(key))
        if raw is None:
            return None
        try:
            task_id = json.loads(raw).get("task_id")
        except (AttributeError, json.JSONDecodeError) as error:
            raise RuntimeError(
                "Invalid Redis in-flight entry for QuarkStudio task "
                f"key {key}."
            ) from error
        # QuarkStudio task IDs currently exceed the exact integer range of
        # Redis Lua's double-backed cjson numbers.  Preserve the identifier as
        # text from submission through URL construction.
        return None if task_id is None else str(task_id)

    def recover_task(self, key: str, task_id: str, lease_seconds: int) -> bool:
        """Take ownership of an expired remote task before replacing it.

        The compare-and-swap prevents two workers that observe the same
        vanished task result from submitting duplicate replacements.
        """
        script = """
        local raw = redis.call('GET', KEYS[1])
        if not raw then return 0 end
        local entry = cjson.decode(raw)
        if tostring(entry.task_id) ~= ARGV[2] then return 0 end
        entry.owner = ARGV[1]
        entry.task_id = cjson.null
        redis.call('SET', KEYS[1], cjson.encode(entry), 'XX', 'EX', ARGV[3])
        return 1
        """
        return bool(
            self._client.eval(
                script,
                1,
                self._flight_key(key),
                self._owner,
                task_id,
                lease_seconds,
            )
        )

    def complete(
        self, key: str, counts: Mapping[str, int], ttl_seconds: int
    ) -> None:
        """Persist counts, then release this owner's in-flight lease."""
        payload = json.dumps(
            {"counts": dict(counts)}, sort_keys=True, separators=(",", ":")
        )
        self._client.set(self._result_key(key), payload, ex=ttl_seconds)
        self._release_if_owner(key)

    def abandon(self, key: str) -> None:
        """Release a lease only when it still belongs to this worker."""
        self._release_if_owner(key)

    def _release_if_owner(self, key: str) -> None:
        script = """
        local raw = redis.call('GET', KEYS[1])
        if not raw then return 0 end
        local entry = cjson.decode(raw)
        if entry.owner ~= ARGV[1] then return 0 end
        return redis.call('DEL', KEYS[1])
        """
        self._client.eval(script, 1, self._flight_key(key), self._owner)

    def _result_key(self, key: str) -> str:
        return f"{self._prefix}:result:{key}"

    def _flight_key(self, key: str) -> str:
        # Version separately from completed results: v1 flight entries stored
        # task IDs as Lua JSON numbers and may already have lost precision.
        return f"{self._prefix}:flight:v{self._FLIGHT_SCHEMA_VERSION}:{key}"


@dataclass(frozen=True)
class _CachedTaskWork:
    """One canonical executable task and all logical experiments it serves."""

    key: str
    group: list
    qpd_cbits: tuple[int, ...]
    observable_cbits: dict[int, int]
    qasm: str
    label: str


class QuarkStudioBatchExecutor:
    """Submit compatible Z-basis fragment experiments once per QPD term."""

    _task_manager: Any
    _chip: str
    _shots: int
    _poll_interval: float
    _request_timeout: float
    _task_timeout: float | None
    _max_poll_errors: int
    _max_task_resubmissions: int
    _request_exception: Any
    _submitted: int
    _compiler: str
    _correct: bool
    _qiskit_optimization_level: int | None
    _hardware_profile: str | None
    _cache: QuarkStudioTaskCache | None
    _cache_ttl_seconds: int
    _cache_lease_seconds: int
    _cache_submission_lease_seconds: int
    _cache_hits: int

    def __init__(
        self,
        token: str,
        chip: str,
        shots: int,
        poll_interval: float,
        *,
        request_timeout: float = 60.0,
        task_timeout: float | None = 43_200.0,
        max_poll_errors: int = 100,
        max_task_resubmissions: int = 100,
        compiler: str = "quarkcircuit",
        correct: bool = False,
        qiskit_optimization_level: int | None = 3,
        hardware_profile: str | None = None,
        cache: QuarkStudioTaskCache | None = None,
        redis_url: str | None = None,
        cache_namespace: str = "qiskit-addon-cutting",
        cache_ttl_seconds: int = 86_400,
        cache_lease_seconds: int | None = None,
    ) -> None:
        if sys.version_info < (3, 12):
            raise RuntimeError(
                "The current QuarkStudio release requires Python 3.12+. "
                f"This interpreter is Python {sys.version.split()[0]}."
            )
        try:
            from quark import Task
            from requests import RequestException
        except ImportError as error:
            raise RuntimeError(
                "Install QuarkStudio in this Python 3.12+ environment: "
                "`python -m pip install -U quarkstudio`."
            ) from error
        if poll_interval < 0:
            raise ValueError("poll_interval must be non-negative.")
        if request_timeout <= 0:
            raise ValueError("request_timeout must be positive.")
        if task_timeout is not None and task_timeout <= 0:
            raise ValueError("task_timeout must be positive or None.")
        if max_poll_errors < 1:
            raise ValueError("max_poll_errors must be positive.")
        if max_task_resubmissions < 0:
            raise ValueError("max_task_resubmissions must be non-negative.")
        if not compiler:
            raise ValueError("compiler must not be empty.")
        if qiskit_optimization_level not in {None, 0, 1, 2, 3}:
            raise ValueError(
                "qiskit_optimization_level must be None or an integer "
                "from 0 through 3."
            )
        if hardware_profile not in {None, "shenglian"}:
            raise ValueError("hardware_profile must be None or 'shenglian'.")
        if cache is not None and redis_url is not None:
            raise ValueError("Pass either cache or redis_url, not both.")
        if cache_ttl_seconds < 1:
            raise ValueError("cache_ttl_seconds must be positive.")
        if cache_lease_seconds is not None and cache_lease_seconds < 1:
            raise ValueError(
                "cache_lease_seconds must be positive when provided."
            )
        self._task_manager = Task(token)
        self._chip = chip
        self._shots = shots
        self._poll_interval = poll_interval
        self._request_timeout = request_timeout
        self._task_timeout = task_timeout
        self._max_poll_errors = max_poll_errors
        self._max_task_resubmissions = max_task_resubmissions
        self._request_exception = RequestException
        self._submitted = 0
        self._compiler = compiler
        self._correct = correct
        self._qiskit_optimization_level = qiskit_optimization_level
        self._hardware_profile = hardware_profile
        self._cache = (
            RedisQuarkStudioTaskCache(redis_url, namespace=cache_namespace)
            if redis_url is not None
            else cache
        )
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache_lease_seconds = cache_lease_seconds or int(
            (task_timeout if task_timeout is not None else 7200.0) + 120
        )
        # A claim without a task ID is only needed until submission finishes.
        # Keeping it for the full task lifetime turns a process crash between
        # ``claim`` and ``record_task`` into an hours-long cache deadlock.
        self._cache_submission_lease_seconds = min(
            self._cache_lease_seconds,
            max(120, int(math.ceil(request_timeout)) + 60),
        )
        self._cache_hits = 0

    @property
    def submitted_tasks(self) -> int:
        """Return the submitted QuarkStudio task count."""
        return self._submitted

    @property
    def cache_hits(self) -> int:
        """Return the completed-cache hit count."""
        return self._cache_hits

    def execute_openqasm2_counts(
        self, qasm: str, *, name: str = "full-circuit-sampling"
    ) -> Mapping[str, int]:
        """Run one complete OpenQASM 2 circuit and return its raw counts.

        This is the companion to :meth:`execute` for workflows that need
        full-circuit computational-basis samples after a wire-cut objective
        optimization.  It intentionally does not apply QPD reconstruction or
        cache interpretation: callers receive the hardware count map exactly
        as QuarkStudio returned it.
        """
        if not qasm.strip():
            raise ValueError("OpenQASM program must not be empty.")
        task_id = self._submit(qasm, name, 1, 1)
        result = self._await_result(task_id, time.monotonic())
        if result.get("status") != "Finished" or "count" not in result:
            raise RuntimeError(
                f"QuarkStudio task {task_id} did not return counts: {result}"
            )
        counts = result["count"]
        if not isinstance(counts, Mapping) or not all(
            isinstance(bitstring, str) and isinstance(count, int)
            for bitstring, count in counts.items()
        ):
            raise RuntimeError(
                f"QuarkStudio task {task_id} returned invalid "
                f"counts: {counts!r}"
            )
        return dict(counts)

    def execute_qiskit_sampler_experiments(
        self,
        experiments: Mapping[Hashable, Sequence],
        *,
        name_prefix: str = "gate-cut",
        max_in_flight: int = 32,
    ) -> Mapping[Hashable, object]:
        """Execute partitioned addon-cutting circuits as SamplerV1 results.

        This is the QuarkStudio execution bridge for the vendored upstream
        ``generate_cutting_experiments`` workflow.  Structurally identical
        circuits are submitted once and their counts are reused in every
        original result position.  Qiskit's reconstruction still receives
        one ordered result entry per logical subexperiment.

        The imports remain local so the native wire-cut workflow does not
        require Qiskit merely to import this module.  At least one transpiler
        pass is always used to lower RZZ and the local QPD maps to OpenQASM 2
        ``u3``/``cx`` operations understood by QuarkStudio.
        """
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
        except ImportError as error:
            raise RuntimeError(
                "Qiskit is required to execute upstream cutting experiments."
            ) from error

        positions_by_signature: dict[tuple, list[tuple[Hashable, int]]] = (
            defaultdict(list)
        )
        circuit_by_signature: dict[tuple, Any] = {}
        result_slots: dict[Hashable, list[object | None]] = {
            label: [None] * len(circuits)
            for label, circuits in experiments.items()
        }
        for label, circuits in experiments.items():
            for index, circuit in enumerate(circuits):
                signature = _qiskit_circuit_signature(circuit)
                positions_by_signature[signature].append((label, index))
                circuit_by_signature.setdefault(signature, circuit)

        # Canonical register names let isomorphic fragments from different
        # partitions share one physical execution when their operations and
        # classical-bit layout are otherwise identical.
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

        optimization_level = getattr(self, "_qiskit_optimization_level", 3)
        optimization_level = (
            0 if optimization_level is None else optimization_level
        )
        hardware_profile = getattr(self, "_hardware_profile", None)
        transpile_options = {
            "optimization_level": optimization_level,
            "seed_transpiler": 42,
            "num_processes": 1,
        }
        if hardware_profile == "shenglian":
            try:
                from qiskit.transpiler import CouplingMap
            except (
                ImportError
            ) as error:  # pragma: no cover - same Qiskit import above
                raise RuntimeError(
                    "Qiskit transpiler support is unavailable."
                ) from error
            transpile_options.update(
                basis_gates=("h", "rx", "ry", "rz", "cz"),
                coupling_map=CouplingMap(_shenglian_coupling_edges()),
                layout_method="sabre",
                routing_method="sabre",
            )
        else:
            transpile_options["basis_gates"] = ("u3", "cx")
        compiled = transpile(canonical_circuits, **transpile_options)

        # Transpilation can make two distinct input circuits identical.  Fold
        # them a second time before submitting any remote task.
        signatures_by_qasm: dict[str, list[tuple]] = defaultdict(list)
        for signature, circuit in zip(signatures, compiled, strict=True):
            signatures_by_qasm[qasm2.dumps(circuit)].append(signature)

        qasms = list(signatures_by_qasm)
        print(
            f"Prepared {sum(len(v) for v in experiments.values())} logical "
            f"subexperiments as {len(qasms)} unique QuarkStudio task(s)."
        )
        counts_by_qasm: dict[str, Mapping[str, int]] = {}
        total = len(qasms)

        def validated_counts(
            task_id: str, result: Mapping
        ) -> Mapping[str, int]:
            if result.get("status") != "Finished" or "count" not in result:
                raise RuntimeError(
                    f"QuarkStudio task {task_id} did not return counts: "
                    f"{result}"
                )
            counts = result["count"]
            if not isinstance(counts, Mapping) or not all(
                isinstance(bitstring, str) and isinstance(count, int)
                for bitstring, count in counts.items()
            ):
                raise RuntimeError(
                    f"QuarkStudio task {task_id} returned invalid "
                    f"counts: {counts!r}"
                )
            return dict(counts)

        cache = getattr(self, "_cache", None)
        if cache is not None:
            counts_by_qasm = self._execute_cached_qiskit_sampler_qasms(
                qasms,
                cache=cache,
                name_prefix=name_prefix,
                max_in_flight=max_in_flight,
                validated_counts=validated_counts,
            )
        else:
            # Confirm one representative circuit before opening a full
            # concurrent submission window. A bad compiler/profile combination
            # then consumes
            # one remote task instead of an entire ``max_in_flight`` chunk.
            first_qasm = qasms[0]
            first_task_id = self._submit(
                first_qasm, f"{name_prefix}-1", 1, total
            )
            first_result = self._await_result(first_task_id, time.monotonic())
            counts_by_qasm[first_qasm] = validated_counts(
                first_task_id, first_result
            )
            if total > 1:
                print(
                    "QuarkStudio canary task succeeded; submitting remaining "
                    f"{total - 1} task(s)."
                )

            for start in range(1, total, max_in_flight):
                chunk = qasms[start : start + max_in_flight]
                pending: dict[str, tuple[str, float]] = {}
                for offset, qasm in enumerate(chunk, start=start + 1):
                    task_id = self._submit(
                        qasm, f"{name_prefix}-{offset}", offset, total
                    )
                    pending[task_id] = (qasm, time.monotonic())
                with ThreadPoolExecutor(
                    max_workers=len(pending),
                    thread_name_prefix="quark-sampler-result",
                ) as pool:
                    futures = {
                        pool.submit(
                            self._await_result, task_id, submitted_at
                        ): task_id
                        for task_id, (_, submitted_at) in pending.items()
                    }
                    for future in futures:
                        task_id = futures[future]
                        result = future.result()
                        counts_by_qasm[pending[task_id][0]] = validated_counts(
                            task_id, result
                        )

        for qasm, equivalent_signatures in signatures_by_qasm.items():
            quasi = _counts_to_quasi_distribution(counts_by_qasm[qasm])
            for signature in equivalent_signatures:
                for label, index in positions_by_signature[signature]:
                    result_slots[label][index] = quasi

        results = {}
        for label, slots in result_slots.items():
            if any(
                slot is None for slot in slots
            ):  # pragma: no cover - defensive invariant
                raise AssertionError(
                    f"Missing QuarkStudio result in partition {label!r}."
                )
            results[label] = SamplerResult(
                quasi_dists=list(slots),
                metadata=[{"shots": self._shots} for _ in slots],
            )
        return results

    def _execute_cached_qiskit_sampler_qasms(
        self,
        qasms: Sequence[str],
        *,
        cache: QuarkStudioTaskCache,
        name_prefix: str,
        max_in_flight: int,
        validated_counts,
    ) -> dict[str, Mapping[str, int]]:
        """Reuse completed or in-flight sampler tasks across VQE processes.

        The cache is applied after structural and transpiled-QASM
        deduplication,
        so each key represents one actual remote measurement.  No result from
        a different shot count or execution configuration is interchangeable.
        """
        counts_by_qasm: dict[str, Mapping[str, int]] = {}
        missing: list[tuple[int, str, str]] = []
        hits_before = self._cache_hits
        submissions_before = self._submitted
        attached = 0
        for position, qasm in enumerate(qasms, start=1):
            key = self._qiskit_sampler_task_cache_key(qasm)
            counts = cache.get_result(key)
            if counts is None:
                missing.append((position, qasm, key))
            else:
                counts_by_qasm[qasm] = counts
                self._cache_hits += 1

        print(
            f"QuarkStudio sampler cache: {self._cache_hits - hits_before} "
            f"completed hit(s), {len(missing)} task(s) to resolve."
        )
        if not missing:
            return counts_by_qasm

        def prepare(
            position: int, qasm: str, key: str
        ) -> tuple[str | None, float]:
            """Submit a claim or attach to another worker's task."""
            nonlocal attached
            started = time.monotonic()
            deadline = (
                None
                if self._task_timeout is None
                else started + self._task_timeout
            )
            while True:
                counts = cache.get_result(key)
                if counts is not None:
                    counts_by_qasm[qasm] = counts
                    self._cache_hits += 1
                    return None, time.monotonic()
                if cache.claim(key, self._cache_submission_lease_seconds):
                    try:
                        # A previous owner may have published the result just
                        # before its lease disappeared.  Recheck after claiming
                        # so this race does not create a duplicate remote job.
                        counts = cache.get_result(key)
                        if counts is not None:
                            cache.abandon(key)
                            counts_by_qasm[qasm] = counts
                            self._cache_hits += 1
                            return None, time.monotonic()
                        task_id = self._submit(
                            qasm,
                            f"{name_prefix}-{position}",
                            position,
                            len(qasms),
                        )
                        cache.record_task(
                            key, task_id, self._cache_lease_seconds
                        )
                    except Exception:
                        cache.abandon(key)
                        raise
                    return task_id, time.monotonic()
                cached_task_id = cache.task_id(key)
                if cached_task_id is not None:
                    attached += 1
                    return cached_task_id, time.monotonic()
                if deadline is not None and time.monotonic() >= deadline:
                    raise TimeoutError(
                        "Redis task claim for sampler circuit "
                        f"{position} did not publish a task ID."
                    )
                time.sleep(max(self._poll_interval, 0.05))

        def finish(
            qasm: str, key: str, task_id: str, submitted_at: float
        ) -> None:
            try:
                result = self._await_result(task_id, submitted_at)
                counts = validated_counts(task_id, result)
                cache.complete(key, counts, self._cache_ttl_seconds)
            except TimeoutError:
                # A local wait limit does not mean the remote task stopped.
                # Keep its recorded ID so a resumed process can attach to it.
                raise
            except Exception:
                cache.abandon(key)
                raise
            counts_by_qasm[qasm] = counts

        # Keep the compiler/profile canary on the first uncached circuit.
        position, qasm, key = missing[0]
        task_id, submitted_at = prepare(position, qasm, key)
        if task_id is not None:
            finish(qasm, key, task_id, submitted_at)
        if len(missing) > 1:
            print(
                "QuarkStudio canary task succeeded or was cached; resolving "
                f"remaining {len(missing) - 1} task(s)."
            )

        for start in range(1, len(missing), max_in_flight):
            chunk = missing[start : start + max_in_flight]
            pending: list[tuple[str, str, str, float]] = []
            for position, qasm, key in chunk:
                task_id, submitted_at = prepare(position, qasm, key)
                if task_id is not None:
                    pending.append((qasm, key, task_id, submitted_at))
            if pending:
                with ThreadPoolExecutor(
                    max_workers=len(pending),
                    thread_name_prefix="quark-sampler-result",
                ) as pool:
                    futures = [
                        pool.submit(self._await_result, task_id, submitted_at)
                        for _, _, task_id, submitted_at in pending
                    ]
                    first_error: Exception | None = None
                    for (qasm, key, task_id, _), future in zip(
                        pending, futures, strict=True
                    ):
                        try:
                            validated_task_counts = validated_counts(
                                task_id, future.result()
                            )
                            cache.complete(
                                key,
                                validated_task_counts,
                                self._cache_ttl_seconds,
                            )
                        except TimeoutError as error:
                            # Preserve the in-flight task for the next resume.
                            if first_error is None:
                                first_error = error
                        except Exception as error:
                            cache.abandon(key)
                            if first_error is None:
                                first_error = error
                        else:
                            counts_by_qasm[qasm] = validated_task_counts
                    if first_error is not None:
                        raise first_error

        print(
            f"QuarkStudio sampler cache resolved {len(qasms)} unique task(s): "
            f"{self._cache_hits - hits_before} completed hit(s), "
            f"{self._submitted - submissions_before} new submission(s), "
            f"{attached} in-flight attachment(s)."
        )
        return counts_by_qasm

    def _qiskit_sampler_task_cache_key(self, qasm: str) -> str:
        """Identify a sampler task without mixing measurement modes."""
        canonical_task = {
            "schema": 1,
            "mode": "qiskit-sampler-counts",
            "qasm": qasm,
            "chip": self._chip,
            "shots": self._shots,
            "options": {
                "compiler": getattr(self, "_compiler", "quarkcircuit"),
                "correct": getattr(self, "_correct", False),
            },
            "compile": getattr(self, "_hardware_profile", None) is None,
        }
        serialized = json.dumps(
            canonical_task, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def execute(
        self, batch: CuttingExperimentBatch
    ) -> CuttingExperimentResults:
        """Submit all all-Z jobs first, then poll their results together."""
        cache = getattr(self, "_cache", None)
        if cache is not None:
            return self._execute_with_cache(batch, cache)
        groups: dict[tuple[int, int], list] = defaultdict(list)
        for experiment in batch.experiments:
            groups[(experiment.term_index, experiment.fragment_label)].append(
                experiment
            )

        pending: dict[
            str, tuple[list, tuple[int, ...], dict[int, int], str, str]
        ] = {}
        submitted_at: dict[str, float] = {}
        resubmissions: dict[tuple[int, int], int] = defaultdict(int)
        total_jobs = len(groups)
        for position, ((term_index, fragment_label), group) in enumerate(
            sorted(groups.items()), start=1
        ):
            fragment_experiment = group[0].fragment_experiment
            if any(
                item.fragment_experiment != fragment_experiment
                for item in group
            ):
                raise ValueError(
                    "Inconsistent fragment data in an experiment group."
                )
            merged_observable = _merge_z_observables(
                item.observable for item in group
            )
            qasm, qpd_cbits, observable_cbits = _fragment_to_openqasm2(
                fragment_experiment,
                merged_observable,
                qiskit_optimization_level=self._qiskit_optimization_level,
                hardware_profile=self._hardware_profile,
            )
            task_id = self._submit(
                qasm,
                f"wire-cut-maxcut-t{term_index}-f{fragment_label}",
                position,
                total_jobs,
            )
            pending[task_id] = (
                group,
                qpd_cbits,
                observable_cbits,
                qasm,
                f"t{term_index}-f{fragment_label}",
            )
            submitted_at[task_id] = time.monotonic()

        print(
            f"All {total_jobs} QuarkStudio tasks submitted; awaiting "
            "results independently."
        )
        values: dict[tuple[int, int, int], float] = {}
        completed = 0
        with ThreadPoolExecutor(
            max_workers=max(1, len(pending)), thread_name_prefix="quark-result"
        ) as pool:
            futures = {
                pool.submit(
                    self._await_result, task_id, submitted_at[task_id]
                ): task_id
                for task_id in pending
            }
            while futures:
                done, _ = wait(
                    futures, timeout=60.0, return_when=FIRST_COMPLETED
                )
                if not done:
                    future_count = len(futures)
                    print(
                        f"Still awaiting {future_count} QuarkStudio task "
                        "result(s)."
                    )
                    continue
                for future in done:
                    task_id = futures.pop(future)
                    group, qpd_cbits, observable_cbits, qasm, label = pending[
                        task_id
                    ]
                    try:
                        result = future.result()
                    except _UnavailableQuarkStudioTaskError as error:
                        result = {"status": "Expired", "error": str(error)}
                    status = result.get("status")
                    if status == "Finished":
                        counts = result["count"]
                        for experiment in group:
                            local_cbits = tuple(
                                observable_cbits[qubit]
                                for qubit in experiment.observable
                            )
                            values[
                                (
                                    experiment.term_index,
                                    experiment.observable_index,
                                    experiment.fragment_label,
                                )
                            ] = _counts_to_weighted_expectation(
                                counts, qpd_cbits, local_cbits
                            )
                        del pending[task_id]
                        del submitted_at[task_id]
                        completed += 1
                        print(
                            f"QuarkStudio task {task_id} finished "
                            f"({completed}/{total_jobs})."
                        )
                        continue
                    if status not in {
                        "Failed",
                        "Canceled",
                        "Cancelled",
                        "Expired",
                    } and not result.get("error"):
                        raise RuntimeError(
                            "Unexpected terminal response for QuarkStudio "
                            f"task {task_id}: {result}"
                        )
                    group_key = (group[0].term_index, group[0].fragment_label)
                    resubmissions[group_key] += 1
                    max_task_resubmissions = getattr(
                        self, "_max_task_resubmissions", 20
                    )
                    if resubmissions[group_key] > max_task_resubmissions:
                        raise RuntimeError(
                            f"QuarkStudio task {task_id} for {label} failed "
                            f"after {resubmissions[group_key]} recovery "
                            f"submissions: {result}"
                        )
                    print(
                        f"QuarkStudio task {task_id} for {label} failed "
                        f"({result.get('error') or status!r}); resubmitting "
                        f"({resubmissions[group_key]}/{max_task_resubmissions}).\n"
                        "QuarkStudio failure response: "
                        f"{_failure_response(result)}"
                    )
                    del pending[task_id]
                    del submitted_at[task_id]
                    replacement_id = self._submit(
                        qasm,
                        f"wire-cut-maxcut-{label}-retry"
                        f"{resubmissions[group_key]}",
                        completed + 1,
                        total_jobs,
                    )
                    pending[replacement_id] = (
                        group,
                        qpd_cbits,
                        observable_cbits,
                        qasm,
                        label,
                    )
                    submitted_at[replacement_id] = time.monotonic()
                    futures[
                        pool.submit(
                            self._await_result,
                            replacement_id,
                            submitted_at[replacement_id],
                        )
                    ] = replacement_id

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

    def _execute_with_cache(
        self, batch: CuttingExperimentBatch, cache: QuarkStudioTaskCache
    ) -> CuttingExperimentResults:
        """Execute a batch while reusing completed counts and in-flight tasks.

        The cache key denotes the complete executable task, not merely a
        fragment: it includes QASM, backend options, and the cbit mapping used
        to interpret returned counts.  Workers sharing an account namespace can
        poll one another's recorded task ID instead of submitting duplicates.
        """
        groups: dict[tuple[int, int], list] = defaultdict(list)
        for experiment in batch.experiments:
            groups[(experiment.term_index, experiment.fragment_label)].append(
                experiment
            )

        works_by_key: dict[str, list[_CachedTaskWork]] = defaultdict(list)
        for (term_index, fragment_label), group in sorted(groups.items()):
            fragment_experiment = group[0].fragment_experiment
            if any(
                item.fragment_experiment != fragment_experiment
                for item in group
            ):
                raise ValueError(
                    "Inconsistent fragment data in an experiment group."
                )
            merged_observable = _merge_z_observables(
                item.observable for item in group
            )
            qasm, qpd_cbits, observable_cbits = _fragment_to_openqasm2(
                fragment_experiment,
                merged_observable,
                qiskit_optimization_level=self._qiskit_optimization_level,
                hardware_profile=self._hardware_profile,
            )
            work = _CachedTaskWork(
                self._task_cache_key(qasm, qpd_cbits, observable_cbits),
                group,
                qpd_cbits,
                observable_cbits,
                qasm,
                f"t{term_index}-f{fragment_label}",
            )
            works_by_key[work.key].append(work)

        values: dict[tuple[int, int, int], float] = {}
        pending: dict[str, tuple[str, list[_CachedTaskWork], float]] = {}
        waiting: dict[str, list[_CachedTaskWork]] = {}
        completed = 0
        total_work = sum(len(works) for works in works_by_key.values())
        positions = {
            key: position for position, key in enumerate(works_by_key, start=1)
        }
        for key, works in works_by_key.items():
            counts = cache.get_result(key)
            if counts is not None:
                self._cache_hits += 1
                self._store_counts(values, works, counts)
                completed += len(works)
                continue
            if cache.claim(key, self._cache_submission_lease_seconds):
                try:
                    task_id = self._submit(
                        works[0].qasm,
                        f"wire-cut-maxcut-{works[0].label}",
                        positions[key],
                        len(works_by_key),
                    )
                    cache.record_task(key, task_id, self._cache_lease_seconds)
                except Exception:
                    cache.abandon(key)
                    raise
                pending[task_id] = (key, works, time.monotonic())
            else:
                waiting[key] = works

        print(
            f"QuarkStudio cache: {self._cache_hits} completed hit(s), "
            f"{len(pending)} new submission(s), "
            f"{len(waiting)} in-flight wait(s)."
        )
        if pending:
            print(
                f"Polling {len(pending)} newly submitted QuarkStudio task(s)."
            )

        resubmissions: dict[str, int] = defaultdict(int)
        with ThreadPoolExecutor(
            max_workers=max(1, len(works_by_key)),
            thread_name_prefix="quark-result",
        ) as pool:
            futures = {
                pool.submit(self._await_result, task_id, submitted_at): task_id
                for task_id, (_, _, submitted_at) in pending.items()
            }
            while futures or waiting:
                for key, works in tuple(waiting.items()):
                    counts = cache.get_result(key)
                    if counts is not None:
                        self._cache_hits += 1
                        self._store_counts(values, works, counts)
                        del waiting[key]
                        completed += len(works)
                        continue
                    cached_task_id = cache.task_id(key)
                    if cached_task_id is None and cache.claim(
                        key, self._cache_submission_lease_seconds
                    ):
                        try:
                            cached_task_id = self._submit(
                                works[0].qasm,
                                f"wire-cut-maxcut-{works[0].label}",
                                positions[key],
                                len(works_by_key),
                            )
                            cache.record_task(
                                key,
                                cached_task_id,
                                self._cache_lease_seconds,
                            )
                        except Exception:
                            cache.abandon(key)
                            raise
                    if cached_task_id is not None:
                        submitted_at = time.monotonic()
                        pending[cached_task_id] = (
                            key,
                            works,
                            submitted_at,
                        )
                        futures[
                            pool.submit(
                                self._await_result,
                                cached_task_id,
                                submitted_at,
                            )
                        ] = cached_task_id
                        del waiting[key]

                if not futures:
                    print(f"Still waiting for {len(waiting)} Redis claim(s).")
                    time.sleep(self._poll_interval)
                    continue
                done, _ = wait(
                    futures, timeout=60.0, return_when=FIRST_COMPLETED
                )
                if not done:
                    future_count = len(futures)
                    waiting_count = len(waiting)
                    print(
                        f"Still awaiting {future_count} task result(s) and "
                        f"{waiting_count} Redis claim(s)."
                    )
                    continue
                for future in done:
                    task_id = futures.pop(future)
                    key, works, _ = pending[task_id]
                    try:
                        result = future.result()
                    except _UnavailableQuarkStudioTaskError as error:
                        result = {"status": "Expired", "error": str(error)}
                    status = result.get("status")
                    if status == "Finished":
                        finished_counts = cast(
                            Mapping[str, int], result["count"]
                        )
                        cache.complete(
                            key,
                            finished_counts,
                            self._cache_ttl_seconds,
                        )
                        self._store_counts(values, works, finished_counts)
                        del pending[task_id]
                        completed += len(works)
                        print(
                            f"QuarkStudio task {task_id} finished "
                            f"(cached work {completed}/{total_work})."
                        )
                        continue
                    if status not in {
                        "Failed",
                        "Canceled",
                        "Cancelled",
                        "Expired",
                    } and not result.get("error"):
                        raise RuntimeError(
                            "Unexpected terminal response for QuarkStudio "
                            f"task {task_id}: {result}"
                        )
                    resubmissions[key] += 1
                    work_label = works[0].label
                    if resubmissions[key] > self._max_task_resubmissions:
                        cache.abandon(key)
                        raise RuntimeError(
                            f"QuarkStudio task {task_id} for {work_label} "
                            "failed after "
                            f"{resubmissions[key]} recovery submissions: "
                            f"{result}"
                        )
                    if not cache.recover_task(
                        key, task_id, self._cache_submission_lease_seconds
                    ):
                        del pending[task_id]
                        waiting[key] = works
                        continue
                    print(
                        f"QuarkStudio task {task_id} for {work_label} failed "
                        f"({result.get('error') or status!r}); resubmitting "
                        f"({resubmissions[key]}/{self._max_task_resubmissions}).\n"
                        "QuarkStudio failure response: "
                        f"{_failure_response(result)}"
                    )
                    replacement_id = self._submit(
                        works[0].qasm,
                        f"wire-cut-maxcut-{works[0].label}-retry{resubmissions[key]}",
                        positions[key],
                        len(works_by_key),
                    )
                    cache.record_task(
                        key, replacement_id, self._cache_lease_seconds
                    )
                    del pending[task_id]
                    submitted_at = time.monotonic()
                    pending[replacement_id] = (key, works, submitted_at)
                    futures[
                        pool.submit(
                            self._await_result, replacement_id, submitted_at
                        )
                    ] = replacement_id

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

    def _result_with_timeout(self, task_id: str) -> dict:
        """Fetch one result with a bounded HTTP call.

        ``quark.Task.result`` delegates to ``requests.Session.get`` without a
        timeout.  A stalled TCP connection therefore blocks the whole batch
        forever.  The SDK exposes the session, endpoint, and token needed for
        the same request, so use those with a bounded timeout here.
        """
        manager = self._task_manager
        session = getattr(manager, "session", None)
        url = getattr(manager, "URL", None)
        token = getattr(manager, "token", None)
        if session is None or url is None or token is None:
            # This branch keeps lightweight test doubles and compatible SDK
            # implementations usable.  QuarkStudio's current SDK always
            # takes the bounded branch above.
            return manager.result(int(task_id))
        try:
            response = session.get(
                f"{url}/task/result/{task_id}",
                headers={"token": token},
                timeout=getattr(self, "_request_timeout", 60.0),
            )
            if response.status_code in {404, 410}:
                raise _UnavailableQuarkStudioTaskError(
                    f"QuarkStudio task {task_id} is no longer available "
                    f"(HTTP {response.status_code})."
                )
            response.raise_for_status()
            result = response.json()
        except (
            Exception
        ) as error:  # The exception class is optional at import time.
            request_exception = getattr(self, "_request_exception", ())
            if isinstance(error, request_exception):
                raise _RetryableQuarkStudioRequestError(str(error)) from error
            raise
        if not isinstance(result, dict):
            raise _RetryableQuarkStudioRequestError(
                f"unexpected result payload type {type(result).__name__}"
            )
        if _result_indicates_unavailable_task(result):
            raise _UnavailableQuarkStudioTaskError(
                f"QuarkStudio task {task_id} returned no retrievable result."
            )
        return result

    def _await_result(self, task_id: str, submitted_at: float) -> dict:
        """Wait independently for one submitted task's terminal result.

        The official non-blocking submission model returns a task ID first;
        an empty result payload merely means that this task is still running.
        This worker therefore never resubmits an empty/``Transpiling`` result.
        It returns only a finished count payload or an explicit terminal
        failure, allowing the coordinating thread to cache each completion as
        soon as it arrives.
        """
        poll_errors = 0
        in_progress = {
            "submitted",
            "pending",
            "queued",
            "compiling",
            "transpiling",
            "running",
        }
        while True:
            task_timeout = self._task_timeout
            if (
                task_timeout is not None
                and time.monotonic() - submitted_at > task_timeout
            ):
                raise TimeoutError(
                    f"QuarkStudio task {task_id} did not finish "
                    f"within {task_timeout:g} seconds."
                )
            try:
                result = self._result_with_timeout(task_id)
            except _RetryableQuarkStudioRequestError:
                poll_errors += 1
                if poll_errors >= self._max_poll_errors:
                    raise
                time.sleep(self._poll_interval)
                continue
            if not result:
                time.sleep(self._poll_interval)
                continue
            status = result.get("status")
            if isinstance(status, str) and status.casefold() in in_progress:
                time.sleep(self._poll_interval)
                continue
            if status == "Finished" and "count" not in result:
                time.sleep(self._poll_interval)
                continue
            return result

    def _store_counts(
        self,
        values: dict[tuple[int, int, int], float],
        works: Iterable[_CachedTaskWork],
        counts: Mapping[str, int],
    ) -> None:
        """Convert cached counts into every served local value."""
        for work in works:
            for experiment in work.group:
                local_cbits = tuple(
                    work.observable_cbits[qubit]
                    for qubit in experiment.observable
                )
                values[
                    (
                        experiment.term_index,
                        experiment.observable_index,
                        experiment.fragment_label,
                    )
                ] = _counts_to_weighted_expectation(
                    counts, work.qpd_cbits, local_cbits
                )

    def _task_cache_key(
        self,
        qasm: str,
        qpd_cbits: tuple[int, ...],
        observable_cbits: Mapping[int, int],
    ) -> str:
        """Hash settings that affect reusable raw measurement counts."""
        canonical_task = {
            "schema": 1,
            "qasm": qasm,
            "chip": self._chip,
            "shots": self._shots,
            "options": {
                "compiler": getattr(self, "_compiler", "quarkcircuit"),
                "correct": getattr(self, "_correct", False),
            },
            "compile": getattr(self, "_hardware_profile", None) is None,
            "qpd_cbits": qpd_cbits,
            "observable_cbits": sorted(observable_cbits.items()),
        }
        serialized = json.dumps(
            canonical_task, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _submit(self, qasm: str, name: str, position: int, total: int) -> str:
        """Submit a task without waiting for its result.

        Submission requests are retried on transient transport errors the
        same way result polls are.  A retry may duplicate a task the server
        actually accepted before the response was lost, but the duplicate
        runs under the same unique name and its result is simply ignored.
        """
        self._submitted += 1
        print(f"Submitting fragment job {position}/{total}: {name}")
        request = {
            "chip": self._chip,
            "name": name,
            "circuit": qasm,
            "shots": self._shots,
            # A hardware-profile QASM has already been laid out, routed,
            # and lowered to the device basis.  Recompiling it on the
            # service would discard that physical-qubit assignment.
            "compile": getattr(self, "_hardware_profile", None) is None,
            "options": {
                "compiler": getattr(self, "_compiler", "quarkcircuit"),
                "correct": getattr(self, "_correct", False),
            },
        }
        max_attempts = max(1, getattr(self, "_max_poll_errors", 1))
        for attempt in range(1, max_attempts + 1):
            try:
                task_id = str(self._task_manager.run(request))
                break
            except Exception as error:
                request_exception = getattr(self, "_request_exception", ())
                if not isinstance(error, request_exception):
                    raise
                if attempt >= max_attempts:
                    raise
                delay = min(
                    getattr(self, "_poll_interval", 5.0)
                    * (2 ** (attempt - 1)),
                    60.0,
                )
                print(
                    f"QuarkStudio submission failed ({error}); retrying "
                    f"attempt {attempt + 1}/{max_attempts} in {delay:g}s."
                )
                time.sleep(delay)
        print(f"QuarkStudio task ID: {task_id}")
        return task_id


def _merge_z_observables(
    observables: Iterable[Mapping[int, str]],
) -> dict[int, str]:
    merged: dict[int, str] = {}
    for observable in observables:
        for qubit, pauli in observable.items():
            if pauli != "Z":
                raise ValueError(
                    "The batched MaxCut executor only supports Z-basis "
                    "observables."
                )
            if qubit in merged and merged[qubit] != pauli:
                raise ValueError(
                    "Incompatible measurement bases in one fragment batch."
                )
            merged[qubit] = pauli
    return merged


def _fragment_to_openqasm2(
    experiment: FragmentExperiment,
    observable: Mapping[int, str],
    *,
    qiskit_optimization_level: int | None = 3,
    hardware_profile: str | None = None,
) -> tuple[str, tuple[int, ...], dict[int, int]]:
    """Serialize and optimize a fragment plus QPD measurements to OpenQASM 2.

    The circuit-cutting plan is already fixed when this function is called.
    Qiskit therefore optimizes only the independently executable fragment,
    including its preparation and measurement-basis changes, and cannot alter
    the cuts, QPD coefficients, or classical-bit interpretation.  ``None``
    disables this final transpilation pass for controlled comparisons.
    """
    if qiskit_optimization_level not in {None, 0, 1, 2, 3}:
        raise ValueError(
            "qiskit_optimization_level must be None or an integer from 0 "
            "through 3."
        )
    if hardware_profile not in {None, "shenglian"}:
        raise ValueError("hardware_profile must be None or 'shenglian'.")
    fragment = experiment.fragment
    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        "gate standalone_rzz(theta) a,b { cx a,b; rz(theta) b; cx a,b; }",
        f"qreg q[{fragment.num_qubits}];",
    ]
    for qubit, state in sorted(experiment.preparations.items()):
        lines.extend(_prepare_state_qasm(qubit, state))
    for operation in fragment.operations:
        lines.extend(_operation_to_qasm(operation))

    qpd_items = tuple(sorted(experiment.terminal_measurements.items()))
    observable_qubits = tuple(
        sorted(qubit for qubit, pauli in observable.items() if pauli == "Z")
    )
    measured_qubits = {qubit for qubit, _ in qpd_items} | set(
        observable_qubits
    )
    unused_qubits = tuple(
        qubit
        for qubit in range(fragment.num_qubits)
        if qubit not in measured_qubits
    )
    measurement_count = (
        len(qpd_items) + len(observable_qubits) + len(unused_qubits)
    )
    lines.append(f"creg c[{max(1, measurement_count)}];")
    for cbit, (qubit, axis) in enumerate(qpd_items):
        lines.extend(_qpd_measurement_qasm(qubit, axis, cbit))
    qpd_cbits = tuple(range(len(qpd_items)))
    observable_cbits: dict[int, int] = {}
    for cbit, qubit in enumerate(observable_qubits, start=len(qpd_items)):
        lines.append(f"measure q[{qubit}] -> c[{cbit}];")
        observable_cbits[qubit] = cbit
    for cbit, qubit in enumerate(
        unused_qubits, start=len(qpd_items) + len(observable_qubits)
    ):
        lines.append(f"measure q[{qubit}] -> c[{cbit}];")
    qasm = "\n".join(lines)
    return (
        _optimize_openqasm2(qasm, qiskit_optimization_level, hardware_profile),
        qpd_cbits,
        observable_cbits,
    )


def _optimize_openqasm2(
    qasm: str,
    optimization_level: int | None,
    hardware_profile: str | None = None,
) -> str:
    """Resynthesize and optionally map an executable fragment with Qiskit.

    ``hardware_profile='shenglian'`` uses the 84-qubit diamond-lattice
    coupling graph and the native ``h/rx/ry/rz/cz`` gate family transcribed
    from the supplied Shenglian hardware view.  The resulting QASM uses the
    physical qubit indexes directly and must be submitted with
    ``compile=False``.
    """
    if optimization_level is None:
        if hardware_profile is not None:
            raise ValueError(
                "A hardware profile requires Qiskit optimization to be "
                "enabled."
            )
        return qasm
    try:
        from qiskit import QuantumCircuit, qasm2, transpile
        from qiskit.transpiler import CouplingMap, PassManager
        from qiskit.transpiler.passes import (
            Collect2qBlocks,
            CommutativeCancellation,
            ConsolidateBlocks,
            Optimize1qGatesDecomposition,
            UnitarySynthesis,
        )
    except ImportError as error:
        raise RuntimeError(
            "Qiskit is required for QASM optimization; set "
            "qiskit_optimization_level=None "
            "to submit the unoptimized fragment."
        ) from error
    circuit = QuantumCircuit.from_qasm_str(qasm)
    # First use Qiskit's preset pipeline, then explicitly collect and
    # resynthesize two-qubit blocks.  The latter is intentionally present even
    # at level 3: it gives deterministic, inspectable control over the last
    # two-qubit synthesis pass before topology routing.
    preset_optimized = transpile(
        circuit,
        basis_gates=("u3", "cx"),
        optimization_level=optimization_level,
        seed_transpiler=42,
    )
    resynthesis = PassManager([
        Collect2qBlocks(),
        ConsolidateBlocks(basis_gates=("u3", "cx"), force_consolidate=True),
        UnitarySynthesis(basis_gates=("u3", "cx"), approximation_degree=1.0),
        Optimize1qGatesDecomposition(basis=("u3", "cx")),
        CommutativeCancellation(),
    ])
    resynthesized = resynthesis.run(preset_optimized)
    # Restore the level-3 fixed point after the explicit resynthesis pass.
    resynthesized = transpile(
        resynthesized,
        basis_gates=("u3", "cx"),
        optimization_level=optimization_level,
        seed_transpiler=42,
    )

    # Level-3's own synthesis is sometimes already the local optimum.  Keep
    # the explicit two-qubit resynthesis candidate only when it does not make
    # the executable circuit worse, prioritizing entangling-gate count and
    # then depth.
    def score(candidate):
        operations = candidate.count_ops()
        return (
            sum(operations.get(gate, 0) for gate in ("cx", "cz")),
            candidate.depth(),
            candidate.size(),
        )

    optimized = min((preset_optimized, resynthesized), key=score)
    if hardware_profile == "shenglian":
        optimized = transpile(
            optimized,
            basis_gates=("h", "rx", "ry", "rz", "cz"),
            coupling_map=CouplingMap(_shenglian_coupling_edges()),
            layout_method="sabre",
            routing_method="sabre",
            optimization_level=optimization_level,
            seed_transpiler=42,
        )
    return qasm2.dumps(optimized)


def _shenglian_coupling_edges() -> tuple[tuple[int, int], ...]:
    """Return directed edges for the 84-qubit Shenglian diamond lattice.

    Qubits are numbered row-major in twelve rows of seven, exactly as shown in
    the provided hardware map.  CZ is symmetric, hence both directions are
    listed for Qiskit's coupling map.
    """
    edges: list[tuple[int, int]] = []
    for row in range(11):
        for column in range(7):
            source = row * 7 + column
            next_columns = (
                (column, column - 1) if row % 2 == 0 else (column, column + 1)
            )
            for next_column in next_columns:
                if 0 <= next_column < 7:
                    target = (row + 1) * 7 + next_column
                    edges.extend(((source, target), (target, source)))
    return tuple(edges)


def _operation_to_qasm(operation: Operation) -> list[str]:
    """Serialize the native one- and two-qubit gate set to OpenQASM 2."""
    matrix, qubits = operation.matrix, operation.qubits
    hadamard = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    if len(qubits) == 1 and np.allclose(matrix, hadamard, atol=1e-12):
        return [f"h q[{qubits[0]}];"]
    if len(qubits) == 1 and np.allclose(
        matrix, np.array([[0, 1], [1, 0]]), atol=1e-12
    ):
        return [f"x q[{qubits[0]}];"]
    if len(qubits) == 1:
        theta = _rx_angle(matrix)
        if theta is not None:
            return [f"u3({_number(theta)},-pi/2,pi/2) q[{qubits[0]}];"]
        theta = _rz_angle(matrix)
        if theta is not None:
            return [f"rz({_number(theta)}) q[{qubits[0]}];"]
    if len(qubits) == 2:
        control, target = qubits
        cx = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]])
        if np.allclose(matrix, cx, atol=1e-12):
            return [f"cx q[{control}],q[{target}];"]
        swap = np.array([
            [1, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1],
        ])
        if np.allclose(matrix, swap, atol=1e-12):
            return [f"swap q[{control}],q[{target}];"]
        theta = _rzz_angle(matrix)
        if theta is not None:
            return [
                f"standalone_rzz({_number(theta)}) "
                f"q[{qubits[0]}],q[{qubits[1]}];"
            ]
    raise ValueError(
        "Add an OpenQASM serializer for this operation before submitting it."
    )


def _rx_angle(matrix: np.ndarray) -> float | None:
    if matrix.shape != (2, 2) or not np.isclose(
        matrix[0, 0].imag, 0.0, atol=1e-12
    ):
        return None
    theta = 2 * np.arctan2(-matrix[0, 1].imag, matrix[0, 0].real)
    expected = np.array([
        [np.cos(theta / 2), -1j * np.sin(theta / 2)],
        [-1j * np.sin(theta / 2), np.cos(theta / 2)],
    ])
    return float(theta) if np.allclose(matrix, expected, atol=1e-12) else None


def _rz_angle(matrix: np.ndarray) -> float | None:
    """Return the RZ angle if ``matrix`` is RZ, otherwise ``None``."""
    if matrix.shape != (2, 2) or not np.allclose(
        matrix, np.diag(np.diag(matrix)), atol=1e-12
    ):
        return None
    theta = np.angle(matrix[1, 1] / matrix[0, 0])
    # Qiskit may preserve a gate-local global phase while decomposing a
    # controlled permutation.  It is physically irrelevant, so only the
    # relative diagonal phase is required for an RZ OpenQASM emission.
    expected_ratio = np.exp(1j * theta)
    ratio = matrix[1, 1] / matrix[0, 0]
    return (
        float(theta)
        if np.allclose(ratio, expected_ratio, atol=1e-12)
        else None
    )


def _rzz_angle(matrix: np.ndarray) -> float | None:
    if matrix.shape != (4, 4) or not np.allclose(
        matrix, np.diag(np.diag(matrix)), atol=1e-12
    ):
        return None
    theta = -2 * np.angle(matrix[0, 0])
    expected = np.diag([
        np.exp(-0.5j * theta),
        np.exp(0.5j * theta),
        np.exp(0.5j * theta),
        np.exp(-0.5j * theta),
    ])
    return float(theta) if np.allclose(matrix, expected, atol=1e-12) else None


def _prepare_state_qasm(qubit: int, state: np.ndarray) -> list[str]:
    states = {
        "zero": np.array([1, 0], dtype=complex),
        "one": np.array([0, 1], dtype=complex),
        "plus": np.array([1, 1], dtype=complex) / np.sqrt(2),
        "minus": np.array([1, -1], dtype=complex) / np.sqrt(2),
        "iplus": np.array([1, 1j], dtype=complex) / np.sqrt(2),
        "iminus": np.array([1, -1j], dtype=complex) / np.sqrt(2),
    }
    name = next(
        (
            name
            for name, known in states.items()
            if np.allclose(state, known, atol=1e-12)
        ),
        None,
    )
    if name is None:
        raise ValueError(
            "The QPD preparation is not one of the six wire-cut states."
        )
    operations: dict[str, list[str]] = {
        "zero": [],
        "one": ["x"],
        "plus": ["h"],
        "minus": ["x", "h"],
        "iplus": ["u3(-pi/2,-pi/2,pi/2)"],
        "iminus": ["u3(pi/2,-pi/2,pi/2)"],
    }
    return [f"{operation} q[{qubit}];" for operation in operations[name]]


def _qpd_measurement_qasm(qubit: int, axis: str, cbit: int) -> list[str]:
    basis_change: dict[str, list[str]] = {
        "X": ["h"],
        "Y": ["sx"],
        "Z": [],
    }
    if axis not in basis_change:
        raise ValueError(f"Unsupported QPD measurement axis: {axis}.")
    return [
        *(f"{operation} q[{qubit}];" for operation in basis_change[axis]),
        f"measure q[{qubit}] -> c[{cbit}];",
    ]


def _counts_to_weighted_expectation(
    counts: Mapping[str, int],
    qpd_cbits: tuple[int, ...],
    observable_cbits: tuple[int, ...],
) -> float:
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("QuarkStudio returned no measurement shots.")
    required_width = max((*qpd_cbits, *observable_cbits), default=-1) + 1
    value = 0.0
    for bitstring, count in counts.items():
        bits = bitstring.replace(" ", "")
        if len(bits) < required_width or any(bit not in "01" for bit in bits):
            raise ValueError(
                f"Unexpected QuarkStudio count key: {bitstring!r}."
            )
        cbit_values = tuple(int(bit) for bit in reversed(bits))
        qpd_sign = 1 - 2 * (sum(cbit_values[cbit] for cbit in qpd_cbits) % 2)
        observable_sign = 1 - 2 * (
            sum(cbit_values[cbit] for cbit in observable_cbits) % 2
        )
        value += count * qpd_sign * observable_sign / total
    return value


def _qiskit_circuit_signature(circuit) -> tuple:
    """Return a register-name-independent signature for a measured circuit."""
    if circuit.parameters:
        raise ValueError(
            "QuarkStudio cutting experiments must be fully parameter-bound."
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


def _counts_to_quasi_distribution(counts: Mapping[str, int]):
    """Normalize QuarkStudio's big-endian OpenQASM counts for SamplerV1."""
    try:
        from qiskit.result import QuasiDistribution
    except ImportError as error:  # pragma: no cover - guarded by the caller
        raise RuntimeError(
            "Qiskit is required to construct sampler results."
        ) from error
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("QuarkStudio returned no measurement shots.")
    probabilities: dict[int, float] = {}
    for bitstring, count in counts.items():
        bits = bitstring.replace(" ", "")
        if not bits or any(bit not in "01" for bit in bits):
            raise ValueError(
                f"Unexpected QuarkStudio count key: {bitstring!r}."
            )
        if not isinstance(count, int) or count < 0:
            raise ValueError(f"Unexpected QuarkStudio count value: {count!r}.")
        outcome = int(bits, 2)
        probabilities[outcome] = (
            probabilities.get(outcome, 0.0) + count / total
        )
    return QuasiDistribution(probabilities)


def _number(value: float) -> str:
    return format(value, ".16g")


def _failure_response(result: Mapping[str, object]) -> str:
    """Serialize the complete failed-task response for terminal diagnostics."""
    return json.dumps(result, ensure_ascii=False, sort_keys=True, default=str)
