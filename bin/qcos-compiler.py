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
#     WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Entry point for the qcos-compiler cloud service."""

import argparse
import logging
import os

import uvicorn

from wy_qcos.cloud.app import app

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080

# Log format with a leading timestamp so every log line carries the
# current service time; mirrors the default Config.LOG.LOG_FORMAT.
LOG_FORMAT = "%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s"

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="qcos-compiler cloud service (openqasm validation "
        "and compilation)"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("QCOS_COMPILER_HOST", DEFAULT_HOST),
        help=f"bind host (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("QCOS_COMPILER_PORT", DEFAULT_PORT)),
        help=f"bind port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("QCOS_COMPILER_LOG_LEVEL", "info"),
        help="log level (default: info)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(), format=LOG_FORMAT,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
