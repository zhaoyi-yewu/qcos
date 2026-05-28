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

from collections.abc import Iterable
from collections.abc import Sequence
from typing import TypeAlias

import networkx as nx

Topology: TypeAlias = list[tuple[int, int]] | list[list[int]] | dict | nx.Graph


def _normalize_qubit_index(value: object) -> int:
    """Normalize a qubit identifier into an integer index.

    Args:
        value (object): Candidate qubit identifier from topology input.

    Returns:
        int: The normalized integer qubit index.
    """
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid qubit identifiers")

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)

        if len(stripped) > 1 and stripped[0] in {"q", "Q", "p", "P"}:
            suffix = stripped[1:]
            if suffix.isdigit():
                return int(suffix)

    raise ValueError(f"Invalid qubit identifier: {value!r}")


def _normalize_edge(edge: Sequence[object]) -> tuple[int, int]:
    """Normalize a topology edge into an integer pair.

    Args:
        edge (Sequence[object]): Edge-like object containing two qubit
            identifiers.

    Returns:
        tuple[int, int]: The normalized edge.
    """
    if len(edge) != 2:
        raise ValueError(f"Invalid topology edge: {edge!r}")

    return (
        _normalize_qubit_index(edge[0]),
        _normalize_qubit_index(edge[1]),
    )


def _extract_coupler_map_edges(
    coupler_map: dict[object, object],
) -> list[tuple[int, int]]:
    """Extract topology edges from a qpu_cfg-style coupler_map.

    Args:
        coupler_map (dict[object, object]): Raw coupler mapping loaded from a
            qpu_cfg-style topology config.

    Returns:
        list[tuple[int, int]]: Valid normalized topology edges.
    """
    topology_edges = []

    for value in coupler_map.values():
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            continue

        try:
            topology_edges.append(_normalize_edge(value))
        except ValueError:
            continue

    return topology_edges


def normalize_topology(topology: Topology) -> list[tuple[int, int]]:
    """Normalize supported topology inputs into integer edge pairs.

    Args:
        topology (Topology): Topology edges, a networkx graph, or a qpu_cfg-
            style topology config.

    Returns:
        list[tuple[int, int]]: Normalized physical coupling edges.
    """
    if isinstance(topology, nx.Graph):
        return [_normalize_edge(edge) for edge in topology.edges]

    if isinstance(topology, dict):
        if "coupler_map" not in topology:
            raise ValueError(
                "Cannot extract topology from qpu_cfg: missing coupler_map."
            )
        coupler_map = topology["coupler_map"]
        if not isinstance(coupler_map, dict):
            raise TypeError("Coupler_map must be a dict.")
        return _extract_coupler_map_edges(coupler_map)

    if not isinstance(topology, Iterable):
        raise TypeError(
            "Topology must be an iterable of edges or a topology config."
        )

    return [_normalize_edge(edge) for edge in topology]
