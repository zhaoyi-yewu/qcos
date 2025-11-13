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

import logging
from pathlib import Path
import time
from datetime import datetime

from qcos.common.config import Config
from qcos.common.constant import Constant
from qcos.transpiler.cmss.transpiler_cmss import TranspilerCmss
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.cmss.compiler.decomposer import decompose_gates
from qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate

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


def main(
    input_file: str,
    output_file: str,
    opt_level: int = Constant.DEFAULT_OPTIMIZATION_LEVEL,
    tech_type: str = "",
    config_file: str = "",
):
    """
    cmss-transpiler performance test
    """
    # input args check
    file_path = Path(input_file).resolve()
    if not file_path.exists():
        logger.error(f"input file[{file_path}] not existed")
        return

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

    # load data from qasm file
    qasm_data = read_qasm_from_file(str(file_path))
    if qasm_data is None:
        logger.error(f"read[{file_path}] file failure")
        return

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
            else:
                raise ValueError(f"tech_type[{tech_type}] is not supported!")

            transpiler = TranspilerCmss(optimization_level=opt_level)
            expected_basis_gates = [
                Constant.SINGLE_QUBIT_GATE_RX,
                Constant.SINGLE_QUBIT_GATE_RY,
            ]
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
                _, ir = get_ir(tree)
            logger.info(f"IR generating: {ir_timer.elapsed:.4f}s")

            # optimize IR
            with Timer() as opt1_timer:
                optimized_ir = optimize_gate(ir, opt_level=opt_level)
            logger.info(f"IR optimizing: {opt1_timer.elapsed:.4f}s")

            # decompose gate by rules
            with Timer() as decompose_timer:
                transpiled_gates = decompose_gates(optimized_ir)
            logger.info(f"gates decomposing: {decompose_timer.elapsed:.4f}s")

            # optimize the transpiled gates
            with Timer() as opt2_timer:
                optimize_gate(transpiled_gates, opt_level=opt_level)
            logger.info(f"gates optimizing: {opt2_timer.elapsed:.4f}s\n")

    logger.info(
        f"total running time of cmss-transpiler: {total_timer.elapsed:.4f}s"
    )
