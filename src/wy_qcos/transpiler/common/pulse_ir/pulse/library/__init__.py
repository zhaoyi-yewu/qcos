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
"""Pulse library.

===========================================
Pulse Library (:mod:`wy_qcos.transpiler.common.pulse_ir.pulse.library`).
===========================================

This library provides Pulse users with convenient methods for building
Pulse waveforms.

A pulse programmer can choose from one of several :ref:`pulse_models` such as
:class:`~Waveform` and :class:`~SymbolicPulse` to create a pulse program.
The :class:`~Waveform` model directly stores the waveform data points in
each class instance. This model provides the most flexibility to express
arbitrary waveforms and allows rapid prototyping of new control
techniques. However, this model is typically memory inefficient and may
be hard to scale to large-size quantum processors. A user can directly
instantiate the :class:`~Waveform` class with a ``samples`` argument,
which is usually a complex numpy array or any kind of array-like data.

In contrast, the :class:`~SymbolicPulse` model only stores the function
and its parameters that generate the waveform in a class instance. It
thus provides greater memory efficiency at the price of less flexibility
in the waveform. This model also defines a small set of pulse subclasses
in :ref:`symbolic_pulses` which are commonly used in superconducting
quantum processors.
An instance of these subclasses can be serialized in the :ref:`qpy_format`
while keeping the memory-efficient parametric representation of waveforms.
Note that :class:`~Waveform` object can be generated from an instance of
a :class:`~SymbolicPulse` which will set values for the parameters and
sample the parametric expression to create the :class:`~Waveform`.


.. _pulse_models:

Pulse Models
============

.. autosummary::
   :toctree: ../stubs/

   Waveform
   SymbolicPulse


.. _symbolic_pulses:

Parametric Pulse Representation
===============================

.. autosummary::
   :toctree: ../stubs/

   Constant
   Drag
   Gaussian
   GaussianSquare
   GaussianSquareDrag
   gaussian_square_echo
   GaussianDeriv
   Sin
   Cos
   Sawtooth
   Triangle
   Square
   Sech
   SechDeriv

"""

from wy_qcos.transpiler.common.pulse_ir.pulse.library.symbolic_pulses import (
    SymbolicPulse,
    ScalableSymbolicPulse,
    Gaussian,
    GaussianSquare,
    GaussianSquareDrag,
    gaussian_square_echo,
    GaussianDeriv,
    Drag,
    Constant,
    Sin,
    Cos,
    Sawtooth,
    Triangle,
    Square,
    Sech,
    SechDeriv,
)
from wy_qcos.transpiler.common.pulse_ir.pulse.library.pulse import Pulse
from wy_qcos.transpiler.common.pulse_ir.pulse.library.waveform import Waveform
