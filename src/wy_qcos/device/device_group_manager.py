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

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.db.models import DeviceGroup
from wy_qcos.db.repositories.device_group import (
    DeviceGroupRepository,
)
from wy_qcos.db.utils.db_utils import create_db_session

logger = logging.getLogger(__name__)


# Default preset device groups.
DEFAULT_DEVICE_GROUP_QC_NONE = "qc.none"
DEFAULT_DEVICE_GROUP_QC_ALL = "qc.all"
DEFAULT_DEVICE_GROUP_QC_REAL = "qc.real"
DEFAULT_DEVICE_GROUP_QC_SIM = "qc.sim"
DEFAULT_DEVICE_GROUP_QC_QUBO = "qc.qubo"

DEFAULT_DEVICE_GROUPS = [
    {
        "id": "00000000-0000-4000-8000-000000000001",
        "name": DEFAULT_DEVICE_GROUP_QC_ALL,
        "project_id": Constant.ADMIN_PROJECT_ID,
        "description": "all quantum computers (real and simulators)",
        "is_public": True,
        "device_names": [Constant.DEVICE_GROUP_DN_ALL],
    },
    {
        "id": "00000000-0000-4000-8000-000000000002",
        "name": DEFAULT_DEVICE_GROUP_QC_REAL,
        "project_id": Constant.ADMIN_PROJECT_ID,
        "description": "all quantum computers (real)",
        "is_public": True,
        "device_names": None,
    },
    {
        "id": "00000000-0000-4000-8000-000000000003",
        "name": DEFAULT_DEVICE_GROUP_QC_NONE,
        "project_id": Constant.ADMIN_PROJECT_ID,
        "description": (
            "no quantum computers (extra_property: "
            "'qc:devices' must be specified explicitly)"
        ),
        "is_public": True,
        "device_names": [],
    },
    {
        "id": "00000000-0000-4000-8000-100000000001",
        "name": DEFAULT_DEVICE_GROUP_QC_SIM,
        "project_id": Constant.ADMIN_PROJECT_ID,
        "description": "all quantum computers (simulators)",
        "is_public": True,
        "device_names": ["qutip_sim"],
    },
    {
        "id": "00000000-0000-4000-8000-200000000001",
        "name": DEFAULT_DEVICE_GROUP_QC_QUBO,
        "project_id": Constant.ADMIN_PROJECT_ID,
        "description": "all QUBO solvers",
        "is_public": True,
        "device_names": None,
    },
]


