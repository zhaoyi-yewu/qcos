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
import os
import sys

from logging.handlers import RotatingFileHandler

from wy_qcos.common.config import Config
from wy_qcos.log import (
    SecureFormatter,
    compress_log_file,
    secure_file_opener,
)

PERF_LEVEL = 15
logging.addLevelName(PERF_LEVEL, "PERF")


def log_perf(logger: logging.Logger, msg, *args, **kwargs):
    """Log a PERF level message."""
    if logger.isEnabledFor(PERF_LEVEL):
        logger._log(PERF_LEVEL, msg, args, **kwargs)


class ColouredFormatter(SecureFormatter):
    """Coloured Formatter for logger module."""

    RESET = "\x1b[0m"
    WHITE = "\x1b[37m"
    RED = "\x1b[31m"
    YELLOW = "\x1b[33m"
    GREEN = "\x1b[32m"
    GREY = "\x1b[38m"

    def format(self, record, colour=False):
        """Format log record."""
        message = super().format(record)

        if not colour:
            return message.replace("#RESET#", "")

        level_no = record.levelno
        if level_no >= logging.CRITICAL:
            colour = self.RED
        elif level_no >= logging.ERROR:
            colour = self.RED
        elif level_no >= logging.WARNING:
            colour = self.YELLOW
        elif level_no >= logging.INFO:
            colour = self.WHITE
        elif level_no >= PERF_LEVEL:
            colour = self.GREEN
        elif level_no >= logging.DEBUG:
            colour = self.GREY
        else:
            colour = self.RESET

        message = message.replace("#RESET#", self.RESET)

        # do not show uvicorn filename and line number in logs
        if record.name.startswith("uvicorn"):
            message = message.replace(
                f"{record.name}:{record.lineno}", "uvicorn"
            )

        message = f"{colour}{message}{self.RESET}"

        return message


class ColouredStreamHandler(logging.StreamHandler):
    """Coloured Stream Handler for logger module."""

    def format(self, record, colour=False):
        if not isinstance(self.formatter, ColouredFormatter):
            self.formatter = ColouredFormatter()

        return self.formatter.format(record, colour)

    def emit(self, record):
        stream = self.stream
        try:
            msg = self.format(record, stream.isatty())
            stream.write(msg)
            stream.write(self.terminator)
            self.flush()
        # On OSX when frozen flush raise a BrokenPipeError
        except BrokenPipeError:
            pass
        except Exception:
            self.handleError(record)


class ThirdPartyDebugFilter:
    """Drop noisy third-party records from console output only."""

    def filter(self, record):
        """Allow application logs and useful third-party records."""
        name = record.name.partition(".")[0]
        if name == "httpx":
            return record.levelno >= logging.WARNING
        if record.levelno >= logging.INFO:
            return 1
        return name not in ("websockets", "httpcore")


def suppress_prefect_third_party_debug():
    """Suppress third-party DEBUG in QCOS's Prefect console output."""
    for name in (
        "websockets",
        "websockets.client",
        "httpcore",
        "httpcore.http11",
    ):
        logging.getLogger(name).setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    for handler in logging.getLogger().handlers:
        if handler.__class__.__name__ != "PrefectConsoleHandler":
            continue
        if not any(
            isinstance(handler_filter, ThirdPartyDebugFilter)
            for handler_filter in handler.filters
        ):
            handler.addFilter(ThirdPartyDebugFilter())


class LogFilter:
    """This filter some noise from the logs."""

    def filter(self, record):
        if (
            isinstance(record.msg, str)
            and "/settings" in record.msg
            and "200" in record.msg
        ):
            return 0
        if (
            isinstance(record.msg, str)
            and "HTTP Request: %s %s " in record.msg
        ):
            return 0
        return 1


class PerfFilter:
    """Allows PERF level and WARNING+ records through."""

    def filter(self, record):
        return (
            1
            if record.levelno == PERF_LEVEL
            or record.levelno >= logging.WARNING
            else 0
        )


class SecureRotatingFileHandler(RotatingFileHandler):
    """Rotate logs opened with restrictive permissions and UTF-8."""

    def _open(self):
        return open(
            self.baseFilename,
            self.mode,
            encoding=self.encoding or "utf-8",
            errors=self.errors or "backslashreplace",
            opener=secure_file_opener,
        )


class CompressedRotatingFileHandler(SecureRotatingFileHandler):
    """Custom rotating file handler with compression support."""

    def doRollover(self):
        if self.stream:
            self.stream.close()
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = f"{self.baseFilename}.{i}.gz"
                dfn = f"{self.baseFilename}.{i + 1}.gz"
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.baseFilename + ".1.gz"
            if os.path.exists(dfn):
                os.remove(dfn)
            compress_log_file(self.baseFilename, dfn)
        self.mode = "w"
        self.stream = self._open()


def init_logger(
    level,
    *,
    logfile=None,
    max_bytes=10000000,
    backup_count=10,
    console=True,
    compression=True,
    quiet=False,
):
    file_stream_handler = None
    console_stream_handler = None
    handlers = []

    if logfile and len(logfile) > 0:
        if compression:
            file_stream_handler = CompressedRotatingFileHandler(
                logfile,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
                errors="backslashreplace",
            )
        else:
            file_stream_handler = SecureRotatingFileHandler(
                logfile,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
                errors="backslashreplace",
            )
        file_stream_handler.formatter = ColouredFormatter(
            Config.LOG.LOG_FORMAT
        )
    if console:
        console_stream_handler = ColouredStreamHandler(sys.stdout)
        console_stream_handler.formatter = ColouredFormatter(
            Config.LOG.LOG_FORMAT
        )
        console_stream_handler.addFilter(ThirdPartyDebugFilter())
    handlers = [
        handler
        for handler in (file_stream_handler, console_stream_handler)
        if handler is not None
    ]
    if quiet:
        for handler in handlers:
            handler.addFilter(logging.Filter(name="user_facing"))
        logging.getLogger("user_facing").propagate = False
    if level > logging.DEBUG:
        for handler in handlers:
            handler.addFilter(LogFilter())
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        for handler in handlers:
            root_logger.addHandler(handler)
    root_logger.setLevel(level)
    return handlers
