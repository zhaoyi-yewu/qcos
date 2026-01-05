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

from __future__ import annotations
import numpy as np
import math as m
from numbers import Number

from wy_qcos.transpiler.common.errors import CircuitException
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.circuit.operators.op_shape import OpShape


class Operator:
    """Matrix operator class.

    Description:
        This represents a matrix operator. Evaluation the equality
        of the maxtrix.
    """

    _op_shape: OpShape

    def __init__(
        self,
        data: QuantumCircuit | np.ndarray | Operator | ScalarOp,
        input_dims: tuple | None = None,
        output_dims: tuple | None = None,
    ):
        """Initialize an operator object.

        Args:
            data (QuantumCircuit or Matrix or Operator or ScalarOp):
                                data to initialize operator.
            input_dims (tuple): the input subsystem dimensions.
                                [Default: None]
            output_dims (tuple): the output subsystem dimensions.
                                 [Default: None]

        Raises:
            CircuitException: if input data cannot be
            initialized as an operator.
        """
        self.atol = 1e-8
        self.rtol = 1e-5
        op_shape = None
        if isinstance(data, (list, np.ndarray)):
            # Default initialization from list or numpy array matrix
            self._data = np.asarray(data, dtype=complex)
        elif isinstance(data, QuantumCircuit):
            self._data = self._init_instruction(data).data
        elif hasattr(data, "to_operator"):
            # If the data object has a 'to_operator' attribute this is given
            # higher preference than the 'to_matrix' method for initializing
            # an Operator object.
            data = data.to_operator()
            self._data = data.data
            op_shape = data._op_shape
        else:
            raise CircuitException("Invalid input data format for Operator.")

        if op_shape:
            self._op_shape = op_shape
        else:
            self._op_shape = OpShape.auto(
                shape=self._data.shape, dims_l=output_dims, dims_r=input_dims
            )

    @property
    def data(self):
        """The underlying Numpy array."""
        return self._data

    @property
    def dim(self):
        """Return tuple (input_shape, output_shape)."""
        return self._op_shape._dim_r, self._op_shape._dim_l

    def to_operator(self) -> Operator:
        """Convert operator to matrix operator class."""
        return self

    @classmethod
    def _init_instruction(cls, instruction):
        """Convert a QuantumCircuit or Operation to an Operator."""
        if hasattr(instruction, "__array__"):
            return Operator(np.array(instruction, dtype=complex))

        dimension = 2**instruction.num_qubits
        op = Operator(np.eye(dimension))
        op._append_instruction(instruction)
        return op

    @classmethod
    def _einsum_matmul(
        cls,
        tensor: np.ndarray,
        mat: np.ndarray,
        indices: list,
        shift: int = 0,
        right_mul: bool = False,
    ):
        """Perform a contraction using Numpy.einsum.

        Args:
            tensor (np.ndarray): a vector or matrix reshaped to
            a rank-N tensor.
            mat (np.ndarray): a matrix reshaped to a rank-2M tensor.
            indices (list): tensor indices to contract with mat.
            shift (int): shift for indices of tensor to contract [Default: 0].
            right_mul (bool): if True right multiply tensor by mat
                              (else left multiply) [Default: False].

        Returns:
            Numpy.ndarray: the matrix multiplied rank-N tensor.

        Raises:
            CircuitException: if mat is not an even rank tensor.
        """
        rank = tensor.ndim
        rank_mat = mat.ndim
        if rank_mat % 2 != 0:
            raise CircuitException(
                "Contracted matrix must have an even number of indices."
            )
        # Get einsum indices for tensor
        indices_tensor = list(range(rank))
        for j, index in enumerate(indices):
            indices_tensor[index + shift] = rank + j
        # Get einsum indices for mat
        mat_contract = list(reversed(range(rank, rank + len(indices))))
        mat_free = [index + shift for index in reversed(indices)]
        if right_mul:
            indices_mat = mat_contract + mat_free
        else:
            indices_mat = mat_free + mat_contract
        return np.einsum(tensor, indices_tensor, mat, indices_mat)

    def compose(
        self,
        other: Operator | ScalarOp,
        qargs: list | None = None,
        front: bool = False,
    ) -> Operator:
        """Compose self operator with other operator.

        Description:
            The composition is defined as self * other if front=False or
            other * self if front=True. If qargs is specified, the composition
            is performed only on the subsystems specified by qargs.

        Args:
            other (Operator or ScalarOp): an operator to compose with.
            qargs (list | None): list of subsystem indices to compose on.
            front (bool): if True compose as  self * other,
                          else other * self.

        Returns:
            Operator: the composed operator.
        """
        if qargs is None:
            qargs = getattr(other, "qargs", None)
        if not isinstance(other, Operator):
            other = Operator(other)

        # Validate dimensions are compatible and return the composed
        # operator dimensions
        new_shape = self._op_shape.compose(other._op_shape, qargs, front)
        input_dims = new_shape.dims_r()
        output_dims = new_shape.dims_l()

        # Full composition of operators
        if qargs is None:
            if front:
                # Composition self * other
                data = np.dot(self._data, other.data)
            else:
                # Composition other * self
                data = np.dot(other.data, self._data)
            ret = Operator(data, input_dims, output_dims)
            ret._op_shape = new_shape
            return ret

        # Compose with other on subsystem
        num_qargs_l, num_qargs_r = self._op_shape.num_qargs
        if front:
            num_indices = num_qargs_r
            shift = num_qargs_l
            right_mul = True
        else:
            num_indices = num_qargs_l
            shift = 0
            right_mul = False

        # Reshape current matrix
        # Note that we must reverse the subsystem dimension order as
        # qubit 0 corresponds to the right-most position in the tensor
        # product, which is the last tensor wire index.
        tensor = np.reshape(self.data, self._op_shape.tensor_shape)
        mat = np.reshape(other.data, other._op_shape.tensor_shape)
        indices = [num_indices - 1 - qubit for qubit in qargs]
        final_shape = [int(np.prod(output_dims)), int(np.prod(input_dims))]
        data = np.reshape(
            Operator._einsum_matmul(tensor, mat, indices, shift, right_mul),
            final_shape,
        )
        ret = Operator(data, input_dims, output_dims)
        ret._op_shape = new_shape
        return ret

    def _append_instruction(self, obj: QuantumCircuit):
        """Append a QuantumCircuit instruction to the operator.

        Args:
            obj (QuantumCircuit): a QuantumCircuit object with operations.
        """
        if not isinstance(obj, QuantumCircuit):
            raise CircuitException("Input object isnot QuantumCircuit.")

        if not m.isclose(obj.global_phase, 0):
            dimension = 2**obj.num_qubits
            op = self.compose(
                ScalarOp(dimension, np.exp(1j * float(obj.global_phase)))
            )
            self._data = op.data

        for ins in obj.get_operations():
            qargs = ins.targets
            if ins.name in ["measure", "sync", "reset", "move"]:
                continue

            mat = ins.to_matrix()
            if mat is not None:
                op = self.compose(mat, qargs=qargs)
                self._data = op.data

    def equiv(
        self,
        other: Operator,
        rtol: float | None = None,
        atol: float | None = None,
    ) -> bool:
        """Return True if operators are equivalent.

        Args:
            other (Operator): an operator object.
            rtol (float): relative tolerance value for comparison.
            atol (float): absolute tolerance value for comparison.

        Returns:
            bool: True if operators are equivalent up to global phase.
        """
        if not isinstance(other, Operator):
            try:
                other = Operator(other)
            except CircuitException:
                return False
        if self.dim != other.dim:
            return False
        if atol is None:
            atol = self.atol
        if rtol is None:
            rtol = self.rtol
        return self.matrix_equal(
            self.data, other.data, ignore_phase=True, rtol=rtol, atol=atol
        )

    def matrix_equal(
        self,
        mat1,
        mat2,
        ignore_phase=False,
        rtol=0,
        atol=0,
        props=None,
    ):
        """Test if two arrays are equal.

        The final comparison is implemented using Numpy.allclose. See its
        documentation for additional information on tolerance parameters.

        If ``ignore_phase`` is True both matrices will be multiplied by
        ``exp(-1j * theta)`` where theta is the first nphase for a
        first non-zero matrix element ``|a| * exp(1j * theta)``.

        Args:
            mat1 (matrix_like): a matrix
            mat2 (matrix_like): a matrix
            ignore_phase (bool): ignore complex-phase differences between
                matrices [Default: False]
            rtol (double): the relative tolerance parameter [Default {}].
            atol (double): the absolute tolerance parameter [Default {}].
            props (dict | None): if not None and ignore_phase is True
                returns the phase difference between the two matrices under
                props['phase_difference']

        Returns:
            bool: True if the matrices are equal or False otherwise.
        """
        if atol is None:
            atol = self.atol
        if rtol is None:
            rtol = self.rtol

        if not isinstance(mat1, np.ndarray):
            mat1 = np.array(mat1)
        if not isinstance(mat2, np.ndarray):
            mat2 = np.array(mat2)

        if mat1.shape != mat2.shape:
            return False

        if ignore_phase:
            phase_difference = 0

            # Get phase of first non-zero entry of mat1 and mat2
            # and multiply all entries by the conjugate
            for elt in mat1.flat:
                if abs(elt) > atol:
                    angle = np.angle(elt)
                    phase_difference -= angle
                    mat1 = np.exp(-1j * angle) * mat1
                    break
            for elt in mat2.flat:
                if abs(elt) > atol:
                    angle = np.angle(elt)
                    phase_difference += angle
                    mat2 = np.exp(-1j * np.angle(elt)) * mat2
                    break
            if props is not None:
                props["phase_difference"] = phase_difference

        return np.allclose(mat1, mat2, rtol=rtol, atol=atol)


