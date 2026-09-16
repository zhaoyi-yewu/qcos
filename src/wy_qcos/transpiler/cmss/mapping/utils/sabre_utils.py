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

    Examples::

        _normalize_qubit_index("Q0")  -> 0
        _normalize_qubit_index("P15") -> 15
        _normalize_qubit_index(3)     -> 3
        _normalize_qubit_index("42")  -> 42
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

    Examples::

        _normalize_edge(["Q0", "Q1"]) -> (0, 1)
        _normalize_edge(("P3", "P4")) -> (3, 4)
        _normalize_edge([2, 5])       -> (2, 5)
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

    Example:
        Input coupler_map::

            {
                "CZ0_1": ["Q0", "Q1"],
                "CZ1_0": ["Q1", "Q0"],
                "CZ2_3": ["Q2", "Q3"],
            }

        Output::

            [(0, 1), (1, 0), (2, 3)]
    """
    topology_edges = []

    for key, value in coupler_map.items():
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise TypeError(
                f"coupler_map[{key!r}] must be a 2-element list/tuple, "
                f"got {value!r}"
            )
        topology_edges.append(_normalize_edge(value))

    return topology_edges


def _extract_qubit_errors(
    readout_error: dict,
) -> dict[int, float]:
    """Extract per-qubit error values from readout_error mapping.

    Args:
        readout_error: Mapping from qubit name to error value.

    Returns:
        Mapping from normalized qubit ID to error value.

    Example:
        Input readout_error::

            {"Q0": 0.001, "Q1": 0.002, "Q5": 0.003}

        Output::

            {0: 0.001, 1: 0.002, 5: 0.003}
    """
    qubit_errors: dict[int, float] = {}
    for qubit_name, error_value in readout_error.items():
        if not isinstance(error_value, (int, float)):
            raise TypeError(
                f"readout_error[{qubit_name!r}] must be numeric, "
                f"got {type(error_value).__name__}"
            )
        qubit_id = _normalize_qubit_index(qubit_name)
        qubit_errors[qubit_id] = float(error_value)
    return qubit_errors


def _extract_edge_errors(
    coupler_map: dict,
    coupler_error: dict,
) -> dict[tuple[int, int], float]:
    """Extract per-edge error values by joining coupler_map and coupler_error.

    Args:
        coupler_map: Mapping from coupler name to qubit pair.
        coupler_error: Mapping from coupler name to error value.

    Returns:
        Mapping from normalized edge tuple to error value.

    Example:
        Input coupler_map::

            {"CZ0_1": ["Q0", "Q1"], "CZ1_0": ["Q1", "Q0"]}

        Input coupler_error::

            {"CZ0_1": 0.01, "CZ1_0": 0.02}

        Output::

            {(0, 1): 0.01, (1, 0): 0.02}
    """
    edge_errors: dict[tuple[int, int], float] = {}
    for coupler_key, qubit_pair in coupler_map.items():
        error_value = coupler_error.get(coupler_key)
        if error_value is None:
            continue
        if not isinstance(error_value, (int, float)):
            raise TypeError(
                f"coupler_error[{coupler_key!r}] must be numeric, "
                f"got {type(error_value).__name__}"
            )
        edge = _normalize_edge(qubit_pair)
        edge_errors[edge] = float(error_value)
    return edge_errors


def extract_topology_data(
    qpu_cfg: dict,
) -> tuple[list[tuple[int, int]], list[float], list[float]]:
    """Extract coupling list and fidelity arrays from qpu_cfg.

    Args:
        qpu_cfg: QPU configuration dict with coupler_map, optional
            coupler_error and readout_error.

    Returns:
        A 3-tuple of:
        - coupling_list: list of (src, dst) edge pairs.
        - edge_fidelities: list aligned with coupling_list (empty if
            unavailable).
        - single_qubit_fidelities: list indexed by physical qubit ID
            (empty if unavailable).

    Note:
        Input errors are converted to fidelities: fidelity = 1 - error.

    Example:
        Input qpu_cfg::

            {
                "coupler_map": {"CZ0_1": ["Q0", "Q1"], "CZ1_0": ["Q1", "Q0"]},
                "coupler_error": {"CZ0_1": 0.01, "CZ1_0": 0.02},
                "readout_error": {"Q0": 0.001, "Q1": 0.002},
            }

        Output::

            coupling_list = [(0, 1), (1, 0)]
            edge_fidelities = [0.99, 0.98]
            single_qubit_fidelities = [0.999, 0.998]
    """
    if "coupler_map" not in qpu_cfg:
        raise ValueError("qpu_cfg missing coupler_map")

    coupler_map = qpu_cfg["coupler_map"]
    if not isinstance(coupler_map, dict):
        raise TypeError("coupler_map must be a dict")

    coupling_list = _extract_coupler_map_edges(coupler_map)

    coupler_error = qpu_cfg.get("coupler_error", {})
    readout_error = qpu_cfg.get("readout_error", {})

    edge_error_dict = (
        _extract_edge_errors(coupler_map, coupler_error)
        if isinstance(coupler_error, dict)
        else {}
    )
    qubit_error_dict = (
        _extract_qubit_errors(readout_error)
        if isinstance(readout_error, dict)
        else {}
    )

    if not edge_error_dict and not qubit_error_dict:
        return coupling_list, [], []

    if edge_error_dict:
        edge_fidelities = []
        for edge in coupling_list:
            if edge not in edge_error_dict:
                raise ValueError(
                    f"Edge {edge} in coupling_list but not in coupler_error"
                )
            edge_fidelities.append(1.0 - edge_error_dict[edge])
    else:
        edge_fidelities = []

    if qubit_error_dict:
        all_qubit_ids = {q for edge in coupling_list for q in edge} | set(
            qubit_error_dict.keys()
        )
        max_qubit_id = max(all_qubit_ids)
        single_qubit_fidelities = [
            1.0 - qubit_error_dict.get(qubit_id, 0.0)
            for qubit_id in range(max_qubit_id + 1)
        ]
    else:
        single_qubit_fidelities = []

    return coupling_list, edge_fidelities, single_qubit_fidelities
