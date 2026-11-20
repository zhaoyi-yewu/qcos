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

import copy
import gzip
import logging
import os
import shutil
import time


_LOG_MESSAGE_TRANSLATION = {
    code: f"\\x{code:02x}" for code in (*range(32), *range(127, 160))
}
_LOG_MESSAGE_TRANSLATION.update({
    ord("\t"): "\\t",
    ord("\n"): "\\n",
    ord("\r"): "\\r",
    0x2028: "\\u2028",
    0x2029: "\\u2029",
})


def sanitize_log_message(message):
    """Escape control characters that could forge log entries."""
    return str(message).translate(_LOG_MESSAGE_TRANSLATION)


class SecureFormatter(logging.Formatter):
    """Format one untrusted log message without control characters."""

    def format(self, record):
        """Sanitize the message while preserving exception formatting."""
        safe_record = copy.copy(record)
        safe_record.msg = sanitize_log_message(record.getMessage())
        safe_record.args = ()
        return super().format(safe_record)


def secure_file_opener(path, flags):
    """Open a log file with owner-only permissions on POSIX systems."""
    file_descriptor = os.open(path, flags, 0o600)
    if os.name == "posix":
        try:
            os.fchmod(file_descriptor, 0o600)
        except OSError:
            os.close(file_descriptor)
            raise
    return file_descriptor


def compress_log_file(file_path, compressed_path=None):
    """Compress a log file without making the archive broadly readable."""
    if compressed_path is None:
        compressed_path = f"{file_path}.gz"
    if os.path.exists(compressed_path):
        compressed_path = f"{file_path}.{time.time_ns()}.gz"
    with (
        open(file_path, "rb") as source,
        open(
            compressed_path, "wb", opener=secure_file_opener
        ) as compressed_stream,
        gzip.GzipFile(fileobj=compressed_stream, mode="wb") as archive,
    ):
        shutil.copyfileobj(source, archive)
    os.remove(file_path)


def init_console_logger(level=logging.INFO, log_format=None, datefmt=None):
    """Configure a sanitized console handler with basicConfig semantics."""
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(SecureFormatter(log_format, datefmt))
        root_logger.addHandler(console_handler)
    root_logger.setLevel(level)
