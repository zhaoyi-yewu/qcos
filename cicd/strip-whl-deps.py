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

"""Remove runtime dependency metadata from a Python wheel file."""

import argparse
import csv
import io
import shutil
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path

METADATA_SUFFIX = ".dist-info/METADATA"
RECORD_SUFFIX = ".dist-info/RECORD"


def _strip_requires_dist(data: bytes) -> bytes:
    """Remove Requires-Dist headers and their continuation lines."""
    text = data.decode("utf-8")
    output = []
    in_headers = True
    skip_continuation = False

    for line in text.splitlines(keepends=True):
        if in_headers:
            if line in ("\n", "\r\n", "\r"):
                in_headers = False
                skip_continuation = False
            elif line.lower().startswith("requires-dist:"):
                skip_continuation = True
                continue
            elif skip_continuation and line.startswith((" ", "\t")):
                continue
            else:
                skip_continuation = False
        output.append(line)

    return "".join(output).encode("utf-8")


def _clear_metadata_record(data: bytes) -> bytes:
    """Clear RECORD checksums for modified METADATA files."""
    text = data.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    reader = csv.reader(io.StringIO(text, newline=""))
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator=newline)

    for row in reader:
        if row and row[0].endswith(METADATA_SUFFIX):
            row = [row[0], "", ""]
        writer.writerow(row)

    return output.getvalue().encode("utf-8")


def strip_wheel_dependencies(wheel_path: str | Path) -> None:
    """Rewrite a wheel without Requires-Dist metadata."""
    wheel_path = Path(wheel_path).expanduser().resolve()
    if wheel_path.suffix.lower() != ".whl":
        raise ValueError("input must be a .whl file")
    if not wheel_path.is_file():
        raise ValueError(f"wheel file not found: {wheel_path}")

    with tempfile.NamedTemporaryFile(
        dir=wheel_path.parent,
        prefix=f"{wheel_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        with (
            zipfile.ZipFile(wheel_path, "r") as source,
            zipfile.ZipFile(temp_path, "w") as target,
        ):
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename.endswith(METADATA_SUFFIX):
                    data = _strip_requires_dist(data)
                elif item.filename.endswith(RECORD_SUFFIX):
                    data = _clear_metadata_record(data)
                target.writestr(item, data)

        shutil.copymode(wheel_path, temp_path)
        temp_path.replace(wheel_path)
    finally:
        temp_path.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path, help="wheel file to rewrite")
    args = parser.parse_args(argv)

    try:
        strip_wheel_dependencies(args.wheel)
    except (
        OSError,
        ValueError,
        UnicodeError,
        csv.Error,
        zipfile.BadZipFile,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Updated wheel: {args.wheel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