class DeviceGroupManager:
    """Device group manager for logical device classification.

    Manages CRUD operations on DeviceGroup records and provides
    device name lookup by group for scheduling.
    """

    def __init__(self, db_engine):
        """Init DeviceGroupManager.

        Args:
            db_engine: SQLAlchemy database engine
        """
        self._db_engine = db_engine
        self.init_db()

    def init_db(self):
        """Init database with default device groups (idempotent).

        Creates default device groups if they do not already exist.
        Safe to run multiple times.
        """
        now = Library.get_current_datetime()
        for group_data in DEFAULT_DEVICE_GROUPS:
            group_id = group_data["id"]
            with create_db_session(self._db_engine) as db_session:
                repo = DeviceGroupRepository(db_session)
                success, _, existing = repo.get_device_group_by_uuid(group_id)
                if success and existing is not None:
                    logger.info(
                        f"Default device group already exists: "
                        f"{group_data['name']} (id: {group_id})"
                    )
                    continue
                group_data["created_at"] = now
                group_data["updated_at"] = now
                success, error, _ = repo.create_device_group(group_data)
                if not success:
                    logger.error(
                        f"Failed to create default device group "
                        f"{group_data['name']} (id: {group_id}): "
                        f"{error}"
                    )
                else:
                    logger.info(
                        f"Created default device group: "
                        f"{group_data['name']} (id: {group_id})"
                    )

    def get_device_group(self, group_id: str) -> DeviceGroup | None:
        """Get device group by ID.

        Args:
            group_id: device group UUID string

        Returns:
            DeviceGroup instance or None if not found.
        """
        if not group_id:
            return None

        with create_db_session(self._db_engine) as db_session:
            repo = DeviceGroupRepository(db_session)
            success, error, group = repo.get_device_group_by_uuid(group_id)
            if not success:
                logger.error(f"Failed to get device group {group_id}: {error}")
                return None
            if group is None:
                logger.warning(f"Device group not found: {group_id}")
                return None
            return group

    def get_device_group_by_name(self, name: str) -> DeviceGroup | None:
        """Get device group by name.

        Args:
            name: device group name

        Returns:
            DeviceGroup instance or None if not found.
        """
        if not name:
            return None

        with create_db_session(self._db_engine) as db_session:
            repo = DeviceGroupRepository(db_session)
            success, error, group = repo.get_device_group_by_name(name)
            if not success:
                logger.error(
                    f"Failed to get device group by name {name}: {error}"
                )
                return None
            if group is None:
                logger.warning(f"Device group not found by name: {name}")
                return None
            return group

    def get_visible_device_group(
        self, group_id: str, project_id: str | None = None
    ) -> DeviceGroup | None:
        """Get device group by ID with visibility scoping.

        A group is visible if it is public or belongs to the
        caller's project.

        Args:
            group_id: device group UUID string
            project_id: caller's project id for scoping

        Returns:
            DeviceGroup instance or None if not found/visible.
        """
        if not group_id:
            return None

        with create_db_session(self._db_engine) as db_session:
            repo = DeviceGroupRepository(db_session)
            success, error, group = repo.get_visible_device_group_by_uuid(
                group_id, project_id=project_id
            )
            if not success:
                logger.error(f"Failed to get device group {group_id}: {error}")
                return None
            if group is None:
                logger.warning(f"Device group not found/visible: {group_id}")
                return None
            return group

    @staticmethod
    def _normalize_filter_names(filters):
        """Normalize group_name/group_names filters into a list.

        Prefers group_names (list) over group_name (str) for
        backward compatibility.

        Args:
            filters: dict of filter conditions or None

        Returns:
            list of names, empty if none specified.
        """
        if not filters:
            return []
        if filters.get("group_names"):
            return list(filters["group_names"])
        if filters.get("group_name"):
            return [filters["group_name"]]
        return []

    def get_device_groups(
        self, filters: dict | None = None
    ) -> list[DeviceGroup]:
        """Get all device groups with optional filtering.

        Args:
            filters: dict of filter conditions. Supported keys:
                - group_names: list of group names to filter by (in-memory)
                - group_name: single group name to filter by (in-memory)
                - group_ids: list of group UUIDs (DB-level IN query)

        Returns:
            list of DeviceGroup instances
        """
        with create_db_session(self._db_engine) as db_session:
            repo = DeviceGroupRepository(db_session)
            # Extract group_ids for DB-level filtering; group_names
            # is applied in-memory (not a direct model column key).
            db_filters = None
            if filters and filters.get("group_ids"):
                db_filters = {"id": filters["group_ids"]}
            success, _, groups = repo.get_device_groups(filters=db_filters)
            if not success:
                return []
            groups = groups or []
            names = self._normalize_filter_names(filters)
            if names:
                groups = [g for g in groups if g.name in names]
            return groups

    def get_visible_device_groups(
        self,
        filters: dict | None = None,
        project_id: str | None = None,
    ) -> list[DeviceGroup]:
        """Get visible device groups with optional filtering.

        A group is visible if it is public or belongs to the
        caller's project.

        Args:
            filters: dict of filter conditions. Supported keys:
                - group_names: list of group names to filter by (in-memory)
                - group_name: single group name to filter by (in-memory)
                - group_ids: list of group UUIDs (in-memory)
            project_id: caller's project id for scoping

        Returns:
            list of DeviceGroup instances
        """
        with create_db_session(self._db_engine) as db_session:
            repo = DeviceGroupRepository(db_session)
            success, _, groups = repo.get_visible_device_groups(
                project_id=project_id
            )
            if not success:
                return []
            groups = groups or []
            # apply group_ids filter if specified (in-memory)
            if filters and filters.get("group_ids"):
                ids_set = {str(gid) for gid in filters["group_ids"]}
                groups = [g for g in groups if str(g.id) in ids_set]
            names = self._normalize_filter_names(filters)
            if names:
                groups = [g for g in groups if g.name in names]
            return groups

    def create_device_group(self, group_data: dict):
        """Create a new device group.

        Args:
            group_data: dict with name, description, device_names,
                is_public, project_id

        Returns:
            (success, error, group_record)
        """
        with create_db_session(self._db_engine) as db_session:
            repo = DeviceGroupRepository(db_session)
            return repo.create_device_group(group_data)

    def update_device_group(
        self,
        group_id: str,
        group_data: dict,
        db_filters: dict | None = None,
    ):
        """Update device group by ID.

        Args:
            group_id: device group UUID string
            group_data: dict with fields to update
            db_filters: optional db filters for permission scoping

        Returns:
            (success, error, group_record)
        """
        with create_db_session(self._db_engine) as db_session:
            repo = DeviceGroupRepository(db_session)
            return repo.update_device_group(
                group_id, group_data, filters=db_filters
            )

    def delete_device_group(
        self, group_id: str, db_filters: dict | None = None
    ):
        """Delete device group by ID.

        Args:
            group_id: device group UUID string
            db_filters: optional db filters for permission scoping

        Returns:
            (success, error)
        """
        with create_db_session(self._db_engine) as db_session:
            repo = DeviceGroupRepository(db_session)
            return repo.delete_device_group(group_id, filters=db_filters)

    def delete_device_groups(
        self,
        group_ids: list[str],
        db_filters: dict | None = None,
        flavor_manager=None,
    ) -> list[tuple[str, bool, str | None]]:
        """Delete multiple device groups by IDs (batch).

        Iterates over each group_id, checks flavor references (if
        flavor_manager provided), deletes it independently, and
        collects per-group results. Does not abort on individual
        failures.

        Args:
            group_ids: list of device group UUID strings
            db_filters: optional db filters for permission scoping
            flavor_manager: optional FlavorManager instance; when
                provided, device groups referenced by flavors are
                not deleted and an error message is returned

        Returns:
            list of (group_id, success, error) tuples
        """
        results: list[tuple[str, bool, str | None]] = []
        for group_id in group_ids:
            # Check flavor references if flavor_manager available
            if flavor_manager is not None:
                group = self.get_device_group(group_id)
                if group is not None:
                    flavor_ids = flavor_manager.get_flavor_ids_by_device_group(
                        group_id
                    )
                    if flavor_ids:
                        flavor_names = []
                        for fid in flavor_ids:
                            f = flavor_manager.get_flavor(fid)
                            if f is not None:
                                flavor_names.append(f.name)
                        names_str = (
                            ", ".join(flavor_names)
                            if flavor_names
                            else str(flavor_ids)
                        )
                        results.append((
                            group_id,
                            False,
                            f"Device group '{group.name}' is "
                            f"referenced by flavor(s): "
                            f"{names_str}. Must remove the "
                            f"device group from the flavor(s) "
                            f"before deleting the device group.",
                        ))
                        continue
            success, error = self.delete_device_group(
                group_id, db_filters=db_filters
            )
            results.append((group_id, success, error if not success else None))
        return results

    def get_device_names_by_group(self, group_name_or_id: str) -> list[str]:
        """Get device names belonging to a group.

        Resolves the group by name or UUID and returns the
        device_names list.

        Args:
            group_name_or_id: device group name or UUID string

        Returns:
            list of device name strings, empty if group not found.
        """
        if not group_name_or_id:
            return []

        # try UUID first
        group = None
        try:
            UUID(group_name_or_id)
            group = self.get_device_group(group_name_or_id)
        except ValueError:
            group = self.get_device_group_by_name(group_name_or_id)

        if group is None:
            logger.warning(f"Device group not found: {group_name_or_id}")
            return []

        return group.device_names or []
