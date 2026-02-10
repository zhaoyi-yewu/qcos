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

from wy_qcos.common.config import Config
from wy_qcos.server import Server

server = Server()


class TestServer:
    @patch("wy_qcos.server.init_logger")
    @patch("wy_qcos.server.Config.load_driver_env_file")
    @patch("wy_qcos.server.argparse.ArgumentParser")
    def test_parse_arguments(
        self,
        mock_argument_parser,
        mock_load_driver_env_file,
        mock_init_logger,
    ):
        mock_init_logger.return_value = None
        mock_parser = Mock()
        mock_argument_parser.return_value = mock_parser

        mock_args = Mock()
        mock_args.config_file = None
        mock_args.config_dir = None
        mock_parser.parse_args.return_value = mock_args
        Config.VEN_DIR = "/invalid_venv_dir"

        server._parse_arguments(None)
        mock_load_driver_env_file.assert_called_once_with(
            f"{Config.VENV_DIR}/venv-configs.toml"
        )
