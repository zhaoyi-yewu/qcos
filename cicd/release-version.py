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
 
"""
Release version script

Prerequisite:
yum install -y git
pip3 install bump-my-version semver

# bump version name
./release-version.py -n 1.0.1
./release-version.py -n 1.0.1-alpha.1
./release-version.py -n 1.0.1-beta.1
./release-version.py -n 1.0.1-rc.1

# bump version part. version part: major, minor, patch, num, stage
./release-version.py -p patch
./release-version.py -p num
./release-version.py -p stage

# dry-run
./release-version.py -d -n 1.0.1

# don't commit in bump-to-version script
./release-version.py -nc -n 1.0.1

# don't create tag in bump-to-version script
./release-version.py -nt -n 1.0.1

# specify master branch, develop branch, release branch
./release-version.py -n 1.0.1 --master-branch master --develop-branch develop \
  --release-branch release-v1.0.1
"""

import os
import pathlib
import re
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

    # Check if release notes is updated
    ignored_keywords = ["-", " ", "#", "##", "###",
                        "无", "新增功能", "变更功能", "修复问题", "移除内容"]
    is_updated = False
    for line in release_notes.split("\n"):
        if is_updated:
            break
        for token in line.split():
            if token not in ignored_keywords:
                is_updated = True
                break
    if not is_updated:
        raise ReleaseException(f"Please update release notes")

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

    # set new-version
    bump_cmd_part = ""
    if bump_version_part:
        bump_cmd_part = f"{bump_version_part}"
    elif bump_version_name:
        semver.Version.parse(bump_version_name)
        bump_cmd_part = f"--new-version {bump_version_name}"

    # set command arguments
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

    # set release notes
    _release_notes = release_notes.replace("### ", "")
    _release_notes = _release_notes.replace("## ", "")
    bump_tag_message = f"--tag-message \"Release Notes\n\n{_release_notes}\""

    # run bump-my-version command
    cmds = [f"bump-my-version bump {bump_cmd_args} {bump_cmd_part} "
            f"{bump_tag_message}"]
    print(f"bump version cmd:\n{';'.join(cmds)}")
    results = run_command(";".join(cmds), cwd=top_dir)
    return results


