#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of MulanPSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import pytest
from unittest.mock import Mock
from datetime import datetime
import uuid

from wy_qcos.api.posiq.routes_jsonrpc.project import (
    create_project,
    get_project,
    get_projects,
    update_project,
    delete_project,
    _get_project_response,
)
from wy_qcos.api.schemas import project as project_schemas
from wy_qcos.common.constant import Constant
from wy_qcos.db.models import Project


class TestGetProjectResponse:
    """Test cases for _get_project_response function."""

    def test_get_project_response_success(self):
        """Test formatting project response."""
        project_id = str(uuid.uuid4())
        now = datetime.now()
        project = Project(
            id=project_id,
            name="test_project",
            description="Test project description",
            created_at=now,
            updated_at=now,
        )

        result = _get_project_response(project)

        assert result is not None
        assert result["id"] == project_id
        assert result["name"] == "test_project"
        assert result["description"] == "Test project description"
        assert "created_at" in result
        assert "updated_at" in result

    def test_get_project_response_no_description(self):
        """Test formatting project response without description."""
        project_id = str(uuid.uuid4())
        now = datetime.now()
        project = Project(
            id=project_id,
            name="project_no_desc",
            created_at=now,
            updated_at=now,
        )

        result = _get_project_response(project)

        assert result["name"] == "project_no_desc"
        assert result["description"] is None


