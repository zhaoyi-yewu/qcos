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
import uuid

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.db.models import Flavor
from wy_qcos.db.repositories.flavor import FlavorRepository
from wy_qcos.scheduler.filters.device_group import (
    DEVICE_GROUP_SPEC_KEY,
)
from wy_qcos.db.repositories.flavor_device_group import (
    FlavorDeviceGroupRepository,
)
from wy_qcos.db.utils.db_utils import create_db_session
from wy_qcos.flavor.errors import FlavorNotFoundError

logger = logging.getLogger(__name__)


# Default preset device group IDs (matching DEFAULT_DEVICE_GROUPS).
DEFAULT_DEVICE_GROUP_QC_ALL_ID = "00000000-0000-4000-8000-000000000001"
DEFAULT_DEVICE_GROUP_QC_REAL_ID = "00000000-0000-4000-8000-000000000002"
DEFAULT_DEVICE_GROUP_QC_SIM_ID = "00000000-0000-4000-8000-100000000001"
DEFAULT_DEVICE_GROUP_QC_QUBO_ID = "00000000-0000-4000-8000-200000000001"

# Default preset flavor names.
DEFAULT_FLAVOR_G1_ALL = "g1.all"
DEFAULT_FLAVOR_R1_ALL = "r1.all"
DEFAULT_FLAVOR_RH1_ALL = "rh1.all"
DEFAULT_FLAVOR_S1_ALL = "s1.all"
DEFAULT_FLAVOR_Q1_ALL = "q1.all"

DEFAULT_FLAVORS = [
    {
        "id": "00000000-0000-4000-8000-000000000001",
        "name": DEFAULT_FLAVOR_G1_ALL,
        "project_id": Constant.ADMIN_PROJECT_ID,
        "description": "all quantum computers (real and simulators)",
        "is_public": True,
        "min_qubits": 1,
        "device_groups": [DEFAULT_DEVICE_GROUP_QC_ALL_ID],
    },
    {
        "id": "00000000-0000-4000-8000-000000000002",
        "name": DEFAULT_FLAVOR_R1_ALL,
        "project_id": Constant.ADMIN_PROJECT_ID,
        "description": "all quantum computers (real)",
        "is_public": True,
        "min_qubits": 1,
        "gate_fidelity_1q_min": 0.99,
        "gate_fidelity_2q_min": 0.99,
        "device_groups": [DEFAULT_DEVICE_GROUP_QC_REAL_ID],
    },
    {
        "id": "00000000-0000-4000-8000-000000000003",
        "name": DEFAULT_FLAVOR_RH1_ALL,
        "project_id": Constant.ADMIN_PROJECT_ID,
        "description": "all quantum computers (real) with high fidelity>=0.99",
        "is_public": True,
        "min_qubits": 1,
        "gate_fidelity_1q_min": 0.99,
        "gate_fidelity_2q_min": 0.99,
        "device_groups": [DEFAULT_DEVICE_GROUP_QC_REAL_ID],
    },
    {
        "id": "00000000-0000-4000-8000-100000000001",
        "name": DEFAULT_FLAVOR_S1_ALL,
        "project_id": Constant.ADMIN_PROJECT_ID,
        "description": "all quantum computers (simulators)",
        "is_public": True,
        "min_qubits": 1,
        "device_groups": [DEFAULT_DEVICE_GROUP_QC_SIM_ID],
    },
    {
        "id": "00000000-0000-4000-8000-200000000001",
        "name": DEFAULT_FLAVOR_Q1_ALL,
        "project_id": Constant.ADMIN_PROJECT_ID,
        "description": "all QUBO solvers",
        "is_public": True,
        "min_qubits": 1,
        "device_groups": [DEFAULT_DEVICE_GROUP_QC_QUBO_ID],
    },
]

# Flavor extra_properties allowed fields.
# Keys must be in 'namespace:name' format.
# supported source code types. (eg., qasm,qasm2,qasm3)
EXTRA_PROPERTY_QC_CODE_TYPES = "qc:code_types"
# explicit option allows any other devices (e.g., dummy,qutip)
EXTRA_PROPERTY_QC_DEVICES = "qc:devices"
# explicit option excludes devices (e.g., dummy,qutip)
EXTRA_PROPERTY_QC_EXCLUDE_DEVICES = "qc:exclude_devices"
# device availability. (eg., 0.99)
EXTRA_PROPERTY_QC_DEVICE_AVAILABILITY = "qc:device_availability"
# tech types. (eg., superconducting,ion_trap)
EXTRA_PROPERTY_QC_TECH_TYPES = "qc:tech_types"

