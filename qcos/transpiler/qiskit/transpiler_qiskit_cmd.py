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


def main():
    relative_path = "samples/qasm/3.0/benchmark/100bits_50000d_v2.qasm"
    file_path = Path(relative_path).resolve()

    if not file_path.exists():
        logger.error(f"file not existed - {file_path}")
        return

    # load data from qasm file
    qasm_data = read_qasm_from_file(str(file_path))
    if qasm_data is None:
        logger.error("read file failure")
        return

    expected_basis_gates = [
        Constant.SINGLE_QUBIT_GATE_RX,
        Constant.SINGLE_QUBIT_GATE_RY,
        Constant.SINGLE_QUBIT_GATE_RZ,
        Constant.TWO_QUBIT_GATE_CX,
    ]
    trans_cfg_inst.set_driver_name("DriverQiskitAerSim")

    transpiler = TranspilerQiskit()
    src_code_info = {"000": qasm_data}

    # performace testing
    logger.info("开始性能测试...")
    with Timer() as total_timer:
        # generate abs tree
        with Timer() as parse_timer:
            parse_result = transpiler.parse(src_code_info)
        logger.info(f"解析QASM文件耗时: {parse_timer.elapsed:.4f}秒")

        # generate IR
        with Timer() as tranpile_timer:
            _ = transpiler.transpile(parse_result, expected_basis_gates)
        logger.info(f"编译量子电路: {tranpile_timer.elapsed:.4f}秒")

    logger.info(f"\n整个流程Qiskit总耗时: {total_timer.elapsed:.4f}秒")
