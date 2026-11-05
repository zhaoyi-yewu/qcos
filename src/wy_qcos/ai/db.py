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

"""Async SQLAlchemy engine factory for QCOS AI modules.

Provides a shared async engine and session factory so that RAG / AI
components can use SQLAlchemy ORM instead of raw SQL.
"""

import logging

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from wy_qcos.common.config import Config

logger = logging.getLogger(__name__)

_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_async_db_url() -> str:
    """Return the database URL converted to an async-compatible form.

    The project config stores a synchronous URL (e.g. postgresql://).
    For PostgreSQL we append the asyncpg driver; for SQLite we use
    aiosqlite.
    """
    url = Config.DATABASE.QCOS_DATABASE_CONNECTION_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


def get_async_engine() -> AsyncEngine:
    """Get or create the shared async engine."""
    global _async_engine
    if _async_engine is None:
        url = _get_async_db_url()
        _async_engine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        # Hide credentials in the log output
        safe_url = url.split("@")[-1] if "@" in url else url
        logger.info(f"Created async engine for {safe_url}")
    return _async_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the shared async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def close_async_engine() -> None:
    """Dispose the shared async engine (e.g. on shutdown)."""
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("Async engine disposed")
