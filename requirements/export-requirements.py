#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You can obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY or FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Export requirements from a pyproject.toml file.

Reads the ``[project.dependencies]`` (core dependencies) and/or the
``[project.optional-dependencies]`` groups (extras) from a
``pyproject.toml`` file and writes the resolved dependency list to a
requirements file.

By default only the core dependencies are exported. Whether to include
the core dependencies is controlled by ``--no-deps``. The optional
``--extras`` option selects which extra groups to include; when
omitted, no extra groups are exported.

Examples
--------

Export only the core dependencies::

    python export-requirements.py pyproject.toml requirements.txt

Export only the ``docs`` and ``test`` extras (no core dependencies)::

    python export-requirements.py pyproject.toml requirements.txt \\
        --no-deps --extras docs --extras test

Export core dependencies and the ``base`` extra::

    python export-requirements.py pyproject.toml requirements.txt \\
        --extras base

The optional arguments may appear before or after the positional
arguments::

    python export-requirements.py --extras base pyproject.toml r.txt
"""

import os
import sys
import tomlkit
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

TOP_DIR = Path(__file__).resolve().parent.parent


def load_pyproject(pyproject_file):
    """Load and return the parsed pyproject.toml content.

    Args:
        pyproject_file: absolute path to the pyproject.toml file

    Returns:
        tomlkit document (dict-like) parsed from the file

    Raises:
        FileNotFoundError: if the pyproject file does not exist
    """
    if not os.path.exists(pyproject_file):
        raise FileNotFoundError(
            f"pyproject file not found: {pyproject_file}")

    with open(pyproject_file, encoding="utf-8") as file:
        return tomlkit.load(file)


def collect_dependencies(pyproject, include_core, extras):
    """Collect dependency strings from a parsed pyproject document.

    Core dependencies (``[project.dependencies]``) are included only
    when ``include_core`` is True (i.e. ``--no-deps`` not set). Extra
    groups are included only for the names listed in ``extras``; when
    ``extras`` is empty or None, no extra groups are exported.

    Args:
        pyproject: parsed pyproject.toml document (tomlkit)
        include_core: whether to include the core dependencies from
            ``[project.dependencies]``
        extras: list of optional-dependency group names to include.
            When ``None`` or empty, no extra groups are exported.

    Returns:
        deps: ordered list of dependency requirement strings, with
            duplicates removed (first occurrence kept)

    Raises:
        Exception: if a requested extra group does not exist
    """
    project = pyproject.get("project", {})
    main_deps = project.get("dependencies", [])
    optional_deps = project.get("optional-dependencies", {})

    deps = []

    # core dependencies
    if include_core:
        deps.extend(main_deps)

    # only the explicitly requested extra groups are included
    for extra in (extras or []):
        if extra not in optional_deps:
            raise Exception(
                f"Extra group '{extra}' not found in "
                f"[project.optional-dependencies]")
        deps.extend(optional_deps[extra])

    # remove duplicates while preserving order
    seen = set()
    unique_deps = []
    for dep in deps:
        if dep not in seen:
            seen.add(dep)
            unique_deps.append(dep)

    return unique_deps


def export_requirements(pyproject_file, output_file, include_core,
                        extras=None):
    """Export requirements from pyproject.toml to a file.

    Args:
        pyproject_file: path to the pyproject.toml file
        output_file: path to the output requirements file
        include_core: whether to include core dependencies
        extras: list of extra group names, or None for all extras

    Returns:
        deps: list of dependency strings that were written
    """
    pyproject = load_pyproject(pyproject_file)
    deps = collect_dependencies(pyproject, include_core, extras)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        for dep in deps:
            file.write(f"{dep}\n")

    return deps


def main(argv=None):
    """Main function.

    Args:
        argv: command line arguments (excluding program name)

    Returns:
        exit code: 0 on success, 2 on error
    """
    if argv is None:
        argv = sys.argv[1:]

    program_shortdesc = __doc__.strip().splitlines()[0]
    program_license = f"""{program_shortdesc}

USAGE
    python export-requirements.py <pyproject.toml> <requirements.txt> \\
        [--no-deps] [--extras GROUP ...]

    The optional arguments (--no-deps, --extras) may appear before or
    after the two positional arguments (pyproject.toml, output file).

ARGUMENTS
    pyproject.toml      Path to the pyproject.toml file (required)
    requirements.txt    Path to the output requirements file (required)

OPTIONS
    --no-deps           Do not export core dependencies
                        ([project.dependencies]). By default the core
                        dependencies are exported.
    --extras GROUP      Optional extra group name to export. May be
                        given multiple times to include several groups
                        (e.g. --extras docs --extras base). When
                        omitted, no extra groups are exported.
"""

    try:
        parser = ArgumentParser(
            description=program_license,
            formatter_class=RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "pyproject",
            help="Path to the pyproject.toml file",
        )
        parser.add_argument(
            "output",
            help="Path to the output requirements file",
        )
        parser.add_argument(
            "--no-deps",
            dest="no_deps",
            action="store_true",
            help="Do not export core dependencies "
                 "([project.dependencies])",
        )
        parser.add_argument(
            "--extras",
            dest="extras",
            action="append",
            default=None,
            help="Optional extra group name to export. May be "
                 "specified multiple times to include several "
                 "groups (e.g. --extras docs --extras base). "
                 "When omitted, no extra groups are exported.",
        )

        args = parser.parse_args(argv)

        pyproject_file = args.pyproject
        output_file = args.output
        include_core = not args.no_deps
        extras = args.extras if args.extras else None

        deps = export_requirements(
            pyproject_file,
            output_file,
            include_core,
            extras,
        )

        # summary
        core_status = "included" if include_core else "excluded"
        if extras:
            extras_str = ", ".join(extras)
        else:
            extras_str = "none"
        print(
            f"[export-requirements] pyproject: {pyproject_file}")
        print(
            f"[export-requirements] output: {output_file}")
        print(
            f"[export-requirements] core dependencies: {core_status}")
        print(
            f"[export-requirements] extras: {extras_str}")
        print(
            f"[export-requirements] total dependencies: {len(deps)}")

        return 0
    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
