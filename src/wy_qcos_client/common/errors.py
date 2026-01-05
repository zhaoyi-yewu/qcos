#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
# Don't import any libraries


class BaseException(Exception):
    """Base exception."""

    def __init__(self, message):
        super().__init__(message)
        self.message = str(message)

    def get_error_code(self):
        """Get error code.

        Returns:
            error code
        """
        return self.error_code

    def get_err_msgs(self):
        return f"[{self.module_name}] {self.err_type}: {self.message}"


class GenericException(BaseException):
    """Generic exception."""

    module_name = "Generic"
    error_code = -10
    err_type = "Error"


class InvalidArguments(BaseException):
    """Invalid arguments."""

    module_name = "Generic"
    error_code = -11
    err_type = "Invalid arguments"
