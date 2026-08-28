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

import argparse
import logging
import sys
import uvicorn

from wy_qcos.api.fastapi_server import app, QcosUvicornServer
from wy_qcos.api.posiq.routes_jsonrpc.routes import all_api
from wy_qcos.common import errors
from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.common.qcos_version import QcosVersion
from wy_qcos.db import database
from wy_qcos.db.utils import db_utils
from wy_qcos.device.device_manager import DeviceManager
from wy_qcos.driver.driver_manager import DriverManager
from wy_qcos.log.logger import init_logger, PERF_LEVEL
from wy_qcos.task_manager import scheduler
from wy_qcos.transpiler.transpiler_manager import TranspilerManager
from wy_qcos.user.project_manager import ProjectManager
from wy_qcos.user.security_manager import SecurityManager
from wy_qcos.user.user_manager import UserManager

logger = logging.getLogger(__name__)

PROGRAM_NAME = Constant.PROGRAM_NAME
PROGRAM_AUTHOR = Constant.PROGRAM_AUTHOR
PROGRAM_VERSION = f"{PROGRAM_NAME} - v{QcosVersion.VERSION} ({PROGRAM_AUTHOR})"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FORMAT = "%(asctime)s %(process)d %(levelname)s [%(name)s] %(message)s"


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
            dest="config_files",
            action="append",
            default=None,
            help="Config file path (can be specified multiple times)",
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
        # read and parse config files
        if args.config_files is None:
            args.config_files = ["/etc/qcos/qcos.toml"]

        for cf in args.config_files:
            Config.load_config_file(cf)

        # read and parse config files under config dir
        if args.config_dir:
            config_files = Library.find_files(
                args.config_dir, pattern="*.toml", recursive=True
            )
            for cf in config_files:
                Config.load_config_file(cf, extra_config=True)

        # validate Config
        Config.validate()

        # load driver env configs
        Config.load_driver_env_file(
            f"{Config.DEFAULT.VENV_DIR}/venv-configs.toml"
        )

        # config log level
        logger_level = logging.INFO
        if Config.DEFAULT.DEBUG:
            logger_level = logging.DEBUG

        log_file = Config.LOG.API_LOG_FILE
        self._stream_handlers = init_logger(
            logger_level,
            logfile=log_file,
            max_bytes=Config.LOG.LOG_ROTATE_MAX_SIZE_MB * 1000000,
            backup_count=Config.LOG.LOG_ROTATE_BACKUP_COUNT,
            console=True,
            compression=Config.LOG.LOG_ROTATE_COMPRESSION,
            quiet=False,
        )
        logger.setLevel(logger_level)

        # TRANSPILER.DEBUG only affects transpiler loggers, not global level
        if Config.TRANSPILER.DEBUG:
            logging.getLogger("wy_qcos.transpiler").setLevel(PERF_LEVEL)
            for h in self._stream_handlers:
                h.setLevel(PERF_LEVEL)

    def run(self, loop):
        """Run the server."""
        self._parse_arguments(sys.argv[1:])
        logger.info(PROGRAM_VERSION)
        logger.info(Config.show_info())

        # get log level
        logger_level = logging.INFO
        access_log = False
        if Config.DEFAULT.DEBUG:
            logger_level = logging.DEBUG
            # only show uvicorn access logs in debug mode
            access_log = True

        # TRANSPILER.DEBUG only affects transpiler loggers, not global level
        if Config.TRANSPILER.DEBUG:
            logging.getLogger("wy_qcos.transpiler").setLevel(PERF_LEVEL)
            for h in self._stream_handlers:
                h.setLevel(PERF_LEVEL)

        # Let uvicorn handle signals; do not register custom signal
        # handlers here.
        try:
            _listen_ip = (
                Config.API_SERVER.API_SERVER_LISTEN_IP
                if Config.API_SERVER.API_SERVER_LISTEN_IP
                else "all IPs"
            )
            logger.info(f"Starting server, listening on '{_listen_ip}'")

            config = uvicorn.Config(
                app,
                host=Config.API_SERVER.API_SERVER_LISTEN_IP,
                port=Config.API_SERVER.API_SERVER_LISTEN_PORT,
                workers=Config.API_SERVER.API_WORKERS,
                loop="uvloop",
                reload=False,
                access_log=access_log,
                lifespan="on",
                ssl_certfile=Config.SSL.CERT_FILE
                if Config.SSL.USE_SSL
                else None,
                ssl_keyfile=Config.SSL.KEY_FILE
                if Config.SSL.USE_SSL
                else None,
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

            # configure wy_qcos root logger to use our handlers
            wy_qcos_logger = logging.getLogger("wy_qcos")
            wy_qcos_logger.handlers = self._stream_handlers
            wy_qcos_logger.setLevel(logger_level)
            wy_qcos_logger.propagate = False

            # init uvicorn server
            server = QcosUvicornServer(config)

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

            # init database BEFORE starting multiprocessing
            # (multiprocessing can reset Config in child processes)
            logger.info("Initializing database...")
            db_engine = database.init_database()
            app.state._db_engine = db_engine

            # init user management module
            logger.info("Init user manager")
            with db_utils.create_db_session(db_engine) as db_session:
                # init project manager
                project_manager = ProjectManager(db_session)
                app.state._project_manager = project_manager
                # init user manager
                user_manager = UserManager(
                    Config.USERS.ACCESS_CONTROL_MODEL_FILE,
                    Config.USERS.ACCESS_CONTROL_POLICY_FILE,
                    all_api,
                    db_session,
                )
                app.state._user_manager = user_manager
                # init security manager
                logger.info("Init security manager")
                security_manager = SecurityManager(user_manager)
                app.state._security_manager = security_manager

            # set driver manager, transpiler in scheduler and device manager
            logger.info("Init scheduler")
            scheduler.set_driver_manager(driver_manager)
            scheduler.set_transpiler_manager(transpiler_manager)
            scheduler.set_device_manager(device_manager)
            scheduler.set_db_engine(db_engine)
            scheduler.init_device_group_manager()
            scheduler.init_flavor_manager()
            scheduler.init_auto_scheduler()
            scheduler.start_taskmanager()
            app.state._task_manager = scheduler.get_task_manager()

            # handle any unfinished jobs from previous runs
            logger.info("Processing unfinished callbacks ...")
            scheduler.process_unfinished_jobs()

            # run any unfinished callbacks
            logger.info("Processing unfinished callbacks ...")
            scheduler.process_callbacks()

            # run forever
            logger.info("API server running ...")
            loop.run_until_complete(server.serve())
        except KeyboardInterrupt as e:
            raise errors.GenericException(
                f"KeyboardInterrupt error while running the server: {e}"
            ) from e
        except Exception as e:
            raise errors.GenericException(
                f"Critical error while running the server: {e}"
            ) from e
        finally:
            print("Killing workers ...")
            scheduler.get_task_manager().kill_workers()
