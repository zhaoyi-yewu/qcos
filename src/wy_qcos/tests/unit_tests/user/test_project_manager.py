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

from types import SimpleNamespace
from unittest.mock import Mock
import uuid

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.user.project_manager import ProjectManager


class TestProjectManager:
    @pytest.fixture
    def project_manager(self):
        mock_repo = Mock()
        manager = ProjectManager(projects_repo=mock_repo)
        return manager, mock_repo

    def test_validate_project_name_valid(self, project_manager):
        manager, _ = project_manager
        manager.validate_project_name("project_1")

    def test_validate_project_name_too_short(self, project_manager):
        manager, _ = project_manager

        with pytest.raises(ValueError, match="too short"):
            manager.validate_project_name("a")

    def test_validate_project_name_too_long(self, project_manager):
        manager, _ = project_manager
        name = "a" * (Constant.MAX_PROJECT_LENGTH + 1)

        with pytest.raises(ValueError, match="too long"):
            manager.validate_project_name(name)

    def test_validate_project_name_startswith_underscore(
        self, project_manager
    ):
        manager, _ = project_manager

        with pytest.raises(ValueError, match="cannot start with underscore"):
            manager.validate_project_name("_project")

    def test_validate_project_name_invalid_chars(self, project_manager):
        manager, _ = project_manager

        with pytest.raises(ValueError, match="is invalid"):
            manager.validate_project_name("project name")

    def test_validate_description_too_long(self, project_manager):
        manager, _ = project_manager
        description = "d" * (Constant.MAX_DESCRIPTION_LENGTH + 1)

        with pytest.raises(ValueError, match="Description is too long"):
            manager.validate_description(description)

    def test_create_project_success_with_auto_uuid(self, project_manager):
        manager, mock_repo = project_manager
        project = SimpleNamespace(id=str(uuid.uuid4()), name="demo")
        mock_repo.get_project_by_name.return_value = (False, None, None)
        mock_repo.create_project.return_value = (True, None, project)

        result = manager.create_project("demo", "desc")

        assert result is project
        create_args = mock_repo.create_project.call_args[0]
        assert create_args[1] == "demo"
        assert create_args[2] == "desc"
        uuid.UUID(create_args[0])
        assert manager.projects_db["demo"] is project
        assert manager._project_name_to_id["demo"] == project.id

    def test_create_project_invalid_uuid(self, project_manager):
        manager, _ = project_manager

        with pytest.raises(ValueError, match="Invalid project ID"):
            manager.create_project("demo", project_id="invalid-uuid")

    def test_create_project_duplicate_name(self, project_manager):
        manager, mock_repo = project_manager
        mock_repo.get_project_by_name.return_value = (
            True,
            None,
            SimpleNamespace(id="1", name="demo"),
        )

        with pytest.raises(ValueError, match="already exists"):
            manager.create_project("demo")

    def test_create_project_repo_failure(self, project_manager):
        manager, mock_repo = project_manager
        mock_repo.get_project_by_name.return_value = (False, None, None)
        mock_repo.create_project.return_value = (False, "db error", None)

        with pytest.raises(ValueError, match="Failed to create project"):
            manager.create_project("demo")

    def test_update_project_duplicate_new_name(self, project_manager):
        manager, mock_repo = project_manager
        old_project = SimpleNamespace(id="1", name="old_name")
        manager.get_project_by_id = Mock(return_value=old_project)
        mock_repo.get_project_by_name.return_value = (
            True,
            None,
            SimpleNamespace(id="2", name="new_name"),
        )

        with pytest.raises(ValueError, match="already exists"):
            manager.update_project("1", project_name="new_name")

    def test_update_project_success_renames_internal_cache(
        self, project_manager
    ):
        manager, mock_repo = project_manager
        old_project = SimpleNamespace(id="1", name="old_name")
        updated_project = SimpleNamespace(id="1", name="new_name")
        manager.get_project_by_id = Mock(return_value=old_project)
        manager.projects_db["old_name"] = old_project
        manager._project_name_to_id["old_name"] = "1"
        mock_repo.get_project_by_name.return_value = (False, None, None)
        mock_repo.update_project.return_value = (True, None, updated_project)

        result = manager.update_project(
            "1",
            project_name="new_name",
            description="updated",
        )

        assert result is updated_project
        assert "old_name" not in manager.projects_db
        assert manager.projects_db["new_name"] is updated_project
        assert manager._project_name_to_id["new_name"] == "1"

    def test_get_projects_with_filters(self, project_manager):
        manager, mock_repo = project_manager
        project_1 = SimpleNamespace(id="1", name="alpha", description="a")
        project_2 = SimpleNamespace(id="2", name="beta", description="b")
        mock_repo.get_projects.return_value = (
            True,
            None,
            [project_1, project_2],
        )

        result = manager.get_projects(filters={"name": "alpha"})

        assert result == {"1": project_1}

    def test_get_projects_with_unknown_filter_attr(self, project_manager):
        manager, mock_repo = project_manager
        project = SimpleNamespace(id="1", name="alpha")
        mock_repo.get_projects.return_value = (True, None, [project])

        result = manager.get_projects(filters={"missing": "value"})

        assert result == {}

    def test_delete_project_reserved_project(self, project_manager):
        manager, _ = project_manager
        reserved_project = SimpleNamespace(
            id=Constant.ADMIN_PROJECT_ID,
            name=Constant.ADMIN_PROJECT_NAME,
        )
        manager.get_project_by_id = Mock(return_value=reserved_project)

        with pytest.raises(ValueError, match="Cannot delete reserved project"):
            manager.delete_project(Constant.ADMIN_PROJECT_ID)

    def test_delete_project_success_clears_cache(self, project_manager):
        manager, mock_repo = project_manager
        project = SimpleNamespace(id="1", name="demo")
        manager.get_project_by_id = Mock(return_value=project)
        manager.projects_db["demo"] = project
        manager._project_name_to_id["demo"] = "1"
        mock_repo.delete_project.return_value = (True, None, project)

        result = manager.delete_project("1")

        assert result is project
        assert "demo" not in manager.projects_db
        assert "demo" not in manager._project_name_to_id

    def test_find_projects_by_name(self, project_manager):
        manager, mock_repo = project_manager
        project_1 = SimpleNamespace(id="1", name="AlphaProject")
        project_2 = SimpleNamespace(id="2", name="beta")
        project_3 = SimpleNamespace(id="3", name="ALPHA-2")
        mock_repo.get_projects.return_value = (
            True,
            None,
            [project_1, project_2, project_3],
        )

        result = manager.find_projects_by_name("alpha")

        assert result == ["AlphaProject", "ALPHA-2"]
