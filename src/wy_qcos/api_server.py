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

import asyncio
import os
import sys
import traceback

from wy_qcos.common.library import Library
from wy_qcos.common.qcos_version import QcosVersion
from wy_qcos.server import Server

__all__ = []
__version__ = QcosVersion.VERSION


def daemonize():
    """Do the UNIX double-fork magic for properly detaching process."""
    try:
        pid = os.fork()
        if pid > 0:
            # Exit first parent
            sys.exit(0)
    except OSError as e:
        print(
            f"First fork failed: {e.errno} ({e.strerror})\n", file=sys.stderr
        )
        sys.exit(1)

    # Decouple from parent environment
    os.setsid()
    os.umask(0o007)

    # Do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # Exit from second parent
            sys.exit(0)
    except OSError as e:
        print(
            f"Second fork failed: {e.errno} ({e.strerror})\n", file=sys.stderr
        )
        sys.exit(1)


def main():
    """Main entry."""
    PID_DIR = "/var/run/qcos"
    PID_FILE = f"{PID_DIR}/qcos-api.pid"

    # kill existing qcos-api process
    Library.kill_pid(PID_FILE)
    Library.mkdir(PID_DIR)
    Library.create_pid_file(PID_FILE)

    # daemonize process
    if "--daemon" in sys.argv:
        daemonize()
    try:
        loop = asyncio.get_event_loop()
        Server().run(loop)
    except Exception as e:
        print(f"{e}\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
