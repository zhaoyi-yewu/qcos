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

import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from wy_qcos.db.models import FlavorDeviceGroup
from wy_qcos.db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class FlavorDeviceGroupRepository(BaseRepository):
    """Database operations for FlavorDeviceGroup mapping table."""

    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    def create_mappings(self, flavor_id: str, device_group_ids: list[str]):
        """Create mapping records for a flavor.

        Args:
            flavor_id: flavor UUID string
            device_group_ids: list of device group UUID strings

        Returns:
            (success, error)
        """
        try:
            for dg_id in device_group_ids:
                mapping = FlavorDeviceGroup(
                    id=str(uuid.uuid4()),
                    flavor_id=str(flavor_id),
                    device_group_id=str(dg_id),
                )
                self._db_session.add(mapping)
            self._db_session.commit()
            return True, None
        except Exception as e:
            self._db_session.rollback()
            return False, str(e)

    def delete_mappings_by_flavor(self, flavor_id: str):
        """Delete all mapping records for a flavor.

        Args:
            flavor_id: flavor UUID string

        Returns:
            (success, error)
        """
        try:
            self._db_session.execute(
                delete(FlavorDeviceGroup).where(
                    FlavorDeviceGroup.flavor_id == str(flavor_id)
                )
            )
            self._db_session.commit()
            return True, None
        except Exception as e:
            self._db_session.rollback()
            return False, str(e)

    def delete_mappings_by_device_group(self, device_group_id: str):
        """Delete all mapping records for a device group.

        Args:
            device_group_id: device group UUID string

        Returns:
            (success, error)
        """
        try:
            self._db_session.execute(
                delete(FlavorDeviceGroup).where(
                    FlavorDeviceGroup.device_group_id == str(device_group_id)
                )
            )
            self._db_session.commit()
            return True, None
        except Exception as e:
            self._db_session.rollback()
            return False, str(e)

    def get_device_group_ids_by_flavor(self, flavor_id: str):
        """Get device group IDs associated with a flavor.

        Args:
            flavor_id: flavor UUID string

        Returns:
            (success, error, list_of_device_group_ids)
        """
        try:
            result = self._db_session.execute(
                select(FlavorDeviceGroup.device_group_id).where(
                    FlavorDeviceGroup.flavor_id == str(flavor_id)
                )
            )
            ids = [str(row[0]) for row in result]
            return True, None, ids
        except Exception as e:
            return False, str(e), []

    def get_flavor_ids_by_device_group(self, device_group_id: str):
        """Get flavor IDs associated with a device group.

        Args:
            device_group_id: device group UUID string

        Returns:
            (success, error, list_of_flavor_ids)
        """
        try:
            result = self._db_session.execute(
                select(FlavorDeviceGroup.flavor_id).where(
                    FlavorDeviceGroup.device_group_id == str(device_group_id)
                )
            )
            ids = [str(row[0]) for row in result]
            return True, None, ids
        except Exception as e:
            return False, str(e), []

    def get_flavor_count_by_device_group(self, device_group_id: str):
        """Count flavors referencing a device group.

        Args:
            device_group_id: device group UUID string

        Returns:
            (success, error, count)
        """
        try:
            result = self._db_session.execute(
                select(FlavorDeviceGroup).where(
                    FlavorDeviceGroup.device_group_id == str(device_group_id)
                )
            )
            count = len(result.fetchall())
            return True, None, count
        except Exception as e:
            return False, str(e), 0

    def replace_mappings(self, flavor_id: str, device_group_ids: list[str]):
        """Replace all mapping records for a flavor.

        Deletes existing mappings and creates new ones.

        Args:
            flavor_id: flavor UUID string
            device_group_ids: list of device group UUID strings

        Returns:
            (success, error)
        """
        try:
            # Delete existing mappings
            self._db_session.execute(
                delete(FlavorDeviceGroup).where(
                    FlavorDeviceGroup.flavor_id == str(flavor_id)
                )
            )
            # Create new mappings
            for dg_id in device_group_ids:
                mapping = FlavorDeviceGroup(
                    id=str(uuid.uuid4()),
                    flavor_id=str(flavor_id),
                    device_group_id=str(dg_id),
                )
                self._db_session.add(mapping)
            self._db_session.commit()
            return True, None
        except Exception as e:
            self._db_session.rollback()
            return False, str(e)
