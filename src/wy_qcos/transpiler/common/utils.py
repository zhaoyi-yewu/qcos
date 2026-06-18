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

import sys
import time
import logging


class TransLogger:
    def __init__(self, allowed_tags=None):
        self.logger = logging.getLogger("wy_qcos.transpiler")
        self.allowed_tags = allowed_tags or []
        self.formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(tag)s]:"
            "%(name)s:%(funcName)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def _log(self, level, msg, tag):
        """Set the log base info.

        Description:
            Only tags in allowed_tags are permitted to output.
            Empty list means no tags are allowed.

        Args:
            level: Log level (e.g., logging.INFO, logging.ERROR).
            msg: Log message.
            tag: Custom tag for categorizing logs (e.g., "PERF",
            "ERROR", "WARNING").
        """
        if tag not in self.allowed_tags:
            return

        self.logger.log(level, msg, extra={"tag": tag})

    def log_perf(self, msg):
        """Performance log (INFO level)."""
        self._log(logging.INFO, msg, "PERF")

    def log_error(self, msg):
        """Error log (ERROR level)."""
        self._log(logging.ERROR, msg, "ERROR")

    def log_warning(self, msg):
        """Warning log (WARNING level)."""
        self._log(logging.INFO, msg, "WARNING")

    def log_debug(self, msg):
        """DEBUG log (DEBUG level)."""
        self._log(logging.INFO, msg, "DEBUG")

    def set_allowed_tags(self, tags):
        self.allowed_tags = tags

    def set_log_file(self, log_file):
        """Set log file path for output.

        Description: Logs passing the tag filter will be written to
            this file in addition to propagating to qcos handlers.

        Args:
            log_file: Path to the log file.
        """
        if log_file is None:
            return
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)


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
    CONS_DICT = {
        QASM_FILE: 0,
        NUM_QUBITS: 1,
        DEPTH: 2,
        TECH_TYPE: 3,
        OPT_LEVEL: 4,
        PARSE_TIME: 5,
        OPT_TIME1: 6,
        DECOMPOSE_RULE_TIME: 7,
        DECOMPOSE_1Q2Q_TIME: 8,
        MAPPING_TIME: 9,
        DECOMPOSE_APPLY_TIME: 10,
        DECOMPOSED_TIME: 11,
        OPT_TIME2: 12,
        TRANSPILE_TIME: 13,
        TOTAL_TIME: 14,
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

    def avg_runtime(self, run_count):
        self.total_time /= run_count
        self.transpile_time /= run_count
        self.parse_time /= run_count
        self.opt_time1 /= run_count
        self.decompose_rule_time /= run_count
        self.decompose_1q2q_time /= run_count
        self.decompose_apply_time /= run_count
        self.opt_time2 /= run_count


def init_cli_logging():
    """Initialize logging for CLI mode.

        Called at startup by CLI tools (qcos-transpiler.py,
        qiskit-transpiler.py, etc.).

    Description:

        root logger set to WARNING, suppressing all INFO/DEBUG logs.
        wy_qcos.transpiler's handler only passes records tagged by
        trans_logger.

        Two operating modes:
            Server mode (server.py):
            ┌────────────────────────────────────────────────────────────────┐
            │  root (handlers=[])                                            │
            │    └── wy_qcos (level=INFO, handlers=[file, console])          │
            │          └── wy_qcos.transpiler (handlers=[], propagate=True)
            │                └── trans_logger (tag filter → flows to wy_qcos)
            └────────────────────────────────────────────────────────────────┘

            CLI mode (qcos-transpiler.py):
            ┌────────────────────────────────────────────────────────────────┐
            │  root (level=WARNING)   ← suppresses all INFO/DEBUG            │
            │    └── wy_qcos (level=WARNING)                                 │
            │          └── wy_qcos.transpiler (level=INFO, propagate=False)
            │                ├── handler: StreamHandler(stdout)              │
            │                │     └── _TagFilter (only passes tagged records)
            │                └── trans_logger → extra={"tag":"PERF"}         │
            │                      → output                                  │
            │  regular logger.info("xxx") (no tag) → _TagFilter blocks       │
            └────────────────────────────────────────────────────────────────┘
    """

    class _TagFilter(logging.Filter):
        def filter(self, record):
            return hasattr(record, "tag")

    logging.getLogger().setLevel(logging.WARNING)
    trans_logger.logger.setLevel(logging.INFO)
    _handler = logging.StreamHandler(sys.stdout)
    _handler.addFilter(_TagFilter())
    _handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(tag)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    trans_logger.logger.addHandler(_handler)
    trans_logger.logger.propagate = False


trans_logger = TransLogger(allowed_tags=[])
