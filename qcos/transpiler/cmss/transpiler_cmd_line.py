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

from qcos.common.config import Config
from qcos.transpiler.cmss.compiler.decomposer import decompose_gates
from qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir
from qcos.transpiler.cmss.optimizer.gate_optimizer import optimize_gate


logger = logging.getLogger(__name__)

VERSION = Config.VERSION
DESCRIPTION = "QCOS Transpiler command line interface"


def read_qasm_from_file(file_path):
    try:
        with open(file_path, 'r', encoding="utf-8") as f:
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
    # 处理文件路径read_qasm_from_file
    relative_path = "samples/qasm/3.0/benchmark/100bits_50000d.qasm"
    file_path = Path(relative_path).resolve()

    if not file_path.exists():
        logger.error(f"file not existed - {file_path}")
        return

    # 读取QASM数据
    qasm_data = read_qasm_from_file(str(file_path))
    if qasm_data is None:
        logger.error("read file failure")
        return

    # 执行性能测试
    logger.info("开始性能测试...")
    with Timer() as total_timer:
        # 生成抽象语法树
        with Timer() as ast_timer:
            tree = get_abs_tree(qasm_data)
        logger.info(f"生成抽象语法树耗时: {ast_timer.elapsed:.4f}秒")

        # 转换为IR
        with Timer() as ir_timer:
            q_num, ir = get_ir(tree)
        logger.info(f"转换为IR耗时: {ir_timer.elapsed:.4f}秒")

        # 优化IR
        with Timer() as opt1_timer:
            optimized_ir = optimize_gate(ir)
        logger.info(f"IR优化耗时: {opt1_timer.elapsed:.4f}秒")

        # 分解门电路
        with Timer() as decompose_timer:
            transpiled_gates = decompose_gates(optimized_ir)
        logger.info(f"门分解耗时: {decompose_timer.elapsed:.4f}秒")

        # 优化分解后的门电路
        with Timer() as opt2_timer:
            optimized_gates = optimize_gate(transpiled_gates)
        logger.info(f"门电路优化耗时: {opt2_timer.elapsed:.4f}秒")

    logger.info(f"\n整个流程总耗时: {total_timer.elapsed:.4f}秒")
