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

import argparse
import logging
from pathlib import Path
from qiskit import qasm2, qasm3
from qiskit.circuit.random import random_circuit

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def generate_random_qasm(
    width: int,
    depth: int,
    max_operands: int = 3,
    qasm_version: str = "3.0",
    output_file: str = "qasm_temp.qasm",
):
    """Generate a random circuit with width and depth.

    Args:
        width (int): number of qubits
        depth (int): depth of quantum circuit
        max_operands (int): maximum qubit operands of each gate
        qasm_version (str): version of openqasm, support "2.0" or "3.0"
        output_file (str): output path for openqasm file
    """
    if width <= 0 or depth <= 0:
        raise ValueError("width and depth must be greater than zero")
    if qasm_version not in ["2.0", "3.0"]:
        raise ValueError("only support openqasm version 2.0 or 3.0")

    # max_operands represent maximum qubit operands of
    # each gate (between 1 and 4)
    qc = random_circuit(width, depth, max_operands=max_operands, measure=True)

    if qasm_version == "2.0":
        # get OpenQASM 2.0 code
        openqasm_code = qasm2.dumps(qc)
    elif qasm_version == "3.0":
        # get OpenQASM 3.0 code
        openqasm_code = qasm3.dumps(qc)
    else:
        raise ValueError("only support openqasm version 2.0 or 3.0")

    output_file_path = Path(output_file).resolve()
    if output_file_path.exists():
        raise ValueError(f"file[{output_file_path}] is already existed!")

    with open(output_file_path, mode="w+", encoding="utf-8") as f:
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
        "-m",
        "--max-operands",
        dest="max_operands",
        type=int,
        default=3,
        help="maximum qubit operands of each gate",
    )
    parser.add_argument(
        "-q",
        "--qasm-version",
        dest="qasm_version",
        type=str,
        default="3.0",
        help="openqasm version",
    )
    parser.add_argument(
        "-o", "--output", type=str, required=True, help="openqasm file"
    )
    args = parser.parse_args()

    generate_random_qasm(
        width=args.width,
        depth=args.depth,
        max_operands=args.max_operands,
        qasm_version=args.qasm_version,
        output_file=args.output,
    )
