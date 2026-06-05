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

import pytest

from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
class TestProject:
    """Project management system tests."""

    test_project_names = [
        "test_get_current_project",
        "test_project_creation",
        "test_project_with_description",
        "test_project_original",
        "test_project_update_name",
        "test_project_update_description",
        "test_project_listing",
        "test_project_deletion",
        "test_project_timestamps",
    ]

    @classmethod
    def _cleanup_test_projects(cls):
        """Clean up test projects."""
        try:
            projects = StLibrary.get_projects(cls.admin_client)
            for project_id, project_info in projects.items():
                project_name = project_info["name"]
                if project_name in cls.test_project_names:
                    StLibrary.delete_project(cls.admin_client, project_id)
        except Exception:  # noqa: S110
            pass

    @classmethod
    def setup_class(cls):
        """Initialize test environment."""
        cls.client = GLOBAL_CONFIGS["client"]
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]

        # Admin credentials for cleanup operations
        cls.admin_user = GLOBAL_CONFIGS["admin_user"]
        cls.admin_password = GLOBAL_CONFIGS["admin_password"]

        # Initialize and clean up test resources
        cls._cleanup_test_projects()

    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        cls._cleanup_test_projects()

    @pytest.mark.smoke
    def test_create_project_basic(self):
        """Test creating a basic project."""
        project_name = "test_project_creation"

        _project_info = StLibrary.create_project(
            self.admin_client, project_name
        )
        project_id = _project_info.get("id")
        project_info, _ = StLibrary.get_project(self.admin_client, project_id)
        assert project_info.get("name") == project_name

    @pytest.mark.smoke
    def test_create_project_with_description(self):
        """Test creating project with description."""
        project_name = "test_project_with_description"
        description = "This is a test project with description"

        # Create project with description
        _project_info = StLibrary.create_project(
            self.admin_client, project_name, description
        )

        project_id = _project_info.get("id")
        project_info, _ = StLibrary.get_project(self.admin_client, project_id)
        assert project_info.get("name") == project_name
        assert project_info.get("description") == description

    @pytest.mark.smoke
    def test_get_projects_list(self):
        """Test getting list of all projects."""
        project_name = "test_project_listing"

        # Create a test project
        _project_info = StLibrary.create_project(
            self.admin_client, project_name
        )
        created_project_id = _project_info.get("id")

        # Get all projects
        projects = StLibrary.get_projects(self.admin_client)
        assert created_project_id in projects
        assert projects[created_project_id].get("name") == project_name

    @pytest.mark.smoke
    def test_update_project_name(self):
        """Test updating project name."""
        original_name = "test_project_original"
        updated_name = "test_project_update_name"

        # Create a test project
        _project_info = StLibrary.create_project(
            self.admin_client, original_name
        )
        project_id = _project_info.get("id")

        # Update project name
        _project_info = StLibrary.update_project(
            self.admin_client, project_id, updated_name
        )

        # Verify project name is updated
        project_info, _ = StLibrary.get_project(self.admin_client, project_id)
        assert project_info.get("name") == updated_name

    @pytest.mark.smoke
    def test_update_project_description(self):
        """Test updating project description."""
        project_name = "test_project_update_description"
        original_description = "Original description"
        updated_description = "Updated description"

        # Create project with description
        _project_info = StLibrary.create_project(
            self.admin_client, project_name, description=original_description
        )
        project_id = _project_info.get("id")

        # Update project description
        _project_info = StLibrary.update_project(
            self.admin_client, project_id, description=updated_description
        )

        # Verify project description is updated
        project_info, _ = StLibrary.get_project(self.admin_client, project_id)
        assert project_info.get("description") == updated_description

    @pytest.mark.smoke
    def test_delete_project(self):
        """Test deleting a project."""
        project_name = "test_project_deletion"

        # Create project
        _project_info = StLibrary.create_project(
            self.admin_client, project_name
        )
        project_id = _project_info.get("id")

        # Delete project
        StLibrary.delete_project(self.admin_client, project_id)

        # Verify project is deleted
        project_info, error_info = StLibrary.get_project(
            self.admin_client, project_id
        )
        assert "not found" in error_info.get("data", {}).get("details", "")

    @pytest.mark.smoke
    def test_project_timestamps(self):
        """Test project creation and update timestamps."""
        project_name = "test_project_timestamps"

        # Create project
        _project_info = StLibrary.create_project(
            self.admin_client, project_name
        )
        project_id = _project_info.get("id")
        created_at = _project_info.get("created_at")
        updated_at = _project_info.get("updated_at")

        # Verify timestamps exist
        assert created_at is not None
        assert updated_at is not None

        # Get project and verify timestamps
        project_info, _ = StLibrary.get_project(self.admin_client, project_id)
        assert project_info.get("created_at") is not None
        assert project_info.get("updated_at") is not None

    @pytest.mark.smoke
    def test_project_properties(self):
        """Test project properties and fields."""
        project_name = "test_get_current_project"
        description = "Test project properties"

        # Create project
        _project_info = StLibrary.create_project(
            self.admin_client, project_name, description=description
        )
        project_id = _project_info.get("id")

        # Verify all project properties
        assert project_id is not None
        assert _project_info.get("name") == project_name
        assert _project_info.get("description") == description
        assert _project_info.get("created_at") is not None
        assert _project_info.get("updated_at") is not None

        # Get project and verify all properties
        project_info, _ = StLibrary.get_project(self.admin_client, project_id)
        assert project_info.get("id") == project_id
        assert project_info.get("name") == project_name
        assert project_info.get("description") == description
