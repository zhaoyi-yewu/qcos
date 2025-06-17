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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import logging
import sys
import os
import shutil
import gzip

from logging.handlers import RotatingFileHandler


class ColouredFormatter(logging.Formatter):
    """
    Coloured Formatter for logger module
    """
    RESET = "\x1B[0m"
    RED = "\x1B[31m"
    YELLOW = "\x1B[33m"
    GREEN = "\x1B[32m"
    PINK = "\x1b[35m"

    def format(self, record, colour=False):

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
            colour = self.GREEN
        elif level_no >= logging.DEBUG:
            colour = self.PINK
        else:
            colour = self.RESET

        message = message.replace("#RESET#", self.RESET)

        # do not show uvicorn filename and line number in logs
        if record.name.startswith("uvicorn"):
            message = message.replace(
                f"{record.name}:{record.lineno}", "uvicorn")

        message = f"{colour}{message}{self.RESET}"

        return message


class ColouredStreamHandler(logging.StreamHandler):
    """
    Coloured Stream Handler for logger module
    """

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


class LogFilter(object):
    """
    This filter some noise from the logs
    """

    def filter(record):
        if isinstance(record.msg, str) and \
                "/settings" in record.msg and "200" in record.msg:
            return 0
        return 1


class CompressedRotatingFileHandler(RotatingFileHandler):
    """
    Custom rotating file handler with compression support.
    """

    def doRollover(self):
        if self.stream:
            self.stream.close()
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = "%s.%d.gz" % (self.baseFilename, i)
                dfn = "%s.%d.gz" % (self.baseFilename, i + 1)
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.baseFilename + ".1.gz"
            if os.path.exists(dfn):
                os.remove(dfn)
            with open(self.baseFilename, "rb") \
                    as f_in, gzip.open(dfn, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        self.mode = "w"
        self.stream = self._open()


def init_logger(
        level, logfile=None, max_bytes=10000000, backup_count=10,
        console=True, compression=True, quiet=False):
    file_stream_handler = None
    console_stream_handler = None
    handlers = []

    if logfile and len(logfile) > 0:
        if compression:
            file_stream_handler = CompressedRotatingFileHandler(
                logfile,
                maxBytes=max_bytes,
                backupCount=backup_count)
        else:
            file_stream_handler = RotatingFileHandler(
                logfile,
                maxBytes=max_bytes,
                backupCount=backup_count)
        file_stream_handler.formatter = ColouredFormatter(
            "{asctime} {levelname} {filename}:{lineno} {message}",
            "%Y-%m-%d %H:%M:%S", "{"
        )
    if console:
        console_stream_handler = ColouredStreamHandler(sys.stdout)
        console_stream_handler.formatter = ColouredFormatter(
            "{asctime} {levelname} {name}:{lineno}#RESET# {message}",
            "%Y-%m-%d %H:%M:%S", "{"
        )
    if quiet:
        file_stream_handler.addFilter(logging.Filter(name="user_facing"))
        console_stream_handler.addFilter(logging.Filter(name="user_facing"))
        logging.getLogger("user_facing").propagate = False
    if level > logging.DEBUG:
        file_stream_handler.addFilter(LogFilter)
        console_stream_handler.addFilter(LogFilter)
    if file_stream_handler:
        handlers.append(file_stream_handler)
    if console_stream_handler:
        handlers.append(console_stream_handler)
    logging.basicConfig(level=level, handlers=handlers)
    return handlers
