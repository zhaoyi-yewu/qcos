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

import enum
from typing import Any
from openqasm3 import ast

from wy_qcos.transpiler.cmss.compiler.openqasm3 import types


class Scope(enum.Enum):
    """Types of scope in OpenQASM 3 programs."""

    GLOBAL = enum.auto()
    GATE = enum.auto()
    FUNCTION = enum.auto()
    LOCAL = enum.auto()
    CALIBRATION = enum.auto()  # Unused
    BUILTIN = enum.auto()
    # NONE scope is for when we're adding an implicit symbol to the table,
    # but it shouldn't actually be accessible by anything outside the context
    # that defines it.  We might need to do this in order to reserve a name
    # that's being defined in the output circuit, but isn't present in the
    # OQ3 program.
    NONE = enum.auto()


class Symbol:
    """An internal symbol used during parsing."""

    __slots__ = ("name", "data", "type", "scope", "definer")

    def __init__(
        self,
        name: str,
        data: Any,
        type: types.Type,
        scope: Scope,
        definer: ast.QASMNode | None = None,
    ):
        self.name = name
        self.data = data
        self.type = type
        self.scope = scope
        self.definer = definer

    def __repr__(self):
        return (
            f"Symbol(name={self.name}, data={self.data}, "
            f"type={self.type}, scope={self.scope})"
        )
