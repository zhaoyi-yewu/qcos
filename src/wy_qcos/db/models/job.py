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
import uuid
from typing import ClassVar

from sqlalchemy.sql.schema import Table
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Integer,
    ForeignKey,
    JSON,
)

from wy_qcos.db.models.base import BaseTable, GUID

logger = logging.getLogger(__name__)


class Job(BaseTable):
    """Job table."""

    __tablename__ = "job"
    __table__: ClassVar[Table]

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    project_id = Column(GUID, ForeignKey("projects.id"), nullable=False)
    user_id = Column(GUID, ForeignKey("users.id"), nullable=True)
    flow_run_id = Column(GUID, nullable=True)
    job_name = Column(String(128))
    job_type = Column(String(32))
    job_status = Column(String(32), default="UNKNOWN")
    job_priority = Column(Integer)
    backend = Column(String(32))
    code_type = Column(String(32))
    source_code = Column(JSON, default=list)
    description = Column(String(256))
    driver_options = Column(JSON, default=dict)
    transpiler = Column(String(32))
    transpiler_options = Column(JSON, default=dict)
    circuit_aggregation = Column(String(32))
    qec_options = Column(JSON, default=dict)
    shots = Column(Integer)
    progress = Column(Integer, default=-1)
    profiling = Column(JSON, default=list)
    callbacks = Column(JSON, default=list)
    is_callback_success = Column(Boolean, default=False)
    dry_run = Column(Boolean, default=False)
    results = Column(JSON, default=list)
    code_compression_level = Column(Integer, default=0)
    tags = Column(JSON, default=list)
    started_at = Column(DateTime)
    updated_at = Column(DateTime)
    ended_at = Column(DateTime)
