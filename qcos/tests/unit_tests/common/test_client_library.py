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

import os
import tempfile

from qcos.common.client_library import ClientLibrary

library = ClientLibrary()


class TestClientLibrary:
    def test_read_file(self):
        file_path = None
        with tempfile.NamedTemporaryFile(
            mode="w+", newline="", suffix=".txt", delete=False
        ) as temp_file:
            temp_file.write("")
            file_path = temp_file.name

        content = library.read_file(file_path)
        assert content is not None

        pattern = {"1": "1"}
        content = library.read_file(file_path, replace_pattern=pattern)
        assert content is not None

        formats = {"2": "2"}
        content = library.read_file(file_path, customer_format=formats)
        assert content is not None
        os.unlink(file_path)

    def test_read_csv_file(self):
        file_path = None
        with tempfile.NamedTemporaryFile(
            mode="w+", newline="", suffix=".csv", delete=False
        ) as temp_file:
            temp_file.write("")
            file_path = temp_file.name

        assert library.read_csv_file(file_path) is not None
        os.unlink(file_path)

    def test_validate_values_enum(self):
        value = ["6", "7", "8", "9"]
        success, _ = library.validate_values_enum("9", "Tzeentch", value)
        assert success is True

        success, _ = library.validate_values_enum(
            None, "Tzeentch", value, allow_none=True
        )
        assert success is True

        success, _ = library.validate_values_enum("13", "Tzeentch", value)
        assert success is False

    def test_validate_values_uuid(self):
        success, _ = library.validate_values_uuid("9", "Tzeentch")
        assert success is False

    def test_validate_values_range(self):
        success, _ = library.validate_values_range(9, "Tzeentch")
        assert success is True

        success, _ = library.validate_values_range(
            9, "Tzeentch", min_value=13, max_value=6
        )
        assert success is False

    def test_validate_values_length(self):
        success, _ = library.validate_values_length(
            None, "Tzeentch", allow_none=True
        )
        assert success is True

        success, _ = library.validate_values_length(
            "99", "Tzeentch", min_value=13, max_value=1
        )
        assert success is False

        success, _ = library.validate_values_length("9", "Tzeentch")
        assert success is True

    def test_validate_schema(self):
        success, _ = library.validate_schema("9", "Tzeentch")
        assert success is False

        success, _ = library.validate_schema(None, "Tzeentch", allow_none=True)
        assert success is True

        success, _ = library.validate_schema("9", None)
        assert success is False
