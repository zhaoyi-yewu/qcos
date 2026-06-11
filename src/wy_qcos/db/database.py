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

from sqlalchemy.engine import Engine
from sqlalchemy import make_url, create_engine, text

from wy_qcos.common.library import Library
from wy_qcos.db.models import Base

logger = logging.getLogger(__name__)


class DatabaseDriver:
    """DatabaseDriver.

    database connection establishment/closure, session creating.
    """

    def __init__(self, database_url, database_name) -> None:
        self._url = database_url
        self._name = database_name
        self._engine: Engine | None = None

    def create_engine(self):
        """Create db engine."""
        # Convert URL string to URL object if needed
        url = (
            self._url
            if hasattr(self._url, "drivername")
            else make_url(self._url)
        )

        # Build engine kwargs based on database type
        engine_kwargs = {"pool_pre_ping": True}

        # Only set pool parameters for databases that support
        # connection pooling. SQLite uses SingletonThreadPool which
        # doesn't support these parameters
        if not url.drivername.startswith("sqlite"):
            engine_kwargs["pool_size"] = 10
            engine_kwargs["max_overflow"] = 1000

        self._engine = create_engine(url, **engine_kwargs)
        return self._engine

    def disconnect_from_db(self) -> None:
        """Dispose of the connection pool used by the database engine."""
        if self._engine is not None:
            self._engine.dispose()

    def create_tables(self) -> None:
        """Create tables."""
        try:
            Base.metadata.create_all(bind=self._engine)
        except Exception as e:
            logger.info(f"Error while creating tables : {e}")
            raise

    def check_connection(self):
        """Check connection."""
        if self._engine is None:
            logger.error("Database engine not initialized")
            raise TimeoutError("Database engine not initialized")

        def is_connected():
            try:
                with self._engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("Database is connected")
                return True, None, None
            except Exception as e:
                logger.error(f"Database connection check failed: {str(e)}")
                return False, str(e), None

        success, err_msg, _ = Library.loop_with_timeout(is_connected, 60, 5)
        if not success:
            raise TimeoutError("Connection to database timeout")


def init_database(qcos_db_url):
    """Init database."""
    db_url = Config.DATABASE.QCOS_DATABASE_CONNECTION_URL
    logger.info(f"Initializing database: {db_url}")

    try:
        config_db_url = make_url(db_url)
        db_driver = DatabaseDriver(config_db_url, config_db_url.database)

        db_engine = db_driver.create_engine()
        db_driver.check_connection()
        logger.info("Database initialized successfully")
        return db_engine
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise
