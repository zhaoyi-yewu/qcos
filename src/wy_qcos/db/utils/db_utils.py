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

from contextlib import contextmanager
from fastapi import Depends
from starlette.requests import HTTPConnection
from sqlalchemy.orm import Session

from wy_qcos.db.repositories import BaseRepository


def get_db_session(request: HTTPConnection) -> Session:
    """Get db session."""
    db_engine = request.app.state._db_engine

    session = Session(db_engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()


def get_repository(repo: type[BaseRepository]):
    """Return database repository object, which contains operation function."""

    def get_repo(
        db_session: Session = Depends(get_db_session),
    ) -> BaseRepository:
        return repo(db_session)

    return get_repo


@contextmanager
def create_db_session(db_engine):
    session = Session(db_engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
