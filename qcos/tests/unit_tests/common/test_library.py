#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
import tempfile
import uuid
from datetime import datetime
from unittest.mock import patch, Mock

from qcos.common.library import Library
from qcos.tests.unit_tests.task_manager.constant_for_test import (
    ConstantForTest,
)

library = Library()
fernet_key = "abcBn4Ol_3bJ7t0IW7TmPCCZurqfw_QRa810U43o_m0="


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

    def test_create_file(self):
        test_file = "test1.txt"
        success, _ = library.create_file(test_file, "123", mode=0o644)
        assert success is True
        library.rm_file(test_file)

    def test_create_pid_file(self):
        test_file = "test.pid"
        library.create_pid_file(test_file)
        assert os.path.isfile(test_file)
        library.rm_file(test_file)

    def test_kill_pid(self):
        test_file = "test.pid"
        library.create_file(test_file, "99999999")
        assert library.kill_pid("test.pid") is None
        assert library.kill_pid("test.pid1") is None
        library.rm_file(test_file)

    def test_find_dirs(self):
        dirs = library.find_dirs(base_dir="tests", recursive=True)
        assert not dirs

    def test_find_files(self):
        assert library.find_files("./") is not None
        assert not (
            library.find_files(
                "./", pattern="test*", recursive=True, exclusives="test*"
            )
        )
        assert not library.find_files("no_such_dir")
        assert (
            library.find_files("./", pattern="test*", recursive=True)
            is not None
        )

    def test_mkdir_rmdir(self):
        dir_name = "test-dir"
        success = library.mkdir(dir_name)
        assert success is True
        success, _ = library.rmdir(dir_name)
        assert success is True

    def test_rm_file(self):
        success, _ = library.rm_file("test.txt")
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
        library.rm_file(file_path)

    def test_read_toml_file(self):
        success, _, _ = library.read_toml_file("test-toml.toml")
        assert success is False

    def test_write_to_toml(self):
        data = {"a": "b", "c": "d"}
        test_file = "test.toml"
        success, _ = library.create_toml(test_file, data)
        assert success is True
        library.rm_file(test_file)

        success, _ = library.create_toml("", data)
        assert success is False

    def test_get_current_datetime(self):
        times = library.get_current_datetime()
        assert isinstance(times, datetime)

    def test_validate_values_enum(self):
        value = ["6", "7", "8", "9"]
        success, _ = library.validate_values_enum("9", "test1", value)
        assert success is True

        success, _ = library.validate_values_enum(
            None, "test1", value, allow_none=True
        )
        assert success is True

        success, _ = library.validate_values_enum("13", "test1", value)
        assert success is False

    def test_validate_values_uuid(self):
        uuid_1 = ConstantForTest.job_id
        success, _ = library.validate_values_uuid(uuid_1, "test1")
        assert success is True

        success, _ = library.validate_values_uuid("9", "test2")
        assert success is False

    def test_validate_values_range(self):
        success, _ = library.validate_values_range(9, "test1")
        assert success is True

        success, _ = library.validate_values_range(
            9, "test1", min_value=13, max_value=6
        )
        assert success is False

    def test_validate_values_length(self):
        success, _ = library.validate_values_length(
            None, "test1", allow_none=True
        )
        assert success is True

        success, _ = library.validate_values_length(
            "99", "test1", min_value=13, max_value=1
        )
        assert success is False

        success, _ = library.validate_values_length("9", "test1")
        assert success is True

    def test_validate_values_list(self):
        value = "987613"
        success, _ = library.validate_values_list(value, "test1", "chaos")
        assert success is False

        value = [9, 8, 7, 6, 13]
        success, _ = library.validate_values_list(value, "test1", str)
        assert success is False

        value = [False, False]
        success, _ = library.validate_values_list(value, "test1", bool)
        assert success is False

        success, _ = library.validate_values_list(
            value, "test1", bool, allow_none=True
        )
        assert success is True

    def test_validate_schema(self):
        success, _ = library.validate_schema("9", "test1")
        assert success is False

        success, _ = library.validate_schema(None, "test1", allow_none=True)
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
        success = library.is_valid_url("127.0.0.1", "test1")
        assert success is False

    def test_get_zip_content(self):
        success, _, _ = library.get_zip_content("pid_file.zip")
        assert success is False

    def test_get_nested_dict_value(self):
        dictionary = {"a": "b", "c": "d"}
        keys = {"1": "1", "2": "2"}
        default = library.get_nested_dict_value(dictionary, keys)
        assert default is None

    @patch("requests.post")
    def test_run_callbacks(self, mock_post):
        data = {
            "job_id": "job_id",
            "job_status": "job_status",
            "backend": "backend",
            "results": "results",
        }
        callbacks = [
            {
                "method": "post",
                "headers": {},
                "retries": 3,
                "timeout": 10,
                "url": "127.0.0.1",
            },
        ]
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response
        success, _ = library.run_callbacks(data, callbacks)
        assert success is True

    @patch("requests.post")
    def test_async_run_callbacks(self, mock_post):
        data = {
            "job_id": "job_id",
            "job_status": "job_status",
            "backend": "backend",
            "results": "results",
        }
        callbacks = [
            {
                "method": "post",
                "headers": {},
                "retries": 3,
                "timeout": 10,
                "url": "127.0.0.1",
            },
        ]
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response
        success, _ = asyncio.run(library.async_run_callbacks(data, callbacks))
        assert success is False

    def test_get_sorted_keys(self):
        sort_obj = {
            "Tzeentch": datetime(2999, 12, 31, 23, 59, 59, 0),
            "N": "Nurgle",
            "K": "Khorne",
            "S": "Slaanesh",
        }
        library.get_sorted_keys(sort_obj, ["-Tzeentch", "Tzeentch"])
        library.get_sorted_keys(sort_obj, "Tzeentch")

        sort_obj = ["Tzeentch", "Nurgle", "Khorne", "Slaanesh"]
        key_tuple = library.get_sorted_keys(sort_obj, "Tzeentch")
        assert key_tuple is not None

    def test_generate_binary_combinations(self):
        return_dict = library.generate_binary_combinations(9, 10)
        assert return_dict is not None
        return_dict = library.generate_binary_combinations(0, 10)
        assert return_dict == {}

    def test_encrypt_text(self):
        success, err_msg, encrypted_text = library.encrypt_text(
            "test", encryption_prefix="++", fernet_key=fernet_key
        )
        print(encrypted_text)
        assert success is True
        assert encrypted_text.startswith("++")

    def test_encrypt_text_wrong_fernet_key(self):
        success, err_msg, encrypted_text = library.encrypt_text(
            "test", encryption_prefix="++", fernet_key="abc"
        )
        assert success is False

    def test_decrypt_text(self):
        plain_text = "test"
        encrypted_text = (
            "++gAAAAABo9uFW1Y929YObWvGy84O5KL8orwhXKirq"
            "87L9Fh2SyxFnl-xWyXh1TXReuofLyevojRPeoWAWkl"
            "27e8oOAZiGeoM-Qg=="
        )
        success, err_msg, decrypted_text = library.decrypt_text(
            encrypted_text, encryption_prefix="++", fernet_key=fernet_key
        )
        assert success is True
        assert decrypted_text == plain_text

    def test_decrypt_text_wrong_encrypted_text(self):
        encrypted_text = (
            "gAAAAABo9uFW1Y929YObWvGy84O5KL8orwhXKirq"
            "87L9Fh2SyxFnl-xWyXh1TXReuofLyevojRPeoWAWkl"
            "27e8oOAZiGeoM-Qg=="
        )
        success, err_msg, decrypted_text = library.decrypt_text(
            encrypted_text, encryption_prefix="++", fernet_key=fernet_key
        )
        assert success is False

    def test_decrypt_text_wrong_fernet_key(self):
        encrypted_text = (
            "++gAAAAABo9uFW1Y929YObWvGy84O5KL8orwhXKirq"
            "87L9Fh2SyxFnl-xWyXh1TXReuofLyevojRPeoWAWkl"
            "27e8oOAZiGeoM-Qg=="
        )
        wrong_fernet_key = "abc"
        success, err_msg, decrypted_text = library.decrypt_text(
            encrypted_text, encryption_prefix="++", fernet_key=wrong_fernet_key
        )
        assert success is False

    def test_mask_password(self):
        password_replace = "*" * 8
        configs = {
            "password": "a123456",
            "my_password": "b123456",
            "my_password_1": "c123456",
            "test": "d123456",
        }
        expected_configs = {
            "password": password_replace,
            "my_password": password_replace,
            "my_password_1": password_replace,
            "test": "d123456",
        }
        actual_configs = library.mask_password(
            configs, password_replace=password_replace
        )
        assert actual_configs == expected_configs

    def test_create_uuid(self):
        new_uuid_1 = library.create_uuid()
        assert isinstance(new_uuid_1, uuid.UUID)
        new_uuid_2 = library.create_uuid(prefix=[0xF0])
        assert isinstance(new_uuid_2, uuid.UUID)
        new_uuid_bytes_2 = new_uuid_2.bytes
        assert new_uuid_bytes_2[0] == 0xF0

    def test_encrypt_virtual_instance_id(self):
        uuid_str = "5eb2cc2b195242aeb2d60cf4907a606b"
        success, _, _ = library.encrypt_virtual_instance_id("dummy", uuid_str)
        assert success is True

        success, _, _ = library.encrypt_virtual_instance_id(
            "dummy", uuid_str, encode=True
        )
        assert success is True

    def test_decrypt_virtual_instance_id(self):
        instance_id = "dummy-5eb2cc2b195242aeb2d60cf4907a606b-43c5"
        success, _, _, _ = library.decrypt_virtual_instance_id(instance_id)
        assert success is False

        instance_id = (
            "ZHVtbXktNWViMmNjMmIxOTUyNDJhZWIyZDYwY2Y0OTA3YTYwNmItNDNjNQ=="
        )
        success, _, _, _ = library.decrypt_virtual_instance_id(
            instance_id, encode=True
        )
        assert success is False
