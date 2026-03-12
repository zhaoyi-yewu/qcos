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

from typing import NoReturn
from openqasm3 import ast


class ConversionError(Exception):
    """Raised when an error occurs converting the AST representation."""

    def __init__(self, message, node: ast.QASMNode | None = None):
        if node is not None and node.span is not None:
            message = (
                f"{node.span.start_line},{node.span.start_column}: {message}"
            )
        self.message = message
        super().__init__(message)


def raise_from_node(node: ast.QASMNode, message: str) -> NoReturn:
    """Raise a :exc:`.ConversionError` caused by the given `node`."""
    raise ConversionError(message, node)
