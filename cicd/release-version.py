#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

"""
Release version script

# bump version part. version part: major, minor, patch
./release-version.py -p patch

# bump version name
./release-version.py -n 1.0.2

# dry-run
./release-version.py -d -p patch

# don't commit
./release-version.py -nc -p patch

# don't tag
./release-version.py -nt -p patch
"""

import os
import pathlib
import semver
import subprocess
import sys

from argparse import ArgumentParser, RawDescriptionHelpFormatter


class ReleaseException(Exception):
    """Release Exception"""


def extract_unreleased_section(md_content, start_marker, end_marker):
    """
    Find contents between start_marker and end_marker from markdown content.

    Args:
        md_content (str): markdown contents
        start_marker (str): start marker string
        end_marker (str): end marker string

    Returns:
        str: contents between start_marker and end_marker
    """

    # find start_marker position
    start_idx = md_content.find(start_marker)
    if start_idx == -1:
        return ""

    # find end_marker position
    end_idx = md_content.find(end_marker, start_idx + len(start_marker))

    # if end idx is not -1, extract the content between start and end
    # otherwise, extract to the end of the text
    if end_idx != -1:
        section_content = md_content[start_idx:end_idx]
    else:
        section_content = md_content[start_idx:]

    # remove the section name and strip blank characters
    return section_content.replace(start_marker, "").strip()


def run_command(command, shell=True, check=True, capture_output=True,
                text=True, cwd=None, env=None):
    """Run command.

    Args:
        command: command
        shell: If true, the command will be executed through the shell
        check: check exit code
        capture_output: capture output
        text: print text
        cwd: working directory
        env: environment variables

    Returns:
        command results
    """
    try:
        results = subprocess.run(
            command,
            shell=shell,
            check=check,
            capture_output=capture_output,
            text=text,
            cwd=cwd,
            env=env,
        )
        return results
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {command}")
        print(f"Error output: {e.stderr}")
        raise


def get_release_notes(changelog_path):
    """Get the release notes from CHANGELOG.md.

    Args:
        changelog_path: path to CHANGELOG

    Returns:
        release notes
    """

    md_text = None
    with open(changelog_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    if not md_text:
        raise ReleaseException(f"Can't find changelog file: {changelog_path}")

    # Extract unreleased chapter content
    release_notes = extract_unreleased_section(
        md_text,
        "## [未发布] - 开发中",
        "## [")
    if not release_notes:
        raise ReleaseException(f"Can't find any release notes")

    return release_notes


def bump_version(bump_version_part, bump_version_name,
                 release_notes,
                 no_commit=False,
                 no_tag=False,
                 verbose=False,
                 dry_run=False,
                 top_dir="."):
    """Bump version.

    Args:
        bump_version_part: bump version part
        bump_version_name: bump version name
        release_notes: release notes
        no_commit: don't commit
        no_tag: don't tag
        verbose: verbose mode
        dry_run: dry run
        top_dir: top dir
    """

    # get environment variables
    env_vars = dict(os.environ)

    bump_cmd_part = ""
    if bump_version_part:
        bump_cmd_part = f"{bump_version_part}"
    elif bump_version_name:
        semver.Version.parse(bump_version_name)
        bump_cmd_part = f"--new-version {bump_version_name}"

    bump_cmd_args_list = []
    if no_commit:
        bump_cmd_args_list.append("--no-commit")
    if no_tag:
        bump_cmd_args_list.append("--no-tag")
    if verbose:
        bump_cmd_args_list.append("--verbose")
    if dry_run:
        bump_cmd_args_list.append("--dry-run")
    bump_cmd_args = " ".join(bump_cmd_args_list)

    # run bump-my-version command
    cmds = [f"bump-my-version bump {bump_cmd_args} {bump_cmd_part}"]
    release_notes = release_notes.replace("### ", "")
    release_notes = release_notes.replace("## ", "")
    env_vars["RELEASE_NOTES"] = f"\n\n{release_notes}"
    results = run_command(";".join(cmds), cwd=top_dir, env=env_vars)
    ret_code = results.returncode
    if ret_code != 0:
        raise ReleaseException(results.stderr)
    print(results.stdout)


def main(argv=None):
    '''main'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_shortdesc = __doc__.strip()
    program_license = f'''{program_shortdesc}

USAGE
'''
    # get top dir
    current_file = pathlib.Path(__file__).resolve()
    current_dir = current_file.parent
    parent_dir = current_dir.parent
    top_dir = str(parent_dir)

    try:
        # config parser
        parser = ArgumentParser(
            description=program_license,
            formatter_class=RawDescriptionHelpFormatter
        )
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("-p", "--bump-version-part",
                           type=str,
                           choices=["major", "minor", "patch"],
                           dest="bump_version_part",
                           help="bump version part. [major | minor | patch]")
        group.add_argument("-n",  "--bump-version-name",
                           dest="bump_version_name",
                           help="bump version name")
        parser.add_argument("-nc", "--no-commit",
                            dest="no_commit",
                            action="store_true",
                            help="commit to git")
        parser.add_argument("-nt", "--no-tag",
                            dest="no_tag",
                            action="store_true",
                            help="create tag in git")
        parser.add_argument("-V", "--verbose",
                            dest="verbose",
                            action="store_true",
                            help="verbose mode")
        parser.add_argument("-d", "--dry-run",
                            dest="dry_run",
                            action="store_true",
                            help="Dry run")

        # parse arguments
        args = parser.parse_args()
        bump_version_part = args.bump_version_part
        bump_version_name = args.bump_version_name
        no_commit = args.no_commit
        no_tag = args.no_tag
        verbose = args.verbose
        dry_run = args.dry_run

        # get release notes
        changelog_path = f"{top_dir}/CHANGELOG.md"
        print(f"Get release notes from: {changelog_path}")
        release_notes = get_release_notes(changelog_path)

        # bump version
        bump_version_str = bump_version_part
        if bump_version_name:
            bump_version_str = bump_version_name
        print(f"Bump version to: {bump_version_str}")
        bump_version(bump_version_part, bump_version_name,
                     release_notes, no_commit=no_commit, no_tag=no_tag,
                     verbose=verbose, dry_run=dry_run, top_dir=top_dir)

        print("Successfully released version")
        return 0

    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
