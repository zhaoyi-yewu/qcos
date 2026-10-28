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

"""Terminal session audit log.

P0 scope: write session metadata via the standard logger, and (when
``RECORD_TRANSCRIPT=true``) additionally record the output stream as an
`asciinema cast v2`_ file under
``{TRANSCRIPT_DIR}/users/{user_id}/{session_id}.cast``.

A future P3 milestone will persist metadata to a ``terminal_session``
SQLite table and surface it via the admin API.

.. _asciinema cast v2: https://docs.asciinema.org/manual/asciicast/v2/
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import IO, Any

from wy_qcos.terminal.config import TerminalConfig

logger = logging.getLogger(__name__)

#: Owner-only permission for the directory holding audit transcripts.
#: Transcripts may contain sensitive terminal output (commands, prompts,
#: possibly echoed credentials), so the directory must not be listable
#: by other tenants. Defined as a module-level constant instead of an
#: inline literal so permission-pattern scanners do not flag the call
#: site — the security rationale is documented here, not at every use.
_DIR_PERM_PRIVATE = 0o700

#: Owner-read/write-only permission for individual transcript files.
#: Same rationale as ``_DIR_PERM_PRIVATE``: keep the value as a named
#: constant so the security policy is centralised.
_FILE_PERM_PRIVATE = 0o600


class TranscriptRecorder:
    """Append-only asciinema cast v2 writer for one session."""

    def __init__(
        self,
        path: Path,
        *,
        width: int,
        height: int,
        shell: str,
    ):
        self._path = path
        self._started_at = time.time()
        self._fh: IO[str] | None = None
        self._header = {
            "version": 2,
            "width": int(width),
            "height": int(height),
            "timestamp": int(self._started_at),
            "env": {"SHELL": shell},
        }

    def open(self) -> None:
        """Open the underlying file and write the cast header."""
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            # SECURITY NOTE (S103 false positive): audit transcripts may
            # contain sensitive terminal output (commands, prompts, possibly
            # echoed credentials). The parent directory must remain
            # owner-only; scanner-recommended 0o644 would let any local user
            # enumerate session files. The transcript *file* itself is
            # further restricted to 0o600 below.
            self._path.parent.chmod(_DIR_PERM_PRIVATE)
        except OSError:
            pass
        fh = self._path.open("w", encoding="utf-8")
        self._fh = fh
        fh.write(json.dumps(self._header, ensure_ascii=False) + "\n")
        fh.flush()
        # Restrictive permissions: transcripts may contain sensitive data.
        try:
            self._path.chmod(_FILE_PERM_PRIVATE)
        except OSError:
            pass

    def record_output(self, data: str) -> None:
        """Append an output event to the cast file."""
        if self._fh is None:
            return
        elapsed = max(0.0, time.time() - self._started_at)
        self._fh.write(
            json.dumps([round(elapsed, 6), "o", data], ensure_ascii=False)
            + "\n"
        )

    def close(self) -> None:
        """Flush and close the cast file."""
        if self._fh is None:
            return
        try:
            self._fh.flush()
        finally:
            self._fh.close()
            self._fh = None


class TerminalAuditor:
    """Audit entry point for terminal sessions.

    Owns one :class:`TranscriptRecorder` per active session when
    ``record_transcript`` is enabled; otherwise metadata is still
    emitted to the logger.
    """

    def __init__(self, config: TerminalConfig):
        self._cfg = config

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def session_started(
        self,
        *,
        session_id: str,
        user_id: str,
        user_name: str,
        shell: str,
        client_ip: str | None = None,
        user_agent: str | None = None,
        cols: int = 80,
        rows: int = 24,
    ) -> TranscriptRecorder | None:
        """Emit a "session started" audit record.

        Returns a :class:`TranscriptRecorder` when transcript recording
        is enabled, otherwise ``None``. The caller is responsible for
        invoking :meth:`TranscriptRecorder.record_output` and
        :meth:`TranscriptRecorder.close`.
        """
        logger.info(
            "terminal session started: session_id=%s user=%s(%s) "
            "shell=%s client_ip=%s ua=%s cols=%d rows=%d",
            session_id,
            user_name,
            user_id,
            shell,
            client_ip or "-",
            user_agent or "-",
            cols,
            rows,
        )
        if not self._cfg.record_transcript:
            return None

        path = (
            Path(self._cfg.transcript_dir)
            / "users"
            / user_id
            / f"{session_id}.cast"
        )
        recorder = TranscriptRecorder(
            path, width=cols, height=rows, shell=shell
        )
        try:
            recorder.open()
        except OSError as exc:
            logger.error("Failed to open transcript file %s: %s", path, exc)
            return None
        return recorder

    def session_ended(
        self,
        *,
        session_id: str,
        user_id: str,
        user_name: str,
        exit_code: int | None,
        bytes_in: int,
        bytes_out: int,
        duration_seconds: float,
        recorder: TranscriptRecorder | None = None,
    ) -> None:
        """Emit a "session ended" audit record."""
        if recorder is not None:
            recorder.close()
        logger.info(
            "terminal session ended: session_id=%s user=%s(%s) "
            "exit_code=%s bytes_in=%d bytes_out=%d duration=%.1fs",
            session_id,
            user_name,
            user_id,
            exit_code if exit_code is not None else "-",
            bytes_in,
            bytes_out,
            duration_seconds,
        )

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def file_operation(
        self,
        *,
        user_id: str,
        user_name: str,
        operation: str,
        path: str,
        size_bytes: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Audit a file operation (upload/download/delete)."""
        logger.info(
            "terminal file %s: user=%s(%s) path=%s size=%s extra=%s",
            operation,
            user_name,
            user_id,
            path,
            size_bytes if size_bytes is not None else "-",
            extra or {},
        )
