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

import numpy as np

from qcos.transpiler.common.errors import CircuitException
from qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from qcos.transpiler.cmss.circuit.operators.op_shape import OpShape


class Operator:
    """Matrix operator class.

    Description:
        This represents a matrix operator. Evaluation the equality
        of the maxtrix.
    """

    def __init__(
        self,
        data: QuantumCircuit | np.ndarray,
        input_dims: tuple | None = None,
        output_dims: tuple | None = None,
    ):
        """Initialize an operator object.

        Args:
            data (QuantumCircuit or matrix):
                                data to initialize operator.
            input_dims (tuple): the input subsystem dimensions.
                                [Default: None]
            output_dims (tuple): the output subsystem dimensions.
                                 [Default: None]

        Raises:
            CircuitException: if input data cannot be
            initialized as an operator.
        """
        if isinstance(data, (list, np.ndarray)):
            # Default initialization from list or numpy array matrix
            self._data = np.asarray(data, dtype=complex)
        elif isinstance(data, QuantumCircuit):
            self._data = self._init_instruction(data)._data
        else:
            raise CircuitException("Invalid input data format for Operator")

        self._op_shape = OpShape.auto(dims_l=output_dims, dims_r=input_dims)

    @classmethod
    def _init_instruction(cls, instruction):
        """Convert a QuantumCircuit or Operation to an Operator."""
        dimension = 2**instruction.num_qubits
        op = Operator(np.eye(dimension))
        return op
