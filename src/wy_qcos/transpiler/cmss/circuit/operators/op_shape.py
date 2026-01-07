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

from numbers import Integral
from functools import reduce
from operator import mul
from math import log2

from wy_qcos.transpiler.common.errors import CircuitException


class OpShape:
    """Multipartite matrix and vector shape class."""

    def __init__(
        self, dims_l=None, dims_r=None, num_qargs_l=None, num_qargs_r=None
    ):
        """Initialize an operator object."""
        # The number of left and right qargs
        # the number of left (output) subsystems
        self._num_qargs_l = 0
        # the number of right (input) subsystems
        self._num_qargs_r = 0

        # Subsystem dimensions
        # This is a tuple of dimensions for each subsystem
        # If None each subsystem is assumed to be a dim=2 (qubit)
        # Tuple of left (output) dimensions
        self._dims_l = None
        # tuple of right (input) dimensions
        self._dims_r = None

        # Set attributes
        if num_qargs_r:
            self._num_qargs_r = int(num_qargs_r)
        if dims_r:
            self._dims_r = tuple(dims_r)
            self._num_qargs_r = len(self._dims_r)
        if num_qargs_l:
            self._num_qargs_l = int(num_qargs_l)
        if dims_l:
            self._dims_l = tuple(dims_l)
            self._num_qargs_l = len(self._dims_l)

    def dims_r(self, qargs=None):
        """Return tuple of input dimension for specified subsystems."""
        if self._dims_r:
            if qargs:
                return tuple(self._dims_r[i] for i in qargs)
            return self._dims_r
        num = self._num_qargs_r if qargs is None else len(qargs)
        return num * (2,)

    def dims_l(self, qargs=None):
        """Return tuple of output dimension for specified subsystems."""
        if self._dims_l:
            if qargs:
                return tuple(self._dims_l[i] for i in qargs)
            return self._dims_l
        num = self._num_qargs_l if qargs is None else len(qargs)
        return num * (2,)

    @property
    def _dim_r(self):
        """Return the total input dimension."""
        if self._dims_r:
            return reduce(mul, self._dims_r)
        return 2**self._num_qargs_r

    @property
    def _dim_l(self):
        """Return the total input dimension."""
        if self._dims_l:
            return reduce(mul, self._dims_l)
        return 2**self._num_qargs_l

    @property
    def size(self):
        """Return the combined dimensions of the object."""
        return self._dim_l * self._dim_r

    @property
    def num_qubits(self):
        """Get number of qubits.

        Description:
            Return number of qubits if shape is N-qubit.
            If Shape is not N-qubit return None.
        """
        if self._dims_l or self._dims_r:
            return None
        if self._num_qargs_l:
            if self._num_qargs_r and self._num_qargs_l != self._num_qargs_r:
                return None
            return self._num_qargs_l
        return self._num_qargs_r

    @property
    def num_qargs(self):
        """Return a tuple of the number of left and right wires."""
        return self._num_qargs_l, self._num_qargs_r

    @property
    def shape(self):
        """Return a tuple of the matrix shape."""
        if self._num_qargs_l == self._num_qargs_r == 0:
            # Scalar shape is op-like
            return (1, 1)
        if not self._num_qargs_r:
            # Vector shape
            return (self._dim_l,)
        # Matrix shape
        return self._dim_l, self._dim_r

    @property
    def tensor_shape(self):
        """Return a tuple of the tensor shape."""
        return tuple(reversed(self.dims_l())) + tuple(reversed(self.dims_r()))

    @property
    def is_square(self):
        """Return True if the left and right dimensions are equal."""
        return (
            self._num_qargs_l == self._num_qargs_r
            and self._dims_l == self._dims_r
        )

    def compose(
        self, other: "OpShape", qargs: list | None = None, front: bool = False
    ):
        """Return composed OpShape."""
        ret = OpShape()
        if qargs is None:
            if front:
                if (
                    self._num_qargs_r != other._num_qargs_l
                    or self._dims_r != other._dims_l
                ):
                    raise CircuitException(
                        "Left and right compose dimensions don't match "
                        f"({self.dims_r()} != {other.dims_l()})"
                    )
                ret._dims_l = self._dims_l
                ret._dims_r = other._dims_r
                ret._num_qargs_l = self._num_qargs_l
                ret._num_qargs_r = other._num_qargs_r
            else:
                if (
                    self._num_qargs_l != other._num_qargs_r
                    or self._dims_l != other._dims_r
                ):
                    raise CircuitException(
                        "Left and right compose dimensions don't match "
                        f"({self.dims_l()} != {other.dims_r()})"
                    )
                ret._dims_l = other._dims_l
                ret._dims_r = self._dims_r
                ret._num_qargs_l = other._num_qargs_l
                ret._num_qargs_r = self._num_qargs_r
            return ret

        if front:
            ret._dims_l = self._dims_l
            ret._num_qargs_l = self._num_qargs_l
            if len(qargs) != other._num_qargs_l:
                raise CircuitException(
                    "Number of qargs does not match "
                    f"({len(qargs)} != {other._num_qargs_l})"
                )
            if self._dims_r or other._dims_r:
                if self.dims_r(qargs) != other.dims_l():
                    raise CircuitException(
                        "Subsystem dimension do not match on specified qargs "
                        f"{self.dims_r(qargs)} != {other.dims_l()}"
                    )
                dims_r = list(self.dims_r())
                for i, dim in zip(qargs, other.dims_r()):
                    dims_r[i] = dim
                ret._dims_r = tuple(dims_r)
                ret._num_qargs_r = len(ret._dims_r)
            else:
                ret._num_qargs_r = self._num_qargs_r
        else:
            ret._dims_r = self._dims_r
            ret._num_qargs_r = self._num_qargs_r
            if len(qargs) != other._num_qargs_r:
                raise CircuitException(
                    "Number of qargs does not match "
                    f"({len(qargs)} != {other._num_qargs_r})"
                )
            if self._dims_l or other._dims_l:
                if self.dims_l(qargs) != other.dims_r():
                    raise CircuitException(
                        "Subsystem dimension do not match on specified qargs "
                        f"{self.dims_l(qargs)} != {other.dims_r()}"
                    )
                dims_l = list(self.dims_l())
                for i, dim in zip(qargs, other.dims_l()):
                    dims_l[i] = dim
                ret._dims_l = tuple(dims_l)
                ret._num_qargs_l = len(ret._dims_l)
            else:
                ret._num_qargs_l = self._num_qargs_l
        return ret

    def validate_shape(self, shape):
        """Raise an exception if shape is not valid for the OpShape."""
        return self._validate(shape, raise_exception=True)

    def _validate(self, shape: tuple, raise_exception: bool = False):
        """Validate OpShape against a matrix or vector shape."""
        ndim = len(shape)
        if ndim > 2:
            if raise_exception:
                raise CircuitException(
                    f"Input shape is not 1 or 2-dimensional (shape = {shape})"
                )
            return False

        if self._dims_l:
            if reduce(mul, self._dims_l) != shape[0]:
                if raise_exception:
                    raise CircuitException(
                        "Output dimensions do not match matrix shape "
                        f"({reduce(mul, self._dims_l)} != {shape[0]})"
                    )
                return False
        elif shape[0] != 2**self._num_qargs_l:
            if raise_exception:
                raise CircuitException(
                    "Number of left qubits does not match matrix shape"
                )
            return False

        if ndim == 2:
            if self._dims_r:
                if reduce(mul, self._dims_r) != shape[1]:
                    if raise_exception:
                        raise CircuitException(
                            "Input dimensions do not match matrix shape "
                            f"({reduce(mul, self._dims_r)} != {shape[1]})"
                        )
                    return False
            elif shape[1] != 2**self._num_qargs_r:
                if raise_exception:
                    raise CircuitException(
                        "Number of right qubits does not match matrix shape"
                    )
                return False
        elif self._dims_r or self._num_qargs_r:
            if raise_exception:
                raise CircuitException(
                    "Input dimension should be empty for vector shape."
                )
            return False

        return True

    @classmethod
    def auto(
        cls,
        shape=None,
        dims_l=None,
        dims_r=None,
        dims=None,
        num_qubits_l=None,
        num_qubits_r=None,
        num_qubits=None,
    ) -> "OpShape":
        """Maxtrix construction.

        Description:
            Construct TensorShape with automatic checking of qubit dimensions.
        """
        if dims and (dims_l or dims_r):
            raise CircuitException("dims cannot be used with dims_l or dims_r")
        if num_qubits and (num_qubits_l or num_qubits_r):
            raise CircuitException(
                "num_qubits cannot be used with num_qubits_l or num_qubits_r"
            )

        if num_qubits:
            num_qubits_l = num_qubits
            num_qubits_r = num_qubits
        if dims:
            dims_l = dims
            dims_r = dims

        if num_qubits_r and num_qubits_l:
            matrix_shape = cls(
                num_qargs_l=num_qubits_r, num_qargs_r=num_qubits_l
            )
        else:
            ndim = len(shape) if shape else 0
            if dims_r is None and num_qubits_r is None and ndim > 1:
                dims_r = shape[1]

            if dims_l is None and num_qubits_l is None and ndim > 0:
                dims_l = shape[0]

            if num_qubits_r is None:
                if isinstance(dims_r, Integral):
                    if dims_r != 0 and (dims_r & (dims_r - 1) == 0):
                        num_qubits_r = int(log2(dims_r))
                        dims_r = None
                    else:
                        dims_r = (dims_r,)
                elif dims_r is not None:
                    if set(dims_r) == {2}:
                        num_qubits_r = len(dims_r)
                        dims_r = None
                    else:
                        dims_r = tuple(dims_r)

            if num_qubits_l is None:
                if isinstance(dims_l, Integral):
                    if dims_l != 0 and (dims_l & (dims_l - 1) == 0):
                        num_qubits_l = int(log2(dims_l))
                        dims_l = None
                    else:
                        dims_l = (dims_l,)
                elif dims_l is not None:
                    if set(dims_l) == {2}:
                        num_qubits_l = len(dims_l)
                        dims_l = None
                    else:
                        dims_l = tuple(dims_l)
            matrix_shape = cls(
                dims_l=dims_l,
                dims_r=dims_r,
                num_qargs_l=num_qubits_l,
                num_qargs_r=num_qubits_r,
            )
        # Validate shape
        if shape:
            matrix_shape.validate_shape(shape)
        return matrix_shape
