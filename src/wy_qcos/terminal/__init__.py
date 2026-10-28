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

"""QCOS in-browser terminal module (P0).

Exposes the public API used by the FastAPI routes:

* :class:`TerminalConfig` — runtime configuration dataclass.
* :class:`SandboxBuilder` — constructs the ``bwrap`` argv.
* :class:`TerminalSession` — a single pty-bound shell.
* :class:`TerminalSessionManager` — in-memory session registry.
* :class:`TerminalAuditor` — audit log + asciinema recorder.
* :class:`FileService` — per-user file operations under ``/data``.

See ``plans/terminal.md`` for the full design.
"""

from wy_qcos.terminal.audit import TerminalAuditor, TranscriptRecorder
from wy_qcos.terminal.config import TerminalConfig
from wy_qcos.terminal.files import (
    FileNotFoundErrorInSandbox,
    FileService,
    FileServiceError,
    NotEmptyDirectoryError,
    PathEscapeError,
    UploadTooLargeError,
)
from wy_qcos.terminal.manager import (
    TerminalSessionLimitError,
    TerminalSessionManager,
)
from wy_qcos.terminal.sandbox import SandboxBuilder
from wy_qcos.terminal.session import TerminalSession

__all__ = [
    "FileNotFoundErrorInSandbox",
    "FileService",
    "FileServiceError",
    "NotEmptyDirectoryError",
    "PathEscapeError",
    "SandboxBuilder",
    "TerminalAuditor",
    "TerminalConfig",
    "TerminalSession",
    "TerminalSessionLimitError",
    "TerminalSessionManager",
    "TranscriptRecorder",
    "UploadTooLargeError",
]
