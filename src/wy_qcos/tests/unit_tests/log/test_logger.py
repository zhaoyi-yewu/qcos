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

"""Unit tests for logging utilities."""

import gzip
import logging
import os
import unittest
from unittest.mock import Mock

from wy_qcos.engine.common import (
    InterceptHandler,
    _allow_log_record,
    _configure_third_party_log_levels,
    secure_loguru_format,
)
from wy_qcos.log import (
    SecureFormatter,
    compress_log_file,
    init_console_logger,
    secure_file_opener,
)
from wy_qcos.log.logger import (
    ColouredFormatter,
    ColouredStreamHandler,
    LogFilter,
    ThirdPartyDebugFilter,
    CompressedRotatingFileHandler,
    init_logger,
    suppress_prefect_third_party_debug,
)

formatter = ColouredFormatter()


def test_secure_formatter_escapes_log_injection():
    """Test SecureFormatter escapes log injection characters."""
    record = logging.LogRecord(
        name="security_test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="user=%s\nINFO forged\x1b[31m",
        args=("alice\radmin",),
        exc_info=None,
    )

    message = SecureFormatter("%(message)s").format(record)

    assert message == ("user=alice\\radmin\\nINFO forged\\x1b[31m")
    assert "\n" not in message
    assert "\r" not in message
    assert "\x1b" not in message
    assert record.msg == "user=%s\nINFO forged\x1b[31m"
    assert record.args == ("alice\radmin",)


def test_secure_loguru_format_escapes_log_injection():
    """Test secure_loguru_format escapes log injection characters."""
    record = {"message": "first\nsecond\x1b[0m"}

    log_format = secure_loguru_format(record, "{message}")

    assert record["message"] == "first\\nsecond\\x1b[0m"
    assert log_format == "{message}\n{exception}"


def test_third_party_debug_logging_is_suppressed(monkeypatch):
    """Test third-party loggers do not inherit application DEBUG level."""
    root_logger = logging.getLogger()
    monkeypatch.setattr(root_logger, "level", logging.DEBUG)
    configured_names = (
        "websockets",
        "websockets.client",
        "httpcore",
        "httpcore.http11",
    )
    for name in configured_names:
        named_logger = logging.getLogger(name)
        monkeypatch.setattr(named_logger, "level", logging.DEBUG)

    _configure_third_party_log_levels()

    assert root_logger.level == logging.DEBUG
    for name in configured_names:
        named_logger = logging.getLogger(name)
        assert named_logger.level == logging.INFO
        assert not named_logger.isEnabledFor(logging.DEBUG)
    for name in ("websockets.server", "httpcore.connection"):
        child_logger = logging.getLogger(name)
        monkeypatch.setattr(child_logger, "level", logging.NOTSET)
        assert child_logger.getEffectiveLevel() == logging.INFO


def test_intercept_handler_filters_third_party_debug(monkeypatch):
    """Test the bridge drops third-party DEBUG after configuration resets."""
    opt_mock = Mock()
    monkeypatch.setattr("wy_qcos.engine.common.logger.opt", opt_mock)
    handler = InterceptHandler()

    for name in ("websockets.client", "httpcore.http11"):
        record = logging.LogRecord(
            name=name,
            level=logging.DEBUG,
            pathname=__file__,
            lineno=1,
            msg="third-party debug",
            args=(),
            exc_info=None,
        )
        handler.emit(record)
    opt_mock.assert_not_called()

    for name, level in (
        ("httpcore.http11", logging.INFO),
        ("wy_qcos.engine", logging.DEBUG),
    ):
        record = logging.LogRecord(
            name=name,
            level=level,
            pathname=__file__,
            lineno=1,
            msg="allowed message",
            args=(),
            exc_info=None,
        )
        handler.emit(record)
    assert opt_mock.call_count == 2


def test_loguru_sink_filter_drops_third_party_debug():
    """Test the sink filter blocks DEBUG from either logging pathway."""
    for name in ("websockets.client", "httpcore.http11"):
        assert not _allow_log_record({
            "name": name,
            "level": Mock(no=logging.DEBUG),
        })
        assert _allow_log_record({
            "name": name,
            "level": Mock(no=logging.INFO),
        })
    assert _allow_log_record({
        "name": "wy_qcos.engine",
        "level": Mock(no=logging.DEBUG),
    })


def test_console_third_party_debug_filter():
    """Test console filtering leaves file behavior and app DEBUG intact."""

    def make_record(name, level):
        return logging.LogRecord(
            name=name,
            level=level,
            pathname=__file__,
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

    console_filter = ThirdPartyDebugFilter()
    for name in ("websockets.client", "httpcore.http11"):
        debug_record = make_record(name, logging.DEBUG)
        info_record = make_record(name, logging.INFO)
        assert not console_filter.filter(debug_record)
        assert console_filter.filter(info_record)
    httpx_info_record = make_record("httpx", logging.INFO)
    assert not console_filter.filter(httpx_info_record)
    assert console_filter.filter(make_record("httpx", logging.WARNING))
    assert console_filter.filter(make_record("wy_qcos.api", logging.DEBUG))


def test_suppress_prefect_third_party_debug(monkeypatch):
    """Test QCOS configures only Prefect console handlers idempotently."""

    class PrefectConsoleHandler(logging.StreamHandler):
        """Simulate Prefect's console handler class."""

    prefect_handler = PrefectConsoleHandler()
    other_handler = logging.StreamHandler()
    root_logger = logging.getLogger()
    monkeypatch.setattr(
        root_logger, "handlers", [prefect_handler, other_handler]
    )
    for name in ("websockets.client", "httpcore.http11", "httpx"):
        named_logger = logging.getLogger(name)
        monkeypatch.setattr(named_logger, "level", logging.DEBUG)

    suppress_prefect_third_party_debug()
    suppress_prefect_third_party_debug()

    assert logging.getLogger("websockets.client").level == logging.INFO
    assert logging.getLogger("httpcore.http11").level == logging.INFO
    assert logging.getLogger("httpx").level == logging.WARNING
    matching_filters = [
        handler_filter
        for handler_filter in prefect_handler.filters
        if isinstance(handler_filter, ThirdPartyDebugFilter)
    ]
    assert len(matching_filters) == 1
    assert other_handler.filters == []
    prefect_handler.close()
    other_handler.close()


def test_secure_file_opener_and_compression(tmp_path):
    """Test secure_file_opener and log compression."""
    log_path = tmp_path / "worker.log"
    with open(
        log_path, "w", encoding="utf-8", opener=secure_file_opener
    ) as stream:
        stream.write("task completed")
    if os.name == "posix":
        assert log_path.stat().st_mode & 0o777 == 0o600

    compress_log_file(log_path)

    compressed_path = tmp_path / "worker.log.gz"
    assert not log_path.exists()
    with gzip.GzipFile(compressed_path, "rb") as stream:
        assert stream.read().decode("utf-8") == "task completed"
    if os.name == "posix":
        assert compressed_path.stat().st_mode & 0o777 == 0o600


def test_init_console_logger_is_idempotent(monkeypatch):
    """Test init_console_logger is idempotent."""
    root_logger = logging.getLogger()
    monkeypatch.setattr(root_logger, "handlers", [])
    monkeypatch.setattr(root_logger, "level", root_logger.level)

    init_console_logger(logging.INFO, "%(message)s")
    init_console_logger(logging.INFO, "%(message)s")

    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0].formatter, SecureFormatter)
    assert root_logger.level == logging.INFO
    root_logger.handlers[0].close()


