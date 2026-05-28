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
"""Functions for converting ``ScheduleBlock`` objects into DAGs."""

from __future__ import annotations

import typing

import rustworkx as rx


from wy_qcos.transpiler.common.pulse_ir.pulse.channels import Channel
from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import (
    UnassignedReferenceError,
)

if typing.TYPE_CHECKING:
    from schedule import ScheduleBlock  # pylint: disable=cyclic-import


def block_to_dag(block: ScheduleBlock) -> rx.PyDAG:
    """Convert schedule block instruction into DAG.

    ``ScheduleBlock`` can be represented as a DAG as needed.
    For example, equality of two programs can be checked efficiently on a
    DAG representation.

    .. code-block:: python

        from wy_qcos.transpiler.common.pulse_ir import pulse

        my_gaussian0 = pulse.Gaussian(100, 0.5, 20)
        my_gaussian1 = pulse.Gaussian(100, 0.3, 10)

        with pulse.build() as sched1:
            with pulse.align_left():
                pulse.play(my_gaussian0, pulse.DriveChannel(0))
                pulse.shift_phase(1.57, pulse.DriveChannel(2))
                pulse.play(my_gaussian1, pulse.DriveChannel(1))

        with pulse.build() as sched2:
            with pulse.align_left():
                pulse.shift_phase(1.57, pulse.DriveChannel(2))
                pulse.play(my_gaussian1, pulse.DriveChannel(1))
                pulse.play(my_gaussian0, pulse.DriveChannel(0))

    Here ``sched1`` and ``sched2`` are different implementations of the
    same program, but this is difficult to confirm on the list
    representation.

    Another example is instruction optimization.

    .. code-block:: python

        from wy_qcos.transpiler.common.pulse_ir import pulse

        with pulse.build() as sched:
            with pulse.align_left():
                pulse.shift_phase(1.57, pulse.DriveChannel(1))
                pulse.play(my_gaussian0, pulse.DriveChannel(0))
                pulse.shift_phase(-1.57, pulse.DriveChannel(1))

    In the above program two ``shift_phase`` instructions can be cancelled
    out because they are consecutive on the same drive channel.
    This can be easily found on the DAG representation.

    Args:
        block ("ScheduleBlock"): A schedule block to be converted.

    Returns:
        Instructions in DAG representation.

    Raises:
        PulseError: When the context is invalid subclass.
    """
    if block.alignment_context.is_sequential:
        return _sequential_allocation(block)
    return _parallel_allocation(block)


def _sequential_allocation(block) -> rx.PyDAG:
    """A helper function to create a DAG of a sequential alignment context."""
    dag = rx.PyDAG()

    edges: list[tuple[int, int]] = []
    prev_id = None
    for elm in block.blocks:
        node_id = dag.add_node(elm)
        if prev_id is not None:
            edges.append((prev_id, node_id))
        prev_id = node_id
    dag.add_edges_from_no_data(edges)
    return dag


def _parallel_allocation(block) -> rx.PyDAG:
    """A helper function to create a DAG of a parallel alignment context."""
    dag = rx.PyDAG()

    slots: dict[Channel, int] = {}
    edges: set[tuple[int, int]] = set()
    prev_reference = None
    for elm in block.blocks:
        node_id = dag.add_node(elm)
        try:
            for chan in elm.channels:
                prev_id = slots.pop(chan, prev_reference)
                if prev_id is not None:
                    edges.add((prev_id, node_id))
                slots[chan] = node_id
        except UnassignedReferenceError:
            # Broadcast channels because the reference's channels are
            # unknown.
            for chan, prev_id in slots.copy().items():
                edges.add((prev_id, node_id))
                slots[chan] = node_id
            prev_reference = node_id
    dag.add_edges_from_no_data(list(edges))
    return dag
