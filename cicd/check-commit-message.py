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
            sys.stderr.write(f"ERROR: Failed to run git command: {e}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            sys.stderr.write("ERROR: Failed to find git command", file=sys.stderr)
            sys.exit(1)

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
        sys.stderr.write("ERROR: Leading characters of commit message cannot be blank\n")
        sys.exit(1)

    # check if is english
    if not is_english_string(first_line):
        sys.stderr.write("ERROR: Commit message summary includes non-English " \
            "characters, which is not allowed. Only English letters are allowed\n")
        sys.exit(1)
    print("[SUCCESS]")

if __name__ == "__main__":
    main()
