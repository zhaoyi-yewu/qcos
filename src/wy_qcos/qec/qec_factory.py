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

from wy_qcos.qec.quantum_code_base import QuantumCodeBase
from wy_qcos.qec.shor_code import ShorCode


class QecFactory:
    """Factory class for creating quantum error correction code instances.

    This class maintains a registry of quantum error correction codes
    and provides a method to create instances by name.

    Example:
        >>> factory = QecFactory()
        >>> shor_code = factory.create("shor")
    """

    def __init__(self, code_dict: dict[str, type[QuantumCodeBase]] = None):
        """Initialize the QEC factory.

        Args:
            code_dict: Optional dictionary mapping code names to code classes.
                       If not provided, a default dictionary with "shor"
                       is used.
        """
        self._code_dict: dict[str, type[QuantumCodeBase]] = {}

        # Use provided code_dict or initialize with default codes
        if code_dict is not None:
            self._code_dict = code_dict.copy()
        else:
            # Default registration
            self.register("shor", ShorCode)

    def register(self, name: str, code_class: type[QuantumCodeBase]) -> None:
        """Register a quantum error correction code class.

        Args:
            name: The name to register the code under.
            code_class: The quantum error correction code class to register.
        """
        if not issubclass(code_class, QuantumCodeBase):
            raise TypeError(f"Code class invalid, got {code_class}")
        self._code_dict[name] = code_class

    def unregister(self, name: str) -> None:
        """Unregister a quantum error correction code.

        Args:
            name: The name of the code to unregister.
        """
        if name not in self._code_dict:
            raise KeyError(f"Code '{name}' is not registered")
        del self._code_dict[name]

    def create(self, name: str) -> QuantumCodeBase:
        """Create an instance of a quantum error correction code.

        Args:
            name: The name of the code to create.

        Returns:
            An instance of the requested quantum error correction code.
        """
        if name not in self._code_dict:
            available_codes = list(self._code_dict.keys())
            raise ValueError(
                f"Unknown quantum error correction code: '{name}'. "
                f"Available codes: {available_codes}"
            )

        code_class = self._code_dict[name]
        return code_class()

    def list_codes(self) -> list:
        """List all registered quantum error correction code names.

        Returns:
            A list of registered code names.
        """
        return list(self._code_dict.keys())

    def get_registry(self) -> dict[str, type[QuantumCodeBase]]:
        """Get the code registry.

        Returns:
            A copy of the internal code registry dictionary.
        """
        return self._code_dict.copy()
