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

from contextlib import contextmanager
from fastapi import Depends
from starlette.requests import HTTPConnection
from sqlalchemy.orm import Session

from wy_qcos.db.repositories.job import JobRepository
from wy_qcos.api import schemas
from wy_qcos.db.database import init_database
from wy_qcos.db.repositories import BaseRepository
from wy_qcos.common.library import Library

logger = logging.getLogger(__name__)


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


async def job_callback(flow, flow_run, state, results=None):
    """Job callback.

    Args:
        flow: flow
        flow_run: flow run
        state: flow state
        results: flow results
    """
    job_id = flow_run.name
    results = state.data.result
    if results is None:
        logger.error(
            f"Update flow result into db error {job_id}: result is empty"
        )

    for i in range(len(results)):
        results[i]["metadata"]["end_date"] = results[i]["metadata"][
            "end_date"
        ].isoformat()

    update_info = schemas.SetJobResultsRequest(
        job_id=job_id,
        results=results,
    )

    # create db session
    parameters = flow_run.parameters
    configs = Library.get_nested_dict_value(
        parameters, "job_info", "global", "configs", default=None
    )
    try:
        db_url = configs.get("QCOS_DATABASE_CONNECTION_URL")
        if db_url == "fake":
            return
        db_engine = init_database(db_url)

        # insert db
        with create_db_session(db_engine) as db_session:
            job_repo = JobRepository(db_session)
            success, e, _ = job_repo.update_job(job_id, update_info)
            if not success or e:
                raise Exception(str(e))
    except Exception as e:
        logger.error(f"Update flow result into db error {job_id}: {str(e)}")
