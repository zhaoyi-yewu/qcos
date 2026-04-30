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

"""QuantumCircuit to Pulse scheduler."""

from wy_qcos.transpiler.common.pulse_ir.compatible.exceptions import (
    QiskitError,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.schedule import Schedule
from wy_qcos.transpiler.common.pulse_ir.scheduler._typing import (
    SchedulableCircuitLike,
)
from wy_qcos.transpiler.common.pulse_ir.scheduler.config import ScheduleConfig
from wy_qcos.transpiler.common.pulse_ir.scheduler.methods import (
    as_late_as_possible,
    as_soon_as_possible,
)
from wy_qcos.transpiler.common.pulse_ir.utils.deprecate_pulse import (
    deprecate_pulse_dependency,
)

from qiskit.providers import BackendV1, BackendV2


@deprecate_pulse_dependency(moving_to_dynamics=True)
def schedule_circuit(
    circuit: SchedulableCircuitLike,
    schedule_config: ScheduleConfig,
    method: str | None = None,
    backend: BackendV1 | BackendV2 | None = None,
) -> Schedule:
    """Schedule a circuit into a pulse schedule.

    If no method is specified, an as-late-as-possible scheduling pass is
    used.

    Supported methods:

        * ``'as_soon_as_possible'``: Schedule pulses greedily on qubit
          resources. Alias: ``'asap'``.
        * ``'as_late_as_possible'``: Schedule pulses late to keep
          qubits in the ground state when possible. Alias: ``'alap'``.

    Args:
        circuit: The quantum circuit to translate.
        schedule_config: Backend-specific parameters for building schedules.
        method: The scheduling pass method to use.
        backend: Backend used to build schedules. It may be BackendV1 or
            BackendV2.

    Returns:
        Schedule corresponding to the input circuit.

    Raises:
        QiskitError: If method isn't recognized.
    """
    methods = {
        "as_soon_as_possible": as_soon_as_possible,
        "asap": as_soon_as_possible,
        "as_late_as_possible": as_late_as_possible,
        "alap": as_late_as_possible,
    }
    if method is None:
        method = "as_late_as_possible"
    try:
        return methods[method](circuit, schedule_config, backend)
    except KeyError as ex:
        raise QiskitError(
            f"Scheduling method {method} isn't recognized."
        ) from ex
