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

from argparse import ArgumentParser
from unittest.mock import patch, Mock

from wy_qcos.server import Server

server = Server()


class TestServer:
    @patch("wy_qcos.server.argparse.ArgumentParser")
    @patch.object(ArgumentParser, "parse_args")
    def test__parse_arguments(self, mock_parse_args, mock_argument_parser):
        mock_args = Mock()
        mock_parse_args.return_value = mock_args
        mock_args.config_file = False
        mock_args.config_dir = False
        server._parse_arguments(None)
