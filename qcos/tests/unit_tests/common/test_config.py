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

from unittest.mock import patch, Mock
import pytest

from qcos.common import errors
from qcos.common.config import Config
from qcos.common.library import Library

config = Config()


class TestConfig:
    @patch.object(Library, "read_toml_file")
    def test_parse_toml_file(self, mock_read_toml_file):
        mock_obj = Mock()
        mock_obj.unwrap.return_value = {
            "1": {"1": "Alice", "2": 2},
            "2": {"1": "Bob", "3": 3},
        }
        mock_read_toml_file.return_value = iter([True, "err_msg", mock_obj])
        with pytest.raises(errors.GenericException) as context:
            config.parse_toml_file("config.toml")
        assert str(context.value) is not None

        mock_read_toml_file.return_value = iter([True, "err_msg", mock_obj])
        config.parse_toml_file("config.toml", extra_config=True)

    def test_show_info(self):
        config.show_info()
