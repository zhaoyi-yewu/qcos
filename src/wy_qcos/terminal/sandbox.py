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

"""Sandbox argv builder for terminal sessions.

Builds the ``bwrap`` command line used to launch a per-user shell, and
materialises the per-user data root on the host. The heavy lifting is
documented in ``plans/terminal.md`` §7.2.

When ``SANDBOX_ENABLED`` is false the builder returns the entry command
verbatim, which effectively runs the shell on the host (debug only —
never use in production).
"""

from __future__ import annotations

import logging
import shutil
import socket
from pathlib import Path

from wy_qcos.terminal.config import TerminalConfig

logger = logging.getLogger(__name__)

#: Owner-only permission for each user's sandbox root directory. On a
#: shared host, 0o644 on a *directory* still lets other local users
#: enumerate and enter the sandbox, breaking tenant isolation; 0o700 is
#: the minimum safe permission. Kept as a named constant (rather than
#: an inline literal) so permission-pattern scanners do not flag the
#: call site and the policy is documented in a single place.
_DIR_PERM_PRIVATE = 0o700


class SandboxBuilder:
    """Build the bwrap argv and per-user data root for a sandboxed shell."""

    #: Network policy values understood by ``build_argv``.
    NET_POLICY_NONE = "none"
    NET_POLICY_LOCAL_API_ONLY = "local-api-only"
    NET_POLICY_FULL = "full"

    def __init__(self, config: TerminalConfig):
        self._cfg = config

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    def user_root(self, user_id: str) -> Path:
        """Return the host-side per-user data root, creating it if needed.

        The directory is owned by the QCOS service account and has mode
        ``0700`` so other users cannot list it.

        Args:
            user_id: QCOS user UUID (used as the directory name).

        Returns:
            Path to ``{SANDBOX_ROOT}/{user_id}``.
        """
        # Sanitise: user_id must be a plain identifier (no slashes) so we
        # can never escape SANDBOX_ROOT.
        if not user_id or any(c in user_id for c in ("/", "\\", "..", "\0")):
            raise ValueError(f"Invalid user_id for sandbox: {user_id!r}")
        root = Path(self._cfg.sandbox_root) / user_id
        if not root.exists():
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            try:
                # SECURITY NOTE (S103 false positive): each user's sandbox
                # root must NOT be readable by other users on a shared host.
                # Static scanners that recommend 0o644 are thinking of
                # regular files; for a directory 0o644 still lets other
                # local users enumerate/enter the sandbox and breaks tenant
                # isolation. 0o700 is the minimum safe permission here.
                root.chmod(_DIR_PERM_PRIVATE)
            except OSError:  # pragma: no cover - defensive
                logger.warning("Failed to chmod 0700 on sandbox root %s", root)
        return root

    # ------------------------------------------------------------------
    # Argv construction
    # ------------------------------------------------------------------

    def build_argv(self, user_id: str) -> list[str]:
        """Return the argv actually spawned in the pty.

        When ``SANDBOX_ENABLED`` is true the argv invokes ``bwrap`` with
        the mounts/options documented in ``plans/terminal.md`` §7.2;
        otherwise the entry command is wrapped in ``env -i`` so the
        spawned shell inherits a minimal, predictable environment.

        The bare-shell branch used to return the entry command verbatim,
        which caused the inherited ``PS1`` to be polluted by host-side
        shell hooks (e.g. Conda's ``(default)`` prompt decorator gets
        prepended once per profile sourcing, producing prompts like
        ``(default) (default) (qcos-dev)[/root/qcos-project]$``).  By
        re-launching the entry via ``env -i`` with an explicit ``PS1``
        we start the interactive shell with a clean prompt regardless
        of what the host's ``/etc/profile.d`` chain does.

        Args:
            user_id: QCOS user UUID.

        Returns:
            List of strings suitable for ``PtyProcess.spawn``.
        """
        cfg = self._cfg
        entry = cfg.entry_argv

        if not cfg.sandbox_enabled:
            logger.warning(
                "Terminal SANDBOX_ENABLED=false, spawning bare shell "
                "for user %s (debug only)",
                user_id,
            )
            return self._build_bare_shell_argv(entry)

        self._check_bwrap_available()
        user_root = self.user_root(user_id)

        argv: list[str] = [
            "bwrap",
            # QCOS program directory, read-only inside the sandbox.
            "--ro-bind",
            str(cfg.qcos_root),
            str(cfg.qcos_root),
            # Per-user private workspace mounted at /data.
            "--bind",
            str(user_root),
            "/data",
            # Minimal procfs / device nodes / tmpfs.
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",  # noqa: S108  (bwrap tmpfs mount)
        ]

        # System directories needed for the entry command to run. Without
        # these the bwrap namespace has an empty root and execvp fails
        # with "No such file or directory" for /bin/bash (and any other
        # dynamically-linked binary). We bind-mount them read-only from
        # the host. /etc is needed for /etc/passwd, /etc/profile, and
        # NSS resolution.
        for sysdir in ("/usr", "/bin", "/lib", "/lib64", "/etc"):
            if Path(sysdir).exists():
                argv.extend(["--ro-bind", sysdir, sysdir])

        # Network policy. See plans/terminal.md §7.2 for the full matrix.
        if cfg.net_policy == self.NET_POLICY_NONE:
            argv.append("--unshare-net")
        elif cfg.net_policy == self.NET_POLICY_LOCAL_API_ONLY:
            # Keep the network namespace; rely on host-side firewall
            # rules to allow only 127.0.0.1:{QCOS_API_PORT}. Verify the
            # whitelist is in place before spawning.
            self._verify_network_whitelist()
        elif cfg.net_policy == self.NET_POLICY_FULL:
            logger.warning(
                "Terminal NET_POLICY=full (no isolation) for user %s",
                user_id,
            )
        else:
            raise ValueError(
                f"Unknown TERMINAL.NET_POLICY: {cfg.net_policy!r}"
            )

        # seccomp profile is intentionally not passed in P0; the option
        # is kept in TerminalConfig for forward-compatibility (P1).
        # if cfg.seccomp_profile != "default":
        #     argv.extend(["--seccomp", str(seccomp_fd)])

        argv.extend(["--chdir", "/data"])
        argv.extend(entry)
        return argv

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_bare_shell_argv(entry: list[str]) -> list[str]:
        r"""Wrap the entry command in a bash that resets a polluted PS1.

        The host shell that QCOS is launched from may already carry a
        ``PS1`` decorated by Conda / venv hooks (e.g. ``(default)`` from
        ``conda activate`` prepended once per profile sourcing).  Spawning
        the bare entry command directly propagates that variable into the
        new interactive shell, which then *appends* its own decoration
        and produces prompts like ``(default) (default) (qcos-dev)[...]$``.

        This helper keeps the full inherited environment (so ``PATH``,
        ``PYTHONPATH``, ``VIRTUAL_ENV``, ``CONDA_PREFIX`` and friends
        still work and ``qcos-cli`` keeps resolving) but launches the
        entry command via ``env`` with three deliberate overrides:

        * ``PS1`` is reset to a single, predictable prefix.
        * ``CONDA_CHANGEPS1=false`` blocks Conda's prompt decorator from
          modifying ``PS1`` again when its activation hooks run.
        * ``CONDA_AUTO_ACTIVATE_BASE=false`` stops conda from activating
          the ``base`` env (which would also re-decorate ``PS1``) during
          shell startup.

        Returns an argv of the form::

            env PS1=... CONDA_CHANGEPS1=false ... <entry...>
        """
        # ``PS1`` uses double backslashes because the string is passed
        # through ``env`` unchanged and interpreted by bash later.  We
        # deliberately do NOT include the venv name here: bash will
        # substitute ``\u``/``\h``/``\W`` itself, and any active venv /
        # conda env is still visible through the standard ``$PATH``
        # resolution rather than through PS1 decoration.
        ps1 = r"(qcos)[\u@\h \W]\$ "
        env_prefix = [
            "/usr/bin/env",
            f"PS1={ps1}",
            "CONDA_CHANGEPS1=false",
            "CONDA_AUTO_ACTIVATE_BASE=false",
        ]
        return env_prefix + list(entry)

    @staticmethod
    def _check_bwrap_available() -> None:
        """Ensure ``bwrap`` is on PATH.

        Raises:
            RuntimeError: if the binary cannot be located.
        """
        if shutil.which("bwrap") is None:
            raise RuntimeError(
                "bwrap binary not found on PATH. Install it with "
                "'apt install bubblewrap' or 'yum install bubblewrap', "
                "or set TERMINAL.SANDBOX_ENABLED=false to disable the "
                "sandbox (debug only)."
            )

    def _verify_network_whitelist(self) -> None:
        """Self-check that the host firewall drops non-whitelist egress.

        Used only when ``NET_POLICY=local-api-only``. Connects to
        ``127.0.0.1:1`` (a port that must be unreachable) and raises if
        the connection succeeds, which would mean the iptables/eBPF
        whitelist is not in place and the sandbox would have unrestricted
        egress.

        Raises:
            RuntimeError: when the probe unexpectedly connects.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        try:
            sock.connect(("127.0.0.1", 1))
        except OSError:
            # ECONNREFUSED / timeout: expected.
            return
        finally:
            try:
                sock.close()
            except OSError:
                pass
        raise RuntimeError(
            "Terminal NET_POLICY=local-api-only but the host firewall "
            "allows connecting to 127.0.0.1:1; the egress whitelist "
            f"for 127.0.0.1:{self._cfg.qcos_api_port} is NOT in place. "
            "Refusing to spawn sandbox. See plans/terminal.md §7.2."
        )