class TestCreateProject:
    """Test cases for create_project function."""

    def test_create_project_success(self):
        """Test successful project creation."""
        project_id = str(uuid.uuid4())
        created_project = Project(
            id=project_id,
            name="new_project",
            description="New project description",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        body = project_schemas.CreateProjectRequest(
            project_name="new_project",
            description="New project description",
        )

        mock_project_manager = Mock()
        mock_project_manager.create_project.return_value = created_project

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._project_manager = mock_project_manager

        result = create_project(body, mock_request)

        assert result is not None
        assert result.name == "new_project"
        assert result.description == "New project description"
        mock_project_manager.create_project.assert_called_once()

    def test_create_project_without_description(self):
        """Test project creation without description."""
        project_id = str(uuid.uuid4())
        created_project = Project(
            id=project_id,
            name="project_no_desc",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        body = project_schemas.CreateProjectRequest(
            project_name="project_no_desc"
        )

        mock_project_manager = Mock()
        mock_project_manager.create_project.return_value = created_project

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._project_manager = mock_project_manager

        result = create_project(body, mock_request)

        assert result is not None
        assert result.name == "project_no_desc"

    def test_create_project_duplicate_name(self):
        """Test creating project with duplicate name."""
        mock_projects_repo = Mock()
        existing_project = Project(
            id=str(uuid.uuid4()),
            name="existing_project",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_projects_repo.get_project_by_name.return_value = (
            True,
            None,
            existing_project,
        )

        body = project_schemas.CreateProjectRequest(
            project_name="existing_project"
        )

        with pytest.raises(Exception):
            create_project(body, None, mock_projects_repo)

    def test_create_project_name_too_short(self):
        """Test creating project with name too short.

        validation at schema level.
        """
        from pydantic import ValidationError

        short_name = "a" * (Constant.MIN_PROJECT_LENGTH - 1)

        with pytest.raises(ValidationError):
            project_schemas.CreateProjectRequest(project_name=short_name)

    def test_create_project_name_too_long(self):
        """Test creating project with name too long.

        validation at schema level.
        """
        from pydantic import ValidationError

        long_name = "a" * (Constant.MAX_PROJECT_LENGTH + 1)

        with pytest.raises(ValidationError):
            project_schemas.CreateProjectRequest(project_name=long_name)

    def test_create_project_creation_fails(self):
        """Test project creation when database operation fails."""
        mock_projects_repo = Mock()
        mock_projects_repo.get_project_by_name.return_value = (
            False,
            None,
            None,
        )
        mock_projects_repo.create_project.return_value = (
            False,
            "Database error",
            None,
        )

        body = project_schemas.CreateProjectRequest(
            project_name="project_fail"
        )

        with pytest.raises(Exception):
            create_project(body, None, mock_projects_repo)


class TestGetProject:
    """Test cases for get_project function."""

    def test_get_project_success(self):
        """Test successful project retrieval."""
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name="test_project",
            description="Test project",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        body = project_schemas.GetProjectRequest(project_id=project_id)

        mock_project_manager = Mock()
        mock_project_manager.get_project_by_id.return_value = project

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._project_manager = mock_project_manager

        result = get_project(body, mock_request)

        assert result is not None
        assert result.name == "test_project"
        mock_project_manager.get_project_by_id.assert_called_once()

    def test_get_project_not_found(self):
        """Test getting non-existent project."""
        mock_projects_repo = Mock()
        project_id = str(uuid.uuid4())
        mock_projects_repo.get_project_by_id.return_value = (
            False,
            f"Can't find project: {project_id}",
            None,
        )

        body = project_schemas.GetProjectRequest(project_id=project_id)

        with pytest.raises(Exception):
            get_project(body, None, mock_projects_repo)

    def test_get_project_invalid_uuid(self):
        """Test getting project with invalid UUID."""
        mock_projects_repo = Mock()
        invalid_uuid = str(uuid.uuid4())
        mock_projects_repo.get_project_by_id.return_value = (
            False,
            f"Can't find project: {invalid_uuid}",
            None,
        )

        body = project_schemas.GetProjectRequest(project_id=invalid_uuid)
        with pytest.raises(Exception):
            get_project(body, None, mock_projects_repo)


class TestGetProjects:
    """Test cases for get_projects function."""

    def test_get_projects_success(self):
        """Test successful retrieval of all projects."""
        project1 = Project(
            id=str(uuid.uuid4()),
            name="project1",
            description="First project",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        project2 = Project(
            id=str(uuid.uuid4()),
            name="project2",
            description="Second project",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_project_manager = Mock()
        mock_project_manager.get_projects.return_value = {
            str(project1.id): project1,
            str(project2.id): project2,
        }

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._project_manager = mock_project_manager

        result = get_projects(mock_request)

        assert isinstance(result, dict)
        assert len(result) == 2
        project_names = [p.name for p in result.values()]
        assert "project1" in project_names
        assert "project2" in project_names

    def test_get_projects_empty(self):
        """Test retrieving projects when none exist."""
        mock_project_manager = Mock()
        mock_project_manager.get_projects.return_value = {}

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._project_manager = mock_project_manager

        result = get_projects(mock_request)

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_get_projects_with_filter(self):
        """Test retrieving projects with filter."""
        project = Project(
            id=str(uuid.uuid4()),
            name="filtered_project",
            description="Filtered project",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_project_manager = Mock()
        mock_project_manager.get_projects.return_value = {
            str(project.id): project
        }

        body = project_schemas.GetProjectsRequest(
            filters={"name": "filtered_project"}
        )
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._project_manager = mock_project_manager

        result = get_projects(mock_request, body)

        assert isinstance(result, dict)
        mock_project_manager.get_projects.assert_called_once()

    def test_get_projects_retrieval_fails(self):
        """Test getting projects when database operation fails."""
        mock_projects_repo = Mock()
        mock_projects_repo.get_projects.return_value = (
            False,
            "Database error",
            None,
        )

        with pytest.raises(Exception):
            get_projects(None, None, mock_projects_repo)


class TestUpdateProject:
    """Test cases for update_project function."""

    def test_update_project_success(self):
        """Test successful project update."""
        project_id = str(uuid.uuid4())
        project_after = Project(
            id=project_id,
            name="updated_project",
            description="Updated description",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        body = project_schemas.UpdateProjectRequest(
            project_id=project_id,
            project_name="updated_project",
            description="Updated description",
        )

        mock_project_manager = Mock()
        mock_project_manager.update_project.return_value = project_after

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._project_manager = mock_project_manager

        result = update_project(body, mock_request)

        assert result is not None
        assert result.name == "updated_project"
        assert result.description == "Updated description"

    def test_update_project_partial(self):
        """Test partial project update."""
        project_id = str(uuid.uuid4())
        updated_project = Project(
            id=project_id,
            name="new_name",
            description="Original description",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        body = project_schemas.UpdateProjectRequest(
            project_id=project_id, project_name="new_name"
        )

        mock_project_manager = Mock()
        mock_project_manager.update_project.return_value = updated_project

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._project_manager = mock_project_manager

        result = update_project(body, mock_request)

        assert result.name == "new_name"

    def test_update_project_not_found(self):
        """Test updating non-existent project."""
        mock_projects_repo = Mock()
        project_id = str(uuid.uuid4())
        mock_projects_repo.get_project_by_id.return_value = (
            False,
            f"Can't find project: {project_id}",
            None,
        )

        body = project_schemas.UpdateProjectRequest(
            project_id=project_id, project_name="new_name"
        )

        with pytest.raises(Exception):
            update_project(body, None, mock_projects_repo)

    def test_update_project_duplicate_name(self):
        """Test updating project to duplicate name."""
        mock_projects_repo = Mock()
        project_id = str(uuid.uuid4())
        original_project = Project(
            id=project_id,
            name="original",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        existing_project = Project(
            id=str(uuid.uuid4()),
            name="existing",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_projects_repo.get_project_by_id.return_value = (
            True,
            None,
            original_project,
        )
        mock_projects_repo.get_project_by_name.return_value = (
            True,
            None,
            existing_project,
        )

        body = project_schemas.UpdateProjectRequest(
            project_id=project_id, project_name="existing"
        )

        with pytest.raises(Exception):
            update_project(body, None, mock_projects_repo)

    def test_update_project_name_too_short(self):
        """Test updating project with name too short.

        validation at schema level.
        """
        from pydantic import ValidationError

        project_id = str(uuid.uuid4())
        short_name = "a" * (Constant.MIN_PROJECT_LENGTH - 1)

        with pytest.raises(ValidationError):
            project_schemas.UpdateProjectRequest(
                project_id=project_id, project_name=short_name
            )

    def test_update_project_name_too_long(self):
        """Test updating project with name too long.

        validation at schema level.
        """
        from pydantic import ValidationError

        project_id = str(uuid.uuid4())
        long_name = "a" * (Constant.MAX_PROJECT_LENGTH + 1)

        with pytest.raises(ValidationError):
            project_schemas.UpdateProjectRequest(
                project_id=project_id, project_name=long_name
            )


class TestDeleteProject:
    """Test cases for delete_project function."""

    def test_delete_project_success(self):
        """Test successful project deletion."""
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name="project_to_delete",
            description="Will be deleted",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        body = project_schemas.DeleteProjectRequest(project_id=project_id)

        mock_project_manager = Mock()
        mock_project_manager.delete_project.return_value = project

        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state._project_manager = mock_project_manager

        result = delete_project(body, mock_request)

        assert result is not None
        assert result.name == "project_to_delete"

    def test_delete_project_not_found(self):
        """Test deleting non-existent project."""
        mock_projects_repo = Mock()
        project_id = str(uuid.uuid4())
        mock_projects_repo.get_project_by_id.return_value = (
            False,
            f"Can't find project: {project_id}",
            None,
        )

        body = project_schemas.DeleteProjectRequest(project_id=project_id)

        with pytest.raises(Exception):
            delete_project(body, None, mock_projects_repo)

    def test_delete_default_project(self):
        """Test cannot delete default project."""
        mock_projects_repo = Mock()
        default_project = Project(
            id=Constant.DEFAULT_PROJECT_ID,
            name="default",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_projects_repo.get_project_by_id.return_value = (
            True,
            None,
            default_project,
        )

        body = project_schemas.DeleteProjectRequest(
            project_id=Constant.DEFAULT_PROJECT_ID
        )

        with pytest.raises(Exception):
            delete_project(body, None, mock_projects_repo)

    def test_delete_admin_project(self):
        """Test cannot delete admin project."""
        mock_projects_repo = Mock()
        admin_project = Project(
            id=Constant.ADMIN_PROJECT_ID,
            name="admin",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_projects_repo.get_project_by_id.return_value = (
            True,
            None,
            admin_project,
        )

        body = project_schemas.DeleteProjectRequest(
            project_id=Constant.ADMIN_PROJECT_ID
        )

        with pytest.raises(Exception):
            delete_project(body, None, mock_projects_repo)

    def test_delete_project_deletion_fails(self):
        """Test project deletion when database operation fails."""
        mock_projects_repo = Mock()
        project_id = str(uuid.uuid4())
        project = Project(
            id=project_id,
            name="project_fail",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_projects_repo.get_project_by_id.return_value = (
            True,
            None,
            project,
        )
        mock_projects_repo.delete_project.return_value = (
            False,
            "Database error",
            None,
        )

        body = project_schemas.DeleteProjectRequest(project_id=project_id)

        with pytest.raises(Exception):
            delete_project(body, None, mock_projects_repo)