class TestColouredFormatter:
    """Test ColouredFormatter colour output."""

    def test_format(self):
        """Test format applies correct colours per log level."""
        mock_record = Mock(spec=logging.LogRecord)
        mock_record.name = "uvicorn_logger"

        mock_record.lineno = 42
        mock_record.exc_info = None
        mock_record.exc_text = None
        mock_record.stack_info = None

        mock_record.levelno = logging.DEBUG
        formatter.format(mock_record)
        msg = formatter.format(mock_record, colour=True)
        assert ColouredFormatter.GREY in msg

        mock_record.levelno = logging.CRITICAL
        msg = formatter.format(mock_record, colour=True)
        assert ColouredFormatter.RED in msg

        mock_record.levelno = logging.ERROR
        msg = formatter.format(mock_record, colour=True)
        assert ColouredFormatter.RED in msg

        mock_record.levelno = logging.WARNING
        msg = formatter.format(mock_record, colour=True)
        assert ColouredFormatter.YELLOW in msg

        mock_record.levelno = logging.INFO
        msg = formatter.format(mock_record, colour=True)
        assert ColouredFormatter.WHITE in msg

        mock_record.levelno = logging.DEBUG - 1
        msg = formatter.format(mock_record, colour=True)
        assert ColouredFormatter.RESET in msg


handler = ColouredStreamHandler()


class TestColouredStreamHandler:
    """Test ColouredStreamHandler formatting."""

    def test_format(self):
        """Test handler format and emit methods."""
        mock_record = Mock(spec=logging.LogRecord)
        mock_record.exc_info = None
        mock_record.exc_text = None
        mock_record.stack_info = None

        ans = handler.format(mock_record)

        assert ans is not None
        assert handler.emit(mock_record) is None


log_filter = LogFilter()


class TestLogFilter:
    """Test LogFilter message filtering."""

    def test_filter(self):
        """Test filter accepts and rejects messages."""
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
    """Test CompressedRotatingFileHandler rollover."""

    def setUp(self):
        """Set up a CompressedRotatingFileHandler instance."""
        self.file_handler = CompressedRotatingFileHandler("files")

    def test_doRollover(self):
        """Test doRollover returns None."""
        self.file_handler.backupCount = 10
        assert self.file_handler.doRollover() is None

    def tearDown(self):
        """Clean up handler and temporary files."""
        del self.file_handler
        os.remove("files.1.gz")
        os.remove("files")


def test_init_logger():
    """Test init_logger with various configurations."""
    handlers = init_logger(logging.DEBUG + 1, logfile="log_file", quiet=True)
    assert handlers is not None
    for handler in handlers:
        handler.close()

    handlers = init_logger(1, logfile="log_file", compression=False)
    assert handlers is not None
    for handler in handlers:
        handler.close()
    os.remove("log_file")

    handlers = init_logger(logging.INFO, quiet=True)
    assert len(handlers) == 1
    assert any(
        isinstance(handler_filter, ThirdPartyDebugFilter)
        for handler_filter in handlers[0].filters
    )

    handlers = init_logger(logging.INFO, console=False, quiet=True)
    assert handlers == []
