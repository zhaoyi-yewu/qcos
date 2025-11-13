#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

import sys
import argparse

from qcos.transpiler.cmss.transpiler_cmd_line import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="cmss transpiler cli")
    parser.add_argument(
        "-i",
        "--input-file",
        dest="input_file",
        type=str,
        required=True,
        help="input file",
    )
    parser.add_argument(
        "-o",
        "--opt-level",
        dest="opt_level",
        type=int,
        default=1,
        help="optimization level",
    )
    parser.add_argument(
        "-t",
        "--tech-type",
        dest="tech_type",
        type=str,
        default="",
        help="technology type",
    )
    parser.add_argument(
        "-c",
        "--config-file",
        dest="config_file",
        type=str,
        default="",
        help="config file",
    )
    parser.add_argument(
        "-O",
        "--output-file",
        dest="output_file",
        type=str,
        required=True,
        help="output file",
    )
    args = parser.parse_args()

    sys.exit(
        main(
            input_file=args.input_file,
            output_file=args.output_file,
            opt_level=args.opt_level,
            tech_type=args.tech_type,
            config_file=args.config_file,
        )
    )
