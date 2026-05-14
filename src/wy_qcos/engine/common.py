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


def convert_log_format_to_loguru(log_format):
    """Convert standard Python logging format to loguru format.

    Args:
        log_format: Standard Python logging format string

    Returns:
        Loguru format string
        e.g., "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} {message}"
    """
    if log_format is None:
        return "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} {message}"

    # Convert format string
    result = log_format

    # Replace %(asctime)s with loguru time format
    result = result.replace("%(asctime)s", "{time:YYYY-MM-DD HH:mm:ss}")

    # Replace %(levelname)s with loguru level
    result = result.replace("%(levelname)s", "{level}")

    # Replace %(name)s (logger name)
    result = result.replace("%(name)s", "{name}")

    # Replace %(module)s (module name) - note: loguru's {name} includes module
    result = result.replace("%(module)s", "{name}")

    # Replace %(lineno)d and %(lineno)s (line number)
    result = result.replace("%(lineno)d", "{line}")
    result = result.replace("%(lineno)s", "{line}")

    # Replace %(message)s
    result = result.replace("%(message)s", "{message}")

    # Replace %(funcName)s (function name)
    result = result.replace("%(funcName)s", "{function}")

    # Replace %(filename)s (file name)
    result = result.replace("%(filename)s", "{file}")

    # Replace %(process)d (process ID)
    result = result.replace("%(process)d", "{process}")

    # Replace %(thread)d (thread ID)
    result = result.replace("%(thread)d", "{thread}")

    return result


def init_logger(
    log_file_path,
    debug=False,
    log_format=None,
    log_rotate_max_size_mb=None,
    log_rotate_backup_count=None,
    log_rotate_compression=None,
):
    """Initialize logger with configurable parameters.

    Args:
        log_file_path: Path to the log file
        debug: Enable debug logging level
        log_format: Custom log format (defaults to Config.LOG_FORMAT)
                   Standard Python logging format string
        log_rotate_max_size_mb: Max size for log rotation in MB
        log_rotate_backup_count: Number of backup log files to retain
        log_rotate_compression: Enable gzip compression for rotated logs
    """
    # Use global Config as default if not provided
    if log_format is None:
        log_format = Config.LOG_FORMAT
    if log_rotate_max_size_mb is None:
        log_rotate_max_size_mb = Config.LOG_ROTATE_MAX_SIZE_MB
    if log_rotate_backup_count is None:
        log_rotate_backup_count = Config.LOG_ROTATE_BACKUP_COUNT
    if log_rotate_compression is None:
        log_rotate_compression = Config.LOG_ROTATE_COMPRESSION

    # Convert standard log format to loguru format
    loguru_format = convert_log_format_to_loguru(log_format)

    # Config Loguru
    # pylint: disable=duplicate-code
    # remove all
    logger.remove()

    # add logger: stdout
    logger.add(
        sys.stdout,
        level="DEBUG" if debug else "INFO",
        format=loguru_format,
        colorize=True,
    )

    # add logger: log file
    logger.add(
        log_file_path,
        level="DEBUG" if debug else "INFO",
        rotation=f"{log_rotate_max_size_mb} MB",
        compression="gz" if log_rotate_compression else None,
        retention=log_rotate_backup_count,
        format=loguru_format,
    )
