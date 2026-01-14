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

import argparse
import asyncio
import functools
import logging
import os
import platform
import signal
import sys
import uvicorn

from wy_qcos.api.fastapi_server import app
from wy_qcos.common import errors
from wy_qcos.common.config import Config
from wy_qcos.common.library import Library
from wy_qcos.common.qcos_version import QcosVersion
from wy_qcos.drivers.device_manager import DeviceManager
from wy_qcos.drivers.driver_manager import DriverManager
from wy_qcos.log.logger import init_logger
from wy_qcos.task_manager import scheduler
from wy_qcos.transpiler.transpiler_manager import TranspilerManager

logger = logging.getLogger(__name__)

PROGRAM_NAME = Config.PROGRAM_NAME
PROGRAM_AUTHOR = Config.PROGRAM_AUTHOR
PROGRAM_VERSION = f"{PROGRAM_NAME} - v{QcosVersion.VERSION} ({PROGRAM_AUTHOR})"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FORMAT = "%(asctime)s %(process)d %(levelname)s [%(name)s] %(message)s"


def _signal_handling():
    """Signal handling."""

    def signal_handler(signame, *args):
        """Signal handler."""
        try:
            if signame == "SIGHUP":
                logger.info(f"Server has got signal {signame}, reloading...")
                # asyncio.ensure_future(Controller.instance().reload())
            else:
                logger.info(f"Server has got signal {signame}, exiting...")
                # send SIGTERM to the server PID so uvicorn can be shutdown
                os.kill(os.getpid(), signal.SIGTERM)
        except asyncio.CancelledError:
            pass

    # SIGINT and SIGTERM are already registered by uvicorn
    signals = ["SIGHUP", "SIGQUIT"]
    if platform.system() != "Linux":
        signals = []
    for signal_name in signals:
        callback = functools.partial(signal_handler, signal_name)
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(getattr(signal, signal_name), callback)


class Server:
    """Server."""

    def __init__(self):
        self._stream_handlers = None

    def _parse_arguments(self, argv):
        """Parse command line arguments and override local configuration.

        Args:
            argv: command line arguments
        """
        parser = argparse.ArgumentParser(description="QCOS api server")
        parser.add_argument(
            "-v",
            "--version",
            help="Show the version",
            action="version",
            version=PROGRAM_VERSION,
        )
        parser.add_argument(
            "-c",
            "--config-file",
            dest="config_file",
            default="/etc/qcos/qcos.toml",
            help="Config file path",
        )
        parser.add_argument(
            "--config-dir",
            dest="config_dir",
            default="/etc/qcos/conf.d/",
            help="Config dir path",
        )
        parser.add_argument(
            "-d",
            "--daemon",
            dest="daemon",
            action="store_true",
            help="Start as a daemon",
        )

        args = parser.parse_args(argv)
        # read and parse config file
        if args.config_file:
            Config.parse_toml_file(args.config_file)

        # read and parse config files under config dir
        if args.config_dir:
            config_files = Library.find_files(
                args.config_dir, pattern="*.toml", recursive=True
            )
            for config_file in config_files:
                Config.parse_toml_file(config_file, extra_config=True)

        # validate Config
        Config.validate()

        # read command line arguments and override configs
        if args.daemon:
            Config.DAEMON = args.daemon

        # config log level
        logger_level = logging.INFO
        if Config.DEBUG:
            logger_level = logging.DEBUG

        log_file = Config.API_LOG_FILE
        self._stream_handlers = init_logger(
            logger_level,
            logfile=log_file,
            max_bytes=Config.LOG_ROTATE_MAX_SIZE_MB * 1000000,
            backup_count=Config.LOG_ROTATE_BACKUP_COUNT,
            console=True,
            compression=Config.LOG_ROTATE_COMPRESSION,
            quiet=False,
        )

    @staticmethod
    def _pid_lock(path):
        """Write the file in a file on the system.

        Check if the process is not already running

        Args:
            path: pid lock file path
        """
        if os.path.exists(path):
            pid = None
            try:
                with open(path, encoding="utf-8") as f:
                    try:
                        pid = int(f.read())
                        # kill returns an error if the process is not running
                        os.kill(pid, 0)
                    except (OSError, SystemError, ValueError):
                        pid = None
            except OSError as e:
                logger.critical("Can't open pid file %s: %s", pid, str(e))
                sys.exit(1)

            if pid:
                logger.critical(
                    "QCOS api server is already running pid: %d", pid
                )
                sys.exit(1)

        try:
            with open(path, "w+", encoding="utf-8") as f:
                f.write(str(os.getpid()))
        except OSError as e:
            logger.critical("Can't write pid file %s: %s", path, str(e))
            sys.exit(1)

    def run(self, loop):
        """Run the server."""
        self._parse_arguments(sys.argv[1:])
        logger.info(PROGRAM_VERSION)
        logger.info(Config.show_info())

        _signal_handling()
        try:
            _listen_ip = (
                Config.API_SERVER_LISTEN_IP
                if Config.API_SERVER_LISTEN_IP
                else "all IPs"
            )
            logger.info(f"Starting server, listening on '{_listen_ip}'")
            # only show uvicorn access logs in debug mode
            access_log = False
            if logger.getEffectiveLevel() == logging.DEBUG:
                access_log = True

            config = uvicorn.Config(
                app,
                host=Config.API_SERVER_LISTEN_IP,
                port=Config.API_SERVER_LISTEN_PORT,
                workers=Config.API_WORKERS,
                reload=False,
                access_log=access_log,
                lifespan="on",
                ssl_certfile=Config.CERT_FILE if Config.USE_SSL else None,
                ssl_keyfile=Config.KEY_FILE if Config.USE_SSL else None,
                ssl_ca_certs=Config.CACERT_FILE if Config.USE_SSL else None,
            )

            # overwrite uvicorn loggers with our own logger
            for uvicorn_logger_name in ("uvicorn", "uvicorn.error"):
                uvicorn_logger = logging.getLogger(uvicorn_logger_name)
                uvicorn_logger.handlers = self._stream_handlers
                uvicorn_logger.propagate = False

            if access_log:
                uvicorn_logger = logging.getLogger("uvicorn.access")
                uvicorn_logger.handlers = self._stream_handlers
                uvicorn_logger.propagate = False

            # init uvicorn server
            server = uvicorn.Server(config)

            # init plugin and drivers
            # init and load drivers
            driver_manager = DriverManager()
            driver_manager.load_drivers()
            driver_manager.init_drivers()

            # init and load transpilers
            transpiler_manager = TranspilerManager()
            transpiler_manager.load_transpilers()
            transpiler_manager.init_transpilers()

            # init and load devices
            device_manager = DeviceManager(Config, driver_manager)
            device_manager.load_devices()
            device_manager.init_devices()

            # set driver manager, transpiler in scheduler and device manager
            scheduler.set_driver_manager(driver_manager)
            scheduler.set_transpiler_manager(transpiler_manager)
            scheduler.set_device_manager(device_manager)
            scheduler.start_taskmanager()

            # run any unfinished callbacks
            logger.info("Processing unfinished callbacks ...")
            scheduler.process_callbacks()

            # run forever
            logger.info("API server running ...")
            loop.run_until_complete(server.serve())
        except Exception as e:
            raise errors.GenericException(
                f"Critical error while running the server: {e}"
            ) from e
