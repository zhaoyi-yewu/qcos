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
from datetime import datetime

from sqlalchemy.sql.schema import Table
from sqlalchemy import Column, String, DateTime, Boolean, Integer

from wy_qcos.db.models.base import BaseTable, ArrayType, GUID, DictList

logger = logging.getLogger(__name__)


class Job(BaseTable):
    """Job table."""

    __tablename__ = "job"
    __table__: ClassVar[Table]

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    project_id = Column(GUID)
    user_id = Column(GUID)
    job_name = Column(String(128))
    job_type = Column(String(32))
    job_priority = Column(Integer)
    code_type = Column(String(10))
    source_code = Column(ArrayType, index=True, default=list)
    description = Column(String(256))
    backend = Column(String(10))
    driver_options = Column(DictList)
    transpiler = Column(String(128))
    transpiler_options = Column(DictList)
    circuit_aggregation = Column(String(32))
    profiling = Column(ArrayType)
    shots = Column(Integer)
    callbacks = Column(ArrayType)
    dry_run = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    results = Column(DictList)
