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
Check git commit messages
"""

import os
import re
import subprocess
import sys


def get_commit_messages():
    """Get commit messages."""
    # check gitlab ci env variables
    if 'CI_COMMIT_MESSAGE' in os.environ:
        msg = os.environ['CI_COMMIT_MESSAGE'].strip()
        # get first line of commit message from env variable
        first_line = msg.split('\n')[0].strip()
        return first_line
    else:
        # use git command to get first line of commit message
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=%B'],
                capture_output=True,
                text=True,
                check=True
            )
            msg = result.stdout.strip()
            first_line = msg.split('\n')[0].strip()
            return first_line
        except subprocess.CalledProcessError as e:
            sys.stderr.write(f"ERROR: Failed to run git command: {e}",
                             file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            sys.stderr.write("ERROR: Failed to find git command",
                             file=sys.stderr)
            sys.exit(1)


def get_commit_messages_summary(count=None, start_from_merge=True):
    """Get the last n commit message summaries.

    Args:
        count (int): Number of commits
        start_from_merge: Start from last merge commit

    Returns:
        commit message list
    """
    # use git command to get the last n commit message summaries
    commit_message_list = []
    try:
        last_merge_commit_id = None
        if start_from_merge:
            result = subprocess.run(
                ["git", "rev-list", "--merges", "-n", "1", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            msg = result.stdout.strip()
            if msg:
                last_merge_commit_id = msg

        cmds = ["git", "log", "--pretty=format:%h %s"]
        if count:
            cmds.append(f"-{count}")
        if last_merge_commit_id:
            cmds.append(f"{last_merge_commit_id}..HEAD")
        result = subprocess.run(
            cmds,
            capture_output=True,
            text=True,
            check=True
        )
        msg = result.stdout.strip()
        _commit_message_list = msg.split('\n')
        for line in _commit_message_list:
            commit_message_list.append(tuple(line.split(" ", maxsplit=1)))
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"ERROR: Failed to run git command: {e}",
                         file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        sys.stderr.write("ERROR: Failed to find git command",
                         file=sys.stderr)
        sys.exit(1)
    return commit_message_list


def is_english_string(s):
    """Check if is english."""
    ascii_pattern = re.compile(r'^[\x20-\x7E]+$')
    return ascii_pattern.match(s) is not None


def main():
    print("Checking commit messages")
    # get first line of commit messages
    first_line = get_commit_messages()
    print(f"Commit message summary: {first_line}")

    if not first_line:
        sys.stderr.write("ERROR: empty line of commit message\n")
        sys.exit(1)

    # check leading characters
    if first_line != first_line.lstrip():
        sys.stderr.write(
            "ERROR: Leading characters of commit message cannot be blank\n")
        sys.exit(1)

    # check if is english
    if not is_english_string(first_line):
        sys.stderr.write("ERROR: Commit message summary includes "
                         "non-English characters, which is not allowed. "
                         "Only English letters are allowed\n")
        sys.exit(1)

    # check duplicated commit messages
    commit_message_list = get_commit_messages_summary(start_from_merge=True)
    last_commit_summary = None
    last_commit_hash = None
    for commit_hash, commit_summary in commit_message_list:
        commit_summary = commit_summary.strip()
        if commit_summary == last_commit_summary:
            sys.stderr.write("ERROR: commit message summary "
                             f"(hash: {last_commit_hash}) is identical "
                             f"to another commit (hash: {commit_hash}). "
                             "Please squash them into one commit\n")
            sys.exit(1)
        if not last_commit_summary:
            last_commit_summary = commit_summary
            last_commit_hash = commit_hash

    print("[SUCCESS]")


if __name__ == "__main__":
    main()
