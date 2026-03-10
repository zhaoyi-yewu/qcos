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

logger = logging.getLogger(__name__)


def init_logging(level=logging.INFO, logfile=None):
    """Init logging."""
    if logger.handlers:
        return

    file_handler = None
    console_handler = logging.StreamHandler()

    if logfile:
        file_handler = logging.FileHandler(logfile, encoding="utf-8")

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s:%(name)s:%(funcName)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if console_handler:
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    if file_handler:
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.setLevel(level)
    logger.propagate = False


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
