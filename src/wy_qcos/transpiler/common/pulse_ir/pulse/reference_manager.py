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
"""Management of schedule block references."""

from collections import UserDict
from wy_qcos.transpiler.common.pulse_ir.pulse.exceptions import PulseError


class ReferenceManager(UserDict):
    """Dictionary wrapper to manage pulse schedule references."""

    def unassigned(self) -> tuple[tuple[str, ...], ...]:
        """Get the keys of unassigned references.

        Returns:
            Tuple of reference keys.
        """
        keys = []
        for key, value in self.items():
            if value is None:
                keys.append(key)
        return tuple(keys)

    def __setitem__(self, key, value):
        if key in self and self[key] is not None:
            # Check subroutine conflict.
            if self[key] != value:
                raise PulseError(
                    f"Subroutine {key} is already assigned to the "
                    "reference of the current scope; however, the newly "
                    "assigned schedule conflicts with the existing "
                    "schedule. "
                    "This operation was not successfully done."
                )
            return
        super().__setitem__(key, value)

    def __repr__(self):
        keys = ", ".join(map(repr, self.keys()))
        return f"{self.__class__.__name__}(references=[{keys}])"

    def __str__(self):
        out = f"{self.__class__.__name__}:"
        for key, reference in self.items():
            prog_repr = repr(reference)
            if len(prog_repr) > 50:
                prog_repr = prog_repr[:50] + "..."
            out += f"\n  - {repr(key)}: {prog_repr}"
        return out
