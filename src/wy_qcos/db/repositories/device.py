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
#     WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Device repository for device state persistence."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from wy_qcos.db.models.device import Device
from wy_qcos.db.repositories.base import BaseRepository


class DeviceRepository(BaseRepository):
    """Database operations related to Device state."""

    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    def get_device_state(self, device_name: str):
        """Get the stored state for a device.

        Args:
            device_name: device name (primary key)

        Returns:
            tuple: (success, error, state_str_or_None)
        """
        try:
            query = select(Device).where(Device.name == device_name)
            result = self._db_session.execute(query)
            record = result.scalars().first()
            if record is None:
                return True, None, None
            return True, None, record.state
        except Exception as e:
            return False, e, None

    def upsert_device_state(
        self, device_name: str, state: str, auto_commit: bool = True
    ):
        """Insert or update the state for a device.

        Args:
            device_name: device name (primary key)
            state: device state string (auto/online/offline/...)
            auto_commit: commit automatically if True

        Returns:
            tuple: (success, error, record)
        """
        try:
            now = datetime.now()
            query = select(Device).where(Device.name == device_name)
            result = self._db_session.execute(query)
            record = result.scalars().first()
            if record is None:
                record = Device(
                    name=device_name,
                    state=state,
                    created_at=now,
                    updated_at=now,
                )
                self._db_session.add(record)
            else:
                record.state = state
                record.updated_at = now
            self._db_session.flush()
            if auto_commit:
                self._db_session.commit()
                self._db_session.refresh(record)
            return True, None, record
        except Exception as e:
            self._db_session.rollback()
            return False, e, None

    def load_all_device_states(self):
        """Load all device states from database.

        Returns:
            tuple: (success, error, dict of {name: state})
        """
        try:
            query = select(Device)
            result = self._db_session.execute(query)
            records = result.scalars().all()
            states = {}
            for record in records:
                states[record.name] = record.state
            return True, None, states
        except Exception as e:
            return False, e, None
