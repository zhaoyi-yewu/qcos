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

"""Convenience entry point into pulse scheduling.

For more control over pulse scheduling, look at
`qiskit.scheduler.schedule_circuit`.
"""

import logging

from time import time

from qiskit.providers.backend import Backend

from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.common.pulse_ir.compatible.exceptions import (
    QiskitError,
)
from wy_qcos.transpiler.common.pulse_ir.pulse import (
    InstructionScheduleMap,
    Schedule,
)
from wy_qcos.transpiler.common.pulse_ir.scheduler.config import ScheduleConfig
from wy_qcos.transpiler.common.pulse_ir.scheduler.schedule_circuit import (
    schedule_circuit,
)
from wy_qcos.transpiler.common.pulse_ir.utils.deprecate_pulse import (
    deprecate_pulse_dependency,
)
from wy_qcos.transpiler.common.pulse_ir.utils.parallel import parallel_map

logger = logging.getLogger(__name__)


def _log_schedule_time(start_time, end_time):
    log_msg = (
        f"Total Scheduling Time - {((end_time - start_time) * 1000):.5f} (ms)"
    )
    logger.info(log_msg)


@deprecate_pulse_dependency(moving_to_dynamics=True)
def schedule(
    circuits: QuantumCircuit | list[QuantumCircuit],
    backend: Backend | None = None,
    inst_map: InstructionScheduleMap | None = None,
    meas_map: list[list[int]] | None = None,
    dt: float | None = None,
    method: str | list[str] | None = None,
) -> Schedule | list[Schedule]:
    r"""Schedule a circuit to a pulse ``Schedule``.

    The backend and any specified methods control scheduling behavior.
    Supported methods are documented in
    :py:mod:`qiskit.scheduler.schedule_circuit`.

    Args:
        circuits: The quantum circuit or circuits to translate
        backend: A backend instance containing hardware-specific scheduling
            data
        inst_map: Mapping of circuit operations to pulse schedules. If
            ``None``, defaults to the ``backend``'s
            ``instruction_schedule_map``
        meas_map: Sets of qubits that must be measured together. If
            ``None``, defaults to the ``backend``'s ``meas_map``
        dt: Output sample rate of backend control electronics. For
            scheduled circuits containing time information, ``dt`` is
            required. If not provided, it is obtained from the backend
            configuration
        method: Optionally specify a particular scheduling method

    Returns:
        A pulse ``Schedule`` that implements the input circuit

    Raises:
        QiskitError: If ``backend`` is missing when ``inst_map`` or
            ``meas_map`` must be derived
    """
    arg_circuits_list = isinstance(circuits, list)
    start_time = time()
    if backend and getattr(backend, "version", 0) > 1:
        if inst_map is None:
            inst_map = backend.instruction_schedule_map
        if meas_map is None:
            meas_map = backend.meas_map
        if dt is None:
            dt = backend.dt
    else:
        if inst_map is None:
            if backend is None:
                raise QiskitError(
                    "Must supply either a backend or "
                    "InstructionScheduleMap for scheduling passes."
                )
            defaults = backend.defaults()
            if defaults is None:
                raise QiskitError(
                    "The backend defaults are unavailable. "
                    "The backend may not support pulse."
                )
            inst_map = defaults.instruction_schedule_map
        if meas_map is None:
            if backend is None:
                raise QiskitError(
                    "Must supply either a backend or a meas_map "
                    "for scheduling passes."
                )
            meas_map = backend.configuration().meas_map
        if dt is None:
            if backend is not None:
                dt = backend.configuration().dt

    schedule_config = ScheduleConfig(
        inst_map=inst_map,
        meas_map=meas_map,
        dt=dt,
    )
    circuits = circuits if isinstance(circuits, list) else [circuits]
    schedules = parallel_map(
        schedule_circuit,
        circuits,
        (schedule_config, method, backend),
    )
    end_time = time()
    _log_schedule_time(start_time, end_time)
    if arg_circuits_list:
        return schedules
    else:
        return schedules[0]
