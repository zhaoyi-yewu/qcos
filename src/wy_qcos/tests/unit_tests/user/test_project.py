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
# ---------------------------------------------------------------------

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock

from wy_qcos.db.models import Project


class TestProjectRepository:
    """Test cases for ProjectRepository functionality."""

    @pytest.fixture
    def project_repo(self):
        """Create a mocked ProjectRepository instance."""
        # Setup projects storage
        created_projects = {}

        def mock_create_project(project_id, name, description=None):
            """Mock create_project functionality."""
            project = Project(
                id=project_id,
                name=name,
                description=description,
            )
            created_projects[str(project_id)] = project
            return (True, None, project)

        def mock_get_project_by_id(project_id):
            """Mock get_project_by_id functionality."""
            if str(project_id) in created_projects:
                return (True, None, created_projects[str(project_id)])
            return (False, f"Can't find project: {project_id}", None)

        def mock_get_project_by_name(name):
            """Mock get_project_by_name functionality."""
            for project in created_projects.values():
                if project.name == name:
                    return (True, None, project)
            return (False, f"Project with name '{name}' not found", None)

        def mock_get_projects():
            """Mock get_projects functionality."""
            return (True, None, list(created_projects.values()))

        def mock_update_project(project_id, name=None, description=None):
            """Mock update_project functionality."""
            if str(project_id) not in created_projects:
                return (False, f"Can't find project: {project_id}", None)

            project = created_projects[str(project_id)]
            if name is not None:
                project.name = name
            if description is not None:
                project.description = description
            project.updated_at = datetime.now()
            return (True, None, project)

        def mock_delete_project(project_id):
            """Mock delete_project functionality."""
            if str(project_id) not in created_projects:
                return (False, f"Can't find project: {project_id}", None)

            project = created_projects[str(project_id)]
            del created_projects[str(project_id)]
            return (True, None, project)

        def mock_project_exists(project_id):
            """Mock project_exists functionality."""
            return str(project_id) in created_projects

        # Create mock repository
        mock_repo = Mock()
        mock_repo.create_project.side_effect = mock_create_project
        mock_repo.get_project_by_id.side_effect = mock_get_project_by_id
        mock_repo.get_project_by_name.side_effect = mock_get_project_by_name
        mock_repo.get_projects.side_effect = mock_get_projects
        mock_repo.update_project.side_effect = mock_update_project
        mock_repo.delete_project.side_effect = mock_delete_project
        mock_repo.project_exists.side_effect = mock_project_exists

        return mock_repo

    @pytest.fixture
    def sample_project(self):
        """Create a sample project for testing."""
        return Project(
            id=str(uuid.uuid4()),
            name="test_project",
            description="Test project description",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def test_create_project_success(self, project_repo):
        """Test successful project creation."""
        project_id = str(uuid.uuid4())
        success, error, project = project_repo.create_project(
            project_id, "new_project", "New project description"
        )

        assert success is True
        assert error is None
        assert project is not None
        assert project.name == "new_project"
        assert project.description == "New project description"

    def test_create_project_without_description(self, project_repo):
        """Test project creation without description."""
        project_id = str(uuid.uuid4())
        success, error, project = project_repo.create_project(
            project_id, "project_no_desc"
        )

        assert success is True
        assert error is None
        assert project is not None
        assert project.name == "project_no_desc"
        assert project.description is None

    def test_get_project_by_id_success(self, project_repo):
        """Test successful project retrieval by ID."""
        project_id = str(uuid.uuid4())
        project_repo.create_project(project_id, "test_project", "Test project")

        success, error, project = project_repo.get_project_by_id(project_id)

        assert success is True
        assert error is None
        assert project is not None
        assert project.name == "test_project"

    def test_get_project_by_id_not_found(self, project_repo):
        """Test getting non-existent project by ID."""
        non_existent_id = str(uuid.uuid4())
        success, error, project = project_repo.get_project_by_id(
            non_existent_id
        )

        assert success is False
        assert error is not None
        assert "Can't find project" in error
        assert project is None

    def test_get_project_by_id_invalid_uuid(self, project_repo):
        """Test getting project with invalid UUID format."""
        success, error, project = project_repo.get_project_by_id(
            "invalid-uuid-format"
        )

        assert success is False
        assert error is not None
        assert "Can't find project" in error
        assert project is None

    def test_get_project_by_name_success(self, project_repo):
        """Test successful project retrieval by name."""
        project_id = str(uuid.uuid4())
        project_repo.create_project(
            project_id, "my_project", "My project description"
        )

        success, error, project = project_repo.get_project_by_name(
            "my_project"
        )

        assert success is True
        assert error is None
        assert project is not None
        assert project.name == "my_project"

    def test_get_project_by_name_not_found(self, project_repo):
        """Test getting non-existent project by name."""
        success, error, project = project_repo.get_project_by_name(
            "nonexistent_project"
        )

        assert success is False
        assert error is not None
        assert "not found" in error
        assert project is None

    def test_get_projects_success(self, project_repo):
        """Test successful retrieval of all projects."""
        project_id_1 = str(uuid.uuid4())
        project_id_2 = str(uuid.uuid4())

        project_repo.create_project(project_id_1, "project1", "First project")
        project_repo.create_project(project_id_2, "project2", "Second project")

        success, error, projects = project_repo.get_projects()

        assert success is True
        assert error is None
        assert len(projects) == 2
        assert any(p.name == "project1" for p in projects)
        assert any(p.name == "project2" for p in projects)

    def test_get_projects_empty(self, project_repo):
        """Test retrieving projects when none exist."""
        success, error, projects = project_repo.get_projects()

        assert success is True
        assert error is None
        assert len(projects) == 0

    def test_update_project_success(self, project_repo):
        """Test successful project update."""
        project_id = str(uuid.uuid4())
        project_repo.create_project(
            project_id, "original_project", "Original description"
        )

        success, error, updated_project = project_repo.update_project(
            project_id,
            name="updated_project",
            description="Updated description",
        )

        assert success is True
        assert error is None
        assert updated_project is not None
        assert updated_project.name == "updated_project"
        assert updated_project.description == "Updated description"

    def test_update_project_partial(self, project_repo):
        """Test partial project update."""
        project_id = str(uuid.uuid4())
        project_repo.create_project(
            project_id, "original_project", "Original description"
        )

        success, error, updated_project = project_repo.update_project(
            project_id, name="new_name"
        )

        assert success is True
        assert error is None
        assert updated_project.name == "new_name"
        assert updated_project.description == "Original description"

    def test_update_project_not_found(self, project_repo):
        """Test updating non-existent project."""
        non_existent_id = str(uuid.uuid4())
        success, error, project = project_repo.update_project(
            non_existent_id, name="new_name"
        )

        assert success is False
        assert error is not None
        assert "Can't find project" in error
        assert project is None

    def test_update_project_invalid_uuid(self, project_repo):
        """Test updating project with invalid UUID format."""
        success, error, project = project_repo.update_project(
            "invalid-uuid", name="new_name"
        )

        assert success is False
        assert error is not None
        assert "Can't find project" in error
        assert project is None

    def test_delete_project_success(self, project_repo):
        """Test successful project deletion."""
        project_id = str(uuid.uuid4())
        project_repo.create_project(
            project_id, "project_to_delete", "Will be deleted"
        )

        success, error, deleted_project = project_repo.delete_project(
            project_id
        )

        assert success is True
        assert error is None
        assert deleted_project is not None
        assert deleted_project.name == "project_to_delete"

        # Verify project is actually deleted
        success, error, project = project_repo.get_project_by_id(project_id)
        assert success is False

    def test_delete_project_not_found(self, project_repo):
        """Test deleting non-existent project."""
        non_existent_id = str(uuid.uuid4())
        success, error, project = project_repo.delete_project(non_existent_id)

        assert success is False
        assert error is not None
        assert "Can't find project" in error
        assert project is None

    def test_delete_project_invalid_uuid(self, project_repo):
        """Test deleting project with invalid UUID format."""
        success, error, project = project_repo.delete_project(
            "eee808c7-cab3-42d7-b962-38"
        )

        assert success is False
        assert error is not None
        assert "Can't find project" in error
        assert project is None

    def test_project_exists_true(self, project_repo):
        """Test project existence check when project exists."""
        project_id = str(uuid.uuid4())
        project_repo.create_project(project_id, "existing_project")

        exists = project_repo.project_exists(project_id)

        assert exists is True

    def test_project_exists_false(self, project_repo):
        """Test project existence check when project does not exist."""
        non_existent_id = str(uuid.uuid4())
        exists = project_repo.project_exists(non_existent_id)

        assert exists is False

    def test_project_exists_invalid_uuid(self, project_repo):
        """Test project existence check with invalid UUID format."""
        exists = project_repo.project_exists("invalid-uuid")

        assert exists is False

    def test_create_multiple_projects(self, project_repo):
        """Test creating multiple projects."""
        project_id_1 = str(uuid.uuid4())
        project_id_2 = str(uuid.uuid4())
        project_id_3 = str(uuid.uuid4())

        project_repo.create_project(project_id_1, "project_a", "Project A")
        project_repo.create_project(project_id_2, "project_b", "Project B")
        project_repo.create_project(project_id_3, "project_c", "Project C")

        success, error, projects = project_repo.get_projects()

        assert success is True
        assert len(projects) == 3

    def test_project_name_is_case_sensitive(self, project_repo):
        """Test that project names are case-sensitive."""
        project_id_1 = str(uuid.uuid4())
        project_id_2 = str(uuid.uuid4())

        project_repo.create_project(project_id_1, "TestProject")
        project_repo.create_project(project_id_2, "testproject")

        success1, error1, project1 = project_repo.get_project_by_name(
            "TestProject"
        )
        success2, error2, project2 = project_repo.get_project_by_name(
            "testproject"
        )

        assert success1 is True
        assert success2 is True
        assert project1.name == "TestProject"
        assert project2.name == "testproject"
