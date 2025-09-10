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

import asyncio
import os
from datetime import datetime

from qcos.common.library import Library

library = Library()


class TestLibrary:
    def test_get_brief_description(self):
        description = "1 2 3 4 5"
        brief = library.get_brief_description(description)
        assert brief == description

    def test_update_dict(self):
        new_kvs = {"a": "b", "c": "d"}
        dictionary = {"a": "c"}
        dictionary = library.update_dict(dictionary, new_kvs)
        assert dictionary == {"a": "b"}

    def test_create_pid_file(self):
        library.create_pid_file("test-pid_file.txt")
        library.create_pid_file("test.txt")
        library.create_pid_file("")

    def test_find_dirs(self):
        library.find_dirs(base_dir="tests", recursive=True)

    def test_find_files(self):
        library.find_files("tests", recursive=True, exclusives="_init_")
        library.find_files("tests")
        library.find_files("no_such_dir")

    def test_mkdir(self):
        assert library.mkdir("test-file") is not None

    def test_rm_file(self):
        assert library.rm_file("test.txt") is True
        library.rm_file("no_such_dir")

    def test_import_classes(self):
        library.import_classes("logger")

    def test_str_match(self):
        assert library.str_match("abc", "abc", ignore_case=True) is True
        assert library.str_match("abc", "abc") is True

    def test_read_file(self):
        content = library.read_file("test-pid_file.txt")
        assert content is not None

        pattern = {"1": "1"}
        content = library.read_file("test-pid_file.txt",
                                    replace_pattern=pattern)
        assert content is not None

        formats = {"2": "2"}
        content = library.read_file("test-pid_file.txt",
                                    customer_format=formats)
        assert content is not None

    def test_read_csv_file(self):
        library.read_csv_file("test-pid_file.txt")

    def test_read_toml_file(self):
        library.read_toml_file("test-pid_file.toml")
        library.read_toml_file("")

    def test_write_to_toml(self):
        data = {"a": "b", "c": "d"}
        library.write_to_toml(data, "test-pid_file.toml")
        library.write_to_toml(data, "")

    def test_write_to_file(self):
        data = {"a": "b", "c": "d"}
        library.write_to_file(data, "test-pid_file.txt")

    def test_get_current_datetime(self):
        library.get_current_datetime()

    def test_validate_values_enum(self):
        value = ["6", "7", "8", "9"]
        library.validate_values_enum("9", "Tzeentch", value)
        library.validate_values_enum(None, "Tzeentch",
                                     value, allow_none=True)
        library.validate_values_enum("13", "Tzeentch", value)

    def test_validate_values_uuid(self):
        library.validate_values_uuid("9", "Tzeentch")

    def test_validate_values_range(self):
        library.validate_values_range(9, "Tzeentch")
        library.validate_values_range(9, "Tzeentch",
                                      min_value=13, max_value=6)

    def test_validate_values_length(self):
        library.validate_values_length(None, "Tzeentch", allow_none=True)
        library.validate_values_length(
            "99", "Tzeentch", min_value=13, max_value=1)
        library.validate_values_length("9", "Tzeentch")

    def test_validate_values_list(self):
        value = "987613"
        library.validate_values_list(value, "Tzeentch", "chaos")
        value = [9, 8, 7, 6, 13]
        library.validate_values_list(value, "Tzeentch", str)
        value = [False, False]
        library.validate_values_list(value, "Tzeentch", bool)
        library.validate_values_list(value, "Tzeentch",
                                     bool, allow_none=True)

    def test_validate_schema(self):
        library.validate_schema("9", "Tzeentch")
        library.validate_schema(None, "Tzeentch", allow_none=True)
        library.validate_schema("9", None)

    def test_is_valid_url(self):
        library.is_valid_url("https://example.com", "Tzeentch")

    def test_get_zip_content(self):
        library.get_zip_content("pid_file.zip")

    def test_get_nested_dict_value(self):
        dictionary = {"a": "b", "c": "d"}
        keys = {"1": "1", "2": "2"}
        library.get_nested_dict_value(dictionary, keys)

    def test_run_callbacks(self):
        data = ["Tzeentch", "Nurgle", "Khorne", "Slaanesh"]
        callbacks = [{"T": "Tzeentch", "N": "Nurgle",
                      "K": "Khorne", "S": "Slaanesh"},
                     {"E": "Emperor"},]
        library.run_callbacks(data, callbacks)

    def test_async_run_callbacks(self):
        data = ["Tzeentch", "Nurgle", "Khorne", "Slaanesh"]
        callbacks = [{"T": "Tzeentch", "N": "Nurgle",
                      "K": "Khorne", "S": "Slaanesh"},
                     {"E": "Emperor"},]
        asyncio.run(library.async_run_callbacks(data, callbacks))

    def test_get_sorted_keys(self):
        sort_obj = {"Tzeentch": datetime(2999, 12, 31, 23, 59, 59, 0),
                    "N": "Nurgle", "K": "Khorne", "S": "Slaanesh"}
        library.get_sorted_keys(sort_obj, ["-Tzeentch", "Tzeentch"])
        library.get_sorted_keys(sort_obj, "Tzeentch")

        sort_obj = ["Tzeentch", "Nurgle", "Khorne", "Slaanesh"]
        library.get_sorted_keys(sort_obj, "Tzeentch")

    def test_generate_binary_combinations(self):
        library.generate_binary_combinations(9, 10)
        library.generate_binary_combinations(0, 10)

        os.remove("test-pid_file.toml")
        os.remove("test-pid_file.txt")
        os.rmdir("test-file")
