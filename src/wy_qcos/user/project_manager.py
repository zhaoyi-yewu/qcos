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
import re
import uuid

from sqlalchemy.orm import Session

from wy_qcos.common.constant import Constant
from wy_qcos.db.repositories.project import ProjectRepository

logger = logging.getLogger(__name__)


class ProjectManager:
    """Project manager for CRUD operations on projects."""

    def __init__(
        self,
        db_session: Session | None = None,
        projects_repo: ProjectRepository | None = None,
    ):
        """Initialize ProjectManager.

        Args:
            db_session: Database session for repository operations
            projects_repo: Project repository (alternative to db_session)
        """
        self._db_session = db_session
        self.projects_repo: ProjectRepository | None = None
        if db_session:
            self.projects_repo = ProjectRepository(db_session)
        elif projects_repo:
            self.projects_repo = projects_repo

        # Internal data structures for managing projects
        self.projects_db = {}
        self._project_name_to_id = {}

    def validate_project_name(self, project_name: str) -> None:
        """Validate project name.

        Args:
            project_name: project name

        Raises:
            ValueError: if project name is invalid
        """
        if len(project_name) < Constant.MIN_PROJECT_LENGTH:
            raise ValueError(
                f"Project name '{project_name}' is too short "
                f"(minimum {Constant.MIN_PROJECT_LENGTH} characters)"
            )

        if len(project_name) > Constant.MAX_PROJECT_LENGTH:
            raise ValueError(
                f"Project name '{project_name}' is too long "
                f"(maximum {Constant.MAX_PROJECT_LENGTH} characters)"
            )

        # Check if project name starts with underscore
        if project_name.startswith("_"):
            raise ValueError(
                f"Project name '{project_name}' cannot start with underscore"
            )

        # Check if project name contains only allowed characters:
        # letters (a-z, A-Z), digits (0-9), hyphen (-), underscore (_)
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", project_name):
            raise ValueError(
                f"Project name '{project_name}' is invalid. "
                f"Must start with a letter or digit and contain only "
                f"letters, digits, hyphens, or underscores"
            )

    def validate_description(self, description: str | None) -> None:
        """Validate description.

        Args:
            description: description

        Raises:
            ValueError: if description is invalid
        """
        if description and len(description) > Constant.MAX_DESCRIPTION_LENGTH:
            raise ValueError(
                f"Description is too long "
                f"(maximum {Constant.MAX_DESCRIPTION_LENGTH} characters)"
            )

    def create_project(
        self,
        project_name: str,
        description: str | None = None,
        project_id: str | None = None,
    ):
        """Create a new project.

        Args:
            project_name: project name (required)
            description: project description (optional)
            project_id: project ID (UUID, optional - auto-generated if
                       not provided)

        Returns:
            created project

        Raises:
            ValueError: if project name is invalid or already exists
        """
        # Validate inputs
        self.validate_project_name(project_name)
        self.validate_description(description)

        # Generate or validate project_id
        if not project_id:
            project_id = str(uuid.uuid4())
        else:
            project_id = str(project_id)
            # Validate project_id is a valid UUID
            try:
                uuid.UUID(project_id)
            except (ValueError, AttributeError):
                raise ValueError(
                    f"Invalid project ID: {project_id}, "
                    f"UUID format is required"
                )

        # Check if project name already exists
        success, _, existing_project = self.projects_repo.get_project_by_name(
            project_name
        )
        if success and existing_project:
            raise ValueError(f"Project '{project_name}' already exists")

        # Create in database
        success, error, project = self.projects_repo.create_project(
            project_id, project_name, description
        )
        if not success or not project:
            raise ValueError(f"Failed to create project: {error}")

        # Add to internal storage
        self.projects_db[project_name] = project
        if hasattr(project, "id"):
            self._project_name_to_id[project_name] = project.id

        logger.info(f"Created project: {project_name} (ID: {project_id})")

        return project

    def update_project(
        self,
        project_id: str,
        project_name: str | None = None,
        description: str | None = None,
    ):
        """Update a project.

        Args:
            project_id: project ID (UUID)
            project_name: new project name (optional)
            description: new project description (optional)

        Returns:
            updated project

        Raises:
            ValueError: if project not found or validation fails
        """
        # Get project by ID
        project = self.get_project_by_id(project_id)
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found")

        old_name = project.name

        # Validate inputs
        if project_name is not None:
            self.validate_project_name(project_name)

            # Check if new name already exists (and is different from current)
            if project_name != old_name:
                success, _, existing_project = (
                    self.projects_repo.get_project_by_name(project_name)
                )
                if success and existing_project:
                    raise ValueError(
                        f"Project '{project_name}' already exists"
                    )

        if description is not None:
            self.validate_description(description)

        # Update in database
        success, error, updated_project = self.projects_repo.update_project(
            project_id, project_name, description
        )
        if not success or not updated_project:
            raise ValueError(f"Failed to update project: {error}")

        # Update internal storage
        if project_name and project_name != old_name:
            # Remove old name entry
            if old_name in self.projects_db:
                del self.projects_db[old_name]
            if old_name in self._project_name_to_id:
                del self._project_name_to_id[old_name]

            # Add new name entry
            self.projects_db[project_name] = updated_project
            if hasattr(updated_project, "id"):
                self._project_name_to_id[project_name] = updated_project.id

        logger.info(
            f"Updated project: {updated_project.name} (ID: {project_id})"
        )

        return updated_project

    def get_project(self, project_name: str | None = None):
        """Get project by name.

        Args:
            project_name: project name

        Returns:
            project object or None if not found
        """
        if project_name is None:
            return None

        success, _, project = self.projects_repo.get_project_by_name(
            project_name
        )
        if success and project:
            return project
        return None

    def get_project_by_id(self, project_id: str):
        """Get project by ID.

        Args:
            project_id: project ID (UUID)

        Returns:
            project object or None if not found
        """
        success, _, project = self.projects_repo.get_project_by_id(
            str(project_id)
        )
        if success and project:
            return project
        return None

    def get_projects(self, filters: dict | None = None) -> dict[str, object]:
        """Get all projects with optional filtering.

        Args:
            filters: Dictionary with filter conditions
                    (e.g., {'name': 'admin'})

        Returns:
            projects keyed by project_id, optionally filtered
        """
        success, _, projects = self.projects_repo.get_projects()
        if not success or not projects:
            return {}

        # Apply filters if provided
        if filters:
            filtered_projects = []
            for project in projects:
                match = True
                for key, value in filters.items():
                    if hasattr(project, key):
                        if getattr(project, key) != value:
                            match = False
                            break
                    else:
                        match = False
                        break
                if match:
                    filtered_projects.append(project)
            projects = filtered_projects

        # Return projects keyed by project_id
        return {str(project.id): project for project in projects}

    def delete_project(self, project_id: str):
        """Delete a project.

        Args:
            project_id: project ID (UUID)

        Returns:
            deleted project

        Raises:
            ValueError: if project not found or is a reserved project
        """
        # Get project by ID
        project = self.get_project_by_id(project_id)
        if not project:
            raise ValueError(f"Project with ID '{project_id}' not found")

        project_name = project.name

        # Don't allow deletion of reserved projects
        reserved_projects = [
            Constant.ADMIN_PROJECT_NAME,
            Constant.DEFAULT_PROJECT_NAME,
        ]
        if project_name in reserved_projects:
            raise ValueError(
                f"Cannot delete reserved project '{project_name}'"
            )

        # Delete from database
        success, error, _ = self.projects_repo.delete_project(project_id)
        if not success:
            raise ValueError(f"Failed to delete project: {error}")

        # Remove from internal storage
        if project_name in self.projects_db:
            del self.projects_db[project_name]
        if project_name in self._project_name_to_id:
            del self._project_name_to_id[project_name]

        logger.info(f"Deleted project: {project_name} (ID: {project_id})")

        return project

    def project_exists(self, project_id: str) -> bool:
        """Check if a project exists.

        Args:
            project_id: project ID (UUID)

        Returns:
            True if project exists, False otherwise
        """
        project = self.get_project_by_id(project_id)
        return project is not None

    def find_projects_by_name(self, pattern: str) -> list[str]:
        """Find projects by name pattern.

        Args:
            pattern: name pattern to search for (case-insensitive)

        Returns:
            list of project names matching the pattern
        """
        success, _, projects = self.projects_repo.get_projects()
        if not success or not projects:
            return []

        matching_projects = []
        pattern_lower = pattern.lower()
        for project in projects:
            if pattern_lower in project.name.lower():
                matching_projects.append(project.name)

        return matching_projects
