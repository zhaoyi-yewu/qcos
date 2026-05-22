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
r"""Pulse transforms.

=================================================
Pulse Transforms (:mod:`wy_qcos.transpiler.common.pulse_ir.pulse.transforms`).
=================================================

The pulse transforms provide transformation routines to reallocate and optimize
pulse programs for backends.

.. _pulse_alignments:

Alignments
==========

The alignment transforms define alignment policies of instructions in
:obj:`.ScheduleBlock`. These transformations are called to create
:obj:`.Schedule`\ s from :obj:`.ScheduleBlock`\ s.

.. autosummary::
   :toctree: ../stubs/

   AlignEquispaced
   AlignFunc
   AlignLeft
   AlignRight
   AlignSequential

These are all subtypes of the abstract base class :class:`AlignmentKind`.

.. autoclass:: AlignmentKind


.. _pulse_canonical_transform:

Canonicalization
================

The canonicalization transforms convert schedules to a form amenable for
execution on OpenPulse backends.

.. autofunction:: add_implicit_acquires
.. autofunction:: align_measures
.. autofunction:: block_to_schedule
.. autofunction:: compress_pulses
.. autofunction:: flatten
.. autofunction:: inline_subroutines
.. autofunction:: pad
.. autofunction:: remove_directives
.. autofunction:: remove_trivial_barriers


.. _pulse_dag:

DAG
===

The DAG transforms create a DAG representation of the input program.
This can be used for instruction optimization and equality checks.

.. autofunction:: block_to_dag


.. _pulse_transform_chain:

Composite transform
===================

A sequence of transformations to generate a target code.

.. autofunction:: target_qobj_transform

"""

from .alignments import (
    AlignEquispaced,
    AlignFunc,
    AlignLeft,
    AlignRight,
    AlignSequential,
    AlignmentKind,
)

from .base_transforms import target_qobj_transform

from .canonicalization import (
    add_implicit_acquires,
    align_measures,
    block_to_schedule,
    compress_pulses,
    flatten,
    inline_subroutines,
    pad,
    remove_directives,
    remove_trivial_barriers,
)

from .dag import block_to_dag