class ScalarOp:
    """Scalar identity operator class."""

    def __init__(
        self, dims: int | tuple | None = None, coeff: int | float = 1.0
    ):
        """Initialize an operator object.

        Args:
            dims (int or tuple): subsystem dimensions.
            coeff (Number): scalar coefficient for the identity
                            operator (Default: 1).

        Raises:
            QiskitError: If the optional coefficient is invalid.
        """
        if not isinstance(coeff, Number):
            raise CircuitException(f"coeff {coeff} must be a number.")
        self._coeff = coeff
        self._op_shape = OpShape.auto(dims_l=dims, dims_r=dims)

    @property
    def dim(self):
        """Return tuple (input_shape, output_shape)."""
        return self._op_shape._dim_r, self._op_shape._dim_l

    @property
    def coeff(self):
        """Return the coefficient."""
        return self._coeff

    def input_dims(self, qargs=None):
        """Return tuple of input dimension for specified subsystems."""
        return self._op_shape.dims_r(qargs)

    def output_dims(self, qargs=None):
        """Return tuple of output dimension for specified subsystems."""
        return self._op_shape.dims_l(qargs)

    def to_matrix(self):
        """Convert to a Numpy matrix."""
        dim, _ = self.dim
        iden = np.eye(dim, dtype=complex)
        return self.coeff * iden

    def to_operator(self) -> Operator:
        """Convert to an Operator object."""
        return Operator(
            self.to_matrix(),
            input_dims=self.input_dims(),
            output_dims=self.output_dims(),
        )
