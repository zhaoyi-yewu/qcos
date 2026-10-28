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

"""Per-user file service scoped to the sandbox ``/data`` directory.

All paths are interpreted as relative to the per-user sandbox root on
the host (``{SANDBOX_ROOT}/{user_id}/``). The service resolves each
incoming path with :meth:`pathlib.Path.resolve` and rejects any path
that escapes the user's root.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: Owner-only permission for the per-user sandbox root directory.
#: 0o700 is the *minimum* safe permission on a multi-tenant host: the
#: "read" bit on a directory grants listing, so 0o644 would let any
#: local user enumerate and read this user's terminal files. The value
#: lives in a named constant so the policy decision is documented in a
#: single place rather than scattered across call sites.
_DIR_PERM_PRIVATE = 0o700


class FileServiceError(Exception):
    """Base class for FileService errors."""


class PathEscapeError(FileServiceError, PermissionError):
    """The requested path escapes the per-user sandbox root."""


class FileNotFoundErrorInSandbox(FileServiceError, FileNotFoundError):
    """The requested path does not exist inside the sandbox."""


class UploadTooLargeError(FileServiceError):
    """The uploaded payload exceeds MAX_UPLOAD_MB."""


class NotEmptyDirectoryError(FileServiceError):
    """Refusing to delete a non-empty directory."""


class FileService:
    """File operations scoped to one user's sandbox root."""

    def __init__(
        self, user_id: str, sandbox_root: Path | str, max_upload_mb: int
    ):
        self._user_id = user_id
        self._root = Path(sandbox_root) / user_id
        self._max_upload_bytes = int(max_upload_mb) * 1024 * 1024
        # Materialise root on first use to mirror SandboxBuilder.
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            # SECURITY NOTE (S103 false positive): 0o700 is the *minimum*
            # safe permission for a per-user sandbox root on a multi-tenant
            # host. Scanners recommending 0o644 are thinking of regular
            # *files*; on a *directory*, 0o644 still grants any local user
            # the ability to enumerate and read this user's terminal files
            # (directory "read" bit = listing). 0o700 enforces tenant
            # isolation and matches OpenSSH `~/.ssh` semantics.
            self._root.chmod(_DIR_PERM_PRIVATE)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def root(self) -> Path:
        """Absolute path of the user's sandbox root on the host."""
        return self._root

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def resolve_filename(self, rel_path: str | None) -> str:
        """Return the basename of ``rel_path`` after sandbox resolution.

        Performs the same path-escape validation as :meth:`_resolve` so
        callers cannot probe the host filesystem by supplying crafted
        relative paths. Intended for HTTP layer code that needs a safe
        ``Content-Disposition`` filename without accessing the private
        ``_resolve`` helper.

        Args:
            rel_path: Caller-supplied relative path.

        Returns:
            The resolved basename, or ``"download"`` when the input
            resolves to the user root itself (no trailing component).

        Raises:
            PathEscapeError: if the resolved path is outside the root.
        """
        return self._resolve(rel_path).name or "download"

    def _resolve(self, rel_path: str | None) -> Path:
        """Resolve ``rel_path`` against the user root.

        Args:
            rel_path: Caller-supplied relative path. ``""``/``None``/
                ``"/"`` all map to the user root itself.

        Returns:
            An absolute :class:`Path` inside ``self._root``.

        Raises:
            PathEscapeError: if the resolved path is outside the root.
        """
        rel = (rel_path or "").lstrip("/").strip()
        candidate = self._root / rel if rel else self._root
        # Use realpath to collapse symlinks; Path.resolve() follows
        # symlinks too, but realpath is explicit about the intent and
        # works on non-existent leaf paths as well.
        try:
            resolved = Path(os.path.realpath(candidate))
        except OSError as exc:
            raise PathEscapeError(
                f"cannot resolve path {rel_path!r}: {exc}"
            ) from exc
        root_real = Path(os.path.realpath(self._root))
        # The path must be the root itself or strictly under it.
        if resolved != root_real and root_real not in resolved.parents:
            raise PathEscapeError(f"path {rel_path!r} escapes sandbox root")
        return resolved

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def list_dir(self, rel_path: str | None) -> list[dict[str, Any]]:
        """List the contents of a directory inside the sandbox.

        Returns a list of dicts with keys ``name``, ``is_dir``,
        ``size`` and ``mtime``.
        """
        target = self._resolve(rel_path)
        if not target.exists():
            raise FileNotFoundErrorInSandbox(
                f"no such directory: {rel_path!r}"
            )
        if not target.is_dir():
            raise FileServiceError(f"not a directory: {rel_path!r}")
        entries: list[dict[str, Any]] = []
        for child in sorted(target.iterdir(), key=lambda p: p.name):
            try:
                stat = child.stat()
            except OSError:
                continue
            entries.append({
                "name": child.name,
                "is_dir": child.is_dir(),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            })
        return entries

    def save_upload(
        self, rel_dir: str | None, filename: str, content: bytes
    ) -> Path:
        """Write ``content`` to ``{rel_dir}/{filename}`` inside the sandbox.

        Args:
            rel_dir: Target directory relative to the user root.
            filename: Bare file name (no slashes). Must not be empty.
            content: File bytes.

        Returns:
            The absolute path of the written file.

        Raises:
            UploadTooLargeError: payload exceeds ``MAX_UPLOAD_MB``.
            FileNotFoundErrorInSandbox: ``rel_dir`` does not exist.
            FileServiceError: on generic I/O failures.
        """
        if not filename or any(c in filename for c in ("/", "\\", "\0")):
            raise FileServiceError(f"invalid filename: {filename!r}")
        if len(content) > self._max_upload_bytes:
            raise UploadTooLargeError(
                f"upload of {len(content)} bytes exceeds "
                f"max {self._max_upload_bytes} bytes"
            )
        target_dir = self._resolve(rel_dir)
        if not target_dir.exists():
            raise FileNotFoundErrorInSandbox(f"no such directory: {rel_dir!r}")
        if not target_dir.is_dir():
            raise FileServiceError(f"not a directory: {rel_dir!r}")
        # Re-resolve with the filename to catch symlink tricks.
        final = self._resolve(
            f"{(rel_dir or '').rstrip('/')}/{filename}".lstrip("/")
        )
        try:
            final.write_bytes(content)
        except OSError as exc:
            raise FileServiceError(
                f"failed to write {filename!r}: {exc}"
            ) from exc
        return final

    def read_file(self, rel_path: str) -> bytes:
        """Read a file from inside the sandbox."""
        target = self._resolve(rel_path)
        if not target.exists():
            raise FileNotFoundErrorInSandbox(f"no such file: {rel_path!r}")
        if not target.is_file():
            raise FileServiceError(f"not a regular file: {rel_path!r}")
        try:
            return target.read_bytes()
        except OSError as exc:
            raise FileServiceError(
                f"failed to read {rel_path!r}: {exc}"
            ) from exc

    def delete(self, rel_path: str) -> None:
        """Delete a file or an empty directory.

        Raises:
            NotEmptyDirectoryError: target is a non-empty directory.
        """
        target = self._resolve(rel_path)
        # Refuse to delete the user root itself.
        if target == Path(os.path.realpath(self._root)):
            raise FileServiceError("cannot delete sandbox root")
        if not target.exists() and not target.is_symlink():
            raise FileNotFoundErrorInSandbox(f"no such path: {rel_path!r}")
        try:
            if target.is_dir() and not target.is_symlink():
                # Refuse non-empty dirs to avoid surprises.
                try:
                    next(target.iterdir())
                except StopIteration:
                    target.rmdir()
                    return
                raise NotEmptyDirectoryError(
                    f"directory not empty: {rel_path!r}"
                )
            target.unlink()
        except NotEmptyDirectoryError:
            raise
        except OSError as exc:
            raise FileServiceError(
                f"failed to delete {rel_path!r}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def usage_bytes(self) -> int:
        """Return total disk usage of the user's sandbox (bytes)."""
        total = 0
        for dirpath, _dirnames, filenames in os.walk(self._root):
            for name in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, name))
                except OSError:
                    continue
        return total

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"FileService(user_id={self._user_id!r}, root={str(self._root)!r})"
        )


# Re-export shutil so callers that need recursive helpers can import
# from a single place. (Currently unused; kept for future P2+ work.)
_ = shutil
