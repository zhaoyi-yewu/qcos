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

"""Pulse dynamics integration helpers.

====================================
Pulse (:mod:`qiskit_dynamics.pulse`)
====================================

.. currentmodule:: qiskit_dynamics.pulse

This module contains tools to interface
:mod:`wy_qcos.transpiler.common.pulse_ir.pulse` with Qiskit Dynamics.
Qiskit Dynamics simulates time evolution using the :class:`Signal`
class, while :mod:`wy_qcos.transpiler.common.pulse_ir.pulse` specifies
pulse instructions using a
:class:`~wy_qcos.transpiler.common.pulse_ir.pulse.Schedule` or
:class:`~wy_qcos.transpiler.common.pulse_ir.pulse.ScheduleBlock`.
These converters transform a
:mod:`wy_qcos.transpiler.common.pulse_ir.pulse` control specification
into :class:`Signal` instances for simulation.

Converters
==========

The conversion from a
:class:`~wy_qcos.transpiler.common.pulse_ir.pulse.Schedule` to a list of
:class:`Signal` instances is done with the
:class:`InstructionToSignals` converter. The following code block shows
a simple instantiation and how to use it to convert a
:class:`~wy_qcos.transpiler.common.pulse_ir.pulse.Schedule` to a list of
:class:`Signal` instances.

.. warning::

    The code blocks below suppress ``DeprecationWarning`` instances
    raised by Qiskit Pulse in `qiskit` `1.3`.

.. jupyter-execute::
    :hide-code:

    # silence deprecation warnings from pulse
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

.. code-block:: python

    converter = InstructionToSignals(dt=1, carriers=None)
    signals = converter.get_signals(sched)

An example schedule, and the corresponding converted signals, is shown below.

.. jupyter-execute::
    :hide-code:

    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec

    from wy_qcos.transpiler.common.pulse_ir import pulse

    from qiskit_dynamics.pulse import InstructionToSignals


    with pulse.build(name="schedule") as sched:
        pulse.play(pulse.Drag(20, 0.5, 4, 0.5), pulse.DriveChannel(0))
        pulse.shift_phase(1.0, pulse.DriveChannel(0))
        pulse.play(pulse.Drag(20, 0.5, 4, 0.5), pulse.DriveChannel(0))
        pulse.shift_frequency(0.5, pulse.DriveChannel(0))
        pulse.play(
            pulse.GaussianSquare(200, 0.3, 4, 150),
            pulse.DriveChannel(0),
        )
        pulse.play(
            pulse.GaussianSquare(200, 0.3, 4, 150),
            pulse.DriveChannel(1),
        )

    fig = plt.figure(constrained_layout=True, figsize=(10, 7))
    spec = gridspec.GridSpec(ncols=2, nrows=2, figure=fig)
    ax1 = fig.add_subplot(spec[0, :])
    ax2 = fig.add_subplot(spec[1, 0])
    ax3 = fig.add_subplot(spec[1, 1])

    converter = InstructionToSignals(dt=1, carriers=None)

    signals = converter.get_signals(sched)

    signals[0].draw(0, 239, 400, axis=ax2, title="Signal from DriveChannel(0)")
    signals[1].draw(0, 239, 400, axis=ax3, title="Signal from DriveChannel(1)")
    sched.draw(axis=ax1)

Converter class
===============

.. autosummary::
   :toctree: ../stubs/

   InstructionToSignals
"""

from .pulse_to_signals import InstructionToSignals
