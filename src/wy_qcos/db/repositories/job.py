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

from uuid import UUID
import logging

from sqlalchemy.orm import Session

from wy_qcos.db.models import Job
from wy_qcos.db.repositories import BaseRepository
from wy_qcos.api import schemas

logger = logging.getLogger(__name__)


class JobRepository(BaseRepository):
    """Database operation function library related to Job."""

    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    def create_job(self, job_create: schemas.SubmitJobRequest):
        """Create a new job."""
        job_create_dict = job_create.model_dump()
        if job_create_dict.get("job_id"):
            job_create_dict["id"] = job_create_dict.get("job_id")
        del job_create_dict["job_id"]
        return self.create(Job, **job_create_dict)

    def get_job_by_uuid(self, job_id: UUID):
        return self.get_by_uuid(Job, str(job_id))

    def get_jobs(self):
        return self.get_all(Job)

    def update_job(
        self, job_id: UUID, job_update: schemas.SetJobResultsRequest
    ):
        """Update a job."""
        job_update_dict = job_update.model_dump()
        del job_update_dict["job_id"]
        job_update_dict["id"] = job_id

        return self.update(Job, str(job_id), **job_update_dict)
