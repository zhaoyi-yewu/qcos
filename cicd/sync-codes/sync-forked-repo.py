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
Sync forked Gitee repo with origin Gitee repo via git operations.

This script clones the forked repo, adds the origin repo as an extra
remote, fetches the origin branch, resets the forked branch to match
the origin branch, and pushes the result back to the forked repo.

Prerequisite:
yum install -y git
pip3 install --break-system-packages GitPython

Examples:
./sync-forked-repo.py
./sync-forked-repo.py --origin-repo WUYUEQbit --origin-branch qcos \
    --forked-repo test --forked-branch qcos
./sync-forked-repo.py --dry-run  # Dry-run, clone+sync but no push
"""

import os
import shutil
import subprocess
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter

# gitee base url
gitee_base = "git@gitee.com"

# default origin (upstream) repo owner and branch
gitee_origin_repo = "WUYUEQbit"
gitee_origin_branch = "develop"

# default forked repo owner and branch
gitee_forked_repo = "test"
gitee_forked_branch = "develop"

# the actual repository name (same for origin and forked)
gitee_repo_name = "qcos"

# local temp working directory
local_work_dir = "/tmp/sync-forked-repo"


class SyncException(Exception):
    """Sync Exception."""


def run_command(command, cwd=None, check=True,
                capture_output=True, text=True):
    """Run command.

    Args:
        command: command, a list of args or a shell string
        cwd: working directory to run the command in
        check: check exit code
        capture_output: capture output
        text: print text

    Returns:
        command results
    """
    if isinstance(command, str):
        command = command.split()
    try:
        results = subprocess.run(
            command,
            shell=False,
            cwd=cwd,
            check=check,
            capture_output=capture_output,
            text=text,
        )
        return results
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {command}")
        print(f"Error output: {e.stderr}")
        raise


def clone_forked_repo(forked_owner, repo_name, branch, work_dir):
    """Clone the forked repo into work_dir.

    Args:
        forked_owner: forked repo owner
        repo_name: repo name
        branch: forked branch to checkout
        work_dir: local working directory
    """
    forked_url = f"{gitee_base}:{forked_owner}/{repo_name}.git"
    print(f"Clone forked repo: {forked_url}, branch: {branch}")

    # clean existing work_dir
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir, ignore_errors=True)
    os.makedirs(work_dir, exist_ok=True)

    cmd = [
        "git", "clone", "--branch", branch, forked_url, work_dir,
    ]
    run_command(cmd, cwd=None)
    print(f"Cloned to {work_dir}")


def add_origin_remote(origin_owner, repo_name, work_dir):
    """Add origin repo as upstream remote.

    Args:
        origin_owner: origin repo owner
        repo_name: repo name
        work_dir: local working directory
    """
    origin_url = f"{gitee_base}:{origin_owner}/{repo_name}.git"
    print(f"Add origin remote: {origin_url}")

    # remove existing upstream if any
    run_command(
        ["git", "remote", "remove", "upstream"],
        cwd=work_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    run_command(
        ["git", "remote", "add", "upstream", origin_url],
        cwd=work_dir,
        capture_output=True,
        text=True,
    )


def sync_branch(origin_owner, origin_branch,
                forked_branch, work_dir):
    """Fetch origin branch and reset forked branch to match it.

    Args:
        origin_owner: origin repo owner
        origin_branch: origin branch name
        forked_branch: forked branch name
        work_dir: local working directory
    """
    print(
        f"Fetch origin {origin_owner}/{origin_branch}"
        f" and reset forked branch {forked_branch}"
    )
    # Current branch is already forked_branch (from clone --branch).
    # Avoid ambiguous "git checkout <branch>" when multiple remotes
    # share the same branch name; reset directly to upstream ref.
    cmds = [
        ["git", "fetch", "upstream"],
        ["git", "reset", "--hard",
         f"refs/remotes/upstream/{origin_branch}"],
    ]
    for cmd in cmds:
        run_command(cmd, cwd=work_dir, capture_output=True, text=True)
    print(f"Forked branch [{forked_branch}] reset to upstream/{origin_branch}")


def push_to_forked(forked_owner, forked_branch, work_dir):
    """Force push the synced branch back to forked repo.

    Args:
        forked_owner: forked repo owner
        forked_branch: forked branch name
        work_dir: local working directory
    """
    print(
        f"Force push to forked repo: "
        f"{gitee_base}:{forked_owner}/{gitee_repo_name}.git, "
        f"branch: {forked_branch}"
    )
    cmd = [
        "git", "push", "-f", "origin",
        f"{forked_branch}:{forked_branch}",
    ]
    run_command(cmd, cwd=work_dir, capture_output=True, text=True)
    print("Push to forked repo success!")


def main(argv=None):
    """main"""
    global gitee_origin_repo
    global gitee_origin_branch
    global gitee_forked_repo
    global gitee_forked_branch

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_shortdesc = __doc__.strip()
    program_license = f"{program_shortdesc}\nUSAGE"

    try:
        parser = ArgumentParser(
            description=program_license,
            formatter_class=RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "--origin-repo",
            dest="origin_repo",
            default=gitee_origin_repo,
            help=f"Origin (upstream) repo owner (default: {gitee_origin_repo})",
        )
        parser.add_argument(
            "--origin-branch",
            dest="origin_branch",
            default=gitee_origin_branch,
            help=f"Origin branch name (default: {gitee_origin_branch})",
        )
        parser.add_argument(
            "--forked-repo",
            dest="forked_repo",
            default=gitee_forked_repo,
            help=f"Forked repo owner (default: {gitee_forked_repo})",
        )
        parser.add_argument(
            "--forked-branch",
            dest="forked_branch",
            default=gitee_forked_branch,
            help=f"Forked branch name (default: {gitee_forked_branch})",
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Dry-run mode: clone and sync locally but do not push",
        )

        args = parser.parse_args()
        origin_owner = args.origin_repo
        origin_branch = args.origin_branch
        forked_owner = args.forked_repo
        forked_branch = args.forked_branch
        dry_run = args.dry_run

        print("==== Sync forked repo with origin repo ====")
        print(f"Origin:  {origin_owner}/{gitee_repo_name}, branch: {origin_branch}")
        print(f"Forked:  {forked_owner}/{gitee_repo_name}, branch: {forked_branch}")

        # 1. clone forked repo
        clone_forked_repo(forked_owner, gitee_repo_name,
                           forked_branch, local_work_dir)

        # 2. add origin as upstream remote
        add_origin_remote(origin_owner, gitee_repo_name, local_work_dir)

        # 3. fetch origin and reset forked branch
        sync_branch(origin_owner, origin_branch,
                    forked_branch, local_work_dir)

        # 4. force push to forked repo
        if dry_run:
            print("[Dry-run mode] Skip pushing to forked repo")
        else:
            push_to_forked(forked_owner, forked_branch, local_work_dir)

        print("\n==== Sync forked repo completed successfully! ====")
        return 0
    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except SyncException as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
