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
import os
import unittest
from unittest.mock import Mock

from qcos.log.logger import (ColouredFormatter,
                             ColouredStreamHandler,
                             LogFilter,
                             CompressedRotatingFileHandler,
                             init_logger)

formatter = ColouredFormatter()


class TestColouredFormatter:
    def test_format(self):
        mock_record = Mock(spec=logging.LogRecord)
        mock_record.name = "uvicorn_logger"

        mock_record.lineno = 42
        mock_record.exc_info = None
        mock_record.exc_text = None
        mock_record.stack_info = None

        mock_record.levelno = logging.DEBUG
        formatter.format(mock_record)
        msg = formatter.format(mock_record, colour=True)
        assert "\x1b[35m" in msg

        mock_record.levelno = logging.CRITICAL
        msg = formatter.format(mock_record, colour=True)
        assert "\x1B[31m" in msg

        mock_record.levelno = logging.ERROR
        msg = formatter.format(mock_record, colour=True)
        assert "\x1B[31m" in msg

        mock_record.levelno = logging.WARNING
        msg = formatter.format(mock_record, colour=True)
        assert "\x1B[33m" in msg

        mock_record.levelno = logging.INFO
        msg = formatter.format(mock_record, colour=True)
        assert "\x1B[32m" in msg

        mock_record.levelno = logging.DEBUG - 1
        msg = formatter.format(mock_record, colour=True)
        assert "\x1B[0m" in msg


handler = ColouredStreamHandler()


class TestColouredStreamHandler:
    def test_format(self):
        mock_record = Mock(spec=logging.LogRecord)
        mock_record.exc_info = None
        mock_record.exc_text = None
        mock_record.stack_info = None

        ans = handler.format(mock_record)
        assert ans is not None

        assert handler.emit(mock_record) is None


log_filter = LogFilter()


class TestLogFilter:
    def test_filter(self):
        mock_record = Mock(spec=logging.LogRecord)
        mock_record.exc_info = None
        mock_record.exc_text = None
        mock_record.stack_info = None

        mock_record.msg = "Hello, /settings, 200"
        ans = log_filter.filter(mock_record)
        assert ans == 0

        mock_record.msg = "HTTP Request: 111 222 "
        ans = log_filter.filter(mock_record)
        assert ans == 1


class TestCompressedRotatingFileHandler(unittest.TestCase):

    def setUp(self):
        self.file_handler = CompressedRotatingFileHandler("files")

    def test_doRollover(self):
        self.file_handler.backupCount = 10
        assert self.file_handler.doRollover() is None
        os.remove("files.1.gz")


def test_init_logger():
    handlers = init_logger(logging.DEBUG + 1,
                           logfile="log_file", quiet=True)
    assert handlers is not None

    handlers = init_logger(1, logfile="log_file", compression=False)
    assert handlers is not None
    os.remove("files")
