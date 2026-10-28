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

"""In-memory registry of live terminal sessions.

The :class:`TerminalSessionManager` is a process-wide singleton. It
enforces per-user and global concurrency limits, and runs a background
reaper task that closes idle sessions.

The manager does NOT own the pty lifecycle end-to-end — the WebSocket
route is responsible for calling :meth:`TerminalSession.start` and
:meth:`TerminalSession.read_loop`. The manager only tracks sessions
and provides lookup/termination.
"""

from __future__ import annotations

import asyncio
import logging
import time

from wy_qcos.terminal.config import TerminalConfig
from wy_qcos.terminal.sandbox import SandboxBuilder
from wy_qcos.terminal.session import TerminalSession

logger = logging.getLogger(__name__)


class TerminalSessionLimitError(RuntimeError):
    """Raised when a new session would exceed a configured limit."""


class TerminalSessionManager:
    """Tracks active terminal sessions and enforces limits."""

    #: Idle-reaper scan interval in seconds.
    REAP_INTERVAL_SECONDS = 60.0

    def __init__(
        self,
        config: TerminalConfig,
        sandbox: SandboxBuilder,
    ):
        self._cfg = config
        self._sandbox = sandbox
        self._sessions: dict[str, TerminalSession] = {}
        self._lock = asyncio.Lock()
        self._reaper_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Singleton accessor
    # ------------------------------------------------------------------

    _INSTANCE: TerminalSessionManager | None = None

    @classmethod
    def instance(cls) -> TerminalSessionManager:
        """Return the process-wide manager, building it lazily.

        Configuration is read from the global ``Config.TERMINAL``
        section on first access. Tests can construct their own manager
        instance directly via the regular constructor.
        """
        if cls._INSTANCE is None:
            from wy_qcos.common.config import Config

            cfg = TerminalConfig.from_config(Config.TERMINAL)
            cls._INSTANCE = cls(cfg, SandboxBuilder(cfg))
        return cls._INSTANCE

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        user_id: str,
        user_name: str,
        cols: int,
        rows: int,
    ) -> TerminalSession:
        """Create and start a new session for the given user.

        Args:
            user_id: QCOS user UUID (used as the sandbox directory).
            user_name: QCOS user login name (used for audit logs).
            cols: Initial terminal width.
            rows: Initial terminal height.

        Returns:
            The newly created :class:`TerminalSession`. The pty has been
            spawned; the caller is responsible for ``read_loop``.

        Raises:
            TerminalSessionLimitError: if a configured cap is reached.
        """
        async with self._lock:
            user_count = sum(
                1 for s in self._sessions.values() if s.user_id == user_id
            )
            if user_count >= self._cfg.max_sessions_per_user:
                raise TerminalSessionLimitError(
                    f"user {user_name} already has "
                    f"{user_count} active terminal sessions "
                    f"(max {self._cfg.max_sessions_per_user})"
                )
            if len(self._sessions) >= self._cfg.max_sessions_total:
                raise TerminalSessionLimitError(
                    f"global terminal session limit reached "
                    f"({self._cfg.max_sessions_total})"
                )

            argv = self._sandbox.build_argv(user_id)
            shell = (
                self._cfg.entry_argv[0]
                if self._cfg.entry_argv
                else self._cfg.default_shell
            )
            session = TerminalSession.new(
                user_id=user_id,
                user_name=user_name,
                shell=shell,
                argv=argv,
            )
            await session.start(cols, rows)
            self._sessions[session.session_id] = session

        self._ensure_reaper_running()
        logger.info(
            "terminal session created: id=%s user=%s(%s) argv=%s",
            session.session_id,
            user_name,
            user_id,
            argv,
        )
        return session

    def get(self, session_id: str) -> TerminalSession | None:
        """Look up a session by id."""
        return self._sessions.get(session_id)

    async def terminate(self, session_id: str | None) -> None:
        """Terminate and unregister a session."""
        if not session_id:
            return
        async with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is None:
            return
        try:
            await session.terminate()
        except Exception:
            logger.exception(
                "error terminating terminal session %s", session_id
            )
        logger.info(
            "terminal session terminated: id=%s user=%s",
            session.session_id,
            session.user_name,
        )

    async def terminate_user_sessions(self, user_id: str) -> int:
        """Terminate all sessions owned by ``user_id``. Returns count."""
        async with self._lock:
            ids = [
                sid
                for sid, s in self._sessions.items()
                if s.user_id == user_id
            ]
        for sid in ids:
            await self.terminate(sid)
        return len(ids)

    # ------------------------------------------------------------------
    # Idle reaper
    # ------------------------------------------------------------------

    def _ensure_reaper_running(self) -> None:
        if self._reaper_task is not None and not self._reaper_task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._reaper_task = loop.create_task(self._reaper_loop())

    async def _reaper_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self.REAP_INTERVAL_SECONDS)
                await self.reap_idle(self._cfg.idle_timeout_seconds)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("terminal idle reaper iteration failed")

    async def reap_idle(self, idle_seconds: int | None = None) -> int:
        """Terminate sessions idle for longer than ``idle_seconds``.

        Returns the number of sessions terminated.
        """
        if idle_seconds is None or idle_seconds <= 0:
            return 0
        now = time.time()
        async with self._lock:
            stale = [
                sid
                for sid, s in self._sessions.items()
                if now - s.last_active_at > idle_seconds
            ]
        for sid in stale:
            logger.info("reaping idle terminal session %s", sid)
            await self.terminate(sid)
        return len(stale)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_sessions(self) -> list[TerminalSession]:
        """Return a snapshot of all live sessions."""
        return list(self._sessions.values())

    async def shutdown(self) -> None:
        """Terminate all sessions and stop the reaper."""
        if self._reaper_task is not None:
            self._reaper_task.cancel()
            try:
                await self._reaper_task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.debug("terminal reaper task error: %s", exc)
            self._reaper_task = None
        async with self._lock:
            ids = list(self._sessions.keys())
        for sid in ids:
            await self.terminate(sid)
