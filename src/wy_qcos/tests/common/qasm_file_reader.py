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
from pathlib import Path
from collections.abc import Iterator


class QasmFileReader:
    """Lazily iterates over QASM files under a directory.

    This reader recursively traverses a directory and lazily yields
    QASM file paths and contents. Files can be ignored by exact file
    name match, assuming file names are globally unique.
    """

    # Project-wide predefined ignore files (file names are globally unique)
    DEFAULT_IGNORE_FILES: set[str] = {
        # bigint
        "bigint.qasm",
        # feynman
        "teleport.qasm",
        "teleportv2.qasm",
        # qasmbench-small
        "bb84_n8.qasm",
        "bb84_n8_transpiled.qasm",
        "error_correctiond3_n5.qasm",
        "error_correctiond3_n5_transpiled.qasm",
        "ipea_n2.qasm",
        "ipea_n2_transpiled.qasm",
        "shor_n5.qasm",
        "shor_n5_transpiled.qasm",
    }

    def __init__(
        self,
        root_dir: str | Path,
        *,
        ignore_files: set[str] | list[str] | None = None,
    ) -> None:
        """Initializes a QasmFileReader.

        Args:
            root_dir: Root directory containing QASM files.
            ignore_files: Optional collection of QASM file names to ignore.
                File names are matched exactly.

        Raises:
            FileNotFoundError: If the root directory does not exist.
            NotADirectoryError: If the root path is not a directory.
        """
        self._root_dir = Path(root_dir).resolve()

        if not self._root_dir.exists():
            raise FileNotFoundError(f"Directory not found: {self._root_dir}")
        if not self._root_dir.is_dir():
            raise NotADirectoryError(f"Not a directory: {self._root_dir}")

        # Merge default ignore files with user-provided ignore files
        self._ignore_files: set[str] = set(self.DEFAULT_IGNORE_FILES)
        if ignore_files:
            self._ignore_files.update(ignore_files)

    def iter_files(self) -> Iterator[Path]:
        """Yields QASM file paths lazily in stable order.

        Yields:
            Paths pointing to QASM files that are not ignored.
        """
        for path in sorted(self._root_dir.glob("**/*.qasm")):
            if not path.is_file():
                continue
            if path.name in self._ignore_files:
                continue
            yield path

    def iter_contents(self) -> Iterator[tuple[Path, str]]:
        """Yields QASM file paths and contents lazily.

        Yields:
            Tuples of (file_path, file_content).
        """
        for path in self.iter_files():
            yield path, path.read_text(encoding="utf-8")

    def iter_texts(self) -> Iterator[str]:
        """Yields QASM file contents lazily.

        Yields:
            QASM file contents as strings.
        """
        for _, content in self.iter_contents():
            yield content
