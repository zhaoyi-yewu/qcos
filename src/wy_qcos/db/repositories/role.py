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

from sqlalchemy.orm import Session

from wy_qcos.db.models import Role
from wy_qcos.db.repositories import BaseRepository
from wy_qcos.api.schemas.user import CreateRoleRequest, UpdateRoleRequest

logger = logging.getLogger(__name__)


class RoleRepository(BaseRepository):
    """Database operation function library related to Roles."""

    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    def create_role(self, role_create: CreateRoleRequest):
        """Create a new role."""
        try:
            role_data = role_create.model_dump()
            success, error, role = self.create(Role, **role_data)
            if success:
                logger.info(f"Role created successfully: {role.role_name}")
                return success, None, role
            else:
                logger.error(f"Failed to create role: {error}")
                return success, error, None
        except Exception as e:
            logger.error(f"Exception while creating role: {e}")
            return False, e, None

    def get_role_by_id(self, role_id: str):
        """Get a role by UUID string ID."""
        try:
            success, error, role = self.get_by_uuid(Role, role_id)
            if success and role:
                return True, None, role
            else:
                return False, f"Role with id {role_id} not found", None
        except Exception as e:
            logger.error(f"Exception while getting role by id: {e}")
            return False, e, None

    def get_role_by_name(self, role_name: str):
        """Get a role by name."""
        try:
            success, error, role = self.get_by_attr(
                Role, "role_name", role_name
            )
            if success and role:
                return True, None, role
            else:
                return False, f"Role with name {role_name} not found", None
        except Exception as e:
            logger.error(f"Exception while getting role by name: {e}")
            return False, e, None

    def get_roles(self, filters: dict | None = None):
        """Get all roles with optional filtering.

        Args:
            filters: Dictionary with filter conditions
                    (e.g., {'role_name': 'admin'})

        Returns:
            Tuple of (success, error, roles)
        """
        try:
            success, error, roles = self.get_all(Role, filters=filters)
            if success:
                return True, None, roles
            else:
                logger.error(f"Failed to get roles: {error}")
                return False, error, None
        except Exception as e:
            logger.error(f"Exception while getting all roles: {e}")
            return False, e, None

    def update_role(self, role_id: str, role_update: UpdateRoleRequest):
        """Update a role."""
        try:
            # First check if role exists
            success, error, existing_role = self.get_by_uuid(Role, role_id)
            if not success or not existing_role:
                return False, f"Role with id {role_id} not found", None

            # Update only provided fields
            update_data = role_update.model_dump(exclude_unset=True)

            # Remove None values to avoid overwriting existing data
            update_data = {
                k: v for k, v in update_data.items() if v is not None
            }

            if update_data:
                success, error, updated_role = self.update(
                    Role, role_id, **update_data
                )
                if success:
                    logger.info(
                        f"Role updated successfully: {updated_role.role_name}"
                    )
                    return True, None, updated_role
                else:
                    logger.error(f"Failed to update role: {error}")
                    return False, error, None
            else:
                # No fields to update, return existing role
                return True, None, existing_role
        except Exception as e:
            logger.error(f"Exception while updating role: {e}")
            self.rollback()
            return False, e, None

    def delete_role_by_id(self, role_id: str):
        """Delete a role by UUID string."""
        try:
            success, error = self.delete_by_uuid(Role, role_id)
            if success:
                logger.info(f"Role deleted successfully: {role_id}")
                return True, None
            else:
                logger.error(f"Failed to delete role: {error}")
                return False, error
        except Exception as e:
            logger.error(f"Exception while deleting role: {e}")
            self.rollback()
            return False, e
