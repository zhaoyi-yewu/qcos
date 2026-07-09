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

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Qiskit-compatible exception and warning types."""


class QiskitError(Exception):
    """Base class for errors raised by Qiskit."""

    def __init__(self, *message):
        """Set the error message."""
        super().__init__(" ".join(message))
        self.message = " ".join(message)

    def __str__(self):
        """Return the message."""
        return repr(self.message)


class QiskitUserConfigError(QiskitError):
    """Raised when an error is encountered reading a user config file."""

    message = "User config invalid"


class MissingOptionalLibraryError(QiskitError, ImportError):
    """Raised when an optional library is missing."""

    def __init__(
        self,
        libname: str,
        name: str,
        pip_install: str | None = None,
        msg: str | None = None,
    ) -> None:
        """Set the error message.

        Args:
            libname: Name of missing library
            name: Name of class, function, module that uses this library
            pip_install: pip install command, if any
            msg: Descriptive message, if any
        """
        message = [f"The '{libname}' library is required to use '{name}'."]
        if pip_install:
            message.append(f"You can install it with '{pip_install}'.")
        if msg:
            message.append(f" {msg}.")

        super().__init__(" ".join(message))
        self.message = " ".join(message)

    def __str__(self) -> str:
        """Return the message."""
        return repr(self.message)


class InvalidFileError(QiskitError):
    """Raised when the file provided is not valid for the specific task."""


class QiskitWarning(UserWarning):
    """Common subclass for Qiskit-specific warnings."""


class OptionalDependencyImportWarning(QiskitWarning):
    """Raised when an optional library raises errors during its import."""

    # Not a subclass of `ImportWarning` because those are hidden by default.


class ExperimentalWarning(QiskitWarning):
    """Raised when an experimental feature is being used."""
