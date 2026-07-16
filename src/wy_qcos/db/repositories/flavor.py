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

from sqlalchemy.orm import Session

from wy_qcos.db.models import Flavor
from wy_qcos.db.repositories import BaseRepository

logger = logging.getLogger(__name__)


class FlavorRepository(BaseRepository):
    """Database operations for Flavor."""

    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    def create_flavor(self, flavor_data: dict):
        """Create a new flavor.

        Args:
            flavor_data: dict with name, description, is_public, specs

        Returns:
            (success, error, flavor_record)
        """
        try:
            db_record = Flavor(**flavor_data)
            self._db_session.add(db_record)
            self._db_session.commit()
            self._db_session.refresh(db_record)
            return True, None, db_record
        except Exception as e:
            self._db_session.rollback()
            return False, str(e), None

    def get_flavor_by_uuid(self, flavor_id: UUID | str):
        """Get flavor by UUID.

        Args:
            flavor_id: flavor UUID

        Returns:
            (success, error, flavor_record)
        """
        return self.get_by_uuid(Flavor, str(flavor_id))

    def get_flavor_by_name(self, name: str):
        """Get flavor by name.

        Args:
            name: flavor name

        Returns:
            (success, error, flavor_record)
        """
        return self.get_by_attr(Flavor, "name", name)

    def get_flavors(self, filters: dict | None = None):
        """Get all flavors with optional filtering.

        Args:
            filters: dict of filter conditions

        Returns:
            (success, error, list_of_flavors)
        """
        return self.get_all(Flavor, filters=filters)

    def get_public_flavors(self):
        """Get all public flavors.

        Returns:
            (success, error, list_of_flavors)
        """
        return self.get_all(Flavor, filters={"is_public": True})

    def delete_flavor(self, flavor_id: UUID | str):
        """Delete flavor by UUID.

        Args:
            flavor_id: flavor UUID

        Returns:
            (success, error)
        """
        try:
            success, error, flavor = self.get_by_uuid(Flavor, str(flavor_id))
            if not success or flavor is None:
                return False, error or "Flavor not found"
            self._db_session.delete(flavor)
            self._db_session.commit()
            return True, None
        except Exception as e:
            self._db_session.rollback()
            return False, str(e)

    def get_jobs_count_by_flavor(self, flavor_id: UUID | str) -> int:
        """Count jobs using a specific flavor.

        Args:
            flavor_id: flavor UUID

        Returns:
            job count
        """
        return self.count_by_attr(Flavor, "id", flavor_id)
