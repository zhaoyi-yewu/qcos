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

from qcos.transpiler.qiskit.transpiler_qiskit_cmd import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="qiskit transpiler cli")
    parser.add_argument(
        "-i",
        "--input-file",
        dest="input_file",
        type=str,
        required=True,
        help="input file",
    )
    parser.add_argument(
        "-g",
        "--gates-list",
        dest="gates_list",
        type=str,
        default="",
        help="basis gates",
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
        default="",
        help="output file",
    )
    args = parser.parse_args()

    sys.exit(
        main(
            input_file=args.input_file,
            basis_gates=args.gates_list,
            opt_level=args.opt_level,
            config_file=args.config_file,
            output_file=args.output_file,
        )
    )
