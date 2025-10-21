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

import logging
from pathlib import Path
import time

from qcos.common.constant import Constant
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.qiskit.transpiler_qiskit import TranspilerQiskit


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

legal_basis_gates = [
    "x",
    "y",
    "z",
    "h",
    "s",
    "sdg",
    "tdg",
    "t",
    "rx",
    "ry",
    "rz",
    "u1",
    "u2",
    "u3",
    "ch",
    "crx",
    "cry",
    "crz",
    "cx",
    "cy",
    "cz",
]


def read_qasm_from_file(file_path):
    try:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"read file error: {e}")
        return None


class Timer:
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.elapsed = self.end - self.start


def main(
    input_file: str,
    basis_gates: str = "",
    qasm_version: str = "3.0",
    opt_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL,
    output_file: str = "",
):
    """qiskit-transpiler performance test"""
    # input args check
    file_path = Path(input_file).resolve()
    if not file_path.exists():
        logger.error(f"input file[{file_path}] not existed")
        return

    output_file_path = Path(output_file).resolve()
    if output_file_path.exists():
        logger.error(f"output file[{output_file_path}] has existed")
        return
    else:
        # create output file
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(f"testing file: {input_file}\n")
        file_handler = logging.FileHandler(output_file_path)
        logger.addHandler(file_handler)

    if qasm_version not in ["2.0", "3.0"]:
        logger.error(
            f"""only support openqasm version 2.0 or 3.0
            openqasm version: {qasm_version}"""
        )
        return

    # load data from qasm file
    qasm_data = read_qasm_from_file(str(file_path))
    if qasm_data is None:
        logger.error("read file failure")
        return

    if basis_gates is None:
        basis_gates_list = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CX,
        ]
    else:
        basis_gates_list = basis_gates.split(",")
        for gate in basis_gates_list:
            if gate not in legal_basis_gates:
                logger.error(f"unsupported the illegal gate[{gate}]")
                return

    trans_cfg_inst.set_driver_name("DriverQiskitAerSim")

    transpiler = TranspilerQiskit(opt_level=opt_level)
    src_code_info = {"000": qasm_data}

    # performace testing
    logger.info("start qiskit performace testing...")
    with Timer() as total_timer:
        # generate abs tree
        with Timer() as parse_timer:
            parse_result = transpiler.parse(src_code_info)
        logger.info(f"parsing OpenQASM: {parse_timer.elapsed:.4f}s")

        # generate IR
        with Timer() as tranpile_timer:
            _ = transpiler.transpile(parse_result, basis_gates_list)
        logger.info(
            f"transpile quantum circuit: {tranpile_timer.elapsed:.4f}s\n"
        )

    logger.info(
        f"total running time of qiskit-transpiler: {total_timer.elapsed:.4f}s"
    )
