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

import sys
import logging
from pathlib import Path
import time
from datetime import datetime
import argparse

from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.qiskit.transpiler_qiskit import TranspilerQiskit


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


def check_file_args(input_file, output_file):
    file_path = Path(input_file).resolve()
    if not file_path.exists():
        logger.error(f"input file[{file_path}] not existed")
        return None

    if output_file != "":
        output_file_path = Path(output_file).resolve()
        if output_file_path.exists():
            logger.info(f"output file[{output_file_path}] has existed")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file_path = output_file_path.with_stem(
                f"{output_file_path.stem}_{timestamp}"
            )

        # create output file
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(f"testing file: {input_file}\n")
        file_handler = logging.FileHandler(output_file_path)
        logger.addHandler(file_handler)

    return file_path


def main_qiskit_transpiler(
    input_file: str,
    basis_gates: str = "",
    opt_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL,
    config_file: str = "",
    output_file: str = "",
):
    """qiskit-transpiler performance test."""
    success = False
    # input args check
    file_path = check_file_args(input_file, output_file)
    if not file_path:
        return success

    # load data from qasm file
    qasm_data = read_qasm_from_file(str(file_path))
    if qasm_data is None:
        logger.error("read file failure")
        return success

    # baisis gates set
    if basis_gates == "":
        basis_gates_list = [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.TWO_QUBIT_GATE_CX,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
    else:
        basis_gates_list = basis_gates.split(",")
        for gate in basis_gates_list:
            gate = gate.strip()
            if gate not in legal_basis_gates:
                logger.error(f"unsupported the illegal gate[{gate}]")
                return success

    # config file parsing
    if config_file != "":
        abs_config_path = Path(config_file).resolve()
        if not abs_config_path.exists():
            raise ValueError(f"config file[{config_file}] not existed!")

        qpu_config = {}
        Config.parse_toml_file(config_file, extra_config=True)
        qpu_config = Config.EXTRA_CONFIGS["qiskit_marrakesh"]["transpiler"][
            "qpu_configs"
        ]
        trans_cfg_inst.set_qpu_cfg(qpu_config)
        trans_cfg_inst.set_tech_type(Constant.TECH_TYPE_SUPERCONDUCTING)
        trans_cfg_inst.set_max_qubits(qpu_config["qubits"])

        trans_cfg_inst.set_driver_name("NoDriverQiskit")
    else:
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

        # transpile the circuit by qiskit
        with Timer() as tranpile_timer:
            _ = transpiler.transpile(parse_result, basis_gates_list)
        logger.info(
            f"transpile quantum circuit: {tranpile_timer.elapsed:.4f}s\n"
        )

    logger.info(
        f"total running time of qiskit-transpiler: {total_timer.elapsed:.4f}s"
    )
    success = True
    return success


def get_parse_args():
    parser = argparse.ArgumentParser(description="qiskit transpiler cli")
    parser.add_argument(
        "-i",
        "--input-file",
        dest="input_file",
        type=str,
        required=True,
        help="Specify input file.",
    )
    parser.add_argument(
        "-g",
        "--gates-list",
        dest="gates_list",
        type=str,
        default="",
        help="Input basis gates.",
    )
    parser.add_argument(
        "-o",
        "--opt-level",
        dest="opt_level",
        type=int,
        default=1,
        help="Input optimization level.",
    )
    parser.add_argument(
        "-c",
        "--config-file",
        dest="config_file",
        type=str,
        default="",
        help="Input config file.",
    )
    parser.add_argument(
        "-O",
        "--output-file",
        dest="output_file",
        type=str,
        default="",
        help="Input output file.",
    )
    args = parser.parse_args()
    qiskit_args = {
        "input_file": args.input_file,
        "basis_gates": args.gates_list,
        "opt_level": args.opt_level,
        "config_file": args.config_file,
        "output_file": args.output_file,
    }
    return qiskit_args


def main(argv=None):
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    # parse arguments
    qiskit_args = get_parse_args()
    sys.exit(
        main_qiskit_transpiler(
            qiskit_args["input_file"],
            qiskit_args["basis_gates"],
            qiskit_args["opt_level"],
            qiskit_args["config_file"],
            qiskit_args["output_file"],
        )
    )
