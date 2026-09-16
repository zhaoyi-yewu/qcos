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

from datetime import datetime
from typing import ClassVar

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql.schema import Table

from wy_qcos.db.models.base import BaseTable


class DeviceAvailabilityHourly(BaseTable):
    """DeviceAvailabilityHourly table - hourly device availability statistics.

    Each row records the sampling counts for one device in one
    whole hour. ``online_count`` counts samples whose status was
    online or busy; ``total_count`` counts all samples. The availability
    rate is derived as ``online_count / total_count`` at query time.
    """

    __tablename__ = "device_availability_hourly"
    __table__: ClassVar[Table]
    __table_args__ = (
        UniqueConstraint(
            "device_name",
            "hour",
            name="uq_device_availability_hourly",
        ),
    )

    # auto-increment integer primary key (database-assigned)
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    device_name = Column(String(255), nullable=False)
    hour = Column(DateTime, nullable=False)
    online_count = Column(Integer, nullable=False, default=0)
    total_count = Column(Integer, nullable=False, default=0)
    # Override BaseTable timestamps with Python-side defaults so
    # ORM inserts (e.g. sqlite fallback) populate them automatically.
    # Use local time (datetime.now) to match the hour column and
    # server_default NOW() which stores local time.
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)
