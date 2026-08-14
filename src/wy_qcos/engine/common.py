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

import logging
import sys

from loguru import logger

from wy_qcos.common.config import Config


class InterceptHandler(logging.Handler):
    """Forward standard logging records to loguru.

    Third-party libraries (e.g. lqcloud) emit logs via the standard
    ``logging`` module. Loguru only routes records produced through
    its own ``logger`` object, so those records never reach the
    stdout/file sinks configured in ``init_logger``. This handler,
    attached to the root logger, re-emits every standard record
    through loguru, bridging the two systems.
    """

    def emit(self, record):
        # Loguru expects a level name; fall back to the numeric
        # level when the name is not recognised.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Walk up the stack to find the frame that issued the log
        # call so loguru reports the original caller (file/line)
        # rather than this handler.
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


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
        log_format: Custom log format (defaults to Config.LOG.LOG_FORMAT)
                   Standard Python logging format string
        log_rotate_max_size_mb: Max size for log rotation in MB
        log_rotate_backup_count: Number of backup log files to retain
        log_rotate_compression: Enable gzip compression for rotated logs
    """
    # Use global Config as default if not provided
    if log_format is None:
        log_format = Config.LOG.LOG_FORMAT
    if log_rotate_max_size_mb is None:
        log_rotate_max_size_mb = Config.LOG.LOG_ROTATE_MAX_SIZE_MB
    if log_rotate_backup_count is None:
        log_rotate_backup_count = Config.LOG.LOG_ROTATE_BACKUP_COUNT
    if log_rotate_compression is None:
        log_rotate_compression = Config.LOG.LOG_ROTATE_COMPRESSION

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

    # Bridge the standard logging module into loguru so that
    # third-party libraries (e.g. lqcloud, requests, urllib3) that
    # emit via ``logging.getLogger(...)`` are also captured by the
    # stdout and file sinks configured above. Without this, their
    # WARNING/ERROR records (such as lqcloud's transient HTTP error
    # retries) never reach the device monitor log file.
    #
    # NOTE: Prefect calls ``logging.config.dictConfig`` during flow
    # execution which re-assigns the *root* logger handlers (see
    # prefect/logging/logging.yml -> root.handlers=[console]). That
    # would silently drop an InterceptHandler installed on the root.
    # To stay immune to this reset we attach InterceptHandler directly
    # to each third-party logger we care about and disable
    # propagation, so the records never travel up to the root logger.
    intercept = InterceptHandler()
    level = logging.DEBUG if debug else logging.INFO
    for name in ("lqcloud", "urllib3", "requests", "charset_normalizer"):
        lib_logger = logging.getLogger(name)
        lib_logger.handlers = [intercept]
        lib_logger.propagate = False
        lib_logger.setLevel(level)

    # Also install InterceptHandler on the root as a catch-all for
    # any other library; if Prefect later resets the root handlers the
    # per-library handlers above still keep working.
    logging.basicConfig(
        level=level,
        handlers=[intercept],
    )
    logging.getLogger().handlers = [intercept]
