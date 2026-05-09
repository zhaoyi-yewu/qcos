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

import itertools
import numpy as np


class Register:
    """Create a quantum register."""

    # display in obj.__dict__
    __slots__ = [
        "_name",
        "_size",
        "_bits",
        "_bit_indices",
        "_repr",
        "_init_pos",
    ]

    # Counter for the number of instances in this class.
    instances_counter = itertools.count()
    # Prefix to use for auto naming.
    prefix = "reg"

    def __init__(
        self,
        size: int | None = None,
        name: str | None = None,
        init_pos: int = 0,
        bits: list[int] | None = None,
    ):
        """Create a new generic register.

        Args:
            size (int): Optional. The number of bits.
            name (str): Optional. The name of the register. If not provided, a
               unique name will be auto-generated from the register type.
            init_pos (int): Optional. The initial position of the register in
            the circuit.
            bits (list[int]): Optional. A list of bit to be used to
               populate the register.
        """
        if (size, bits) == (None, None) or (
            size is not None and bits is not None
        ):
            raise ValueError(
                f"""Exactly one of the size or bits arguments can be
                "provided. size={size}, bits={bits}."""
            )

        init_pos_int = int(init_pos)

        if bits is not None:
            if isinstance(bits, list):
                for bit in bits:
                    if not isinstance(bit, int):
                        raise TypeError(
                            f"Bits must be integers. bits: {bits}"
                        )
            else:
                raise TypeError(f"Bits must be list. bits: {bits}")
            bits.sort()
            self._bits = bits
            self._size = len(bits)
        else:
            if size is None:
                raise ValueError("Size cannot be None when bits is None.")

            if size < 0:
                raise ValueError(
                    f"Register size must be non-negative. size: {size}"
                )
            self._size = int(size)
            self._bits = [idx + init_pos_int for idx in range(self._size)]

        if name is None:
            name = f"{self.prefix}{next(self.instances_counter)}"

        self._name = str(name)
        self._init_pos = int(init_pos)

        self._repr = (
            f"{self.__class__.__qualname__}({self.size}, '{self.name}')"
        )

        self._bit_indices = None

    @property
    def name(self):
        """Get the register name."""
        return self._name

    @property
    def size(self):
        """Get the register size."""
        return self._size

    def __repr__(self):
        """Return the official string representing the register."""
        return self._repr

    def __len__(self):
        """Return register size."""
        return self._size

    def __getitem__(self, key: int | slice | list):
        """Get qubits from the register.

        Arg:
            key (int or slice or list): index of the bit to be retrieved.

        Returns:
            qubit or clbit positon: a qubit or clbit
            if key is int. If key is a slice, returns a list.
        """
        if not isinstance(key, (int, np.integer, slice, list)):
            raise TypeError(
                "expected integer or \
                                   slice index into register"
            )
        if isinstance(key, slice):
            return self._bits[key]
        elif isinstance(key, list):
            if max(key) < len(self):
                return [self._bits[idx] for idx in key]
            else:
                raise KeyError("register index out of range")
        else:
            return self._bits[key]

    def __iter__(self):
        for idx in range(self._size):
            yield self._bits[idx]

    def index(self, bit):
        """Find the index of the provided bit within this register."""
        if self._bit_indices is None:
            self._bit_indices = {
                bit: idx for idx, bit in enumerate(self._bits)
            }

        try:
            return self._bit_indices[bit]
        except KeyError as err:
            raise KeyError(
                f"Bit {bit} not found \
                             in Register {self}."
            ) from err

    def __eq__(self, other):
        """Two Registers are the same if they are of the same type.

        Args:
            other (Register): other Register

        Returns:
            bool: `self` and `other` are equal.
        """
        if self is other:
            return True

        res = False
        if type(self) is type(other) and self._repr == other._repr:
            if self._bits == other._bits:
                res = True
        return res


class QuantumRegister(Register):
    """Create a quantum register."""

    instances_counter = itertools.count()
    prefix = "q"


class ClassicalRegister(Register):
    """Create a classical register."""

    instances_counter = itertools.count()
    prefix = "c"
