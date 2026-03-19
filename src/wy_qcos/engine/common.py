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

from loguru import logger

from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant


def init_logger(log_file_path, debug=False):
    # Config Loguru
    # pylint: disable=duplicate-code
    # remove all
    logger.remove()

    # add logger: stdout
    logger.add(
        sys.stdout,
        level="DEBUG" if debug else "INFO",
        format=Constant.PREFECT_JOB_LOG_FORMAT,
        colorize=True,
    )

    # add logger: log file
    logger.add(
        log_file_path,
        level="DEBUG" if debug else "INFO",
        rotation=f"{Config.LOG_ROTATE_MAX_SIZE_MB} MB",
        compression="gz" if Config.LOG_ROTATE_COMPRESSION else None,
        retention=Config.LOG_ROTATE_BACKUP_COUNT,
        format=Constant.PREFECT_JOB_LOG_FORMAT,
    )
