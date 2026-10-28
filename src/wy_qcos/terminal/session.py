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

"""Single interactive terminal session bound to a pty.

Wraps ``ptyprocess.PtyProcessUnicode`` with asyncio-friendly helpers:

* ``read_loop`` registers the pty's master fd with the running event
  loop via :meth:`asyncio.AbstractEventLoop.add_reader` (Linux
  fast-path); each readable event is forwarded to a caller-provided
  coroutine.
* ``write``/``resize``/``terminate`` are safe to call from the WS
  handler task.

The class is intentionally minimal — the WS route owns the lifecycle.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

# ptyprocess is Linux/Unix only. Import lazily inside ``start`` so that
# importing this module on Windows still succeeds (we just can't spawn).
try:  # pragma: no cover - import guard
    from ptyprocess import PtyProcessUnicode as _PtyProcessUnicode
except ImportError:  # pragma: no cover - on Windows
    _PtyProcessUnicode = None

# Public alias kept so ``start`` can raise a clear error on platforms
# without ptyprocess (e.g. Windows dev machines). Using a single
# assignment silences mypy's ``no-redef`` diagnostic.
PtyProcessUnicode: Any = _PtyProcessUnicode


# Type alias for the async output callback.
OutputCallback = Callable[[str], Awaitable[None]]
ExitCallback = Callable[[int | None], Awaitable[None]]


class TerminalSession:
    """A single pty-bound interactive shell session."""

    #: Bytes to read per event-loop callback. Matches default xterm.js
    #: chunking and keeps latency low.
    READ_CHUNK = 65536

    def __init__(
        self,
        *,
        session_id: str,
        user_id: str,
        user_name: str,
        shell: str,
        argv: list[str],
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.user_name = user_name
        self.shell = shell
        self.argv = list(argv)
        self.pty: Any = None  # PtyProcessUnicode once started
        self.created_at = time.time()
        self.last_active_at = self.created_at
        self.bytes_in = 0
        self.bytes_out = 0
        self.exit_code: int | None = None
        self._closing = False

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def new(
        cls,
        *,
        user_id: str,
        user_name: str,
        shell: str,
        argv: list[str],
    ) -> TerminalSession:
        """Build a session with a fresh UUID4 session id."""
        return cls(
            session_id=uuid.uuid4().hex,
            user_id=user_id,
            user_name=user_name,
            shell=shell,
            argv=argv,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self, cols: int, rows: int) -> None:
        """Spawn the underlying pty process.

        Args:
            cols: Initial terminal width in columns.
            rows: Initial terminal height in rows.

        Raises:
            RuntimeError: if ptyprocess is unavailable on this platform.
        """
        if PtyProcessUnicode is None:
            raise RuntimeError("ptyprocess is not available on this platform")
        # ptyprocess.spawn accepts ``dimensions=(rows, cols)``.
        self.pty = PtyProcessUnicode.spawn(
            self.argv, dimensions=(int(rows), int(cols))
        )
        self.last_active_at = time.time()

    def is_alive(self) -> bool:
        """Return True while the child process is running."""
        if self.pty is None:
            return False
        try:
            return bool(self.pty.isalive())
        except Exception:  # pragma: no cover - defensive
            return False

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def write(self, data: str) -> None:
        """Write user input to the pty."""
        if not self.pty or self._closing:
            return
        try:
            self.pty.write(data)
            self.bytes_in += len(data.encode("utf-8", errors="ignore"))
            self.last_active_at = time.time()
        except (EOFError, OSError) as exc:
            logger.debug(
                "terminal %s: write failed (%s)", self.session_id, exc
            )

    def resize(self, cols: int, rows: int) -> None:
        """Update the pty's window size (TIOCSWINSZ)."""
        if not self.pty:
            return
        try:
            # ptyprocess uses (rows, cols) ordering.
            self.pty.setwinsize(int(rows), int(cols))
            self.last_active_at = time.time()
        except (OSError, AttributeError) as exc:
            logger.debug(
                "terminal %s: resize failed (%s)", self.session_id, exc
            )

    async def read_loop(
        self,
        on_output: OutputCallback,
        on_exit: ExitCallback | None = None,
    ) -> None:
        """Forward pty output to ``on_output`` until EOF.

        Registers the pty master fd with the running event loop using
        :meth:`asyncio.AbstractEventLoop.add_reader`. Each readable event
        is converted to text via :class:`PtyProcessUnicode` and handed to
        ``on_output``. On EOF (child process exit) ``on_exit`` is called
        with the exit code and the loop terminates.

        Args:
            on_output: Async callable invoked with each output chunk.
            on_exit: Async callable invoked once when the pty closes.
        """
        if self.pty is None:
            raise RuntimeError("session not started")

        loop = asyncio.get_running_loop()
        done: asyncio.Future[int | None] = loop.create_future()
        fd = self.pty.fd

        def _on_readable() -> None:
            if done.done():
                return
            try:
                # PtyProcessUnicode.read returns str; may raise EOFError.
                data = self.pty.read(self.READ_CHUNK)
            except EOFError:
                _finish(self._collect_exit_code())
                return
            except (OSError, UnicodeDecodeError) as exc:
                logger.debug(
                    "terminal %s: read error (%s)",
                    self.session_id,
                    exc,
                )
                _finish(self._collect_exit_code())
                return
            if not data:
                # Nothing read (rare); let the loop come back later.
                return
            self.bytes_out += len(data.encode("utf-8", errors="ignore"))
            self.last_active_at = time.time()
            # Schedule the user callback; read_loop must stay sync.
            asyncio.ensure_future(self._safe_emit(on_output, data))

        def _finish(code: int | None) -> None:
            if done.done():
                return
            try:
                loop.remove_reader(fd)
            except Exception as exc:
                logger.debug(
                    "terminal %s: remove_reader failed: %s",
                    self.session_id,
                    exc,
                )
            self.exit_code = code
            done.set_result(code)

        loop.add_reader(fd, _on_readable)
        try:
            code = await done
        finally:
            try:
                loop.remove_reader(fd)
            except Exception as exc:
                logger.debug(
                    "terminal %s: final remove_reader failed: %s",
                    self.session_id,
                    exc,
                )
        if on_exit is not None:
            try:
                await on_exit(code)
            except Exception:
                logger.exception(
                    "terminal %s: on_exit callback raised",
                    self.session_id,
                )

    async def _safe_emit(self, callback: OutputCallback, data: str) -> None:
        try:
            await callback(data)
        except Exception:
            logger.exception(
                "terminal %s: output callback raised", self.session_id
            )

    def _collect_exit_code(self) -> int | None:
        """Best-effort read of the child's exit status."""
        if self.pty is None:
            return None
        try:
            # ptyprocess exposes ``exitstatus`` after wait().
            status = getattr(self.pty, "exitstatus", None)
            if status is not None:
                return int(status)
            # Fallback: poll without blocking.
            if hasattr(self.pty, "wait"):
                return int(self.pty.wait())
        except Exception as exc:
            logger.debug(
                "terminal %s: failed to collect exit code: %s",
                self.session_id,
                exc,
            )
        return None

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    async def terminate(self, grace_seconds: float = 2.0) -> None:
        """Terminate the pty, escalating SIGTERM -> SIGKILL.

        Args:
            grace_seconds: How long to wait after SIGTERM before sending
                SIGKILL. Defaults to 2 seconds.
        """
        if self._closing:
            return
        self._closing = True
        if self.pty is None:
            return
        try:
            if self.is_alive():
                try:
                    self.pty.terminate(force=False)
                except Exception as exc:
                    # ptyprocess may not have ``terminate`` on all
                    # platforms; fall back to kill().
                    logger.debug(
                        "terminal %s: terminate() failed (%s); "
                        "falling back to SIGTERM",
                        self.session_id,
                        exc,
                    )
                    try:
                        self.pty.kill(signal.SIGTERM)
                    except Exception as exc2:
                        logger.debug(
                            "terminal %s: SIGTERM failed: %s",
                            self.session_id,
                            exc2,
                        )
                # Wait up to ``grace_seconds`` for the child to exit.
                deadline = time.monotonic() + grace_seconds
                while time.monotonic() < deadline and self.is_alive():
                    await asyncio.sleep(0.05)
                if self.is_alive():
                    try:
                        self.pty.kill(signal.SIGKILL)
                    except Exception as exc:
                        logger.debug(
                            "terminal %s: SIGKILL failed: %s",
                            self.session_id,
                            exc,
                        )
        finally:
            try:
                self.pty.close(force=True)
            except Exception as exc:
                logger.debug(
                    "terminal %s: pty close failed: %s",
                    self.session_id,
                    exc,
                )
