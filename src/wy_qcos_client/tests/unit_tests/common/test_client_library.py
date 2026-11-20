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

"""Unit tests for ClientLibrary file and validation helpers."""

import os
from tempfile import TemporaryDirectory

from wy_qcos_client.common.client_library import ClientLibrary

library = ClientLibrary()


class TestClientLibrary:
    """Test ClientLibrary file reading and validation helpers."""

    def test_read_file(self):
        """Test read_file method."""
        with TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "data.txt")
            with open(file_path, "w", encoding="utf-8") as temp_file:
                temp_file.write("")

            content = library.read_file(file_path)
            assert content is not None

            pattern = {"1": "1"}
            content = library.read_file(file_path, replace_pattern=pattern)
            assert content is not None

            formats = {"2": "2"}
            content = library.read_file(file_path, customer_format=formats)
            assert content is not None

    def test_read_csv_file(self):
        """Test read_csv_file method."""
        with TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "data.csv")
            with open(file_path, "w", encoding="utf-8") as temp_file:
                temp_file.write("")

            assert library.read_csv_file(file_path) is not None

    def test_validate_values_enum(self):
        """Test validate_values_enum method."""
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
        """Test validate_values_uuid method."""
        success, _ = library.validate_values_uuid("9", "Tzeentch")
        assert success is False

    def test_validate_values_range(self):
        """Test validate_values_range method."""
        success, _ = library.validate_values_range(9, "Tzeentch")
        assert success is True

        success, _ = library.validate_values_range(
            9, "Tzeentch", min_value=13, max_value=6
        )
        assert success is False

    def test_validate_values_length(self):
        """Test validate_values_length method."""
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
        """Test validate_schema method."""
        success, _ = library.validate_schema("9", "Tzeentch")
        assert success is False

        success, _ = library.validate_schema(None, "Tzeentch", allow_none=True)
        assert success is True

        success, _ = library.validate_schema("9", None)
        assert success is False

    def test_validate_name_valid(self):
        """Test validate_name with valid names."""
        success, _ = library.validate_name("my-device")
        assert success is True
        success, _ = library.validate_name("device_001")
        assert success is True
        success, _ = library.validate_name("a")
        assert success is True
        success, _ = library.validate_name("a" * 64)
        assert success is True
        success, _ = library.validate_name("ALL_CAPS-123")
        assert success is True

    def test_validate_name_none(self):
        """Test validate_name with None (allow_none=True)."""
        success, _ = library.validate_name(None)
        assert success is True

    def test_validate_name_empty(self):
        """Test validate_name with empty string."""
        success, _ = library.validate_name("")
        assert success is False

    def test_validate_name_too_long(self):
        """Test validate_name with name longer than 64 chars."""
        success, _ = library.validate_name("a" * 65)
        assert success is False

    def test_validate_name_invalid_chars(self):
        """Test validate_name with invalid characters."""
        success, _ = library.validate_name("device name")
        assert success is False
        success, _ = library.validate_name("device@name")
        assert success is False
        success, _ = library.validate_name("device.name")
        assert success is False
        success, _ = library.validate_name("中文设备名")
        assert success is False
