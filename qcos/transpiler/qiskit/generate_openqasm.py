#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
import argparse
import logging
from qiskit import qasm2, qasm3
from qiskit.circuit.random import random_circuit

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def generate_random_qasm(
    width: int,
    depth: int,
    qasm_version: str = "3.0",
    output_file: str = "qasm_temp.qasm",
):
    """
    generate a random circuit with width and depth

    Args:
        width (int): number of qubits
        depth (int): depth of quantum circuit
        qasm_version (str): version of openqasm, support "2.0" or "3.0"
        output_file (str): output path for openqasm file
    """
    if width <= 0 or depth <= 0:
        raise ValueError("width and depth must be greater than zero")
    if qasm_version not in ["2.0", "3.0"]:
        raise ValueError("only support openqasm version 2.0 or 3.0")

    # max_operands represent maximum qubit operands of
    # each gate (between 1 and 4)
    qc = random_circuit(width, depth, max_operands=3, measure=True)

    if qasm_version == "2.0":
        # get OpenQASM 2.0 code
        openqasm_code = qasm2.dumps(qc)
    else:
        # get OpenQASM 3.0 code
        openqasm_code = qasm3.dumps(qc)

    current_prj_path = os.getcwd()
    qasm_path = os.path.join(
        current_prj_path, "samples", "qasm", qasm_version, "benchmark"
    )

    if output_file is None:
        final_output_file = os.path.join(
            qasm_path, f"{width}bits_{depth}d.qasm"
        )
    else:
        final_output_file = output_file

    if os.path.exists(final_output_file):
        logger.error(f"file[{final_output_file}] is already existed!")
        return
    else:
        with open(final_output_file, mode="w+", encoding="utf-8") as f:
            f.write(openqasm_code)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="generate the openqasm file with width and depth"
    )
    parser.add_argument(
        "-w", "--width", type=int, default=100, help="qubits number"
    )
    parser.add_argument(
        "-d", "--depth", type=int, default=5000, help="circuit depth"
    )
    parser.add_argument(
        "-q",
        "--qasm_version",
        type=str,
        default="3.0",
        help="openqasm version",
    )
    parser.add_argument("-o", "--output", type=str, help="openqasm file")
    args = parser.parse_args()

    generate_random_qasm(
        args.width, args.depth, args.qasm_version, args.output
    )
