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
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from wy_qcos.db.models import DeviceGroup
from wy_qcos.db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class DeviceGroupRepository(BaseRepository):
    """Database operations for DeviceGroup."""

    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    def create_device_group(self, group_data: dict):
        """Create a new device group.

        Args:
            group_data: dict with name, description, device_names,
                is_public, project_id

        Returns:
            (success, error, group_record)
        """
        try:
            db_record = DeviceGroup(**group_data)
            self._db_session.add(db_record)
            self._db_session.commit()
            self._db_session.refresh(db_record)
            return True, None, db_record
        except Exception as e:
            self._db_session.rollback()
            return False, str(e), None

    def get_device_group_by_uuid(
        self, group_id: UUID | str, filters: dict | None = None
    ):
        """Get device group by UUID.

        Args:
            group_id: device group UUID
            filters: optional db filters for permission scoping

        Returns:
            (success, error, group_record)
        """
        return self.get_by_uuid(DeviceGroup, str(group_id), filters=filters)

    def get_device_group_by_name(self, name: str):
        """Get device group by name.

        Args:
            name: device group name

        Returns:
            (success, error, group_record)
        """
        return self.get_by_attr(DeviceGroup, "name", name)

    def get_visible_device_group_by_uuid(
        self, group_id: UUID | str, project_id: str | None = None
    ):
        """Get device group by UUID with visibility scoping.

        A group is visible if it is public or belongs to the
        caller's project.

        Args:
            group_id: device group UUID
            project_id: caller's project id for scoping

        Returns:
            (success, error, group_record)
        """
        try:
            query = select(DeviceGroup).where(
                DeviceGroup.id == str(group_id),
                or_(
                    DeviceGroup.is_public.is_(True),
                    DeviceGroup.project_id == project_id,
                ),
            )
            result = self._db_session.execute(query)
            group = result.scalars().first()
            if group is None:
                return True, None, None
            self._db_session.refresh(group)
            return True, None, group
        except Exception as e:
            return False, str(e), None

    def get_visible_device_groups(self, project_id: str | None = None):
        """Get all device groups with visibility scoping.

        A group is visible if it is public or belongs to the
        caller's project.

        Args:
            project_id: caller's project id for scoping

        Returns:
            (success, error, list_of_groups)
        """
        try:
            query = select(DeviceGroup).where(
                or_(
                    DeviceGroup.is_public.is_(True),
                    DeviceGroup.project_id == project_id,
                )
            )
            result = self._db_session.execute(query)
            groups = result.scalars().all()
            for g in groups:
                try:
                    self._db_session.refresh(g)
                except Exception as e:
                    logger.debug(f"Refresh error for group: {e}")
            return True, None, groups
        except Exception as e:
            return False, str(e), None

    def get_device_groups(self, filters: dict | None = None):
        """Get all device groups with optional filtering.

        Args:
            filters: dict of filter conditions

        Returns:
            (success, error, list_of_groups)
        """
        return self.get_all(DeviceGroup, filters=filters)

    def delete_device_group(
        self, group_id: UUID | str, filters: dict | None = None
    ):
        """Delete device group by UUID.

        Args:
            group_id: device group UUID
            filters: optional db filters for permission scoping

        Returns:
            (success, error)
        """
        try:
            success, error, group = self.get_by_uuid(
                DeviceGroup, str(group_id), filters=filters
            )
            if not success or group is None:
                return False, error or "Device group not found"
            self._db_session.delete(group)
            self._db_session.commit()
            return True, None
        except IntegrityError:
            self._db_session.rollback()
            # check for foreign key constraint violation
            return False, (
                "Flavor is still referenced by other resources (e.g. flavors) "
                "and cannot be deleted."
            )
        except Exception as e:
            self._db_session.rollback()
            # check for foreign key constraint violation
            # (e.g. device group still referenced by flavors)
            err_str = str(e)
            if (
                "foreign key constraint" in err_str
                or "violates foreign key" in err_str
                or "23503" in err_str
            ):
                return False, (
                    "Device group is still referenced by "
                    "other resources (e.g. flavors) and "
                    "cannot be deleted"
                )
            return False, err_str

    def update_device_group(
        self,
        group_id: UUID | str,
        group_data: dict,
        filters: dict | None = None,
    ):
        """Update device group by UUID.

        Args:
            group_id: device group UUID
            group_data: dict with fields to update
            filters: optional db filters for permission scoping

        Returns:
            (success, error, group_record)
        """
        try:
            success, error, group = self.get_by_uuid(
                DeviceGroup, str(group_id), filters=filters
            )
            if not success or group is None:
                return (
                    False,
                    error or "Device group not found",
                    None,
                )
            for key, value in group_data.items():
                if hasattr(group, key):
                    setattr(group, key, value)
            self._db_session.commit()
            self._db_session.refresh(group)
            return True, None, group
        except Exception as e:
            self._db_session.rollback()
            return False, str(e), None
