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

import os
import sys

# Internal build script for generating debugging test .so size.
# Usage:
#     python libsize.py file.so save.txt -- displays the size of file.so and, if save.txt exists, compares it to the
#                                           size in it, then overwrites save.txt with the new size for future runs.

if len(sys.argv) != 3:
    sys.exit("Invalid arguments: usage: python libsize.py file.so save.txt")

lib = sys.argv[1]
save = sys.argv[2]

if not os.path.exists(lib):
    sys.exit(f"Error: requested file ({lib}) does not exist")

libsize = os.path.getsize(lib)

print("------", os.path.basename(lib), "file size:", libsize, end="")

if os.path.exists(save):
    with open(save) as sf:
        oldsize = int(sf.readline())

    if oldsize > 0:
        change = libsize - oldsize
        if change == 0:
            print(" (no change)")
        else:
            print(f" (change of {change:+} bytes = {change / oldsize:+.2%})")
else:
    print()

with open(save, "w") as sf:
    sf.write(str(libsize))
