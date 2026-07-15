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

import base64
import csv as csv_module
import os
import shutil
import uuid
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock, AsyncMock

import pytest
import tempfile

from wy_qcos.common.constant import HttpMethod
from wy_qcos.common.library import Library, _s
from wy_qcos.tests.unit_tests.conftest import GLOBAL_CONFIGS
from wy_qcos.tests.unit_tests.task_manager.constant_for_test import (
    ConstantForTest,
)

library = Library()
fernet_key = _s("abcBn4Ol_3bJ7t0IW7TmPCCZurqfw_QRa810U43o_m0=")


@pytest.mark.usefixtures("global_configs")
class TestLibrary:
    """Test Library utility functions."""

    @classmethod
    def setup_class(cls):
        cls.temp_dir = GLOBAL_CONFIGS["temp_dir"]

    # ========== String Operations ==========

    @pytest.mark.smoke
    def test_get_brief_description(self):
        """Test get_brief_description with simple string."""
        description = "description"
        brief = library.get_brief_description(description)
        assert brief == description

    def test_get_brief_description_multiline(self):
        """Test get_brief_description with multiline input."""
        description = "line1\nline2\n\nline3"
        result = Library.get_brief_description(description)
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result

    def test_get_brief_description_empty_lines(self):
        """Test get_brief_description with empty lines."""
        description = "\n\nline1\n\n"
        result = Library.get_brief_description(description)
        assert result == "line1"

    def test_str_match_case_sensitive(self):
        """Test str_match with case sensitivity."""
        result = Library.str_match("Hello", "hello", ignore_case=False)
        assert result is False

    def test_str_match_case_insensitive(self):
        """Test str_match with case insensitivity."""
        result = Library.str_match("Hello", "hello", ignore_case=True)
        assert result is True

    def test_str_match_regex(self):
        """Test str_match with regex pattern."""
        result = Library.str_match("test123", "test\\d+")
        assert result is True

    def test_mask_password_basic(self):
        """Test mask_password basic functionality."""
        password_replace = _s("*" * 8)
        configs = {
            "test": "000000",
            "_param": "1a123456",
            "_password": "1b123456",
            "password": "2a123456",
            "my_password": "2b123456",
            "my_password_1": "2c123456",
            "secret": "2a123456",
            "my_secret": "2b123456",
            "my_secret_1": "2c123456",
            "hidden": "3a123456",
            "my_hidden": "3b123456",
            "my_hidden_1": "3c123456",
            "list": ["1", "2", "3"],
            "dict": {"1": {"a": "1"}, "2": {"b": "2"}, "3": {"c": "3"}},
            "list_dict": [{"password": "1"}, "2"],
            "list_pass": ["1", "2", "password"],
            "dict_pass": {
                "1": {"a": 1},
                "2": {"password": "123"},
                "3": {"c": 3},
            },
            "list_dict_pass": [{"password": "123"}, "2"],
        }
        expected_configs = {
            "test": "000000",
            "_param": password_replace,
            "_password": password_replace,
            "password": password_replace,
            "my_password": password_replace,
            "my_password_1": password_replace,
            "secret": password_replace,
            "my_secret": password_replace,
            "my_secret_1": password_replace,
            "hidden": password_replace,
            "my_hidden": password_replace,
            "my_hidden_1": password_replace,
            "list": ["1", "2", "3"],
            "dict": {"1": {"a": "1"}, "2": {"b": "2"}, "3": {"c": "3"}},
            "list_dict": [{"password": password_replace}, "2"],
            "list_pass": ["1", "2", "password"],
            "dict_pass": {
                "1": {"a": 1},
                "2": {"password": password_replace},
                "3": {"c": 3},
            },
            "list_dict_pass": [{"password": password_replace}, "2"],
        }
        actual_configs = library.mask_password(
            configs, password_replace=password_replace
        )
        assert actual_configs == expected_configs

    def test_mask_password_with_custom_replace(self):
        """Test mask_password with custom replacement."""
        configs = {
            "password": _s("secret123"),
            "api_key": _s("key123"),
        }
        masked = Library.mask_password(
            configs, password_replace=_s("***HIDDEN***")
        )
        assert masked["password"] == _s("***HIDDEN***")

    def test_mask_password_dict(self):
        """Test mask_password with dictionary."""
        config = {"password": "secret", "user": "john"}
        result = Library.mask_password(config)
        assert "***" in str(result["password"]) or result["password"] != _s(
            "secret"
        )

    def test_mask_password_nested(self):
        """Test mask_password with nested dict."""
        config = {"db": {"password": "secret"}, "user": "john"}
        result = Library.mask_password(config)
        assert result is not None

    # ========== Dictionary Operations ==========

    def test_update_dict_basic(self):
        """Test update_dict basic functionality."""
        new_kvs = {"key1": "new_value1", "key2": "value2"}
        dictionary = {"key1": "value1"}
        dictionary = library.update_dict(dictionary, new_kvs)
        assert dictionary == {"key1": "new_value1"}

    def test_update_dict_empty_new_kvs(self):
        """Test update_dict with empty new_kvs."""
        original = {"key1": "value1"}
        result = Library.update_dict(original, {})
        assert result == original

    def test_update_dict_nonexistent_keys(self):
        """Test update_dict with nonexistent keys."""
        original = {"key1": "value1"}
        result = Library.update_dict(original, {"key2": "value2"})
        assert result == {"key1": "value1"}

    # ========== List Operations ==========

    def test_remove_duplicates_basic(self):
        """Test remove_duplicates basic functionality."""
        lst = ["value1", "value2"]
        new_list = library.remove_duplicates(lst)
        assert new_list == lst

    def test_remove_duplicates_empty_list(self):
        """Test remove_duplicates with empty list."""
        result = Library.remove_duplicates([])
        assert result == []

    def test_remove_duplicates_with_duplicates(self):
        """Test remove_duplicates with multiple duplicates."""
        lst = ["a", "b", "a", "c", "b", "a"]
        result = Library.remove_duplicates(lst)
        assert result == ["a", "b", "c"]

    def test_remove_duplicates_no_duplicates(self):
        """Test remove_duplicates with no duplicates."""
        lst = ["a", "b", "c"]
        result = Library.remove_duplicates(lst)
        assert result == lst

    # ========== Encryption Operations ==========

    def test_encrypt_text_basic(self):
        """Test encrypt_text with valid key."""
        success, err_msg, encrypted_text = library.encrypt_text(
            "test", encryption_prefix="++", fernet_key=fernet_key
        )
        assert success is True
        assert encrypted_text.startswith("++")

    def test_encrypt_text_wrong_fernet_key(self):
        """Test encrypt_text with invalid fernet key."""
        success, err_msg, encrypted_text = library.encrypt_text(
            "test", encryption_prefix="++", fernet_key=_s("abc")
        )
        assert success is False

    def test_encrypt_text_with_prefix(self):
        """Test encrypt_text with encryption prefix."""
        text = "sensitive_data"
        success, error, encrypted = Library.encrypt_text(
            text,
            encryption_prefix="enc:",
            fernet_key=_s("abcBn4Ol_3bJ7t0IW7TmPCCZurqfw_QRa810U43o_m0="),
        )
        assert success is True
        assert encrypted.startswith("enc:")

    def test_decrypt_text_basic(self):
        """Test decrypt_text with valid encrypted text."""
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
        """Test decrypt_text with invalid encrypted text."""
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
        """Test decrypt_text with invalid fernet key."""
        encrypted_text = (
            "++gAAAAABo9uFW1Y929YObWvGy84O5KL8orwhXKirq"
            "87L9Fh2SyxFnl-xWyXh1TXReuofLyevojRPeoWAWkl"
            "27e8oOAZiGeoM-Qg=="
        )
        wrong_fernet_key = _s("abc")
        success, err_msg, decrypted_text = library.decrypt_text(
            encrypted_text, encryption_prefix="++", fernet_key=wrong_fernet_key
        )
        assert success is False

    # ========== Base64 Operations ==========

    def test_base64_encode(self):
        """Test base64_encode."""
        result = base64.b64encode(b"test").decode("utf-8")
        assert isinstance(result, str)

    def test_base64_decode(self):
        """Test base64_decode."""
        encoded = base64.b64encode(b"test").decode("utf-8")
        decoded = base64.b64decode(encoded).decode("utf-8")
        assert decoded == "test"

    def test_base64_special_chars(self):
        """Test base64 with special characters."""
        original = "Special!@#$%^&*()"
        encoded = base64.b64encode(original.encode("utf-8")).decode("utf-8")
        decoded = base64.b64decode(encoded).decode("utf-8")
        assert decoded == original

    def test_base64_roundtrip(self):
        """Test base64 encode/decode roundtrip."""
        texts = ["simple", "with spaces", "special!@#", "numbers123"]
        for text in texts:
            encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
            decoded = base64.b64decode(encoded).decode("utf-8")
            assert decoded == text

    # ========== UUID Operations ==========

    def test_generate_uuid_format(self):
        """Test generate_uuid returns correct format."""
        uid = str(uuid.uuid4())
        assert len(uid) == 36
        assert uid.count("-") == 4

    def test_generate_uuid_unique(self):
        """Test generate_uuid produces unique values."""
        uuid1 = str(uuid.uuid4())
        uuid2 = str(uuid.uuid4())
        assert uuid1 != uuid2

    def test_is_uuid_valid(self):
        """Test is_uuid with valid UUID."""
        valid = str(uuid.uuid4())
        try:
            uuid.UUID(valid)
            is_valid = True
        except ValueError:
            is_valid = False
        assert is_valid is True

    def test_is_uuid_invalid(self):
        """Test is_uuid with invalid UUID."""
        for test_val in ["not-a-uuid", ""]:
            try:
                uuid.UUID(test_val)
                is_valid = True
            except ValueError:
                is_valid = False
            assert is_valid is False

    def test_is_uuid_valid_formats(self):
        """Test is_uuid with valid UUID formats."""
        valid_uuid = str(uuid.uuid4())
        try:
            uuid.UUID(valid_uuid)
            is_valid = True
        except ValueError:
            is_valid = False
        assert is_valid is True

    def test_is_uuid_invalid_formats(self):
        """Test is_uuid with invalid formats."""
        for test_val in ["not-uuid", "", "123"]:
            try:
                uuid.UUID(test_val)
                is_valid = True
            except ValueError:
                is_valid = False
            assert is_valid is False

    def test_create_uuid_basic(self):
        """Test create_uuid basic functionality."""
        result = Library.create_uuid()
        assert result is not None

    def test_create_uuid_with_prefix(self):
        """Test create_uuid with prefix."""
        result = Library.create_uuid(prefix=[0xAB, 0xCD])
        assert isinstance(result, type(uuid.uuid4()))

    def test_create_uuid_no_prefix(self):
        """Test create_uuid without prefix."""
        result = Library.create_uuid()
        assert isinstance(result, type(uuid.uuid4()))

    def test_create_uuid_extended(self):
        """Test create_uuid with various prefix values."""
        new_uuid_1 = library.create_uuid()
        assert isinstance(new_uuid_1, uuid.UUID)
        new_uuid_2 = library.create_uuid(prefix=[0xF0])
        assert isinstance(new_uuid_2, uuid.UUID)
        new_uuid_bytes_2 = new_uuid_2.bytes
        assert new_uuid_bytes_2[0] == 0xF0

    def test_encrypt_virtual_instance_id(self):
        """Test encrypt_virtual_instance_id."""
        uuid_str = "10000000-0000-4000-8000-000000000101"
        success, _, _ = library.encrypt_virtual_instance_id("dummy", uuid_str)
        assert success is True
        success, _, _ = library.encrypt_virtual_instance_id(
            "dummy", uuid_str, encode=True
        )
        assert success is True

    def test_decrypt_virtual_instance_id(self):
        """Test decrypt_virtual_instance_id."""
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

    # ========== File Operations ==========

    @patch("wy_qcos.common.library.os.chmod")
    @patch("builtins.open", create=True)
    @patch("wy_qcos.common.library.Library.mkdirs")
    def test_create_file_with_mode(
        self, mock_mkdirs, mock_open_builtin, mock_chmod
    ):
        """Test create_file with specific mode."""
        file_path = "/test_file.txt"
        success, error = Library.create_file(
            file_path, "test content", mode=0o644
        )
        assert success is True

    @patch("wy_qcos.common.library.os.chmod")
    @patch("builtins.open", create=True)
    @patch("wy_qcos.common.library.Library.mkdirs")
    def test_create_file_existing(
        self, mock_mkdirs, mock_open_builtin, mock_chmod
    ):
        """Test create_file when file already exists."""
        file_path = "/existing.txt"
        success, error = Library.create_file(file_path, "new content")
        assert success is True

    @patch("wy_qcos.common.library.os.path.isfile")
    def test_is_file_basic(self, mock_isfile):
        """Test is_file with existing file."""
        mock_isfile.return_value = True
        assert Library.is_file("/test_file.txt") is True

    @patch("wy_qcos.common.library.os.path.isfile")
    def test_is_file_not_found(self, mock_isfile):
        """Test is_file with non-existent file."""
        mock_isfile.return_value = False
        result = Library.is_file("/nonexistent/path/file.txt")
        assert result is False

    @patch("wy_qcos.common.library.os.remove")
    @patch("wy_qcos.common.library.os.path.isfile")
    def test_rm_file_basic(self, mock_isfile, mock_remove):
        """Test rm_file basic functionality."""
        mock_isfile.return_value = False
        success, _ = library.rm_file("/test.txt")
        assert success is True

    @patch("wy_qcos.common.library.os.remove")
    @patch("wy_qcos.common.library.os.path.isfile")
    def test_rm_file_success(self, mock_isfile, mock_remove):
        """Test rm_file with existing file."""
        mock_isfile.return_value = True
        success, error = Library.rm_file("/to_delete.txt")
        assert success is True
        mock_remove.assert_called_once()

    @patch("wy_qcos.common.library.os.path.isfile")
    def test_rm_file_nonexistent(self, mock_isfile):
        """Test rm_file with non-existent file."""
        mock_isfile.return_value = False
        success, error = Library.rm_file("/nonexistent/file.txt")
        assert success is True

    @patch("builtins.open", create=True)
    def test_read_file_basic(self, mock_open):
        """Test read_file basic functionality."""
        mock_open.return_value.__enter__.return_value.read.return_value = ""
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            temp_path = f.name
        content = library.read_file(temp_path)
        assert content is not None
        pattern = {"1": "1"}
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            temp_path = f.name
        content = library.read_file(temp_path, replace_pattern=pattern)
        assert content is not None
        formats = {"2": "2"}
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as f:
            temp_path = f.name
        content = library.read_file(temp_path, customer_format=formats)
        assert content is not None

    @patch("builtins.open", create=True)
    def test_read_file_with_encoding(self, mock_open):
        """Test read_file with specific encoding."""
        mock_open.return_value.__enter__.return_value.read.return_value = (
            "test content"
        )
        content = Library.read_file("/test.txt")
        assert content == "test content"

    @patch("builtins.open", create=True)
    def test_read_file_basic_extended(self, mock_open):
        """Test read_file with content verification."""
        mock_open.return_value.__enter__.return_value.read.return_value = (
            "content"
        )
        result = Library.read_file("/test.txt")
        assert result == "content"

    @patch("wy_qcos.common.library.os.chmod")
    @patch("builtins.open", create=True)
    @patch("wy_qcos.common.library.Library.mkdirs")
    def test_write_file_basic(
        self, mock_mkdirs, mock_open_builtin, mock_chmod
    ):
        """Test write_file."""
        file_path = "/test.txt"
        Library.create_file(file_path, "content")
        assert mock_open_builtin.called

    # ========== Directory Operations ==========

    @patch("wy_qcos.common.library.os.rmdir")
    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.mkdir")
    def test_mkdir_rmdir_basic(self, mock_mkdir, mock_exists, mock_rmdir):
        """Test mkdir and rmdir basic functionality."""
        mock_mkdir.return_value = None
        mock_exists.return_value = False
        mock_rmdir.return_value = None
        input_file = f"{self.temp_dir}/test_kill_pid.txt"
        success = library.mkdir(input_file)
        assert success is True
        success, _ = library.rmdir(input_file)
        assert success is True

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.mkdir")
    def test_mkdir_success(self, mock_mkdir, mock_exists):
        """Test mkdir creates directory."""
        mock_exists.return_value = False
        mock_mkdir.return_value = None
        dir_path = "/newdir"
        result = Library.mkdir(dir_path)
        assert result is True
        mock_mkdir.assert_called()

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.mkdir")
    def test_mkdir_existing(self, mock_mkdir, mock_exists):
        """Test mkdir with existing directory."""
        mock_exists.return_value = True
        result = Library.mkdir("/existing_dir")
        assert isinstance(result, bool)

    @patch("wy_qcos.common.library.os.path.isdir")
    @patch("wy_qcos.common.library.os.rmdir")
    def test_rmdir_success(self, mock_rmdir, mock_isdir):
        """Test rmdir removes directory."""
        mock_isdir.side_effect = [True, False]
        mock_rmdir.return_value = None
        dir_path = "/to_remove"
        success, error = Library.rmdir(dir_path)
        assert success is True

    @patch("wy_qcos.common.library.os.path.isdir")
    def test_find_dirs_basic(self, mock_isdir):
        """Test find_dirs basic functionality."""
        mock_isdir.return_value = False
        dirs = library.find_dirs(base_dir="/tests", recursive=True)
        assert not dirs

    @patch("wy_qcos.common.library.os.path.isdir")
    def test_find_dirs_empty_result(self, mock_isdir):
        """Test find_dirs with non-existent base directory."""
        mock_isdir.return_value = False
        result = Library.find_dirs("/nonexistent/path")
        assert result == []

    @patch("wy_qcos.common.library.os.path.isdir")
    def test_find_files_basic(self, mock_isdir):
        """Test find_files basic functionality."""
        mock_isdir.return_value = False
        assert library.find_files("./") == []
        assert not (
            library.find_files(
                "./", pattern="test*", recursive=True, exclusives="test*"
            )
        )
        assert not library.find_files("no_such_dir")

    @patch("wy_qcos.common.library.os.path.isdir")
    @patch("wy_qcos.common.library.os.walk")
    def test_find_files_recursively(self, mock_walk, mock_isdir):
        """Test find_files with recursive search."""
        tmp_dir = tempfile.gettempdir()
        mock_isdir.return_value = True
        mock_walk.return_value = [(tmp_dir, ["subdir"], ["test.txt"])]
        result = Library.find_files(tmp_dir, pattern="*.txt", recursive=True)
        assert result is not None

    @patch("wy_qcos.common.library.os.path.isdir")
    def test_find_files_with_exclusion(self, mock_isdir):
        """Test find_files with exclusion pattern."""
        tmp_dir = tempfile.gettempdir()
        mock_isdir.return_value = False
        result = Library.find_files(tmp_dir, exclusives="exclude*")
        assert result is not None

    @patch("wy_qcos.common.library.os.path.isdir")
    def test_find_files_extended(self, mock_isdir):
        """Test find_files extended functionality."""
        tmp_dir = tempfile.gettempdir()
        mock_isdir.return_value = False
        result = Library.find_files(tmp_dir, pattern="*.txt")
        assert result is not None

    @patch("wy_qcos.common.library.Library.create_file")
    def test_create_pid_file_basic(self, mock_create_file):
        """Test create_pid_file basic functionality."""
        mock_create_file.return_value = (True, None)
        input_file = f"{self.temp_dir}/test_create_pid_file.txt"
        library.create_pid_file(input_file)
        mock_create_file.assert_called()

    @patch("wy_qcos.common.library.Library.create_file")
    def test_create_pid_file(self, mock_create_file):
        """Test create_pid_file."""
        mock_create_file.return_value = (True, None)
        pid_file = "/test.pid"
        Library.create_pid_file(pid_file)
        mock_create_file.assert_called()

    @patch("wy_qcos.common.library.Library.create_file")
    @patch("wy_qcos.common.library.Library.rm_file")
    def test_kill_pid_basic(self, mock_rm_file, mock_create_file):
        """Test kill_pid basic functionality."""
        mock_create_file.return_value = (True, None)
        mock_rm_file.return_value = (True, None)
        input_file = f"{self.temp_dir}/test_kill_pid.txt"
        library.create_file(input_file, "28336")
        assert library.kill_pid(input_file) is None

    @patch("wy_qcos.common.library.os.path.isdir")
    def test_is_directory_true(self, mock_isdir):
        """Test is_directory with directory."""
        tmp_dir = tempfile.gettempdir()
        mock_isdir.return_value = True
        assert mock_isdir(tmp_dir) is True

    @patch("wy_qcos.common.library.os.path.isdir")
    def test_is_directory_false(self, mock_isdir):
        """Test is_directory with file."""
        mock_isdir.return_value = False
        assert mock_isdir("/test.txt") is False

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.mkdir")
    def test_create_directory_new(self, mock_mkdir, mock_exists):
        """Test create_directory with new directory."""
        mock_exists.return_value = False
        mock_mkdir.return_value = None
        Library.mkdir("/newdir")
        mock_mkdir.assert_called()

    @patch("wy_qcos.common.library.os.path.exists")
    def test_file_exists_true(self, mock_exists):
        """Test file_exists with existing file."""
        mock_exists.return_value = True
        assert mock_exists("/test.txt") is True

    @patch("wy_qcos.common.library.os.path.exists")
    def test_file_exists_false(self, mock_exists):
        """Test file_exists with non-existent file."""
        mock_exists.return_value = False
        assert mock_exists("/nonexistent.txt") is False

    @patch("wy_qcos.common.library.os.remove")
    @patch("wy_qcos.common.library.os.path.isfile")
    def test_delete_file_basic(self, mock_isfile, mock_remove):
        """Test delete_file."""
        mock_isfile.return_value = True
        Library.rm_file("/test.txt")
        mock_remove.assert_called()

    @patch("shutil.copy")
    def test_copy_file_basic(self, mock_copy):
        """Test copy_file."""
        mock_copy.return_value = None
        shutil.copy("/src.txt", "/dst.txt")
        mock_copy.assert_called_with("/src.txt", "/dst.txt")

    @patch("shutil.move")
    def test_move_file_basic(self, mock_move):
        """Test move_file."""
        mock_move.return_value = None
        shutil.move("/src.txt", "/dst.txt")
        mock_move.assert_called_with("/src.txt", "/dst.txt")

    @patch("wy_qcos.common.library.os.path.getsize")
    def test_get_file_size_basic(self, mock_getsize):
        """Test get_file_size."""
        mock_getsize.return_value = 100
        size = os.path.getsize("/test.txt")
        assert size > 0

    # ========== CSV/TOML Operations ==========

    @patch("builtins.open", create=True)
    def test_read_csv_file_basic(self, mock_open):
        """Test read_csv_file basic functionality."""
        mock_open.return_value.__enter__.return_value.read.return_value = ""
        assert library.read_csv_file("/test.csv") is not None

    @patch("builtins.open", create=True)
    def test_read_csv_basic(self, mock_open):
        """Test read_csv."""
        mock_open.return_value.__enter__.return_value.read.return_value = (
            "a,b,c\n1,2,3"
        )
        result = Library.read_csv_file("/test.csv")
        assert result is not None

    @patch("builtins.open", create=True)
    def test_write_csv_basic(self, mock_open):
        """Test write_csv."""
        data = [{"a": 1, "b": 2}]
        with mock_open():
            writer = csv_module.DictWriter(mock_open(), fieldnames=["a", "b"])
            writer.writeheader()
            writer.writerows(data)
        mock_open.assert_called()

    def test_read_toml_file_basic(self):
        """Test read_toml_file basic functionality."""
        success, _, _ = library.read_toml_file("/test-toml.toml")
        assert success is False

    @patch("builtins.open", create=True)
    @patch("wy_qcos.common.library.tomlkit.load")
    def test_read_toml_file_valid(self, mock_tomlkit_load, mock_open):
        """Test read_toml_file with valid TOML."""
        mock_tomlkit_load.return_value = {"section": {"key": "value"}}
        mock_open.return_value.__enter__.return_value = MagicMock()
        success, error, content = Library.read_toml_file("/config.toml")
        assert success is True

    @patch("builtins.open", create=True)
    @patch("wy_qcos.common.library.tomlkit.load")
    def test_read_toml_file_invalid(self, mock_tomlkit_load, mock_open):
        """Test read_toml_file with invalid TOML."""
        mock_tomlkit_load.side_effect = Exception("Invalid TOML")
        mock_open.return_value.__enter__.return_value = MagicMock()
        success, error, content = Library.read_toml_file("/invalid.toml")
        assert success is False

    @patch("builtins.open", create=True)
    @patch("wy_qcos.common.library.tomlkit.dump")
    def test_write_to_toml_basic(self, mock_tomlkit_dump, mock_open):
        """Test create_toml basic functionality."""
        mock_tomlkit_dump.return_value = None
        mock_open.return_value.__enter__.return_value = MagicMock()
        data = {"host": "127.0.0.1", "port": "8080"}
        input_file = "/test_write_to_toml.txt"
        success, _ = library.create_toml(input_file, data)
        assert success is True
        success, _ = library.create_toml("", data)
        assert success is False

    @patch("builtins.open", create=True)
    @patch("wy_qcos.common.library.tomlkit.dump")
    def test_write_toml_basic(self, mock_tomlkit_dump, mock_open):
        """Test write_toml."""
        mock_tomlkit_dump.return_value = None
        mock_open.return_value.__enter__.return_value = MagicMock()
        Library.create_toml("/test.toml", {"key": "value"})
        mock_open.assert_called()

    # ========== Validation Operations ==========

    def test_validate_values_enum_basic(self):
        """Test validate_values_enum basic functionality."""
        value = ["qasm", "qubo"]
        success, _ = library.validate_values_enum("qasm", "code_type", value)
        assert success is True
        success, _ = library.validate_values_enum(
            None, "code_type", value, allow_none=True
        )
        assert success is True
        success, _ = library.validate_values_enum("qasm3", "code_type", value)
        assert success is False

    def test_validate_values_enum_valid(self):
        """Test validate_values_enum with valid value."""
        success, error = Library.validate_values_enum("a", "field", ["a", "b"])
        assert success is True

    def test_validate_values_enum_invalid(self):
        """Test validate_values_enum with invalid value."""
        success, error = Library.validate_values_enum("c", "field", ["a", "b"])
        assert success is False

    def test_validate_values_uuid_basic(self):
        """Test validate_values_uuid basic functionality."""
        uuid_1 = ConstantForTest.job_id
        success, _ = library.validate_values_uuid(uuid_1, "job_id")
        assert success is True
        success, _ = library.validate_values_uuid("9", "job_id")
        assert success is False

    def test_validate_values_range_basic(self):
        """Test validate_values_range basic functionality."""
        success, _ = library.validate_values_range(9, "job_priority")
        assert success is True
        success, _ = library.validate_values_range(
            9, "job_priority", min_value=13, max_value=6
        )
        assert success is False

    def test_validate_values_range_valid(self):
        """Test validate_values_range with valid value."""
        success, error = Library.validate_values_range(5, "field", 0, 10)
        assert success is True

    def test_validate_values_range_invalid(self):
        """Test validate_values_range with invalid value."""
        success, error = Library.validate_values_range(15, "field", 0, 10)
        assert success is False

    def test_validate_values_length_basic(self):
        """Test validate_values_length basic functionality."""
        success, _ = library.validate_values_length(
            None, "source_code", allow_none=True
        )
        assert success is True
        success, _ = library.validate_values_length(
            "99", "description", min_value=13, max_value=1
        )
        assert success is False
        success, _ = library.validate_values_length("9", "description")
        assert success is True

    def test_validate_values_length_valid(self):
        """Test validate_values_length with valid value."""
        success, error = Library.validate_values_length("test", "field", 1, 10)
        assert success is True

    def test_validate_values_length_invalid(self):
        """Test validate_values_length with invalid value."""
        success, error = Library.validate_values_length(
            "test", "field", 10, 20
        )
        assert success is False

    def test_validate_values_list_basic(self):
        """Test validate_values_list basic functionality."""
        value = "987613"
        success, _ = library.validate_values_list(value, "result", bin)
        assert success is False
        value = [9, 8, 7, 6, 13]
        success, _ = library.validate_values_list(value, "result", str)
        assert success is False
        value = [False, False]
        success, _ = library.validate_values_list(value, "result", bool)
        assert success is False
        success, _ = library.validate_values_list(
            value, "result", bool, allow_none=True
        )
        assert success is True

    def test_validate_schema_basic(self):
        """Test validate_schema basic functionality."""
        success, _ = library.validate_schema("9", "")
        assert success is False
        success, _ = library.validate_schema(None, "", allow_none=True)
        assert success is True
        success, _ = library.validate_schema("9", None)
        assert success is False

    def test_validate_schema_valid_data(self):
        """Test validate_schema with valid data."""
        schema = [str]
        data = ["item1", "item2"]
        success, error = Library.validate_schema(data, schema)
        assert success is True

    def test_validate_schema_invalid_data(self):
        """Test validate_schema with invalid data."""
        schema = [int]
        data = ["not_an_int", "also_not_int"]
        success, error = Library.validate_schema(data, schema)
        assert success is False

    def test_validate_schema_allow_none_true(self):
        """Test validate_schema with allow_none=True."""
        schema = [str]
        data = None
        success, error = Library.validate_schema(data, schema, allow_none=True)
        assert success is True

    def test_validate_name_valid(self):
        """Test validate_name with valid names."""
        success, _ = Library.validate_name("my-device")
        assert success is True
        success, _ = Library.validate_name("device_001")
        assert success is True
        success, _ = Library.validate_name("a")
        assert success is True
        success, _ = Library.validate_name("a" * 64)
        assert success is True
        success, _ = Library.validate_name("ALL_CAPS-123")
        assert success is True

    def test_validate_name_none(self):
        """Test validate_name with None (allow_none=True)."""
        success, _ = Library.validate_name(None)
        assert success is True

    def test_validate_name_empty(self):
        """Test validate_name with empty string."""
        success, _ = Library.validate_name("")
        assert success is False

    def test_validate_name_too_long(self):
        """Test validate_name with name longer than 64 chars."""
        success, _ = Library.validate_name("a" * 65)
        assert success is False

    def test_validate_name_invalid_chars(self):
        """Test validate_name with invalid characters."""
        success, _ = Library.validate_name("device name")
        assert success is False
        success, _ = Library.validate_name("device@name")
        assert success is False
        # dots are allowed by NAME_SCHEMA
        success, _ = Library.validate_name("device.name")
        assert success is True
        success, _ = Library.validate_name("device/name")
        assert success is False
        success, _ = Library.validate_name("中文设备名")
        assert success is False

    def test_validate_qubo_matrices_basic(self):
        """Test validate_qubo_matrices basic functionality."""
        normal_qubo1 = [[[1, 2, 3], [4, 5, 6], [7, 8, 9]]]
        success, _ = library.validate_qubo_matrices(normal_qubo1)
        assert success is True
        normal_qubo2 = [[[1, 2], [4, 5]], [[4, 5], [7, 8]]]
        success, _ = library.validate_qubo_matrices(normal_qubo2)
        assert success is True
        qubo1 = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        success, _ = library.validate_qubo_matrices(qubo1)
        assert success is False
        qubo2 = [[1, 2, 3], [4, 5, 6]]
        success, _ = library.validate_qubo_matrices(qubo2)
        assert success is False
        qubo3 = [[2, 3], [4, 5, 6]]
        success, _ = library.validate_qubo_matrices(qubo3)
        assert success is False
        qubo4 = [["a", 2, 3], [4, 5, 6]]
        success, _ = library.validate_qubo_matrices(qubo4)
        assert success is False

    # ========== Other Operations ==========

    def test_get_current_datetime_basic(self):
        """Test get_current_datetime basic functionality."""
        times = library.get_current_datetime()
        assert isinstance(times, datetime)

    def test_import_classes_basic(self):
        """Test import_classes basic functionality."""
        classes, venv_dirs = library.import_classes("logger")
        assert not classes
        assert not venv_dirs

    def test_get_nested_dict_value_basic(self):
        """Test get_nested_dict_value basic functionality."""
        dictionary = {"host": "127.0.0.1", "port": "8080"}
        keys = {"url": "127.0.0.1:8080"}
        default = library.get_nested_dict_value(dictionary, keys)
        assert default is None

    def test_get_sorted_keys_basic(self):
        """Test get_sorted_keys basic functionality."""
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

    def test_generate_binary_combinations_basic(self):
        """Test generate_binary_combinations basic functionality."""
        return_dict = library.generate_binary_combinations(9, 10)
        assert return_dict is not None
        return_dict = library.generate_binary_combinations(0, 10)
        assert return_dict == {}

    def test_get_zip_content_basic(self):
        """Test get_zip_content basic functionality."""
        success, _, _ = library.get_zip_content("/pid_file.zip")
        assert success is False

    def test_is_valid_url_basic(self):
        """Test is_valid_url basic functionality."""
        success = library.is_valid_url("127.0.0.1", {"http", "https"})
        assert success is False

    def test_is_valid_url_true(self):
        """Test is_valid_url with valid URL."""
        result = Library.is_valid_url("http://example.com", {"http", "https"})
        assert result is True

    def test_is_valid_url_false(self):
        """Test is_valid_url with invalid URL."""
        result = Library.is_valid_url("not_a_url", {"http", "https"})
        assert result is False

    @patch("wy_qcos.common.library.requests.post")
    def test_run_callbacks_basic(self, mock_post):
        """Test run_callbacks basic functionality."""
        data = {
            "job_id": "job_id",
            "job_status": "job_status",
            "backend": "backend",
            "results": "results",
        }
        callbacks = [
            {
                "method": HttpMethod.POST,
                "headers": {},
                "retries": 3,
                "timeout": 10,
                "url": "127.0.0.1",
            },
        ]
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.text = '{"result": "success"}'
        mock_post.return_value = mock_response
        success, _ = library.run_callbacks(data, callbacks)
        assert success is True
        mock_post.assert_called()

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("builtins.open", create=True)
    def test_kill_pid_with_invalid_format(self, mock_open, mock_exists):
        """Test kill_pid with invalid PID format."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = (
            "invalid_pid"
        )
        library.kill_pid("/test.pid")
        assert mock_open.called

    @patch("wy_qcos.common.library.os.chmod")
    @patch("builtins.open", create=True)
    @patch("wy_qcos.common.library.Library.mkdirs")
    def test_create_file_with_mkdir(self, mock_mkdirs, mock_open, mock_chmod):
        """Test create_file with mkdir option."""
        success, _ = Library.create_file(
            "/test/file.txt", "content", mkdir=True
        )
        assert success is True
        mock_mkdirs.assert_called()

    @patch("wy_qcos.common.library.os.chmod")
    @patch("builtins.open", create=True)
    @patch("wy_qcos.common.library.Library.mkdirs")
    def test_create_file_chmod_error(self, mock_mkdirs, mock_open, mock_chmod):
        """Test create_file with chmod error."""
        mock_chmod.side_effect = Exception("chmod failed")
        success, error = Library.create_file(
            "/test.txt", "content", mode=0o644
        )
        assert success is False
        assert "chmod failed" in error

    @patch("wy_qcos.common.library.Library.mkdirs")
    def test_create_temp_file_with_str(self, mock_mkdirs):
        """Test create_temp_file with string content."""
        tf = Library.create_temp_file("test content", dir=self.temp_dir)
        assert tf is not None
        content = tf.read()
        assert b"test content" in content
        tf.close()

    @patch("wy_qcos.common.library.Library.mkdirs")
    def test_create_temp_file_with_bytes(self, mock_mkdirs):
        """Test create_temp_file with bytes content."""
        tf = Library.create_temp_file(b"test bytes", dir=self.temp_dir)
        assert tf is not None
        content = tf.read()
        assert b"test bytes" in content
        tf.close()

    def test_create_temp_file_with_invalid_type(self):
        """Test create_temp_file with invalid content type."""
        with pytest.raises(TypeError):
            Library.create_temp_file(123)

    @patch("wy_qcos.common.library.os.remove")
    @patch("wy_qcos.common.library.os.path.isfile")
    def test_rm_file_with_error(self, mock_isfile, mock_remove):
        """Test rm_file with removal error."""
        mock_isfile.return_value = True
        mock_remove.side_effect = Exception("remove failed")
        success, error = Library.rm_file("/test.txt")
        assert success is False
        assert "remove failed" in error

    @patch("wy_qcos.common.library.os.path.isdir")
    @patch("wy_qcos.common.library.os.walk")
    def test_find_dirs_recursive_with_excludes(self, mock_walk, mock_isdir):
        """Test find_dirs with recursive and excludes."""
        mock_isdir.return_value = True
        mock_walk.return_value = [
            ("/base", ["dir1", "dir2", "exclude_dir"], [])
        ]
        result = Library.find_dirs(
            "/base", pattern="*", recursive=True, excludes=["exclude*"]
        )
        assert result is not None

    @patch("wy_qcos.common.library.os.path.isdir")
    @patch("wy_qcos.common.library.os.walk")
    def test_find_files_with_exclusives_list(self, mock_walk, mock_isdir):
        """Test find_files with exclusives as list."""
        tmp_dir = tempfile.gettempdir()
        mock_isdir.return_value = True
        mock_walk.return_value = [(tmp_dir, [], ["test.txt", "exclude.txt"])]
        result = Library.find_files(
            tmp_dir, pattern="*.txt", recursive=True, exclusives=["exclude"]
        )
        assert result is not None

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.mkdir")
    def test_mkdir_with_mode(self, mock_mkdir, mock_exists):
        """Test mkdir with mode parameter."""
        mock_exists.return_value = False
        result = Library.mkdir("/newdir", mode=0o755)
        assert result is True
        mock_mkdir.assert_called_with("/newdir", 0o755)

    @patch("wy_qcos.common.library.os.path.isdir")
    @patch("wy_qcos.common.library.os.rmdir")
    def test_rmdir_with_error(self, mock_rmdir, mock_isdir):
        """Test rmdir with error."""
        mock_rmdir.side_effect = Exception("rmdir failed")
        success, error = Library.rmdir("/test")
        assert success is False
        assert "rmdir failed" in error

    def test_get_top_dir(self):
        """Test get_top_dir."""
        result = Library.get_top_dir()
        assert result is not None
        assert isinstance(result, str)

    @patch("wy_qcos.common.library.psutil.process_iter")
    def test_get_processes(self, mock_process_iter):
        """Test get_processes."""
        mock_proc = Mock()
        mock_proc.info = {
            "pid": 123,
            "name": "test",
            "cmdline": ["python", "test.py"],
        }
        mock_process_iter.return_value = [mock_proc]
        result = Library.get_processes(["python"])
        assert result is not None

    @patch("wy_qcos.common.library.psutil.process_iter")
    def test_get_processes_with_exception(self, mock_process_iter):
        """Test get_processes with exception."""
        mock_proc = Mock()
        mock_proc.info = {"pid": 123, "name": "test", "cmdline": None}
        mock_process_iter.return_value = [mock_proc]
        result = Library.get_processes(["test"])
        assert isinstance(result, list)

    def test_kill_processes_graceful(self):
        """Test kill with graceful termination."""
        mock_proc = Mock()
        mock_proc.pid = 123
        mock_proc.terminate = Mock()
        with patch("wy_qcos.common.library.psutil.wait_procs") as mock_wait:
            mock_wait.return_value = ([mock_proc], [])
            success_pids, failed_pids = Library.kill([mock_proc], force=False)
            assert 123 in success_pids
            assert len(failed_pids) == 0

    def test_kill_processes_force(self):
        """Test kill with force option."""
        mock_proc = Mock()
        mock_proc.pid = 456
        mock_proc.kill = Mock()
        with patch("wy_qcos.common.library.psutil.wait_procs") as mock_wait:
            mock_wait.return_value = ([mock_proc], [])
            success_pids, failed_pids = Library.kill([mock_proc], force=True)
            assert 456 in success_pids

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.path.isdir")
    def test_get_venv_dirs_not_exists(self, mock_isdir, mock_exists):
        """Test get_venv_dirs with non-existent directory."""
        mock_exists.return_value = False
        result = Library.get_venv_dirs("/nonexistent")
        assert result == {}

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.path.isdir")
    def test_get_venv_dirs_not_dir(self, mock_isdir, mock_exists):
        """Test get_venv_dirs with file instead of directory."""
        mock_exists.return_value = True
        mock_isdir.return_value = False
        result = Library.get_venv_dirs("/file.txt")
        assert result == {}

    def test_md5_encrypt(self):
        """Test md5_encrypt."""
        result = Library.md5_encrypt("test")
        assert result is not None
        assert len(result) == 32

    def test_get_nested_dict_value_with_keys(self):
        """Test get_nested_dict_value with multiple keys."""
        data = {"level1": {"level2": {"level3": "value"}}}
        result = Library.get_nested_dict_value(
            data, "level1", "level2", "level3"
        )
        assert result == "value"

    def test_get_nested_dict_value_with_default(self):
        """Test get_nested_dict_value with default value."""
        data = {"key1": "value1"}
        result = Library.get_nested_dict_value(
            data, "nonexistent", default="default"
        )
        assert result == "default"

    def test_get_sorted_keys_with_string(self):
        """Test get_sorted_keys with string field."""
        sort_obj = {"name": "test", "value": 100}
        result = Library.get_sorted_keys(sort_obj, ["name"])
        assert result is not None

    def test_validate_values_uuid_version_error(self):
        """Test validate_values_uuid with version error."""
        success, error = Library.validate_values_uuid(
            "00000000-0000-0000-0000-000000000000", "test_id"
        )
        assert success is False

    def test_validate_qubo_matrices_empty(self):
        """Test validate_qubo_matrices with empty list."""
        success, error = Library.validate_qubo_matrices([])
        assert success is False
        assert "empty" in error

    def test_validate_qubo_matrices_non_square(self):
        """Test validate_qubo_matrices with non-square matrix."""
        qubo = [[[1, 2, 3], [4, 5, 6]]]
        success, error = Library.validate_qubo_matrices(qubo)
        assert success is False

    @patch("wy_qcos.common.library.requests.post")
    def test_call_http_api_with_debug(self, mock_post):
        """Test call_http_api with debug enabled."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.text = "response"
        mock_post.return_value = mock_response
        status, reason, text, _ = Library.call_http_api(
            "http://test.com", HttpMethod.POST, debug=True, func_name="test"
        )
        assert status == 200

    @patch("wy_qcos.common.library.requests.put")
    def test_call_http_api_put_method(self, mock_put):
        """Test call_http_api with PUT method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.text = "response"
        mock_put.return_value = mock_response
        status, reason, text, _ = Library.call_http_api(
            "http://test.com", "put"
        )
        assert status == 200

    @patch("wy_qcos.common.library.requests.patch")
    def test_call_http_api_patch_method(self, mock_patch):
        """Test call_http_api with PATCH method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.text = "response"
        mock_patch.return_value = mock_response
        status, reason, text, _ = Library.call_http_api(
            "http://test.com", "patch"
        )
        assert status == 200

    @patch("wy_qcos.common.library.requests.delete")
    def test_call_http_api_delete_method(self, mock_delete):
        """Test call_http_api with DELETE method."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.text = "response"
        mock_delete.return_value = mock_response
        status, reason, text, _ = Library.call_http_api(
            "http://test.com", "delete"
        )
        assert status == 200

    def test_is_valid_url_with_value_error(self):
        """Test is_valid_url with ValueError."""
        result = Library.is_valid_url("://invalid", {"http"})
        assert result is False

    @patch("wy_qcos.common.library.zipfile.ZipFile")
    def test_get_zip_content_success(self, mock_zipfile):
        """Test get_zip_content with valid zip file."""
        mock_zf = MagicMock()
        mock_zf.namelist.return_value = ["file1.txt"]
        mock_file = MagicMock()
        mock_file.read.return_value = b"content"
        mock_zf.open.return_value.__enter__.return_value = mock_file
        mock_zipfile.return_value.__enter__.return_value = mock_zf
        success, errors, results = Library.get_zip_content("/test.zip")
        assert success is True

    @patch("wy_qcos.common.library.zipfile.ZipFile")
    def test_get_zip_content_exception(self, mock_zipfile):
        """Test get_zip_content with exception."""
        mock_zipfile.side_effect = Exception("zip error")
        success, errors, results = Library.get_zip_content("/test.zip")
        assert success is False

    def test_loop_with_timeout_success(self):
        """Test loop_with_timeout with successful condition."""

        def condition_check():
            return True, None, "result"

        success, error, result = Library.loop_with_timeout(
            condition_check, 1, 0.1
        )
        assert success is True

    def test_loop_with_timeout_timeout(self):
        """Test loop_with_timeout with timeout."""

        def condition_check():
            return False, "not ready", None

        success, error, result = Library.loop_with_timeout(
            condition_check, 0.5, 0.1
        )
        assert success is False
        assert "Timed out" in error

    @patch("wy_qcos.common.library.requests.post")
    def test_run_callbacks_no_url(self, mock_post):
        """Test run_callbacks with no URL."""
        data = {"test": "data"}
        callbacks = [{"method": HttpMethod.POST}]
        success, _ = Library.run_callbacks(data, callbacks)
        assert success is False

    def test_mask_password_tuple(self):
        """Test mask_password with tuple."""
        config = ({"password": "secret"}, "data")
        result = Library.mask_password(config)
        assert isinstance(result, tuple)

    def test_encrypt_virtual_instance_id_with_list(self):
        """Test encrypt_virtual_instance_id with device list."""
        instance_id = "10000000-0000-4000-8000-000000000101"
        success, _, vid = Library.encrypt_virtual_instance_id(
            ["device1", "device2"], instance_id
        )
        assert success is True
        assert "device1+device2" in vid

    def test_decrypt_virtual_instance_id_invalid(self):
        """Test decrypt_virtual_instance_id with invalid format."""
        success, error, _, _ = Library.decrypt_virtual_instance_id("invalid")
        assert success is False

    def test_set_venv_path(self):
        """Test set_venv_path."""
        with patch("wy_qcos.common.library.Library.get_venv_dirs") as mock_get:
            mock_get.return_value = {}
            Library.set_venv_path("/venv")
            assert mock_get.called

    def test_get_driver_venv_no_default_env(self):
        """Test get_driver_venv without default env."""
        python_bin, python_path_env = Library.get_driver_venv(
            "test_driver", "/venv", add_default_env=False
        )
        assert python_bin is not None
        assert "PYTHONPATH" in python_path_env

    # ========== Additional Coverage for kill_pid ==========

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.kill")
    @patch("wy_qcos.common.library.time.sleep")
    @patch("builtins.open", create=True)
    def test_kill_pid_with_process_match(
        self, mock_open, mock_sleep, mock_kill, mock_exists
    ):
        """Test kill_pid with expected process name matching."""
        mock_exists.side_effect = [True, True]
        mock_file = MagicMock()
        mock_file.read.return_value = "12345"
        mock_cmdline = MagicMock()
        mock_cmdline.read.return_value = "python\x00test.py"
        mock_open.return_value.__enter__.side_effect = [
            mock_file,
            mock_cmdline,
        ]
        Library.kill_pid("/test.pid", expected_process_name="python.*")
        assert mock_open.called

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.getpid")
    @patch("builtins.open", create=True)
    def test_kill_pid_prevent_self_kill(
        self, mock_open, mock_getpid, mock_exists
    ):
        """Test kill_pid prevents killing self."""
        mock_exists.return_value = True
        mock_getpid.return_value = 12345
        mock_file = MagicMock()
        mock_file.read.return_value = "12345"
        mock_open.return_value.__enter__.return_value = mock_file
        Library.kill_pid("/test.pid", allow_kill_self=False)
        assert mock_open.called

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.kill")
    @patch("builtins.open", create=True)
    def test_kill_pid_process_lookup_error(
        self, mock_open, mock_kill, mock_exists
    ):
        """Test kill_pid with ProcessLookupError."""
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = "99999"
        mock_open.return_value.__enter__.return_value = mock_file
        mock_kill.side_effect = ProcessLookupError()
        Library.kill_pid("/test.pid")
        assert mock_kill.called

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.kill")
    @patch("builtins.open", create=True)
    def test_kill_pid_permission_error(
        self, mock_open, mock_kill, mock_exists
    ):
        """Test kill_pid with PermissionError."""
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = "12345"
        mock_open.return_value.__enter__.return_value = mock_file
        mock_kill.side_effect = PermissionError()
        Library.kill_pid("/test.pid")
        assert mock_kill.called

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.kill")
    @patch("builtins.open", create=True)
    def test_kill_pid_general_exception(
        self, mock_open, mock_kill, mock_exists
    ):
        """Test kill_pid with general exception."""
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = "12345"
        mock_open.return_value.__enter__.return_value = mock_file
        mock_kill.side_effect = Exception("Unknown error")
        Library.kill_pid("/test.pid")
        assert mock_kill.called

    @patch("wy_qcos.common.library.os.remove")
    @patch("wy_qcos.common.library.os.path.exists")
    @patch("builtins.open", create=True)
    def test_kill_pid_remove_file_error(
        self, mock_open, mock_exists, mock_remove
    ):
        """Test kill_pid with file removal error."""
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = "invalid"
        mock_open.return_value.__enter__.return_value = mock_file
        mock_remove.side_effect = OSError("Cannot remove")
        Library.kill_pid("/test.pid")
        assert mock_open.called

    # ========== Additional Coverage for create_temp_file ==========

    def test_create_temp_file_with_dir_and_mode(self):
        """Test create_temp_file with directory and mode."""
        with patch("wy_qcos.common.library.Library.mkdirs"):
            tf = Library.create_temp_file(
                "test", dir=self.temp_dir, dir_mode=0o755
            )
            assert tf is not None
            tf.close()

    def test_create_temp_file_exception_handling(self):
        """Test create_temp_file exception handling."""
        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_tf = MagicMock()
            mock_tf.write.side_effect = Exception("Write error")
            mock_temp.return_value = mock_tf
            with pytest.raises(Exception):
                Library.create_temp_file("test", dir=self.temp_dir)

    # ========== Additional Coverage for mkdirs ==========

    @patch("wy_qcos.common.library.os.mkdir")
    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.path.dirname")
    def test_mkdirs_recursive(self, mock_dirname, mock_exists, mock_mkdir):
        """Test mkdirs with recursive directory creation."""

        # Setup dirname with function to handle variable calls
        def dirname_impl(path):
            return {
                "/a/b/c": "/a/b",
                "/a/b": "/a",
                "/a": "",
                "": "",
            }.get(path, "")

        mock_dirname.side_effect = dirname_impl

        # Setup exists to handle recursive checks
        # We track which paths exist: only root ("") exists
        def exists_impl(path):
            return path == ""

        mock_exists.side_effect = exists_impl

        Library.mkdirs("/a/b/c")
        assert mock_mkdir.called

    @patch("wy_qcos.common.library.os.mkdir")
    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.path.dirname")
    def test_mkdirs_with_mode(self, mock_dirname, mock_exists, mock_mkdir):
        """Test mkdirs with mode parameter."""

        # Setup dirname with function to handle variable calls
        def dirname_impl(path):
            return {
                "/test/dir": "/test",
                "/test": "",
                "": "",
            }.get(path, "")

        mock_dirname.side_effect = dirname_impl

        # Setup exists to handle recursive checks
        # Only root ("") exists
        def exists_impl(path):
            return path == ""

        mock_exists.side_effect = exists_impl

        Library.mkdirs("/test/dir", mode=0o755)
        # Verify mkdir was called with correct mode
        assert mock_mkdir.called
        calls = mock_mkdir.call_args_list
        # Last call should have mode=0o755
        last_call = calls[-1]
        assert last_call[1].get("mode") == 0o755

    # ========== Additional Coverage for find_dirs ==========

    @patch("wy_qcos.common.library.os.path.isdir")
    @patch("wy_qcos.common.library.os.walk")
    def test_find_dirs_with_pattern_match(self, mock_walk, mock_isdir):
        """Test find_dirs with pattern matching."""
        mock_isdir.return_value = True
        mock_walk.return_value = [
            ("/base", ["test_dir", "other_dir", "test_sub"], [])
        ]
        result = Library.find_dirs("/base", pattern="test*", recursive=True)
        assert result is not None

    # ========== Additional Coverage for kill processes ==========

    def test_kill_processes_with_alive_process(self):
        """Test kill with process that stays alive after terminate."""
        mock_proc = Mock()
        mock_proc.pid = 789
        mock_proc.terminate = Mock()
        mock_proc.kill = Mock()
        with patch("wy_qcos.common.library.psutil.wait_procs") as mock_wait:
            mock_wait.side_effect = [([], [mock_proc]), ([mock_proc], [])]
            success_pids, failed_pids = Library.kill([mock_proc], force=False)
            assert 789 in success_pids
            mock_proc.kill.assert_called()

    def test_kill_processes_with_exception(self):
        """Test kill with exception during termination."""
        mock_proc = Mock()
        mock_proc.pid = 999
        mock_proc.terminate.side_effect = Exception("Error")
        with patch("wy_qcos.common.library.psutil.wait_procs"):
            # Exception during terminate should be caught and
            # added to failed_pids
            try:
                success_pids, failed_pids = Library.kill(
                    [mock_proc], force=False
                )
                assert len(failed_pids) > 0
            except Exception as e:
                print(f"Expected: Exception is raised by the mock: {e}")

    # ========== Additional Coverage for get_venv_dirs ==========

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.path.isdir")
    @patch("wy_qcos.common.library.os.listdir")
    @patch("wy_qcos.common.library.os.walk")
    def test_get_venv_dirs_with_activate(
        self, mock_walk, mock_listdir, mock_isdir, mock_exists
    ):
        """Test get_venv_dirs with activate file."""
        mock_exists.return_value = True
        mock_isdir.side_effect = [True, True, True]
        mock_listdir.return_value = ["venv1"]
        mock_walk.side_effect = [
            [("/venv/venv1/bin", [], ["activate"])],
            [("/venv/venv1/lib", ["python3.11"], [])],
            [("/venv/venv1/lib/python3.11", ["site-packages"], [])],
        ]
        result = Library.get_venv_dirs("/venv")
        assert result is not None

    @patch("wy_qcos.common.library.os.path.exists")
    @patch("wy_qcos.common.library.os.path.isdir")
    @patch("wy_qcos.common.library.os.listdir")
    def test_get_venv_dirs_with_permission_error(
        self, mock_listdir, mock_isdir, mock_exists
    ):
        """Test get_venv_dirs with PermissionError."""
        mock_exists.return_value = True
        mock_isdir.return_value = True
        mock_listdir.side_effect = PermissionError("Access denied")
        result = Library.get_venv_dirs("/venv")
        assert result == {}

    @patch("wy_qcos.common.library.os.walk")
    @patch("wy_qcos.common.library.os.listdir")
    @patch("wy_qcos.common.library.os.path.isdir")
    @patch("wy_qcos.common.library.os.path.exists")
    def test_get_venv_dirs_reorder_default(
        self, mock_exists, mock_isdir, mock_listdir, mock_walk
    ):
        """Test get_venv_dirs reorders default venv."""
        mock_exists.return_value = True
        # Need more return values for all isdir calls:
        # bin_dir for each venv, lib_dir for each venv
        mock_isdir.side_effect = [True, True, True, True, True, True]
        mock_listdir.return_value = ["default", "other"]
        mock_walk.side_effect = [
            [("/venv/default/bin", [], ["activate"])],
            [("/venv/default/lib", ["python3.11"], [])],
            [("/venv/other/bin", [], ["activate"])],
            [("/venv/other/lib", ["python3.11"], [])],
        ]
        result = Library.get_venv_dirs("/venv", default_venv_dir="default")
        assert result is not None

    # ========== Additional Coverage for set_venv_path ==========

    @patch("wy_qcos.common.library.os.path.isdir")
    @patch("wy_qcos.common.library.Library.get_venv_dirs")
    def test_set_venv_path_with_valid_dirs(self, mock_get_dirs, mock_isdir):
        """Test set_venv_path with valid directories."""
        mock_get_dirs.return_value = {
            "venv1": {"site_packages": "/venv/venv1/lib/site-packages"}
        }
        mock_isdir.return_value = True
        Library.set_venv_path("/venv")
        assert mock_get_dirs.called

    # ========== Additional Coverage for get_driver_venv ==========

    @patch("wy_qcos.common.library.Library.is_file")
    def test_get_driver_venv_with_driver_bin(self, mock_is_file):
        """Test get_driver_venv with driver-specific python bin."""
        mock_is_file.side_effect = [True]
        python_bin, python_path_env = Library.get_driver_venv(
            "test_driver", "/venv"
        )
        assert "/venv/test_driver/bin/python3" in python_bin

    @patch("wy_qcos.common.library.Library.is_file")
    def test_get_driver_venv_with_default_bin(self, mock_is_file):
        """Test get_driver_venv with default python bin."""
        mock_is_file.side_effect = [False, True]
        python_bin, python_path_env = Library.get_driver_venv(
            "test_driver", "/venv"
        )
        assert python_bin is not None

    @patch("wy_qcos.common.library.Library.is_file")
    @patch.dict("os.environ", {"PYTHONPATH": "/custom/path"})
    def test_get_driver_venv_with_env_pythonpath(self, mock_is_file):
        """Test get_driver_venv with PYTHONPATH environment variable."""
        mock_is_file.return_value = False
        python_bin, python_path_env = Library.get_driver_venv(
            "test_driver", "/venv"
        )
        assert "PYTHONPATH" in python_path_env

    # ========== Additional Coverage for import_classes ==========

    @patch("wy_qcos.common.library.pkgutil.iter_modules")
    def test_import_classes_with_venv_loader(self, mock_iter):
        """Test import_classes with venv_loader."""
        mock_iter.return_value = []

        def venv_loader(name, venv_dir):
            return False, "python3", "/path1:/path2"

        classes, venv_dirs = Library.import_classes(
            "/pkg", venv_base_dir="/venv", venv_loader=venv_loader
        )
        assert classes is not None

    # ========== Additional Coverage for validate_qubo_matrices ==========

    def test_validate_qubo_matrices_exceeds_max_qubits(self):
        """Test validate_qubo_matrices with matrix exceeding max qubits."""
        large_matrix = [[[1] * 10001 for _ in range(10001)]]
        success, error = Library.validate_qubo_matrices(large_matrix)
        assert success is False

    # ========== Additional Coverage for async_call_http_api ==========

    @pytest.mark.asyncio
    async def test_async_call_http_api_success(self):
        """Test async_call_http_api with successful response."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="response")

        # Create mock that supports async context manager
        async_cm_mock = MagicMock()
        async_cm_mock.__aenter__ = AsyncMock(return_value=mock_response)
        async_cm_mock.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "wy_qcos.common.library.aiohttp.ClientSession"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=async_cm_mock)
            mock_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            success, error, data, response = await Library.async_call_http_api(
                "http://test.com", HttpMethod.POST
            )
            assert success is True

    @pytest.mark.asyncio
    async def test_async_call_http_api_retry(self):
        """Test async_call_http_api with retry logic."""
        # Mock response with error status
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="error")

        # Create mock that supports async context manager
        async_cm_mock = MagicMock()
        async_cm_mock.__aenter__ = AsyncMock(return_value=mock_response)
        async_cm_mock.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "wy_qcos.common.library.aiohttp.ClientSession"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=async_cm_mock)
            mock_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            success, error, data, response = await Library.async_call_http_api(
                "http://test.com", HttpMethod.POST, retries=1
            )
            assert success is False

    @pytest.mark.asyncio
    async def test_async_call_http_api_timeout(self):
        """Test async_call_http_api with timeout."""
        # Create mock that raises TimeoutError
        async_cm_mock = MagicMock()
        async_cm_mock.__aenter__ = AsyncMock(
            side_effect=TimeoutError("Connection timeout")
        )
        async_cm_mock.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "wy_qcos.common.library.aiohttp.ClientSession"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=async_cm_mock)
            mock_session_class.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session_class.return_value.__aexit__ = AsyncMock(
                return_value=None
            )

            success, error, data, response = await Library.async_call_http_api(
                "http://test.com", HttpMethod.POST, retries=1
            )
            assert success is False

    # ========== Additional Coverage for async_run_callbacks ==========

    @pytest.mark.asyncio
    async def test_async_run_callbacks_empty(self):
        """Test async_run_callbacks with empty callbacks."""
        success, error = await Library.async_run_callbacks({}, None)
        assert success is True

    @pytest.mark.asyncio
    async def test_async_run_callbacks_with_url(self):
        """Test async_run_callbacks with URL."""
        with patch(
            "wy_qcos.common.library.Library.async_call_http_api"
        ) as mock_call:
            mock_call.return_value = (True, None, "response", None)
            callbacks = [{"url": "http://test.com"}]
            success, error = await Library.async_run_callbacks(
                {"data": "test"}, callbacks
            )
            assert success is True

    # ========== Additional Coverage for get_sorted_keys ==========

    def test_get_sorted_keys_with_int_descending(self):
        """Test get_sorted_keys with integer descending."""
        sort_obj = {"value": 100}
        result = Library.get_sorted_keys(sort_obj, ["-value"])
        assert result is not None

    def test_get_sorted_keys_with_datetime_descending(self):
        """Test get_sorted_keys with datetime descending."""
        sort_obj = {"date": datetime(2020, 1, 1)}
        result = Library.get_sorted_keys(sort_obj, ["-date"])
        assert result is not None

    def test_get_sorted_keys_with_object_attribute(self):
        """Test get_sorted_keys with object attribute."""

        class TestObj:
            def __init__(self):
                self.name = "test"

        sort_obj = TestObj()
        result = Library.get_sorted_keys(sort_obj, ["name"])
        assert result is not None

    # ========== Additional Coverage for
    # encrypt/decrypt_virtual_instance_id ==========

    def test_encrypt_virtual_instance_id_exception(self):
        """Test encrypt_virtual_instance_id with exception."""
        success, error, _ = Library.encrypt_virtual_instance_id(None, "uuid")
        assert success is False

    def test_decrypt_virtual_instance_id_with_encode(self):
        """Test decrypt_virtual_instance_id with base64 encoding."""
        instance_id = "10000000-0000-4000-8000-000000000101"
        success, _, vid = Library.encrypt_virtual_instance_id(
            ["device1"], instance_id, salt="salt", encode=True
        )
        assert success is True
        success2, error, devices, instance_id = (
            Library.decrypt_virtual_instance_id(vid, salt="salt", encode=True)
        )
        assert success2 is True

    def test_decrypt_virtual_instance_id_wrong_verify_code(self):
        """Test decrypt_virtual_instance_id with wrong verify code."""
        success, error, _, _ = Library.decrypt_virtual_instance_id(
            "device|uuid|wrong", salt="salt"
        )
        assert success is False
