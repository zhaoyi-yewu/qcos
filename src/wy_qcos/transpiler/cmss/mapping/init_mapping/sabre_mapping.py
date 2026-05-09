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

from networkx import Graph

from wy_qcos.common.cmss.base_operation import OperationType
from wy_qcos.common.cmss.gate_operation import GateOperation
from wy_qcos.transpiler.cmss.mapping.routing.sabre_routing import SABRE


_INITIAL_MAPPING_PREFIX_LAYERS = 25


def _extract_two_qubit_layer_prefix(
    gates_list: list[GateOperation], prefix_layers: int
) -> list[GateOperation]:
    if prefix_layers <= 0 or not gates_list:
        return list(gates_list)

    last_layer_by_qubit: dict[int, int] = {}
    last_prefix_index = -1
    max_layer = -1

    for index, gate in enumerate(gates_list):
        if gate.operation_type != OperationType.DOUBLE_QUBIT_OPERATION.value:
            continue

        q0, q1 = gate.targets
        layer = (
            max(
                last_layer_by_qubit.get(q0, -1),
                last_layer_by_qubit.get(q1, -1),
            )
            + 1
        )
        last_layer_by_qubit[q0] = layer
        last_layer_by_qubit[q1] = layer
        max_layer = max(max_layer, layer)
        if layer < prefix_layers:
            last_prefix_index = index

    if max_layer < prefix_layers:
        return list(gates_list)

    if last_prefix_index < 0:
        return list(gates_list)

    return list(gates_list[: last_prefix_index + 1])


def sabre_initial_mapping(
    gates_list: list[GateOperation], coupling_graph: Graph
):
    """Get the initial mapping.

    Args:
        gates_list (list[GateOperation]): a list of gates.
        coupling_graph (Graph): coupling graph of the quantum machine.

    Returns:
        list[int]: the initial mapping.
    """
    sabre = SABRE(coupling_graph)
    prefix_gates = _extract_two_qubit_layer_prefix(
        gates_list, _INITIAL_MAPPING_PREFIX_LAYERS
    )
    reverse_gates = list(reversed(prefix_gates))
    # get initial mapping for reverse ir
    sabre.execute(prefix_gates)
    reverse_mapping = sabre.logic2phy.copy()
    # get the initial mapping for original ir
    sabre.execute(reverse_gates, initial_l2p=reverse_mapping)
    mapping = sabre.logic2phy.copy()
    return mapping
