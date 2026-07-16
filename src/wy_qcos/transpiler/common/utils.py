#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

import time


class Timer:
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.elapsed = self.end - self.start


class TranspilePerfConstant:
    QASM_FILE = "qasm文件"
    NUM_QUBITS = "比特数"
    GATE_COUNT = "门数量"
    DEPTH = "电路深度"
    TECH_TYPE = "qpu类型"
    OPT_LEVEL = "优化级别"
    PARSE_TIME = "解析时间(s)"
    OPT_TIME1 = "优化1(s)"
    DECOMPOSE_RULE_TIME = "分解规则(s)"
    DECOMPOSE_1Q2Q_TIME = "分解1q2q(s)"
    MAPPING_TIME = "映射时间(s)"
    DECOMPOSE_APPLY_TIME = "分解应用(s)"
    DECOMPOSED_TIME = "分解总时间(s)"
    OPT_TIME2 = "优化2(s)"
    TRANSPILE_TIME = "转译时间(s)"
    TOTAL_TIME = "总时间(s)"
    TRANSPILED_GATE_COUNT = "转译后门数量"
    TRANSPILED_DEPTH = "转译后电路深度"
    CONS_DICT = {
        QASM_FILE: 0,
        NUM_QUBITS: 1,
        GATE_COUNT: 2,
        DEPTH: 3,
        TECH_TYPE: 4,
        OPT_LEVEL: 5,
        PARSE_TIME: 6,
        OPT_TIME1: 7,
        DECOMPOSE_RULE_TIME: 8,
        DECOMPOSE_1Q2Q_TIME: 9,
        MAPPING_TIME: 10,
        DECOMPOSE_APPLY_TIME: 11,
        DECOMPOSED_TIME: 12,
        OPT_TIME2: 13,
        TRANSPILE_TIME: 14,
        TOTAL_TIME: 15,
        TRANSPILED_GATE_COUNT: 16,
        TRANSPILED_DEPTH: 17,
    }


class TranspileRuntime:
    def __init__(self):
        self.total_time = 0.0
        self.transpile_time = 0.0
        self.parse_time = 0.0
        self.opt_time1 = 0.0
        self.decompose_rule_time = 0.0
        self.decompose_1q2q_time = 0.0
        self.decompose_apply_time = 0.0
        self.decomposed_time = 0.0
        self.opt_time2 = 0.0
        self.mapping_time = 0.0
        self.routing_time = 0.0
        self.transpiled_gate_count = 0
        self.transpiled_depth = 0

    def add_runtime(self, runtime: "TranspileRuntime"):
        self.total_time += runtime.total_time
        self.transpile_time += runtime.transpile_time
        self.parse_time += runtime.parse_time
        self.opt_time1 += runtime.opt_time1
        self.decompose_rule_time += runtime.decompose_rule_time
        self.decompose_1q2q_time += runtime.decompose_1q2q_time
        self.decompose_apply_time += runtime.decompose_apply_time
        self.opt_time2 += runtime.opt_time2
        self.mapping_time += runtime.mapping_time
        self.routing_time += runtime.routing_time
        self.transpiled_gate_count += runtime.transpiled_gate_count
        self.transpiled_depth += runtime.transpiled_depth

    def avg_runtime(self, run_count):
        self.total_time /= run_count
        self.transpile_time /= run_count
        self.parse_time /= run_count
        self.opt_time1 /= run_count
        self.decompose_rule_time /= run_count
        self.decompose_1q2q_time /= run_count
        self.decompose_apply_time /= run_count
        self.opt_time2 /= run_count
        self.mapping_time /= run_count
        self.routing_time /= run_count
        self.transpiled_gate_count //= run_count
        self.transpiled_depth //= run_count
