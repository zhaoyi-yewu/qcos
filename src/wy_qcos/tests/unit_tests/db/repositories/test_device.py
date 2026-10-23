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

"""Unit tests for DeviceRepository."""

from datetime import datetime

from wy_qcos.db.models.device import Device
from wy_qcos.db.repositories.device import DeviceRepository


class TestDeviceRepository:
    """Test DeviceRepository class."""

    def test_get_device_state_found(self, in_memory_db):
        """Test getting state for existing device."""
        repo = DeviceRepository(in_memory_db)
        now = datetime.now()
        device = Device(
            name="dev1", state="online", created_at=now, updated_at=now
        )
        in_memory_db.add(device)
        in_memory_db.commit()

        success, error, state = repo.get_device_state("dev1")
        assert success is True
        assert error is None
        assert state == "online"

    def test_get_device_state_not_found(self, in_memory_db):
        """Test getting state for non-existent device."""
        repo = DeviceRepository(in_memory_db)
        success, error, state = repo.get_device_state("nonexistent")
        assert success is True
        assert error is None
        assert state is None

    def test_get_device_state_db_error(self, mock_db_session):
        """Test getting state when database raises exception."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = DeviceRepository(mock_db_session)
        success, error, state = repo.get_device_state("dev1")
        assert success is False
        assert error is not None
        assert state is None

    def test_upsert_device_state_insert(self, in_memory_db):
        """Test upserting state for new device (insert)."""
        repo = DeviceRepository(in_memory_db)
        success, error, record = repo.upsert_device_state("dev1", "online")
        assert success is True
        assert error is None
        assert record is not None
        assert record.name == "dev1"
        assert record.state == "online"

    def test_upsert_device_state_update(self, in_memory_db):
        """Test upserting state for existing device (update)."""
        repo = DeviceRepository(in_memory_db)
        now = datetime.now()
        device = Device(
            name="dev1", state="offline", created_at=now, updated_at=now
        )
        in_memory_db.add(device)
        in_memory_db.commit()

        success, error, record = repo.upsert_device_state("dev1", "online")
        assert success is True
        assert error is None
        assert record.state == "online"

    def test_upsert_device_state_no_commit(self, in_memory_db):
        """Test upsert without auto commit."""
        repo = DeviceRepository(in_memory_db)
        success, error, record = repo.upsert_device_state(
            "dev1", "online", auto_commit=False
        )
        assert success is True
        # rollback to avoid affecting other tests
        in_memory_db.rollback()

    def test_upsert_device_state_error(self, mock_db_session):
        """Test upsert when database raises exception."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = DeviceRepository(mock_db_session)
        success, error, record = repo.upsert_device_state("dev1", "online")
        assert success is False
        assert error is not None
        assert record is None

    def test_load_all_device_states(self, in_memory_db):
        """Test loading all device states."""
        repo = DeviceRepository(in_memory_db)
        now = datetime.now()
        devices = [
            Device(
                name="dev1", state="online", created_at=now, updated_at=now
            ),
            Device(
                name="dev2", state="offline", created_at=now, updated_at=now
            ),
        ]
        for d in devices:
            in_memory_db.add(d)
        in_memory_db.commit()

        success, error, states = repo.load_all_device_states()
        assert success is True
        assert error is None
        assert states == {"dev1": "online", "dev2": "offline"}

    def test_load_all_device_states_empty(self, in_memory_db):
        """Test loading all device states when empty."""
        repo = DeviceRepository(in_memory_db)
        success, error, states = repo.load_all_device_states()
        assert success is True
        assert states == {}

    def test_load_all_device_states_error(self, mock_db_session):
        """Test loading all states when database raises exception."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = DeviceRepository(mock_db_session)
        success, error, states = repo.load_all_device_states()
        assert success is False
        assert error is not None
        assert states is None
