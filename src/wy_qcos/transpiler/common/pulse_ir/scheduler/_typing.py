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

"""Typing helpers for pulse scheduler interfaces."""

from typing import Any, Protocol


class CircuitOperationLike(Protocol):
    """Operation interface required by the scheduler."""

    name: str
    duration: int
    params: list[Any]


class CircuitInstructionLike(Protocol):
    """Instruction interface required by the scheduler."""

    operation: CircuitOperationLike
    qubits: list[Any]
    clbits: list[Any]


class SchedulableCircuitLike(Protocol):
    """Circuit interface required by pulse scheduling."""

    name: str | None
    data: list[CircuitInstructionLike]
    qubits: list[Any]
    clbits: list[Any]
    calibrations: dict[str, Any]
