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

from sqlalchemy import select
from sqlalchemy.orm import Session

from wy_qcos.db.models import Project
from wy_qcos.db.repositories import BaseRepository

logger = logging.getLogger(__name__)


def _validate_uuid(project_id: str) -> bool:
    """Validate if the project_id is a valid UUID format.

    Args:
        project_id: project ID string to validate

    Returns:
        True if valid UUID, False otherwise
    """
    try:
        uuid.UUID(project_id)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


class ProjectRepository(BaseRepository):
    """Database operation function library related to Projects."""

    def __init__(self, db_session: Session) -> None:
        super().__init__(db_session)

    def get_project_by_id(
        self, project_id: str
    ) -> tuple[bool, str | None, Project | None]:
        """Get project by ID.

        Args:
            project_id: project ID

        Returns:
            tuple of (success, error, project)
        """
        try:
            if not _validate_uuid(project_id):
                logger.error(f"Invalid UUID format: {project_id}")
                return (
                    False,
                    f"Can't find project: {project_id}",
                    None,
                )
            stmt = select(Project).where(Project.id == project_id)
            project = self._db_session.execute(stmt).scalars().first()
            if project:
                return (True, None, project)
            return (
                False,
                f"Can't find project: {project_id}",
                None,
            )
        except Exception:
            logger.error(f"Failed to get project by ID: {project_id}")
            return (False, f"Can't find project: {project_id}", None)

    def get_project_by_name(
        self, name: str
    ) -> tuple[bool, str | None, Project | None]:
        """Get project by name.

        Args:
            name: project name

        Returns:
            tuple of (success, error, project)
        """
        try:
            stmt = select(Project).where(Project.name == name)
            project = self._db_session.execute(stmt).scalars().first()
            if project:
                return (True, None, project)
            return (
                False,
                f"Project with name '{name}' not found",
                None,
            )
        except Exception as e:
            logger.error(f"Failed to get project by name: {e}")
            return (False, str(e), None)

    def get_projects(self) -> tuple[bool, str | None, list[Project] | None]:
        """Get all projects.

        Returns:
            tuple of (success, error, projects)
        """
        try:
            stmt = select(Project)
            projects = self._db_session.execute(stmt).scalars().all()
            return (True, None, projects)
        except Exception as e:
            logger.error(f"Failed to get projects: {e}")
            return (False, str(e), None)

    def create_project(
        self, project_id: str, name: str, description: str | None = None
    ) -> tuple[bool, str | None, Project | None]:
        """Create a project.

        Args:
            project_id: project ID (UUID string)
            name: project name
            description: project description (optional)

        Returns:
            tuple of (success, error, project)
        """
        try:
            if not _validate_uuid(project_id):
                logger.error(f"Invalid UUID format: {project_id}")
                return (
                    False,
                    f"Invalid project ID format: {project_id}",
                    None,
                )
            project = Project(
                id=project_id, name=name, description=description
            )
            self._db_session.add(project)
            self._db_session.commit()
            logger.info(f"Created project: {name} (ID: {project_id})")
            return (True, None, project)
        except Exception as e:
            self._db_session.rollback()
            logger.error(f"Failed to create project: {e}")
            return (False, str(e), None)

    def update_project(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> tuple[bool, str | None, Project | None]:
        """Update a project.

        Args:
            project_id: project ID (UUID string)
            name: new project name (optional)
            description: new project description (optional)

        Returns:
            tuple of (success, error, project)
        """
        try:
            if not _validate_uuid(project_id):
                logger.error(f"Invalid UUID format: {project_id}")
                return (
                    False,
                    f"Can't find project: {project_id}",
                    None,
                )
            stmt = select(Project).where(Project.id == project_id)
            project = self._db_session.execute(stmt).scalars().first()
            if not project:
                return (
                    False,
                    f"Can't find project: {project_id}",
                    None,
                )

            if name is not None:
                project.name = name

            if description is not None:
                project.description = description

            self._db_session.commit()
            self._db_session.refresh(project)
            logger.info(f"Updated project: {project.name} (ID: {project_id})")
            return (True, None, project)
        except Exception:
            self._db_session.rollback()
            logger.error(f"Failed to update project: {project_id}")
            return (False, f"Can't find project: {project_id}", None)

    def delete_project(
        self, project_id: str
    ) -> tuple[bool, str | None, Project | None]:
        """Delete a project.

        Args:
            project_id: project ID (UUID string)

        Returns:
            tuple of (success, error, project)
        """
        try:
            if not _validate_uuid(project_id):
                logger.error(f"Invalid UUID format: {project_id}")
                return (
                    False,
                    f"Can't find project: {project_id}",
                    None,
                )
            stmt = select(Project).where(Project.id == project_id)
            project = self._db_session.execute(stmt).scalars().first()
            if not project:
                return (
                    False,
                    f"Can't find project: {project_id}",
                    None,
                )

            project_name = project.name
            self._db_session.delete(project)
            self._db_session.commit()
            logger.info(f"Deleted project: {project_name} (ID: {project_id})")
            return (True, None, project)
        except Exception:
            self._db_session.rollback()
            logger.error(f"Failed to delete project: {project_id}")
            return (False, f"Can't find project: {project_id}", None)

    def project_exists(self, project_id: str) -> bool:
        """Check if project exists.

        Args:
            project_id: project ID

        Returns:
            True if project exists, False otherwise
        """
        try:
            if not _validate_uuid(project_id):
                logger.error(f"Invalid UUID format: {project_id}")
                return False
            stmt = select(Project).where(Project.id == project_id)
            project = self._db_session.execute(stmt).scalars().first()
            return project is not None
        except Exception:
            logger.error(f"Failed to check project existence: {project_id}")
            return False