EXTRA_PROPERTIES_ALLOWED_FIELDS = [
    EXTRA_PROPERTY_QC_CODE_TYPES,
    EXTRA_PROPERTY_QC_DEVICES,
    EXTRA_PROPERTY_QC_EXCLUDE_DEVICES,
    EXTRA_PROPERTY_QC_DEVICE_AVAILABILITY,
    EXTRA_PROPERTY_QC_TECH_TYPES,
]


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
        self.init_db()

    def init_db(self):
        """Init database with default preset flavors (idempotent).

        Creates default preset flavors if they do not already exist.
        Safe to run multiple times.
        """
        now = Library.get_current_datetime()
        for flavor_data in DEFAULT_FLAVORS:
            flavor_id = flavor_data["id"]
            with create_db_session(self._db_engine) as db_session:
                repo = FlavorRepository(db_session)
                success, _, existing = repo.get_flavor_by_uuid(flavor_id)
                if success and existing is not None:
                    logger.info(
                        f"Default flavor already exists: "
                        f"{flavor_data['name']} (id: {flavor_id})"
                    )
                    continue
                flavor_data["created_at"] = now
                flavor_data["updated_at"] = now
                success, error, _ = repo.create_flavor(flavor_data)
                if not success:
                    logger.error(
                        f"Failed to create default flavor "
                        f"{flavor_data['name']} (id: {flavor_id}): "
                        f"{error}"
                    )
                else:
                    logger.info(
                        f"Created default flavor: "
                        f"{flavor_data['name']} (id: {flavor_id})"
                    )

    def validate_extra_properties(self, extra_properties: dict):
        """Validate flavor extra_properties.

        Each value in extra_properties must be in 'key=value'
        format, where key must be in the allowed fields set.

        Args:
            extra_properties: dict of extra properties to validate.
                Each value should be a string in 'key=value' format.

        Returns:
            (success, error) tuple. error is None on success.
        """
        if not extra_properties:
            return True, None
        allowed = EXTRA_PROPERTIES_ALLOWED_FIELDS
        for prop_key, prop_value in extra_properties.items():
            if prop_key not in allowed:
                return (
                    False,
                    f"Unsupported extra_properties field: "
                    f"'{prop_key}'. Allowed fields: {allowed}",
                )
        return True, None

    def validate_device_groups(
        self,
        device_group_ids: list[str],
        device_group_manager=None,
    ):
        """Validate device group IDs.

        Checks that device_groups is non-empty and that each
        device group UUID exists in the database.

        Args:
            device_group_ids: list of device group UUID strings
            device_group_manager: DeviceGroupManager instance for
                lookup (optional, if None only checks non-empty)

        Returns:
            (success, error) tuple. error is None on success.
        """
        if not device_group_ids:
            return (
                False,
                "device_groups is required (at least one)",
            )
        if device_group_manager is None:
            return True, None
        for dg_id in device_group_ids:
            group = device_group_manager.get_device_group(str(dg_id))
            if group is None:
                return (
                    False,
                    f"Device group not found: {dg_id}",
                )
        return True, None

    def get_flavor_ids_by_device_group(
        self, device_group_id: str
    ) -> list[str]:
        """Get flavor IDs associated with a device group.

        Args:
            device_group_id: device group UUID string

        Returns:
            list of flavor UUID strings, empty if none or error.
        """
        if not device_group_id:
            return []
        with create_db_session(self._db_engine) as db_session:
            dg_repo = FlavorDeviceGroupRepository(db_session)
            success, _, flavor_ids = dg_repo.get_flavor_ids_by_device_group(
                device_group_id
            )
            if not success:
                logger.error(
                    f"Failed to get flavors for device group {device_group_id}"
                )
                return []
            return flavor_ids

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

    def get_flavor_by_name(self, name: str) -> Flavor | None:
        """Get flavor by name.

        Args:
            name: flavor name

        Returns:
            Flavor instance or None if not found.
        """
        if not name:
            return None

        with create_db_session(self._db_engine) as db_session:
            repo = FlavorRepository(db_session)
            success, error, flavor = repo.get_flavor_by_name(name)
            if not success:
                logger.error(f"Failed to get flavor by name {name}: {error}")
                return None
            if flavor is None:
                logger.warning(f"Flavor not found by name: {name}")
                return None
            return flavor

    def get_flavor_device_groups(self, flavor_id: str) -> list[str]:
        """Get device group IDs associated with a flavor.

        Args:
            flavor_id: flavor UUID string

        Returns:
            list of device group UUID strings, empty if none or
            flavor not found.
        """
        if not flavor_id:
            return []
        with create_db_session(self._db_engine) as db_session:
            dg_repo = FlavorDeviceGroupRepository(db_session)
            success, _, group_ids = dg_repo.get_device_group_ids_by_flavor(
                flavor_id
            )
            if not success:
                logger.error(
                    f"Failed to get device groups for flavor {flavor_id}"
                )
                return []
            return group_ids

    def get_flavor_specs(self, flavor_id: str) -> dict:
        """Get flavor specs by ID.

        Builds a specs dict from flavor's independent columns
        (min_qubits, max_qubits, gate_fidelity_*)
        merged with extra_properties (user custom properties).
        Also injects the first device group UUID as
        'qc:device_groups' for DeviceGroupFilter compatibility.

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

        specs = {}
        if flavor.min_qubits is not None:
            specs["min_qubits"] = flavor.min_qubits
        if flavor.max_qubits is not None:
            specs["max_qubits"] = flavor.max_qubits
        if flavor.gate_fidelity_1q_min is not None:
            specs["gate_fidelity_1q_min"] = flavor.gate_fidelity_1q_min
        if flavor.gate_fidelity_2q_min is not None:
            specs["gate_fidelity_2q_min"] = flavor.gate_fidelity_2q_min
        # merge extra_properties (user custom properties)
        if flavor.extra_properties:
            specs.update(flavor.extra_properties)
        # inject device group reference from mapping table
        # for DeviceGroupFilter compatibility
        group_ids = self.get_flavor_device_groups(flavor_id)
        if group_ids:
            specs[DEVICE_GROUP_SPEC_KEY] = group_ids[0]
        return specs

    def get_visible_flavor(
        self, flavor_id: str, project_id: str | None = None
    ) -> Flavor | None:
        """Get flavor by ID with visibility scoping.

        A flavor is visible if it is public or belongs to the
        caller's project.

        Args:
            flavor_id: flavor UUID string
            project_id: caller's project id for scoping

        Returns:
            Flavor instance or None if not found/visible.
        """
        if not flavor_id:
            return None

        with create_db_session(self._db_engine) as db_session:
            repo = FlavorRepository(db_session)
            success, error, flavor = repo.get_visible_flavor_by_uuid(
                flavor_id, project_id=project_id
            )
            if not success:
                logger.error(f"Failed to get flavor {flavor_id}: {error}")
                return None
            if flavor is None:
                logger.warning(f"Flavor not found/visible: {flavor_id}")
                return None
            return flavor

    @staticmethod
    def _normalize_filter_names(filters):
        """Normalize flavor_name/flavor_names filters into a list.

        Prefers flavor_names (list) over flavor_name (str) for
        backward compatibility.

        Args:
            filters: dict of filter conditions or None

        Returns:
            list of names, empty if none specified.
        """
        if not filters:
            return []
        if filters.get("flavor_names"):
            return list(filters["flavor_names"])
        if filters.get("flavor_name"):
            return [filters["flavor_name"]]
        return []

    def get_flavors(
        self,
        filters: dict | None = None,
    ) -> list[Flavor]:
        """Get all flavors with optional filtering.

        Args:
            filters: dict of filter conditions. Supported keys:
                - flavor_names: list of flavor names to filter by (in-memory)
                - flavor_name: single flavor name to filter by (in-memory)
                - flavor_ids: list of flavor UUIDs (DB-level IN query)

        Returns:
            list of Flavor instances
        """
        with create_db_session(self._db_engine) as db_session:
            repo = FlavorRepository(db_session)
            # Extract flavor_ids for DB-level filtering; flavor_names
            # is applied in-memory (not a direct model column key).
            db_filters = None
            if filters and filters.get("flavor_ids"):
                db_filters = {"id": filters["flavor_ids"]}
            success, _, flavors = repo.get_flavors(filters=db_filters)
            if not success:
                return []
            flavors = flavors or []
            # apply name filter if specified (in-memory)
            names = self._normalize_filter_names(filters)
            if names:
                flavors = [f for f in flavors if f.name in names]
            return flavors

    def get_visible_flavors(
        self,
        filters: dict | None = None,
        project_id: str | None = None,
    ) -> list[Flavor]:
        """Get visible flavors with optional filtering.

        A flavor is visible if it is public or belongs to the
        caller's project.

        Args:
            filters: dict of filter conditions. Supported keys:
                - flavor_names: list of flavor names to filter by (in-memory)
                - flavor_name: single flavor name to filter by (in-memory)
                - flavor_ids: list of flavor UUIDs (in-memory)
            project_id: caller's project id for scoping

        Returns:
            list of Flavor instances
        """
        with create_db_session(self._db_engine) as db_session:
            repo = FlavorRepository(db_session)
            success, _, flavors = repo.get_visible_flavors(
                project_id=project_id
            )
            if not success:
                return []
            flavors = flavors or []
            # apply flavor_ids filter if specified (in-memory)
            if filters and filters.get("flavor_ids"):
                ids_set = {str(fid) for fid in filters["flavor_ids"]}
                flavors = [f for f in flavors if str(f.id) in ids_set]
            # apply name filter if specified (in-memory)
            names = self._normalize_filter_names(filters)
            if names:
                flavors = [f for f in flavors if f.name in names]
            return flavors

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

    def update_flavor(
        self,
        flavor_id: str,
        flavor_data: dict,
        db_filters: dict | None = None,
    ):
        """Update flavor by ID.

        Args:
            flavor_id: flavor UUID string
            flavor_data: dict with fields to update
            db_filters: optional db filters for permission scoping

        Returns:
            (success, error, flavor_record)
        """
        with create_db_session(self._db_engine) as db_session:
            repo = FlavorRepository(db_session)
            return repo.update_flavor(
                flavor_id, flavor_data, filters=db_filters
            )

    def delete_flavor(self, flavor_id: str, db_filters: dict | None = None):
        """Delete flavor by ID.

        Args:
            flavor_id: flavor UUID string
            db_filters: optional db filters for permission scoping

        Returns:
            (success, error)
        """
        with create_db_session(self._db_engine) as db_session:
            repo = FlavorRepository(db_session)
            return repo.delete_flavor(flavor_id, filters=db_filters)

    def get_flavor_responses(
        self,
        filters: dict | None = None,
        project_id: str | None = None,
    ) -> list[Flavor]:
        """Get flavors with device_groups resolved, for API response.

        Fetches flavors (with optional visibility scoping when
        project_id is provided) and attaches the resolved
        device_groups UUID list to each flavor instance.

        Args:
            filters: dict of filter conditions (see get_flavors)
            project_id: caller's project id for visibility scoping;
                when None, all flavors are returned

        Returns:
            list of Flavor instances with device_groups populated
        """
        if project_id is None:
            flavors = self.get_flavors(filters=filters)
        else:
            flavors = self.get_visible_flavors(
                filters=filters, project_id=project_id
            )
        for f in flavors:
            f.device_groups = [
                uuid.UUID(dg_id)
                for dg_id in self.get_flavor_device_groups(str(f.id))
            ]
        return flavors

    def delete_flavors(
        self,
        flavor_ids: list[str],
        db_filters: dict | None = None,
    ) -> list[tuple[str, bool, str | None]]:
        """Delete multiple flavors by IDs (batch).

        Deduplicates flavor_ids preserving order, iterates over
        each flavor_id, deletes it independently, and collects
        per-flavor results. Does not abort on individual failures.

        Args:
            flavor_ids: list of flavor UUID strings
            db_filters: optional db filters for permission scoping

        Returns:
            list of (flavor_id, success, error) tuples
        """
        # Deduplicate flavor_ids preserving order
        flavor_ids = list(dict.fromkeys(flavor_ids))
        results = []
        for flavor_id in flavor_ids:
            with create_db_session(self._db_engine) as db_session:
                repo = FlavorRepository(db_session)
                success, error = repo.delete_flavor(
                    flavor_id, filters=db_filters
                )
                results.append((flavor_id, success, error))
        return results
