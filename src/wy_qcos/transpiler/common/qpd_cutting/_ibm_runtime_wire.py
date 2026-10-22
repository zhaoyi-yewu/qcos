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

"""IBM Quantum Runtime adapter for wire-cut Z-basis fragment experiments.

The adapter deliberately reuses the backend-neutral QPD batch and the same
OpenQASM serialization used by the QuarkStudio adapter.  IBM's target-aware
preset pass manager then performs the final layout, routing, and native-gate
translation for the selected live backend before ``SamplerV2`` is submitted.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ._quarkstudio_wire import (
    _counts_to_weighted_expectation,
    _fragment_to_openqasm2,
    _merge_z_observables,
)
from ._wire_cutting_service import (
    CuttingExperimentBatch,
    CuttingExperimentResults,
)


@dataclass(frozen=True)
class _IBMWork:
    """Canonical IBM sampler publication and reconstruction metadata."""

    group: list
    qpd_cbits: tuple[int, ...]
    observable_cbits: dict[int, int]
    circuit: Any
    label: str


class IBMQuantumBatchExecutor:
    """Compile wire-cut fragments for an IBM backend and submit SamplerV2 jobs.

    A sampler submission is asynchronous: ``run`` returns a job immediately.
    Compatible term/fragment circuits are submitted together in bounded chunks,
    then their results are awaited independently per submitted IBM job.
    """

    def __init__(
        self,
        service: Any,
        *,
        backend_name: str | None,
        shots: int,
        optimization_level: int = 3,
        max_circuits_per_job: int = 100,
        sampler_factory: Callable[[Any], Any] | None = None,
        pass_manager_factory: Callable[[Any, int], Any] | None = None,
    ) -> None:
        if shots < 1:
            raise ValueError("shots must be positive.")
        if optimization_level not in {0, 1, 2, 3}:
            raise ValueError(
                "optimization_level must be an integer from 0 through 3."
            )
        if max_circuits_per_job < 1:
            raise ValueError("max_circuits_per_job must be positive.")
        self._service = service
        self._backend_name = backend_name
        self._shots = shots
        self._optimization_level = optimization_level
        self._max_circuits_per_job = max_circuits_per_job
        self._sampler_factory = sampler_factory
        self._pass_manager_factory = pass_manager_factory
        self._submitted = 0

    @property
    def submitted_tasks(self) -> int:
        """Number of asynchronous IBM Runtime sampler jobs submitted."""
        return self._submitted

    @property
    def cache_hits(self) -> int:
        """Return zero because IBM execution has no shared count cache."""
        return 0

    def execute(
        self, batch: CuttingExperimentBatch
    ) -> CuttingExperimentResults:
        """Submit canonical fragment circuits and reconstruct local values."""
        backend = (
            self._service.backend(self._backend_name)
            if self._backend_name
            else self._service.least_busy(
                operational=True,
                simulator=False,
                min_num_qubits=max(
                    item.fragment_experiment.fragment.num_qubits
                    for item in batch.experiments
                ),
            )
        )
        pass_manager = self._make_pass_manager(backend)
        works = self._compile_works(batch, pass_manager)
        values: dict[tuple[int, int, int], float] = {}

        for start in range(0, len(works), self._max_circuits_per_job):
            chunk = works[start : start + self._max_circuits_per_job]
            sampler = self._make_sampler(backend)
            job = sampler.run(
                [work.circuit for work in chunk], shots=self._shots
            )
            self._submitted += 1
            job_id = getattr(job, "job_id", lambda: "<unknown>")()
            print(
                f"IBM Runtime job {job_id} submitted "
                f"({start + 1}-{start + len(chunk)}/{len(works)} canonical "
                "fragment circuits)."
            )
            result = job.result()
            for work, publication in zip(chunk, result, strict=True):
                counts = _sampler_publication_counts(publication)
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
            print(f"IBM Runtime job {job_id} finished.")

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

    def _compile_works(
        self, batch: CuttingExperimentBatch, pass_manager: Any
    ) -> list[_IBMWork]:
        groups: dict[tuple[int, int], list] = defaultdict(list)
        for experiment in batch.experiments:
            groups[(experiment.term_index, experiment.fragment_label)].append(
                experiment
            )

        works: list[_IBMWork] = []
        for (term_index, fragment_label), group in sorted(groups.items()):
            fragment_experiment = group[0].fragment_experiment
            if any(
                item.fragment_experiment != fragment_experiment
                for item in group
            ):
                raise ValueError(
                    "Inconsistent fragment data in an IBM experiment group."
                )
            merged_observable = _merge_z_observables(
                item.observable for item in group
            )
            # IBM's backend target owns the final compilation.  Avoid the
            # generic Qiskit pass here so the target-aware pass manager sees
            # the fragment before its native-gate and routing decisions.
            qasm, qpd_cbits, observable_cbits = _fragment_to_openqasm2(
                fragment_experiment,
                merged_observable,
                qiskit_optimization_level=None,
            )
            circuit = self._qasm_to_circuit(qasm)
            works.append(
                _IBMWork(
                    group,
                    qpd_cbits,
                    observable_cbits,
                    pass_manager.run(circuit),
                    f"t{term_index}-f{fragment_label}",
                )
            )
        return works

    def _make_pass_manager(self, backend: Any) -> Any:
        if self._pass_manager_factory is not None:
            return self._pass_manager_factory(
                backend, self._optimization_level
            )
        try:
            from qiskit.transpiler import generate_preset_pass_manager
        except (
            ImportError
        ) as error:  # pragma: no cover - qiskit is a base dependency
            raise RuntimeError(
                "Install qiskit to compile IBM Runtime circuits."
            ) from error
        return generate_preset_pass_manager(
            backend=backend, optimization_level=self._optimization_level
        )

    def _make_sampler(self, backend: Any) -> Any:
        if self._sampler_factory is not None:
            return self._sampler_factory(backend)
        try:
            from qiskit_ibm_runtime import SamplerV2
        except ImportError as error:
            raise RuntimeError(
                "Install qiskit-ibm-runtime to execute IBM Quantum jobs: "
                "`python -m pip install -U qiskit-ibm-runtime`."
            ) from error
        return SamplerV2(mode=backend)

    @staticmethod
    def _qasm_to_circuit(qasm: str) -> Any:
        try:
            from qiskit import QuantumCircuit
        except (
            ImportError
        ) as error:  # pragma: no cover - qiskit is a base dependency
            raise RuntimeError(
                "Install qiskit to compile IBM Runtime circuits."
            ) from error
        return QuantumCircuit.from_qasm_str(qasm)


def _sampler_publication_counts(publication: Any) -> Mapping[str, int]:
    """Extract the classical-register counts from a SamplerV2 result."""
    data = publication.data
    if hasattr(data, "c"):
        return data.c.get_counts()
    keys = tuple(data.keys())
    if len(keys) != 1:
        raise ValueError(
            "Expected one classical register in the IBM SamplerV2 "
            "publication, "
            f"found {keys!r}."
        )
    return getattr(data, keys[0]).get_counts()
