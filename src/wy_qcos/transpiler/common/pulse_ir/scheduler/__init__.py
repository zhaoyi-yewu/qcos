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

"""Circuit scheduler interfaces.

===========================================
Circuit Scheduler (:mod:`qiskit.scheduler`)
===========================================

.. currentmodule:: qiskit.scheduler

A circuit scheduler compiles a circuit program to a pulse program.

Core API
========

.. autoclass:: ScheduleConfig

.. currentmodule:: qiskit.scheduler.schedule_circuit
.. autofunction:: schedule_circuit
.. currentmodule:: qiskit.scheduler

Pulse scheduling methods
========================

.. currentmodule:: qiskit.scheduler.methods
.. autofunction:: as_soon_as_possible
.. autofunction:: as_late_as_possible
.. currentmodule:: qiskit.scheduler
"""

from wy_qcos.transpiler.common.pulse_ir.scheduler import schedule_circuit
from wy_qcos.transpiler.common.pulse_ir.scheduler.config import ScheduleConfig
