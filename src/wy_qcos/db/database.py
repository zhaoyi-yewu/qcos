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
from sqlalchemy import make_url, create_engine

from wy_qcos.db.models import Base
from wy_qcos.common.config import Config

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
        self._engine = create_engine(
            self._url,
            pool_size=10,
            max_overflow=1000,
            pool_pre_ping=True,
        )
        return self._engine

    def disconnect_from_db(self) -> None:
        """Dispose of the connection pool used by the database engine."""
        if self._engine is not None:
            self._engine.dispose()

    def create_tables(self) -> None:
        """Create tables."""
        try:
            Base.metadata.create_all(bind=self._engine)  # type: ignore[attr-defined]
        except Exception as e:
            logger.info(f"Error while creating tables : {e}")
            raise Exception(e)


def init_database():
    """Init database."""
    if Config.QCOS_DATABASE_CONNECTION_URL == "fake":
        logger.info("Skip init database without db config.")
        return

    logger.info("Init database ...")
    config_db_url = make_url(Config.QCOS_DATABASE_CONNECTION_URL)
    db_driver = DatabaseDriver(config_db_url, config_db_url.database)

    db_engine = db_driver.create_engine()
    db_driver.create_tables()
    return db_engine
