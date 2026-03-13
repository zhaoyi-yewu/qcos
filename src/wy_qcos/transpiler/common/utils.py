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
import logging


class TransLogger:
    def __init__(self, logfile=None, allowed_tags=None):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        # 默认允许所有标记，若指定则过滤
        self.allowed_tags = allowed_tags or []

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(tag)s]:"
            "%(name)s:%(funcName)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler = None
        if logfile:
            file_handler = logging.FileHandler(logfile, encoding="utf-8")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        self.logger.propagate = False

    def _log(self, level, msg, tag):
        """Set the log base info.

        Description:
            If allowed_tags is emtpy, all tags are allowed.

        Args:
            level: Log level (e.g., logging.INFO, logging.ERROR).
            msg: Log message.
            tag: Custom tag for categorizing logs (e.g., "PERF",
            "ERROR", "WARNING").
        """
        if self.allowed_tags and tag not in self.allowed_tags:
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

    # Set allowed tags for filtering logs. If empty, all tags are allowed.
    def set_allowed_tags(self, tags):
        self.allowed_tags = tags

    def set_log_file(self, log_file):
        """Set log file path for output.

        Description: Output content will be written to the output file.
            If None, logs will only be output to console.

        Args:
            log_file: Path to the log file.
        """
        if log_file is None:
            return
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(tag)s]:"
            "%(name)s:%(funcName)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)


class Timer:
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.elapsed = self.end - self.start


class TranspileRuntime:
    def __init__(self):
        self.total_time = 0.0
        self.transpile_time = 0.0
        self.parse_time = 0.0
        self.opt_time1 = 0.0
        self.decompose_rule_time = 0.0
        self.decompose_1q2q_time = 0.0
        self.decompose_apply_time = 0.0
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


trans_logger = TransLogger(allowed_tags=["PERF", "ERROR", "DEBUG"])
