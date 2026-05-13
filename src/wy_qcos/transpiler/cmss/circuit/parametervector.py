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

"""ParameterVector module for circuit-level batch parametric operations."""

from wy_qcos.transpiler.cmss.compiler.openqasm3.state import Parameter


class ParameterVectorElement(Parameter):
    """An element of a ParameterVector."""

    def __init__(self, vector, index):
        self._vector = vector
        self._index = index
        name = f"{vector.name}[{index}]"
        super().__init__(name)

    @property
    def vector(self):
        """Return the parent ParameterVector."""
        return self._vector

    @property
    def index(self):
        """Return the index within the parent ParameterVector."""
        return self._index

    def __repr__(self):
        return f"ParameterVectorElement({self._vector.name}[{self._index}])"


class ParameterVector:
    """A vector of Parameters for batch parameterization."""

    def __init__(self, name, length=0):
        self._name = name
        self._params = [ParameterVectorElement(self, i) for i in range(length)]

    @property
    def name(self):
        """Return the name of the ParameterVector."""
        return self._name

    def __len__(self):
        return len(self._params)

    def __iter__(self):
        return iter(self._params)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return self._params[index]
        return self._params[index]

    def __repr__(self):
        return (
            f"ParameterVector(name={self._name}, length={len(self._params)})"
        )

    def resize(self, length):
        """Resize the parameter vector."""
        if length > len(self._params):
            for i in range(len(self._params), length):
                self._params.append(ParameterVectorElement(self, i))
        elif length < len(self._params):
            self._params = self._params[:length]


__all__ = ["ParameterVector", "ParameterVectorElement"]
