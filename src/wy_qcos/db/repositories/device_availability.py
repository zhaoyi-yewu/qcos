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
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from wy_qcos.common.constant import Constant
from wy_qcos.db.models import DeviceAvailabilityHourly
from wy_qcos.db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class DeviceAvailabilityRepository(BaseRepository):
    """Database operations for DeviceAvailabilityHourly."""

    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    def upsert_hourly(self, hour, items):
        """Upsert hourly availability records for multiple devices.

        For each (device_name, hour) pair, insert a new row or
        update the existing online_count/total_count when the
        unique constraint conflicts.

        Args:
            hour: the whole-hour datetime to aggregate for
            items: list of dicts with keys device_name,
                online_count, total_count

        Returns:
            (success, error)
        """
        if not items:
            return True, None
        try:
            now = datetime.now()
            dialect_name = (
                self._db_session.bind.dialect.name
                if self._db_session.bind is not None
                else ""
            )
            if dialect_name == Constant.DB_DIALECT_POSTGRESQL:
                # Bulk upsert via PostgreSQL ON CONFLICT.
                # created_at/updated_at are provided explicitly because
                # pg_insert does not apply Python-side column defaults
                # and the columns are NOT NULL without server_default.
                rows = [
                    {
                        "device_name": it["device_name"],
                        "hour": hour,
                        "online_count": it.get("online_count", 0),
                        "total_count": it.get("total_count", 0),
                        "created_at": now,
                        "updated_at": now,
                    }
                    for it in items
                ]
                stmt = pg_insert(DeviceAvailabilityHourly).values(rows)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_device_availability_hourly",
                    set_={
                        "online_count": stmt.excluded.online_count,
                        "total_count": stmt.excluded.total_count,
                        "updated_at": now,
                    },
                )
                self._db_session.execute(stmt)
            else:
                # Fallback: select-then-insert/update (e.g. sqlite)
                for it in items:
                    dev = it["device_name"]
                    q = select(DeviceAvailabilityHourly).where(
                        DeviceAvailabilityHourly.device_name == dev,
                        DeviceAvailabilityHourly.hour == hour,
                    )
                    existing = (
                        self._db_session.execute(q).scalars().one_or_none()
                    )
                    if existing is None:
                        self._db_session.add(
                            DeviceAvailabilityHourly(
                                device_name=dev,
                                hour=hour,
                                online_count=it.get("online_count", 0),
                                total_count=it.get("total_count", 0),
                                created_at=now,
                                updated_at=now,
                            )
                        )
                    else:
                        existing.online_count = it.get("online_count", 0)
                        existing.total_count = it.get("total_count", 0)
                        existing.updated_at = now
            self._db_session.commit()
            return True, None
        except Exception as e:
            self._db_session.rollback()
            logger.error(f"upsert_hourly failed: {e}")
            return False, str(e)

    def get_availability(self, device_name, start, end):
        """Get availability records for a device within a time range.

        Args:
            device_name: device name
            start: start datetime (inclusive)
            end: end datetime (exclusive)

        Returns:
            list of DeviceAvailabilityHourly records ordered by hour asc
        """
        q = (
            select(DeviceAvailabilityHourly)
            .where(
                DeviceAvailabilityHourly.device_name == device_name,
                DeviceAvailabilityHourly.hour >= start,
                DeviceAvailabilityHourly.hour < end,
            )
            .order_by(DeviceAvailabilityHourly.hour.asc())
        )
        return list(self._db_session.execute(q).scalars().all())

    def get_last_hour_availability(self, device_name, before_hour):
        """Get availability rate for the most recent aggregated hour.

        Returns the rate for the latest row strictly before
        ``before_hour``.

        Args:
            device_name: device name
            before_hour: datetime; returns the latest row with
                hour < before_hour

        Returns:
            availability rate (float) or None when no record exists
        """
        q = (
            select(DeviceAvailabilityHourly)
            .where(
                DeviceAvailabilityHourly.device_name == device_name,
                DeviceAvailabilityHourly.hour < before_hour,
            )
            .order_by(DeviceAvailabilityHourly.hour.desc())
            .limit(1)
        )
        rec = self._db_session.execute(q).scalars().one_or_none()
        if rec is None or not rec.total_count:
            return None
        return rec.online_count / rec.total_count

    def get_overall_availability_counts(self, device_name, before_hour):
        """Get aggregated availability counts from all historical records.

        Sums online_count and total_count across every hourly row
        strictly before ``before_hour``. Used to compute an overall
        availability rate combined with the current-hour real-time counts.

        Args:
            device_name: device name
            before_hour: datetime; only rows with hour < before_hour
                are included

        Returns:
            (online_count, total_count) tuple, or None when no
            record exists
        """
        q = select(DeviceAvailabilityHourly).where(
            DeviceAvailabilityHourly.device_name == device_name,
            DeviceAvailabilityHourly.hour < before_hour,
        )
        records = list(self._db_session.execute(q).scalars().all())
        if not records:
            return None
        total_online = sum(r.online_count for r in records)
        total_all = sum(r.total_count for r in records)
        return (total_online, total_all)
