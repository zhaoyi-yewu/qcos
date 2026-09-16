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

import logging

from unittest.mock import patch, Mock

import pytest

from wy_qcos.common.config import Config
from wy_qcos.log.logger import PERF_LEVEL
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
        mock_args.config_files = []
        mock_args.config_dir = None
        mock_parser.parse_args.return_value = mock_args
        Config.DEFAULT.VENV_DIR = "/invalid_venv_dir"

        server._parse_arguments(None)
        mock_load_driver_env_file.assert_called_once_with(
            f"{Config.DEFAULT.VENV_DIR}/venv-configs.toml"
        )

    @patch("wy_qcos.server.init_logger")
    @patch("wy_qcos.server.Config.load_driver_env_file")
    @patch("wy_qcos.server.Config.load_config_file")
    @patch("wy_qcos.server.argparse.ArgumentParser")
    def test_parse_arguments_with_config_files(
        self,
        mock_argument_parser,
        mock_load_config_file,
        mock_load_driver_env_file,
        mock_init_logger,
    ):
        """config_files specified: each file is loaded."""
        mock_init_logger.return_value = [Mock()]
        mock_parser = Mock()
        mock_argument_parser.return_value = mock_parser

        mock_args = Mock()
        mock_args.config_files = ["/custom/config.toml"]
        mock_args.config_dir = None
        mock_parser.parse_args.return_value = mock_args
        Config.DEFAULT.VENV_DIR = "/venv"

        server._parse_arguments(None)
        mock_load_config_file.assert_called_once_with("/custom/config.toml")
        mock_load_driver_env_file.assert_called_once()

    @patch("wy_qcos.server.init_logger")
    @patch("wy_qcos.server.Config.load_driver_env_file")
    @patch("wy_qcos.server.Config.load_config_file")
    @patch("wy_qcos.server.Library.find_files")
    @patch("wy_qcos.server.argparse.ArgumentParser")
    def test_parse_arguments_with_config_dir(
        self,
        mock_argument_parser,
        mock_find_files,
        mock_load_config_file,
        mock_load_driver_env_file,
        mock_init_logger,
    ):
        """config_dir specified: find_files scans and loads them."""
        mock_init_logger.return_value = [Mock()]
        mock_parser = Mock()
        mock_argument_parser.return_value = mock_parser

        mock_args = Mock()
        mock_args.config_files = []
        mock_args.config_dir = "/etc/qcos/conf.d/"
        mock_parser.parse_args.return_value = mock_args
        mock_find_files.return_value = ["/etc/qcos/conf.d/dev1.toml"]
        Config.DEFAULT.VENV_DIR = "/venv"

        server._parse_arguments(None)
        mock_find_files.assert_called_once()
        mock_load_config_file.assert_called_once_with(
            "/etc/qcos/conf.d/dev1.toml", extra_config=True
        )
        mock_load_driver_env_file.assert_called_once()

    @patch("wy_qcos.server.init_logger")
    @patch("wy_qcos.server.Config.load_driver_env_file")
    @patch("wy_qcos.server.argparse.ArgumentParser")
    def test_parse_arguments_debug_mode(
        self,
        mock_argument_parser,
        mock_load_driver_env_file,
        mock_init_logger,
    ):
        """DEBUG=True sets logger level to DEBUG."""
        mock_init_logger.return_value = [Mock()]
        mock_parser = Mock()
        mock_argument_parser.return_value = mock_parser

        mock_args = Mock()
        mock_args.config_files = []
        mock_args.config_dir = None
        mock_parser.parse_args.return_value = mock_args
        Config.DEFAULT.VENV_DIR = "/venv"
        Config.DEFAULT.DEBUG = True

        server._parse_arguments(None)
        mock_init_logger.assert_called_once()
        call_args = mock_init_logger.call_args
        assert call_args.args[0] == logging.DEBUG

    @patch("wy_qcos.server.init_logger")
    @patch("wy_qcos.server.Config.load_driver_env_file")
    @patch("wy_qcos.server.argparse.ArgumentParser")
    def test_parse_arguments_transpiler_debug(
        self,
        mock_argument_parser,
        mock_load_driver_env_file,
        mock_init_logger,
    ):
        """TRANSPILER.DEBUG sets transpiler logger to PERF_LEVEL."""
        mock_handler = Mock()
        mock_init_logger.return_value = [mock_handler]
        mock_parser = Mock()
        mock_argument_parser.return_value = mock_parser

        mock_args = Mock()
        mock_args.config_files = []
        mock_args.config_dir = None
        mock_parser.parse_args.return_value = mock_args
        Config.DEFAULT.VENV_DIR = "/venv"
        Config.DEFAULT.DEBUG = False
        Config.TRANSPILER.DEBUG = True

        server._parse_arguments(None)
        mock_handler.setLevel.assert_called_once_with(PERF_LEVEL)

    @patch("wy_qcos.server.init_logger")
    @patch("wy_qcos.server.Config.load_driver_env_file")
    @patch("wy_qcos.server.argparse.ArgumentParser")
    def test_parse_arguments_no_transpiler_debug(
        self,
        mock_argument_parser,
        mock_load_driver_env_file,
        mock_init_logger,
    ):
        """TRANSPILER.DEBUG=False does not set transpiler logger."""
        mock_handler = Mock()
        mock_init_logger.return_value = [mock_handler]
        mock_parser = Mock()
        mock_argument_parser.return_value = mock_parser

        mock_args = Mock()
        mock_args.config_files = []
        mock_args.config_dir = None
        mock_parser.parse_args.return_value = mock_args
        Config.DEFAULT.VENV_DIR = "/venv"
        Config.DEFAULT.DEBUG = False
        Config.TRANSPILER.DEBUG = False

        server._parse_arguments(None)
        mock_handler.setLevel.assert_not_called()

    @patch("wy_qcos.server.TranspilerManager")
    @patch("wy_qcos.server.DriverManager")
    @patch("wy_qcos.server.DeviceManager")
    @patch("wy_qcos.server.database")
    @patch("wy_qcos.server.QcosUvicornServer")
    @patch("wy_qcos.server.uvicorn")
    @patch("wy_qcos.server.scheduler")
    @patch("wy_qcos.server.init_logger")
    @patch("wy_qcos.server.Config.load_driver_env_file")
    @patch("wy_qcos.server.argparse.ArgumentParser")
    def test_run_keyboard_interrupt(
        self,
        mock_argument_parser,
        mock_load_driver_env_file,
        mock_init_logger,
        mock_scheduler,
        mock_uvicorn,
        mock_uvicorn_server_cls,
        mock_database,
        mock_device_manager_cls,
        mock_driver_manager_cls,
        mock_transpiler_manager_cls,
    ):
        """run() raises GenericException on KeyboardInterrupt."""
        from wy_qcos.common import errors

        mock_handler = Mock()
        mock_handler.level = logging.INFO
        mock_init_logger.return_value = [mock_handler]
        mock_parser = Mock()
        mock_argument_parser.return_value = mock_parser

        mock_args = Mock()
        mock_args.config_files = []
        mock_args.config_dir = None
        mock_parser.parse_args.return_value = mock_args
        Config.DEFAULT.VENV_DIR = "/venv"
        Config.DEFAULT.DEBUG = False
        Config.TRANSPILER.DEBUG = False

        mock_task_manager = Mock()
        mock_scheduler.get_task_manager.return_value = mock_task_manager

        mock_loop = Mock()
        mock_loop.run_until_complete.side_effect = KeyboardInterrupt("ctrl-c")

        with pytest.raises(errors.GenericException):
            server.run(mock_loop)

    @patch("wy_qcos.server.TranspilerManager")
    @patch("wy_qcos.server.DriverManager")
    @patch("wy_qcos.server.DeviceManager")
    @patch("wy_qcos.server.database")
    @patch("wy_qcos.server.QcosUvicornServer")
    @patch("wy_qcos.server.uvicorn")
    @patch("wy_qcos.server.scheduler")
    @patch("wy_qcos.server.init_logger")
    @patch("wy_qcos.server.Config.load_driver_env_file")
    @patch("wy_qcos.server.argparse.ArgumentParser")
    def test_run_critical_error(
        self,
        mock_argument_parser,
        mock_load_driver_env_file,
        mock_init_logger,
        mock_scheduler,
        mock_uvicorn,
        mock_uvicorn_server_cls,
        mock_database,
        mock_device_manager_cls,
        mock_driver_manager_cls,
        mock_transpiler_manager_cls,
    ):
        """run() raises GenericException on general Exception."""
        from wy_qcos.common import errors

        mock_handler = Mock()
        mock_handler.level = logging.INFO
        mock_init_logger.return_value = [mock_handler]
        mock_parser = Mock()
        mock_argument_parser.return_value = mock_parser

        mock_args = Mock()
        mock_args.config_files = []
        mock_args.config_dir = None
        mock_parser.parse_args.return_value = mock_args
        Config.DEFAULT.VENV_DIR = "/venv"
        Config.DEFAULT.DEBUG = False
        Config.TRANSPILER.DEBUG = False

        mock_task_manager = Mock()
        mock_scheduler.get_task_manager.return_value = mock_task_manager

        mock_loop = Mock()
        mock_loop.run_until_complete.side_effect = Exception("boom")

        with pytest.raises(errors.GenericException):
            server.run(mock_loop)
