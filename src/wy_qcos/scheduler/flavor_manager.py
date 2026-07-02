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

from wy_qcos.db.models import Flavor
from wy_qcos.db.repositories.flavor import FlavorRepository
from wy_qcos.db.utils.db_utils import create_db_session
from wy_qcos.scheduler.errors import FlavorNotFoundError

logger = logging.getLogger(__name__)


class FlavorManager:
    """Flavor manager for preset scheduling policies.

    Manages CRUD operations on Flavor records and provides
    lookup for scheduling.
    """

    def __init__(self, db_engine):
        """Init FlavorManager.

        Args:
            db_engine: SQLAlchemy database engine
        """
        self._db_engine = db_engine

    def get_flavor(self, flavor_id: str) -> Flavor | None:
        """Get flavor by ID.

        Args:
            flavor_id: flavor UUID string

        Returns:
            Flavor instance or None if not found.

        Raises:
            FlavorNotFoundError: if flavor_id is invalid
        """
        if not flavor_id:
            return None

        with create_db_session(self._db_engine) as db_session:
            repo = FlavorRepository(db_session)
            success, error, flavor = repo.get_flavor_by_uuid(flavor_id)
            if not success:
                logger.error(f"Failed to get flavor {flavor_id}: {error}")
                return None
            if flavor is None:
                logger.warning(f"Flavor not found: {flavor_id}")
                return None
            return flavor

    def get_flavor_specs(self, flavor_id: str) -> dict:
        """Get flavor specs by ID.

        Args:
            flavor_id: flavor UUID string

        Returns:
            flavor specs dict, empty if flavor not found.

        Raises:
            FlavorNotFoundError: if flavor_id is specified but not found
        """
        if not flavor_id:
            return {}
        flavor = self.get_flavor(flavor_id)
        if flavor is None:
            raise FlavorNotFoundError(f"Flavor not found: {flavor_id}")
        return flavor.specs or {}

    def get_flavors(self, public_only: bool = False) -> list[Flavor]:
        """Get all flavors.

        Args:
            public_only: if True, only return public flavors

        Returns:
            list of Flavor instances
        """
        with create_db_session(self._db_engine) as db_session:
            repo = FlavorRepository(db_session)
            if public_only:
                success, _, flavors = repo.get_public_flavors()
            else:
                success, _, flavors = repo.get_flavors()
            if not success:
                return []
            return flavors or []

    def create_flavor(self, flavor_data: dict):
        """Create a new flavor.

        Args:
            flavor_data: dict with name, description, is_public, specs

        Returns:
            (success, error, flavor_record)
        """
        with create_db_session(self._db_engine) as db_session:
            repo = FlavorRepository(db_session)
            return repo.create_flavor(flavor_data)

    def delete_flavor(self, flavor_id: str):
        """Delete flavor by ID.

        Args:
            flavor_id: flavor UUID string

        Returns:
            (success, error)
        """
        with create_db_session(self._db_engine) as db_session:
            repo = FlavorRepository(db_session)
            return repo.delete_flavor(flavor_id)
