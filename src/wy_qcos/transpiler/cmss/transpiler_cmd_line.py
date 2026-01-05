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
from wy_qcos.transpiler.cmss.transpiler_cmss import TranspilerCmss
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.cmss.compiler.decomposer import decompose_gates
from wy_qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from wy_qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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


def main_cmss_transpiler(
    input_file: str,
    output_file: str,
    opt_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL,
    tech_type: str = "",
    config_file: str = "",
):
    """cmss-transpiler performance test."""
    success = False
    # input args check
    file_path = check_file_args(input_file, output_file)
    if not file_path:
        return success

    # load data from qasm file
    qasm_data = read_qasm_from_file(str(file_path))
    if qasm_data is None:
        logger.error(f"read[{file_path}] file failure")
        return success

    # performace testing
    logger.info("start qiskit performace testing...")
    with Timer() as total_timer:
        if tech_type != "":
            # parse the config file of qpu
            abs_config_path = Path(config_file).resolve()
            if not abs_config_path.exists():
                raise ValueError(f"config file[{config_file}] not existed!")

            qpu_config = {}
            Config.parse_toml_file(config_file, extra_config=True)
            if tech_type == Constant.TECH_TYPE_NEUTRAL_ATOM:
                qpu_config = Config.EXTRA_CONFIGS["hanyuan1"]["transpiler"][
                    "qpu_configs"
                ]
                trans_cfg_inst.set_qpu_cfg(qpu_config)
                trans_cfg_inst.set_tech_type(tech_type)
                trans_cfg_inst.set_max_qubits(qpu_config["qubits"])

                transpiler = TranspilerCmss(optimization_level=opt_level)
                expected_basis_gates = [
                    Constant.SINGLE_QUBIT_GATE_RX,
                    Constant.SINGLE_QUBIT_GATE_RY,
                ]
            elif tech_type == Constant.TECH_TYPE_SUPERCONDUCTING:
                qpu_config = Config.EXTRA_CONFIGS["spinq_rpc"]["transpiler"][
                    "qpu_configs"
                ]
                trans_cfg_inst.set_qpu_cfg(qpu_config)
                trans_cfg_inst.set_tech_type(tech_type)
                trans_cfg_inst.set_max_qubits(qpu_config["qubits"])

                transpiler = TranspilerCmss(optimization_level=opt_level)
                expected_basis_gates = [
                    Constant.SINGLE_QUBIT_GATE_RX,
                    Constant.SINGLE_QUBIT_GATE_RY,
                    Constant.TWO_QUBIT_GATE_CX,
                ]
            else:
                raise ValueError(f"tech_type[{tech_type}] is not supported!")

            # generate basis gates list
            with Timer() as ast_timer:
                src_code_info = {"000": qasm_data}
                parse_result = transpiler.parse(src_code_info)
            logger.info(f"parse openqasm: {ast_timer.elapsed:.4f}s")

            # optimize the transpiled gates
            with Timer() as tranpile_timer:
                _, _ = transpiler.transpile(parse_result, expected_basis_gates)
            logger.info(f"cmss tranpiler: {tranpile_timer.elapsed:.4f}s\n")
        else:
            # generate abs tree
            with Timer() as ast_timer:
                tree = get_abs_tree(qasm_data)
            logger.info(f"abs tree: {ast_timer.elapsed:.4f}s")

            # generate IR
            with Timer() as ir_timer:
                cir: QuantumCircuit = get_ir(tree)
                gates_list = cir.get_operations()
            logger.info(f"IR generating: {ir_timer.elapsed:.4f}s")

            # optimize IR
            with Timer() as opt1_timer:
                optimized_gates = optimize_gate(
                    gates_list, opt_level=opt_level
                )
            logger.info(f"IR optimizing: {opt1_timer.elapsed:.4f}s")

            # decompose gate by rules
            supp_basis_gates = [
                Constant.SINGLE_QUBIT_GATE_RX,
                Constant.SINGLE_QUBIT_GATE_RY,
                Constant.TWO_QUBIT_GATE_CX,
            ]
            with Timer() as decompose_timer:
                transpiled_gates = decompose_gates(
                    optimized_gates, supp_basis_gates
                )
            logger.info(f"gates decomposing: {decompose_timer.elapsed:.4f}s")

            # optimize the transpiled gates
            with Timer() as opt2_timer:
                optimize_gate(transpiled_gates, opt_level=opt_level)
            logger.info(f"gates optimizing: {opt2_timer.elapsed:.4f}s\n")

    logger.info(
        f"total running time of cmss-transpiler: {total_timer.elapsed:.4f}s"
    )
    success = True
    return success


def get_parse_args():
    parser = argparse.ArgumentParser(description="cmss transpiler cli")
    parser.add_argument(
        "-i",
        "--input-file",
        dest="input_file",
        type=str,
        required=True,
        help="Specify input file.",
    )
    parser.add_argument(
        "-o",
        "--opt-level",
        dest="opt_level",
        type=int,
        default=1,
        help="Input optimization level",
    )
    parser.add_argument(
        "-t",
        "--tech-type",
        dest="tech_type",
        type=str,
        default="",
        help="Input technology type.",
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
    cmss_args = {
        "input_file": args.input_file,
        "output_file": args.output_file,
        "opt_level": args.opt_level,
        "tech_type": args.tech_type,
        "config_file": args.config_file,
    }
    return cmss_args


def main(argv=None):
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    # parse arguments
    cmss_args = get_parse_args()
    sys.exit(
        main_cmss_transpiler(
            cmss_args["input_file"],
            cmss_args["output_file"],
            cmss_args["opt_level"],
            cmss_args["tech_type"],
            cmss_args["config_file"],
        )
    )
