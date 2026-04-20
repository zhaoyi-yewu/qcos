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

from unittest.mock import patch, Mock
import pytest

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library
from wy_qcos.common.constant import Constant
from wy_qcos.common import errors

config = Config()


class TestConfig:
    @patch.object(Library, "read_toml_file")
    def test_parse_toml_file(self, mock_read_toml_file):
        mock_obj = Mock()
        mock_obj.unwrap.return_value = {
            "result": {"shots": 100},
        }
        mock_read_toml_file.return_value = iter([True, "err_msg", mock_obj])

        mock_read_toml_file.return_value = iter([False, "err_msg", mock_obj])
        with pytest.raises(Exception) as context:
            config.load_config_file("/config.toml")
        assert str(context.value) is not None

        mock_read_toml_file.return_value = iter([True, "err_msg", mock_obj])
        config.load_config_file("/config.toml", extra_config=True)

        mock_read_toml_file.return_value = iter([False, "err_msg", mock_obj])
        with pytest.raises(Exception) as context:
            config.load_config_file("/config.toml", extra_config=True)
        assert str(context.value) is not None

    def test_show_info(self):
        assert config.show_info() is not None

    @patch.object(Library, "read_toml_file")
    @patch.object(Library, "decrypt_text")
    def test_load_config_file_with_encrypted_value(
        self, mock_decrypt, mock_read_toml
    ):
        """Test loading config with encrypted values."""
        mock_config = {
            "DEFAULT": {
                "debug": "false",
                "password_salt": f"{Constant.ENCRYPTION_PREFIX}abc123"
            }
        }
        mock_obj = Mock()
        mock_obj.unwrap.return_value = mock_config
        mock_read_toml.return_value = (True, None, mock_obj)
        mock_decrypt.return_value = (True, None, "decrypted_salt")

        config.load_config_file("/config.toml")
        mock_decrypt.assert_called()

    @patch.object(Library, "read_toml_file")
    @patch.object(Library, "decrypt_text")
    def test_load_config_file_decrypt_failure(
        self, mock_decrypt, mock_read_toml
    ):
        """Test load config with decryption failure."""
        mock_config = {
            "DEFAULT": {
                "password_salt": f"{Constant.ENCRYPTION_PREFIX}abc123"
            }
        }
        mock_obj = Mock()
        mock_obj.unwrap.return_value = mock_config
        mock_read_toml.return_value = (True, None, mock_obj)
        mock_decrypt.return_value = (False, "Decrypt error", None)

        with pytest.raises(errors.GenericException):
            config.load_config_file("/config.toml")

    def test_get_configs_without_mask(self):
        """Test get_configs without password masking."""
        configs = config.get_configs(mask_password=False)
        assert isinstance(configs, dict)
        assert "DEBUG" in configs

    @patch.object(Library, "mask_password")
    def test_get_configs_with_mask(self, mock_mask):
        """Test get_configs with password masking."""
        mock_mask.return_value = {"password": "***"}
        configs = config.get_configs(mask_password=True)
        mock_mask.assert_called_once()

    def test_get_extra_configs(self):
        """Test get_extra_configs returns dict."""
        Config._EXTRA_CONFIGS = {"section": {"key": "value"}}
        extra = config.get_extra_configs()
        assert isinstance(extra, dict)

    def test_get_driver_env_configs(self):
        """Test get_driver_env_configs returns dict."""
        Config._DRIVER_ENV_CONFIGS = {"driver": "config"}
        driver_configs = config.get_driver_env_configs()
        assert isinstance(driver_configs, dict)

    @patch.object(Library, "read_toml_file")
    def test_load_config_file_invalid_section_key(self, mock_read_toml):
        """Test loading config with invalid key in DEFAULT section."""
        mock_config = {
            "DEFAULT": {"invalid_config_key": "value"}
        }
        mock_obj = Mock()
        mock_obj.unwrap.return_value = mock_config
        mock_read_toml.return_value = (True, None, mock_obj)

        with pytest.raises(errors.GenericException) as exc:
            config.load_config_file("/config.toml")
        assert "Can't find config key" in str(exc.value)

    @patch.object(Library, "read_toml_file")
    def test_load_config_file_valid_section_invalid_key(self, mock_read_toml):
        """Test valid section but with invalid config key."""
        mock_config = {
            "DEFAULT": {"nonexistent_param": "value"}
        }
        mock_obj = Mock()
        mock_obj.unwrap.return_value = mock_config
        mock_read_toml.return_value = (True, None, mock_obj)

        with pytest.raises(errors.GenericException):
            config.load_config_file("/config.toml")

    @patch.object(Library, "read_toml_file")
    def test_load_extra_config_not_in_valid_sections(self, mock_read_toml):
        """Test extra config loading when section not in valid sections."""
        mock_config = {
            "CUSTOM_SECTION": {"custom_key": "custom_value"}
        }
        mock_obj = Mock()
        mock_obj.unwrap.return_value = mock_config
        mock_read_toml.return_value = (True, None, mock_obj)

        Config._EXTRA_CONFIGS = {}
        config.load_config_file("/config.toml", extra_config=False)
        # Should add to extra configs since CUSTOM_SECTION not in VALID_SECTIONS

    @patch.object(Library, "read_toml_file")
    def test_load_driver_env_file_copy_from_handling(self, mock_read_toml):
        """Test driver env file with copy_from handling."""
        from collections import OrderedDict
        from pathlib import Path
        mock_configs = OrderedDict([
            ("base_driver", {
                "deps_filepaths": ["deps.txt"],
                "envs": ["ENV1", "ENV2"]
            }),
            ("derived_driver", {"copy_from": "base_driver"})
        ])
        mock_read_toml.return_value = (True, None, mock_configs)

        with patch("pathlib.Path.parent") as mock_parent:
            mock_parent_obj = Mock()
            mock_parent_obj.__truediv__ = Mock(return_value=Path("/test/deps.txt"))
            mock_parent.__truediv__ = Mock(return_value=mock_parent_obj)
            with patch("pathlib.Path.resolve") as mock_resolve:
                mock_resolve.return_value = Path("/test/deps.txt")
                config.load_driver_env_file("/driver_env.toml")

    def test_validate_device_list_duplicates(self):
        """Test that duplicate devices are removed."""
        original_devices = Config.DEVICE_LIST
        try:
            Config.DEVICE_LIST = ["device1", "device1", "device2"]
            with patch.object(Library, "remove_duplicates") as mock_remove:
                with patch.object(Library, "validate_schema") as mock_validate:
                    mock_remove.return_value = ["device1", "device2"]
                    mock_validate.return_value = (True, None)
                    config.validate()
                    mock_remove.assert_called_once()
        finally:
            Config.DEVICE_LIST = original_devices

    def test_validate_single_auth_mode_virt_only(self):
        """Test validate succeeds with only ENABLE_VIRT."""
        original_virt = Config.ENABLE_VIRT
        original_mgmt = Config.ENABLE_USER_MGMT
        try:
            Config.ENABLE_VIRT = True
            Config.ENABLE_USER_MGMT = False
            with patch.object(Library, "remove_duplicates") as mock_remove:
                with patch.object(Library, "validate_schema") as mock_validate:
                    mock_remove.return_value = []
                    mock_validate.return_value = (True, None)
                    config.validate()  # Should not raise
        finally:
            Config.ENABLE_VIRT = original_virt
            Config.ENABLE_USER_MGMT = original_mgmt

    def test_validate_single_auth_mode_user_mgmt_only(self):
        """Test validate succeeds with only ENABLE_USER_MGMT."""
        original_virt = Config.ENABLE_VIRT
        original_mgmt = Config.ENABLE_USER_MGMT
        try:
            Config.ENABLE_VIRT = False
            Config.ENABLE_USER_MGMT = True
            with patch.object(Library, "remove_duplicates") as mock_remove:
                with patch.object(Library, "validate_schema") as mock_validate:
                    mock_remove.return_value = []
                    mock_validate.return_value = (True, None)
                    config.validate()  # Should not raise
        finally:
            Config.ENABLE_VIRT = original_virt
            Config.ENABLE_USER_MGMT = original_mgmt

    def test_get_configs_filters_private_attributes(self):
        """Test get_configs filters out private and magic attributes."""
        configs = config.get_configs(mask_password=False)
        # Should not include attributes starting with _ or __
        for key in configs.keys():
            assert not key.startswith('_'), f"Config should not include private attr: {key}"

    def test_show_info_formatting(self):
        """Test show_info returns properly formatted string."""
        info = config.show_info()
        assert isinstance(info, str)
        assert "[Configs]" in info
        assert len(info) > 10