def is_git_repo_clean():
    """Check git repo is clean.

    Returns:
        bool: True if git repo is clean, False otherwise
    """

    cmds = ["git status --porcelain --untracked-files=no"]
    results = run_command(";".join(cmds))
    ret_code = results.returncode
    if ret_code != 0:
        err_msg = (f"Failed to check if git repo is clean. "
                   f"Reason: {results.stderr}")
        raise ReleaseException(err_msg)
    status_output = results.stdout.strip()
    if not status_output:
        return True
    else:
        return False


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
                           choices=["major", "minor", "patch", "num", "stage"],
                           dest="bump_version_part",
                           help="bump version part. "
                                "[major | minor | patch | num | stage]")
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
        parser.add_argument("--git-remote",
                           dest="git_remote",
                           default="origin",
                           help="git remote name. Default: origin")
        parser.add_argument("--master-branch",
                           dest="master_branch",
                           default="master",
                           help="master branch name. Default: master")
        parser.add_argument("--develop-branch",
                           dest="develop_branch",
                           default="develop",
                           help="develop branch name. Default: develop")
        parser.add_argument("--release-branch",
                           dest="release_branch",
                           help="release branch name")
        parser.add_argument("--release-notes",
                           dest="release_notes",
                           default=None,
                           help="release notes")
        parser.add_argument("--skip-tests",
                            dest="skip_tests",
                            action="store_true",
                            help="skip CICD test scripts: cicd/run-cicd.sh")
        parser.add_argument("--skip-push",
                            dest="skip_push",
                            action="store_true",
                            help="skip pushing commits or tags")
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
        git_remote = args.git_remote
        master_branch = args.master_branch
        develop_branch = args.develop_branch
        release_branch = args.release_branch
        release_notes = args.release_notes
        skip_tests = args.skip_tests
        skip_push = args.skip_push
        verbose = args.verbose
        dry_run = args.dry_run

        # check git repo is clean
        if is_git_repo_clean():
            print("* Git repo is clean")
        else:
            err_msg = "Git repo is not clean"
            raise ReleaseException(err_msg)

        # checkout develop branch
        print(f"* Checkout develop branch: {develop_branch}")
        cmds = [f"git checkout {develop_branch}"]
        results = run_command(";".join(cmds), cwd=top_dir)
        ret_code = results.returncode
        if ret_code != 0:
            err_msg = (f"Failed to checkout develop branch: {develop_branch}. "
                       f"Reason: {results.stderr}")
            raise ReleaseException(err_msg)

        # get bump version using dry-run
        print(f"* Get bump version using dry-run")
        _bump_version_name = bump_version_name
        bump_version_str = bump_version_part
        if bump_version_name:
            bump_version_str = bump_version_name
        else:
            result = bump_version(bump_version_part, bump_version_part,
                                  "", no_commit=False, no_tag=False,
                                  verbose=True, dry_run=True, top_dir=top_dir)
            ret_code = results.returncode
            if ret_code != 0:
                err_msg = (
                    f"Failed to get new version. "
                    f"Reason: {results.stderr}")
                raise ReleaseException(err_msg)
            version_pattern  = re.compile(
                r"New version will be '"
                r"(\d+\.\d+\.\d+(?:-(?:alpha|beta|rc|stable)\.\d+)?)'")
            match = version_pattern.search(result.stdout)
            if not match:
                err_msg = (
                    f"Failed to match new version. "
                    f"Reason: {results.stderr}")
                raise ReleaseException(err_msg)
            _bump_version_name = match.group(1)
        print(f"  bump version is: {_bump_version_name}")

        # create new release branch
        if not release_branch:
            release_branch = f"release/v{_bump_version_name}"
        print(f"* Create new release branch: {release_branch}")
        cmds = [f"git checkout -b {release_branch}"]
        results = run_command(";".join(cmds), cwd=top_dir)
        ret_code = results.returncode
        if ret_code != 0:
            err_msg = (f"Failed to create release branch: {release_branch}. "
                       f"Reason: {results.stderr}")
            raise ReleaseException(err_msg)

        # get release notes
        if release_notes:
            release_notes_dict = {
                "version": _bump_version_name
            }
            release_notes = release_notes.format(**release_notes_dict)
        else:
            changelog_path = f"{top_dir}/CHANGELOG.md"
            print(f"* Get release notes from: {changelog_path}")
            release_notes = get_release_notes(changelog_path)

        # bump version
        print(f"* Bump version to: {bump_version_str}")
        results = bump_version(bump_version_part, bump_version_name,
                               release_notes, no_commit=no_commit,
                               no_tag=no_tag, verbose=verbose,
                               dry_run=dry_run, top_dir=top_dir)
        print(f"  bump version results: {results.stdout}")
        ret_code = results.returncode
        if ret_code != 0:
            err_msg = f"Failed to bump version. Reason: {results.stderr}"
            raise ReleaseException(err_msg)

        # run CICD tests
        if skip_tests:
            print(f"* Skipped CICD tests")
        else:
            print(f"* Run CICD tests")
            cmds = [f"{top_dir}/cicd/run-cicd.sh"]
            results = run_command(";".join(cmds), capture_output=False,
                                  cwd=top_dir)
            ret_code = results.returncode
            if ret_code != 0:
                err_msg = (
                    f"Failed to run CICD scripts: {';'.join(cmds)}. "
                    f"Reason: {results.stderr}")
                raise ReleaseException(err_msg)

        # check git repo is clean
        if is_git_repo_clean():
            print("* Git repo is clean")
        else:
            err_msg = "Git repo is not clean"
            raise ReleaseException(err_msg)

        # push commits and tag to master branch, and merge to branch develop
        tag_name = f"v{_bump_version_name}"
        merge_cmds = [
            # merge back to develop branch
            f"git checkout {develop_branch}",
            f"git pull {git_remote} {develop_branch}",
            f"git merge --no-ff {release_branch}",
            # merge to master branch
            f"git checkout {master_branch}",
            f"git pull {git_remote} {master_branch}",
            f"git merge --no-ff {release_branch}",
        ]
        push_cmds = []
        if skip_push:
            print(f"* Skipped pushing commits or tags")
        else:
            print(f"* Push commits and tags")
            push_cmds = [
                # push release branch and tags
                f"git push {git_remote} {release_branch}",
                f"git push {git_remote} {tag_name}",
                # push to master branch
                f"git push {git_remote} {master_branch}",
            ]
        cmds = merge_cmds + push_cmds
        print("  Running push commands:")
        print(f"  {';'.join(cmds)}")
        results = run_command(";".join(cmds), cwd=top_dir)
        ret_code = results.returncode
        if ret_code != 0:
            err_msg = (
                f"Failed to pushing commits or tags. "
                f"Reason: {results.stderr}")
            raise ReleaseException(err_msg)

        cmds = [f"git checkout {develop_branch}"]
        results = run_command(";".join(cmds), cwd=top_dir)
        ret_code = results.returncode
        if ret_code != 0:
            err_msg = (
                f"Failed to checkout develop branch: {develop_branch}. "
                f"Reason: {results.stderr}")
            raise ReleaseException(err_msg)

        print(f"\nSuccessfully released version: v{_bump_version_name}")
        return 0

    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
