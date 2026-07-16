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
from sqlalchemy.orm import Session

from wy_qcos.db.models import Flavor
from wy_qcos.db.repositories import BaseRepository
from wy_qcos.db.repositories.flavor_device_group import (
    FlavorDeviceGroupRepository,
)

logger = logging.getLogger(__name__)


class FlavorRepository(BaseRepository):
    """Database operations for Flavor."""

    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    def create_flavor(self, flavor_data: dict):
        """Create a new flavor.

        Args:
            flavor_data: dict with name, description, is_public, properties.
                May contain 'device_groups' key (list of device group UUID
                strings) which will be used to create mapping records.

        Returns:
            (success, error, flavor_record)
        """
        try:
            # Extract device_groups before creating Flavor record
            device_group_ids = flavor_data.pop("device_groups", None)
            db_record = Flavor(**flavor_data)
            self._db_session.add(db_record)
            self._db_session.commit()
            self._db_session.refresh(db_record)

            # Create device group mappings if provided
            if device_group_ids:
                dg_repo = FlavorDeviceGroupRepository(self._db_session)
                ok, err = dg_repo.create_mappings(
                    str(db_record.id), device_group_ids
                )
                if not ok:
                    logger.error(
                        f"Failed to create device group mappings "
                        f"for flavor {db_record.id}: {err}"
                    )

            return True, None, db_record
        except Exception as e:
            self._db_session.rollback()
            return False, str(e), None

    def get_flavor_by_uuid(
        self, flavor_id: UUID | str, filters: dict | None = None
    ):
        """Get flavor by UUID.

        Args:
            flavor_id: flavor UUID
            filters: optional db filters for permission scoping

        Returns:
            (success, error, flavor_record)
        """
        return self.get_by_uuid(Flavor, str(flavor_id), filters=filters)

    def get_flavor_by_name(self, name: str):
        """Get flavor by name.

        Args:
            name: flavor name

        Returns:
            (success, error, flavor_record)
        """
        return self.get_by_attr(Flavor, "name", name)

    def get_visible_flavor_by_uuid(
        self, flavor_id: UUID | str, project_id: str | None = None
    ):
        """Get flavor by UUID with visibility scoping.

        A flavor is visible if it is public or belongs to the
        caller's project.

        Args:
            flavor_id: flavor UUID
            project_id: caller's project id for scoping

        Returns:
            (success, error, flavor_record)
        """
        try:
            query = select(Flavor).where(
                Flavor.id == str(flavor_id),
                or_(
                    Flavor.is_public.is_(True),
                    Flavor.project_id == project_id,
                ),
            )
            result = self._db_session.execute(query)
            flavor = result.scalars().first()
            if flavor is None:
                return True, None, None
            self._db_session.refresh(flavor)
            return True, None, flavor
        except Exception as e:
            return False, str(e), None

    def get_visible_flavors(self, project_id: str | None = None):
        """Get all flavors with visibility scoping.

        A flavor is visible if it is public or belongs to the
        caller's project.

        Args:
            project_id: caller's project id for scoping

        Returns:
            (success, error, list_of_flavors)
        """
        try:
            query = select(Flavor).where(
                or_(
                    Flavor.is_public.is_(True),
                    Flavor.project_id == project_id,
                )
            )
            result = self._db_session.execute(query)
            flavors = result.scalars().all()
            for f in flavors:
                try:
                    self._db_session.refresh(f)
                except Exception as e:
                    logger.debug(f"Refresh error for flavor: {e}")
            return True, None, flavors
        except Exception as e:
            return False, str(e), None

    def get_flavors(self, filters: dict | None = None):
        """Get all flavors with optional filtering.

        Args:
            filters: dict of filter conditions

        Returns:
            (success, error, list_of_flavors)
        """
        return self.get_all(Flavor, filters=filters)

    def delete_flavor(
        self, flavor_id: UUID | str, filters: dict | None = None
    ):
        """Delete flavor by UUID.

        Args:
            flavor_id: flavor UUID
            filters: optional db filters for permission scoping

        Returns:
            (success, error)
        """
        try:
            success, error, flavor = self.get_by_uuid(
                Flavor, str(flavor_id), filters=filters
            )
            if not success or flavor is None:
                return False, error or "Flavor not found"
            # Delete device group mappings before deleting flavor
            dg_repo = FlavorDeviceGroupRepository(self._db_session)
            dg_repo.delete_mappings_by_flavor(str(flavor_id))
            self._db_session.delete(flavor)
            self._db_session.commit()
            return True, None
        except Exception as e:
            self._db_session.rollback()
            return False, str(e)

    def update_flavor(
        self,
        flavor_id: UUID | str,
        flavor_data: dict,
        filters: dict | None = None,
    ):
        """Update flavor by UUID.

        Args:
            flavor_id: flavor UUID
            flavor_data: dict with fields to update. May contain
                'device_groups' key (list of device group UUID strings)
                which will replace existing mappings.
            filters: optional db filters for permission scoping

        Returns:
            (success, error, flavor_record)
        """
        try:
            success, error, flavor = self.get_by_uuid(
                Flavor, str(flavor_id), filters=filters
            )
            if not success or flavor is None:
                return False, error or "Flavor not found", None
            # Extract device_groups before updating flavor fields
            device_group_ids = flavor_data.pop("device_groups", None)
            for key, value in flavor_data.items():
                if hasattr(flavor, key):
                    setattr(flavor, key, value)
            self._db_session.commit()
            self._db_session.refresh(flavor)

            # Replace device group mappings if provided
            if device_group_ids is not None:
                dg_repo = FlavorDeviceGroupRepository(self._db_session)
                ok, err = dg_repo.replace_mappings(
                    str(flavor.id), device_group_ids
                )
                if not ok:
                    logger.error(
                        f"Failed to replace device group mappings "
                        f"for flavor {flavor.id}: {err}"
                    )

            return True, None, flavor
        except Exception as e:
            self._db_session.rollback()
            return False, str(e), None
