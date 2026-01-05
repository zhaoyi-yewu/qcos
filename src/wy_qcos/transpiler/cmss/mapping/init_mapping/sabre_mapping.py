#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from wy_qcos.transpiler.cmss.common.gate_operation import GateOperation
from wy_qcos.transpiler.cmss.mapping.routing.sabre_routing import SABRE


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
    # TODO lwc: use subcircuit is faster
    reverse_gates = list(reversed(gates_list))
    # get initial mapping for reverse ir
    sabre.execute(gates_list)
    reverse_mapping = sabre.logic2phy.copy()
    # get the initial mapping for original ir
    sabre.execute(reverse_gates, initial_l2p=reverse_mapping)
    mapping = sabre.logic2phy.copy()
    return mapping
