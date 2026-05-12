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

"""Simple script for rebuilding .codespell-ignore-lines

Usage:

cat < /dev/null > .codespell-ignore-lines
pre-commit run --all-files codespell >& /tmp/codespell_errors.txt
python3 tools/codespell_ignore_lines_from_errors.py /tmp/codespell_errors.txt > .codespell-ignore-lines

git diff to review changes, then commit, push.
"""

import sys
from typing import List


def run(args: List[str]) -> None:
    assert len(args) == 1, "codespell_errors.txt"
    cache = {}
    done = set()
    with open(args[0]) as f:
        lines = f.read().splitlines()

    for line in sorted(lines):
        i = line.find(" ==> ")
        if i > 0:
            flds = line[:i].split(":")
            if len(flds) >= 2:
                filename, line_num = flds[:2]
                if filename not in cache:
                    with open(filename) as f:
                        cache[filename] = f.read().splitlines()
                supp = cache[filename][int(line_num) - 1]
                if supp not in done:
                    print(supp)
                    done.add(supp)


if __name__ == "__main__":
    run(args=sys.argv[1:])
