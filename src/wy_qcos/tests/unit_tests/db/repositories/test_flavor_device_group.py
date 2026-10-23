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

"""Unit tests for FlavorDeviceGroupRepository."""

import uuid

from wy_qcos.db.models import FlavorDeviceGroup
from wy_qcos.db.repositories.flavor_device_group import (
    FlavorDeviceGroupRepository,
)


class TestFlavorDeviceGroupRepository:
    """Test FlavorDeviceGroupRepository class."""

    def test_create_mappings_success(self, in_memory_db):
        """Test creating mappings successfully."""
        repo = FlavorDeviceGroupRepository(in_memory_db)
        flavor_id = str(uuid.uuid4())
        dg_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        success, error = repo.create_mappings(flavor_id, dg_ids)
        assert success is True
        assert error is None

        # Verify records were created
        from sqlalchemy import select

        q = select(FlavorDeviceGroup).where(
            FlavorDeviceGroup.flavor_id == flavor_id
        )
        records = in_memory_db.execute(q).scalars().all()
        assert len(records) == 2

    def test_create_mappings_empty_list(self, in_memory_db):
        """Test creating mappings with empty list."""
        repo = FlavorDeviceGroupRepository(in_memory_db)
        success, error = repo.create_mappings(str(uuid.uuid4()), [])
        assert success is True

    def test_create_mappings_error(self, mock_db_session):
        """Test creating mappings with database error."""
        mock_db_session.commit.side_effect = Exception("DB error")
        repo = FlavorDeviceGroupRepository(mock_db_session)
        success, error = repo.create_mappings(
            str(uuid.uuid4()), [str(uuid.uuid4())]
        )
        assert success is False
        assert "DB error" in error

    def test_delete_mappings_by_flavor_success(self, in_memory_db):
        """Test deleting mappings by flavor successfully."""
        repo = FlavorDeviceGroupRepository(in_memory_db)
        flavor_id = str(uuid.uuid4())
        mapping = FlavorDeviceGroup(
            id=str(uuid.uuid4()),
            flavor_id=flavor_id,
            device_group_id=str(uuid.uuid4()),
        )
        in_memory_db.add(mapping)
        in_memory_db.commit()

        success, error = repo.delete_mappings_by_flavor(flavor_id)
        assert success is True

        # Verify deletion
        from sqlalchemy import select

        q = select(FlavorDeviceGroup).where(
            FlavorDeviceGroup.flavor_id == flavor_id
        )
        assert in_memory_db.execute(q).scalars().first() is None

    def test_delete_mappings_by_flavor_error(self, mock_db_session):
        """Test deleting mappings by flavor with database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = FlavorDeviceGroupRepository(mock_db_session)
        success, error = repo.delete_mappings_by_flavor(str(uuid.uuid4()))
        assert success is False
        assert "DB error" in error

    def test_delete_mappings_by_device_group_success(self, in_memory_db):
        """Test deleting mappings by device group successfully."""
        repo = FlavorDeviceGroupRepository(in_memory_db)
        dg_id = str(uuid.uuid4())
        mapping = FlavorDeviceGroup(
            id=str(uuid.uuid4()),
            flavor_id=str(uuid.uuid4()),
            device_group_id=dg_id,
        )
        in_memory_db.add(mapping)
        in_memory_db.commit()

        success, error = repo.delete_mappings_by_device_group(dg_id)
        assert success is True

        # Verify deletion
        from sqlalchemy import select

        q = select(FlavorDeviceGroup).where(
            FlavorDeviceGroup.device_group_id == dg_id
        )
        assert in_memory_db.execute(q).scalars().first() is None

    def test_delete_mappings_by_device_group_error(self, mock_db_session):
        """Test deleting mappings by device group with database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = FlavorDeviceGroupRepository(mock_db_session)
        success, error = repo.delete_mappings_by_device_group(
            str(uuid.uuid4())
        )
        assert success is False
        assert "DB error" in error

    def test_get_device_group_ids_by_flavor_success(self, in_memory_db):
        """Test getting device group IDs by flavor."""
        repo = FlavorDeviceGroupRepository(in_memory_db)
        flavor_id = str(uuid.uuid4())
        dg_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        for dg_id in dg_ids:
            mapping = FlavorDeviceGroup(
                id=str(uuid.uuid4()),
                flavor_id=flavor_id,
                device_group_id=dg_id,
            )
            in_memory_db.add(mapping)
        in_memory_db.commit()

        success, error, result = repo.get_device_group_ids_by_flavor(flavor_id)
        assert success is True
        assert len(result) == 2

    def test_get_device_group_ids_by_flavor_empty(self, in_memory_db):
        """Test getting device group IDs for flavor with no mappings."""
        repo = FlavorDeviceGroupRepository(in_memory_db)
        success, error, result = repo.get_device_group_ids_by_flavor(
            str(uuid.uuid4())
        )
        assert success is True
        assert result == []

    def test_get_device_group_ids_by_flavor_error(self, mock_db_session):
        """Test getting device group IDs with database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = FlavorDeviceGroupRepository(mock_db_session)
        success, error, result = repo.get_device_group_ids_by_flavor(
            str(uuid.uuid4())
        )
        assert success is False
        assert "DB error" in error
        assert result == []
