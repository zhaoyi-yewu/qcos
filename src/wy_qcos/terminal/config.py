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

"""Terminal module configuration.

Defines the runtime configuration used by terminal-related helpers
(:class:`~wy_qcos.terminal.sandbox.SandboxBuilder`,
:class:`~wy_qcos.terminal.manager.TerminalSessionManager`,
:class:`~wy_qcos.terminal.files.FileService`, etc.).

The configuration is loaded once from the global ``Config.TERMINAL``
section via :meth:`TerminalConfig.from_config`, and then passed to the
components explicitly. This keeps the terminal module loosely coupled
from the rest of the QCOS configuration system.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from wy_qcos.common.config import TerminalSection


@dataclass(frozen=True)
class TerminalConfig:
    """Runtime configuration for the terminal module.

    The fields mirror the ``[TERMINAL]`` section of ``qcos.toml``. See
    ``plans/terminal.md`` §7.4 for the authoritative list.
    """

    enabled: bool = False
    idle_timeout_seconds: int = 1800
    max_sessions_per_user: int = 4
    max_sessions_total: int = 128
    default_shell: str = "/bin/bash"
    entry_command: str = "/bin/bash"
    sandbox_enabled: bool = True
    sandbox_root: Path = Path("/var/qcos/users")
    qcos_root: Path = Path("/opt/qcos")
    seccomp_profile: str = "default"
    net_policy: str = "none"  # one of: none / local-api-only / full
    qcos_api_port: int = 8000
    max_upload_mb: int = 100
    record_transcript: bool = False
    transcript_dir: Path = Path("/var/log/qcos/terminal")

    # Backward-compat derived values (computed lazily).
    _entry_argv: list[str] = field(
        init=False, repr=False, compare=False, default_factory=list
    )

    def __post_init__(self) -> None:
        # Normalize to Path (pydantic may hand us str).
        object.__setattr__(self, "sandbox_root", Path(self.sandbox_root))
        object.__setattr__(self, "qcos_root", Path(self.qcos_root))
        object.__setattr__(self, "transcript_dir", Path(self.transcript_dir))
        # Parse ENTRY_COMMAND to argv once. Use shlex so that quoted
        # arguments are preserved (e.g. ``qcos-cli interactive --debug``).
        argv = shlex.split(self.entry_command) if self.entry_command else []
        if not argv:
            argv = [self.default_shell]
        object.__setattr__(self, "_entry_argv", list(argv))

    @property
    def entry_argv(self) -> list[str]:
        """Return the entry argv spawned inside the sandbox."""
        return list(self._entry_argv)

    @classmethod
    def from_config(cls, section: TerminalSection) -> TerminalConfig:
        """Build a :class:`TerminalConfig` from a Config section.

        Args:
            section: ``Config.TERMINAL`` (a :class:`TerminalSection`).

        Returns:
            TerminalConfig populated with the section's values.
        """
        # QCOS_API_PORT became optional in the schema: when omitted we
        # fall back to the API server's listen port so operators don't
        # have to keep two fields in sync. Read it lazily to avoid a
        # circular import with wy_qcos.common.config at module load time.
        api_port_override = section.QCOS_API_PORT
        if api_port_override is None:
            # Import here to keep terminal/config.py decoupled from the
            # global Config singleton at module load time.
            from wy_qcos.common.config import Config

            api_port_override = Config.API_SERVER.API_SERVER_LISTEN_PORT
        return cls(
            enabled=bool(section.ENABLED),
            idle_timeout_seconds=int(section.IDLE_TIMEOUT_SECONDS),
            max_sessions_per_user=int(section.MAX_SESSIONS_PER_USER),
            max_sessions_total=int(section.MAX_SESSIONS_TOTAL),
            default_shell=str(section.DEFAULT_SHELL),
            entry_command=str(section.ENTRY_COMMAND),
            sandbox_enabled=bool(section.SANDBOX_ENABLED),
            sandbox_root=Path(section.SANDBOX_ROOT),
            qcos_root=Path(section.QCOS_ROOT),
            seccomp_profile=str(section.SECCOMP_PROFILE),
            net_policy=str(section.NET_POLICY),
            qcos_api_port=int(api_port_override),
            max_upload_mb=int(section.MAX_UPLOAD_MB),
            record_transcript=bool(section.RECORD_TRANSCRIPT),
            transcript_dir=Path(section.TRANSCRIPT_DIR),
        )
