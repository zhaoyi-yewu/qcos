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

"""Factory for creating error mitigation technique instances."""

from __future__ import annotations


from wy_qcos.error_mitigation.mitigation_base import MitigationBase
from wy_qcos.error_mitigation.readout_mitigation import ReadoutMitigation
from wy_qcos.error_mitigation.zne_mitigation import ZNEMitigation


class MitigationFactory:
    """Factory for creating error mitigation technique instances.

    Maintains a registry of mitigation classes and provides methods
    to create instances by name.

    Example:
        >>> factory = MitigationFactory()
        >>> rem = factory.create("readout", calibration_shots=8192)
    """

    _registry: dict[str, type[MitigationBase]] = {}

    def __init__(self):
        self._registry = {
            "readout": ReadoutMitigation,
            "rem": ReadoutMitigation,
            "zne": ZNEMitigation,
        }

    def register(self, name: str, cls: type[MitigationBase]) -> None:
        """Register a mitigation class.

        Args:
            name: Registry name.
            cls: Mitigation class (must extend MitigationBase).

        Raises:
            TypeError: If cls is not a MitigationBase subclass.
        """
        if not issubclass(cls, MitigationBase):
            raise TypeError(f"Invalid mitigation class: {cls}")
        self._registry[name] = cls

    def create(self, name: str, **kwargs) -> MitigationBase:
        """Create a mitigation instance.

        Args:
            name: Registered name of the mitigation technique.
            **kwargs: Constructor arguments.

        Returns:
            MitigationBase instance.

        Raises:
            ValueError: If name is not registered.
        """
        if name not in self._registry:
            available = list(set(self._registry.keys()))
            raise ValueError(
                f"Unknown mitigation technique: '{name}'. "
                f"Available: {available}"
            )
        cls = self._registry[name]
        return cls(**kwargs)

    def list_available(self) -> list[str]:
        """List registered mitigation technique names."""
        return sorted(set(self._registry.keys()))
