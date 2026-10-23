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

"""Unit tests for ProjectRepository."""

import uuid

from wy_qcos.db.models import Project
from wy_qcos.db.repositories.project import (
    ProjectRepository,
    _validate_uuid,
)


class TestValidateUuid:
    """Test _validate_uuid helper function."""

    def test_valid_uuid(self):
        assert _validate_uuid(str(uuid.uuid4())) is True

    def test_invalid_uuid(self):
        assert _validate_uuid("not-a-uuid") is False

    def test_none_uuid(self):
        assert _validate_uuid(None) is False

    def test_int_uuid(self):
        assert _validate_uuid(12345) is False


class TestProjectRepository:
    """Test ProjectRepository class."""

    def test_get_project_by_id_success(self, in_memory_db):
        """Test getting project by valid ID."""
        repo = ProjectRepository(in_memory_db)
        pid = str(uuid.uuid4())
        project = Project(id=pid, name="test-project")
        in_memory_db.add(project)
        in_memory_db.commit()

        success, error, result = repo.get_project_by_id(pid)
        assert success is True
        assert error is None
        assert result.name == "test-project"

    def test_get_project_by_id_not_found(self, in_memory_db):
        """Test getting project by non-existent ID."""
        repo = ProjectRepository(in_memory_db)
        success, error, result = repo.get_project_by_id(str(uuid.uuid4()))
        assert success is False
        assert error is not None
        assert result is None

    def test_get_project_by_id_invalid_uuid(self, in_memory_db):
        """Test getting project by invalid UUID."""
        repo = ProjectRepository(in_memory_db)
        success, error, result = repo.get_project_by_id("invalid-uuid")
        assert success is False
        assert "Can't find project" in error
        assert result is None

    def test_get_project_by_name_success(self, in_memory_db):
        """Test getting project by name."""
        repo = ProjectRepository(in_memory_db)
        project = Project(id=str(uuid.uuid4()), name="test-project")
        in_memory_db.add(project)
        in_memory_db.commit()

        success, error, result = repo.get_project_by_name("test-project")
        assert success is True
        assert error is None
        assert result is not None

    def test_get_project_by_name_not_found(self, in_memory_db):
        """Test getting project by non-existent name."""
        repo = ProjectRepository(in_memory_db)
        success, error, result = repo.get_project_by_name("nonexistent")
        assert success is False
        assert "not found" in error
        assert result is None

    def test_get_projects(self, in_memory_db):
        """Test getting all projects."""
        repo = ProjectRepository(in_memory_db)
        for i in range(3):
            in_memory_db.add(Project(id=str(uuid.uuid4()), name=f"proj-{i}"))
        in_memory_db.commit()

        success, error, projects = repo.get_projects()
        assert success is True
        assert error is None
        assert len(projects) == 3

    def test_get_projects_error(self, mock_db_session):
        """Test getting all projects with database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = ProjectRepository(mock_db_session)
        success, error, projects = repo.get_projects()
        assert success is False
        assert "DB error" in error
        assert projects is None

    def test_create_project_success(self, in_memory_db):
        """Test creating a project."""
        repo = ProjectRepository(in_memory_db)
        pid = str(uuid.uuid4())
        success, error, project = repo.create_project(
            pid, "new-project", "description"
        )
        assert success is True
        assert error is None
        assert project.name == "new-project"

    def test_create_project_invalid_uuid(self, in_memory_db):
        """Test creating project with invalid UUID."""
        repo = ProjectRepository(in_memory_db)
        success, error, project = repo.create_project(
            "invalid-uuid", "new-project"
        )
        assert success is False
        assert "Invalid project ID format" in error
        assert project is None

    def test_create_project_duplicate(self, in_memory_db):
        """Test creating project with duplicate name."""
        repo = ProjectRepository(in_memory_db)
        pid = str(uuid.uuid4())
        repo.create_project(pid, "duplicate-project")

        success, error, project = repo.create_project(
            str(uuid.uuid4()), "duplicate-project"
        )
        assert success is False
        assert project is None

    def test_update_project_success(self, in_memory_db):
        """Test updating a project."""
        repo = ProjectRepository(in_memory_db)
        pid = str(uuid.uuid4())
        project = Project(id=pid, name="old-name")
        in_memory_db.add(project)
        in_memory_db.commit()

        success, error, result = repo.update_project(
            pid, name="new-name", description="new-desc"
        )
        assert success is True
        assert result.name == "new-name"
        assert result.description == "new-desc"

    def test_update_project_not_found(self, in_memory_db):
        """Test updating non-existent project."""
        repo = ProjectRepository(in_memory_db)
        success, error, result = repo.update_project(
            str(uuid.uuid4()), name="new-name"
        )
        assert success is False
        assert "Can't find project" in error
        assert result is None

    def test_update_project_invalid_uuid(self, in_memory_db):
        """Test updating project with invalid UUID."""
        repo = ProjectRepository(in_memory_db)
        success, error, result = repo.update_project(
            "invalid-uuid", name="new-name"
        )
        assert success is False
        assert result is None

    def test_update_project_partial(self, in_memory_db):
        """Test updating only some fields."""
        repo = ProjectRepository(in_memory_db)
        pid = str(uuid.uuid4())
        project = Project(id=pid, name="old-name", description="old-desc")
        in_memory_db.add(project)
        in_memory_db.commit()

        success, error, result = repo.update_project(pid, name="new-name")
        assert success is True
        assert result.name == "new-name"
        assert result.description == "old-desc"

    def test_delete_project_success(self, in_memory_db):
        """Test deleting a project."""
        repo = ProjectRepository(in_memory_db)
        pid = str(uuid.uuid4())
        project = Project(id=pid, name="to-delete")
        in_memory_db.add(project)
        in_memory_db.commit()

        success, error, result = repo.delete_project(pid)
        assert success is True
        assert result is not None

        # Verify deletion
        from sqlalchemy import select

        q = select(Project).where(Project.id == pid)
        assert in_memory_db.execute(q).scalars().first() is None

    def test_delete_project_not_found(self, in_memory_db):
        """Test deleting non-existent project."""
        repo = ProjectRepository(in_memory_db)
        success, error, result = repo.delete_project(str(uuid.uuid4()))
        assert success is False
        assert result is None

    def test_delete_project_invalid_uuid(self, in_memory_db):
        """Test deleting project with invalid UUID."""
        repo = ProjectRepository(in_memory_db)
        success, error, result = repo.delete_project("invalid-uuid")
        assert success is False
        assert result is None

    def test_project_exists_true(self, in_memory_db):
        """Test project_exists returns True for existing project."""
        repo = ProjectRepository(in_memory_db)
        pid = str(uuid.uuid4())
        project = Project(id=pid, name="exists")
        in_memory_db.add(project)
        in_memory_db.commit()

        assert repo.project_exists(pid) is True

    def test_project_exists_false(self, in_memory_db):
        """Test project_exists returns False for non-existent project."""
        repo = ProjectRepository(in_memory_db)
        assert repo.project_exists(str(uuid.uuid4())) is False

    def test_project_exists_invalid_uuid(self, in_memory_db):
        """Test project_exists returns False for invalid UUID."""
        repo = ProjectRepository(in_memory_db)
        assert repo.project_exists("invalid-uuid") is False

    def test_project_exists_db_error(self, mock_db_session):
        """Test project_exists handles database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = ProjectRepository(mock_db_session)
        assert repo.project_exists(str(uuid.uuid4())) is False
