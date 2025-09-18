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
from unittest.mock import patch, Mock

from qcos.common.library import Library

library = Library()


class TestLibrary:
    def test_get_brief_description(self):
        description = "description"
        brief = library.get_brief_description(description)
        assert brief == description

    def test_update_dict(self):
        new_kvs = {"key1": "new_value1", "key2": "value2"}
        dictionary = {"key1": "value1"}
        dictionary = library.update_dict(dictionary, new_kvs)
        assert dictionary == {"key1": "new_value1"}

    def test_remove_duplicates(self):
        lst = ["value1", "value2"]
        new_list = library.remove_duplicates(lst)
        assert new_list == lst

    def test_create_pid_file(self):
        library.create_pid_file("test-pid_file.txt")
        library.create_pid_file("test.txt")
        library.create_pid_file("")

    def test_find_dirs(self):
        dirs = library.find_dirs(base_dir="tests", recursive=True)
        assert not dirs

    def test_find_files(self):
        library.find_files("tests", recursive=True, exclusives="_init_")
        library.find_files("tests")
        library.find_files("no_such_dir")

    def test_mkdir(self):
        assert library.mkdir("test-file") is not None

    def test_rm_file(self):
        success = library.rm_file("test.txt")
        library.rm_file("no_such_dir")
        assert success is True

    def test_import_classes(self):
        classes = library.import_classes("logger")
        assert not classes

    def test_str_match(self):
        success = library.str_match("abc", "abc", ignore_case=True)
        assert success is True

        success = library.str_match("abc", "abc")
        assert success is True

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
        assert library.read_csv_file("test-pid_file.txt") is not None

    def test_read_toml_file(self):
        success, _, _ = library.read_toml_file("test-pid_file.toml")
        assert success is False
        library.read_toml_file("")

    def test_write_to_toml(self):
        data = {"a": "b", "c": "d"}
        success, _ = library.write_to_toml(data, "test-pid_file.toml")
        assert success is True

        success, _ = library.write_to_toml(data, "")
        assert success is False

    def test_write_to_file(self):
        data = {"a": "b", "c": "d"}
        success, _ = library.write_to_file(data, "test-pid_file.txt")
        assert success is False

    def test_get_current_datetime(self):
        times = library.get_current_datetime()
        assert isinstance(times, datetime)

    def test_validate_values_enum(self):
        value = ["6", "7", "8", "9"]
        success, _ = library.validate_values_enum("9", "Tzeentch", value)
        assert success is True

        success, _ = library.validate_values_enum(None, "Tzeentch",
                                                  value, allow_none=True)
        assert success is True

        success, _ = library.validate_values_enum("13", "Tzeentch", value)
        assert success is False

    def test_validate_values_uuid(self):
        success, _ = library.validate_values_uuid("9", "Tzeentch")
        assert success is False

    def test_validate_values_range(self):
        success, _ = library.validate_values_range(9, "Tzeentch")
        assert success is True

        success, _ = library.validate_values_range(9, "Tzeentch",
                                                   min_value=13, max_value=6)
        assert success is False

    def test_validate_values_length(self):
        success, _ = library.validate_values_length(None, "Tzeentch",
                                                    allow_none=True)
        assert success is True

        success, _ = library.validate_values_length("99", "Tzeentch",
                                                    min_value=13, max_value=1)
        assert success is False

        success, _ = library.validate_values_length("9", "Tzeentch")
        assert success is True

    def test_validate_values_list(self):
        value = "987613"
        success, _ = library.validate_values_list(value, "Tzeentch", "chaos")
        assert success is False

        value = [9, 8, 7, 6, 13]
        success, _ = library.validate_values_list(value, "Tzeentch", str)
        assert success is False

        value = [False, False]
        success, _ = library.validate_values_list(value, "Tzeentch", bool)
        assert success is False

        success, _ = library.validate_values_list(value, "Tzeentch",
                                                  bool, allow_none=True)
        assert success is True

    def test_validate_schema(self):
        success, _ = library.validate_schema("9", "Tzeentch")
        assert success is False

        success, _ = library.validate_schema(None, "Tzeentch",
                                             allow_none=True)
        assert success is True

        success, _ = library.validate_schema("9", None)
        assert success is False

    def test_check_qubo_matrixs_bit_width(self):
        qubo_matrixs = [[[-480, 508, -48],
                         [508, -508, -48],
                         [-48, -48, 60]]]
        library.check_qubo_matrixs_bit_width(qubo_matrixs)
        qubo_matrixs = [[[-512, 520, -48],
                         [520, -520, -48],
                         [-48, -48, 40]],
                        [[-488, 516, -48],
                         [516, -516, -48],
                         [-48, -48, 60]]]
        library.check_qubo_matrixs_bit_width(qubo_matrixs)

    def test_is_valid_url(self):
        success = library.is_valid_url("127.0.0.1", "Tzeentch")
        assert success is False

    def test_get_zip_content(self):
        success, _, _ = library.get_zip_content("pid_file.zip")
        assert success is False

    def test_get_nested_dict_value(self):
        dictionary = {"a": "b", "c": "d"}
        keys = {"1": "1", "2": "2"}
        default = library.get_nested_dict_value(dictionary, keys)
        assert default is None

    @patch('requests.post')
    def test_run_callbacks(self, mock_post):
        data = {
            "job_id": "job_id",
            "job_status": "job_status",
            "backend": "backend",
            "results": "results"
        }
        callbacks = [{"method": "post", "headers": {},
                      "retries": 3, "timeout": 10,
                      "url": "127.0.0.1"},]
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response
        success, _ = library.run_callbacks(data, callbacks)
        assert success is True

    @patch('requests.post')
    def test_async_run_callbacks(self, mock_post):
        data = {
            "job_id": "job_id",
            "job_status": "job_status",
            "backend": "backend",
            "results": "results"
        }
        callbacks = [{"method": "post", "headers": {},
                      "retries": 3, "timeout": 10,
                      "url": "127.0.0.1"},]
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response
        success, _ = asyncio.run(library.async_run_callbacks(data, callbacks))
        assert success is False

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
