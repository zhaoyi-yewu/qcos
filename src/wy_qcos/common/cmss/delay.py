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

"""Circuit-level Delay instruction."""

from wy_qcos.common.cmss.base_operation import (
    BaseOperation,
    OperationType,
)


class Delay(BaseOperation):
    """Delay instruction that idles a qubit for a specified duration."""

    def __init__(self, duration, unit="dt", name="delay"):
        super().__init__(
            name=name,
            targets=[],
            operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
        )
        self._duration = duration
        self._unit = unit

    @property
    def duration(self):
        """Return the duration of the delay."""
        return self._duration

    @duration.setter
    def duration(self, value):
        """Set the duration of the delay."""
        self._duration = value

    @property
    def unit(self):
        """Return the time unit of the duration."""
        return self._unit

    @property
    def params(self):
        """Return instruction params."""
        return [self._duration]

    def __repr__(self):
        return f"Delay(duration={self._duration}, unit='{self._unit}')"


__all__ = ["Delay"]
