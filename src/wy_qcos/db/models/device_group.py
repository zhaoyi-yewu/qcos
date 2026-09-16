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

import uuid
from typing import ClassVar

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    JSON,
    String,
)
from sqlalchemy.sql.schema import Table

from wy_qcos.common.constant import Constant
from wy_qcos.db.models.base import BaseTable, GUID


class DeviceGroup(BaseTable):
    """DeviceGroup table - logical grouping of devices."""

    __tablename__ = "device_groups"
    __table__: ClassVar[Table]

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    project_id = Column(
        GUID,
        ForeignKey("projects.id"),
        nullable=False,
        default=uuid.UUID(Constant.ADMIN_PROJECT_ID),
    )
    name = Column(String(128), nullable=False, unique=True)
    description = Column(String(256))
    device_names = Column(JSON, nullable=True, default=None)
    is_public = Column(Boolean, default=True)
