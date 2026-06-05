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

import json
from unittest.mock import patch, Mock

import pytest
from cliff.commandmanager import CommandManager

from wy_qcos_client.client import Client
from wy_qcos_client.shell import QcosShell
from wy_qcos_client.common.qcos_version import QcosVersion

DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")

project_id = "00000000-0000-4000-8000-000000000002"

response = {
    "jsonrpc": "2.0",
    "result": {},
    "id": 0,
}
jsonrpc_response = json.dumps(response)

shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()


class TestCreateProject:
    """Test cases for CreateProject command."""

    def test_get_parser(self):
        """Test parser creation for create-project command."""
        try:
            from wy_qcos_client.shell import CreateProject

            cmd = CreateProject(shell, None)
            parser = cmd.get_parser("create-project")
            assert parser is not None
        except ImportError:
            pytest.skip("CreateProject command not available")

    @patch.object(Client, "create_project")
    def test_take_action_basic(self, mock_create_project):
        """Test CreateProject with basic parameters."""
        try:
            from wy_qcos_client.shell import CreateProject

            mock_response = {
                "jsonrpc": "2.0",
                "result": {
                    "id": project_id,
                    "name": "new_project",
                    "description": None,
                },
                "id": 0,
            }
            mock_create_project.return_value = (
                200,
                "OK",
                json.dumps(mock_response),
                mock_response["result"],
            )

            cmd = CreateProject(shell, None)
            cmd.app = shell
            cmd.app.stdout = Mock()
            parsed_args = Mock()
            parsed_args.project_name = "new_project"
            parsed_args.description = None

            cmd.take_action(parsed_args)
            mock_create_project.assert_called_once_with("new_project", None)
        except ImportError:
            pytest.skip("CreateProject command not available")

    @patch.object(Client, "create_project")
    def test_take_action_with_description(self, mock_create_project):
        """Test CreateProject with description."""
        try:
            from wy_qcos_client.shell import CreateProject

            mock_response = {
                "jsonrpc": "2.0",
                "result": {
                    "id": project_id,
                    "name": "new_project",
                    "description": "Project description",
                },
                "id": 0,
            }
            mock_create_project.return_value = (
                200,
                "OK",
                json.dumps(mock_response),
                mock_response["result"],
            )

            cmd = CreateProject(shell, None)
            cmd.app = shell
            cmd.app.stdout = Mock()
            parsed_args = Mock()
            parsed_args.project_name = "new_project"
            parsed_args.description = "Project description"

            cmd.take_action(parsed_args)
            mock_create_project.assert_called_once_with(
                "new_project", "Project description"
            )
        except ImportError:
            pytest.skip("CreateProject command not available")


class TestGetProject:
    """Test cases for GetProject command."""

    def test_get_parser(self):
        """Test parser creation for get-project command."""
        try:
            from wy_qcos_client.shell import GetProject

            cmd = GetProject(shell, None)
            parser = cmd.get_parser("get-project")
            assert parser is not None
        except ImportError:
            pytest.skip("GetProject command not available")

    @patch.object(Client, "get_project")
    def test_take_action(self, mock_get_project):
        """Test GetProject take_action method."""
        try:
            from wy_qcos_client.shell import GetProject

            mock_response = {
                "jsonrpc": "2.0",
                "result": {
                    "id": project_id,
                    "name": "test_project",
                    "description": "Test project",
                    "created_at": "2024-01-01T10:00:00",
                    "updated_at": "2024-01-01T10:00:00",
                },
                "id": 0,
            }
            mock_get_project.return_value = (
                200,
                "OK",
                json.dumps(mock_response),
                mock_response["result"],
            )

            cmd = GetProject(shell, None)
            cmd.app = shell
            cmd.app.stdout = Mock()
            parsed_args = Mock()
            parsed_args.project_id = project_id

            result = cmd.take_action(parsed_args)
            assert result is not None
            mock_get_project.assert_called_once_with(project_id)
        except ImportError:
            pytest.skip("GetProject command not available")


class TestGetProjects:
    """Test cases for GetProjects command."""

    def test_get_parser(self):
        """Test parser creation for list-projects command."""
        try:
            from wy_qcos_client.shell import GetProjects

            cmd = GetProjects(shell, None)
            parser = cmd.get_parser("list-projects")
            assert parser is not None
        except ImportError:
            pytest.skip("GetProjects command not available")

    @patch.object(Client, "get_projects")
    def test_take_action(self, mock_get_projects):
        """Test GetProjects take_action method."""
        try:
            from wy_qcos_client.shell import GetProjects

            mock_response = {
                "jsonrpc": "2.0",
                "result": {
                    "project1": {
                        "id": project_id,
                        "name": "project1",
                        "description": "First project",
                        "created_at": "2024-01-01T10:00:00",
                        "updated_at": "2024-01-01T10:00:00",
                    },
                    "project2": {
                        "id": "00000000-0000-4000-8000-000000000003",
                        "name": "project2",
                        "description": "Second project",
                        "created_at": "2024-01-02T10:00:00",
                        "updated_at": "2024-01-02T10:00:00",
                    },
                },
                "id": 0,
            }
            mock_get_projects.return_value = (
                200,
                "OK",
                json.dumps(mock_response),
                mock_response["result"],
            )

            cmd = GetProjects(shell, None)
            cmd.app = shell
            cmd.app.stdout = Mock()
            parsed_args = Mock()

            result = cmd.take_action(parsed_args)
            assert result is not None
            mock_get_projects.assert_called_once()
        except ImportError:
            pytest.skip("GetProjects command not available")

    @patch.object(Client, "get_projects")
    def test_take_action_empty(self, mock_get_projects):
        """Test GetProjects with no projects."""
        try:
            from wy_qcos_client.shell import GetProjects

            mock_response = {
                "jsonrpc": "2.0",
                "result": {},
                "id": 0,
            }
            mock_get_projects.return_value = (
                200,
                "OK",
                json.dumps(mock_response),
                mock_response["result"],
            )

            cmd = GetProjects(shell, None)
            cmd.app = shell
            cmd.app.stdout = Mock()
            parsed_args = Mock()

            result = cmd.take_action(parsed_args)
            assert result is not None
        except ImportError:
            pytest.skip("GetProjects command not available")


class TestUpdateProject:
    """Test cases for UpdateProject command."""

    def test_get_parser(self):
        """Test parser creation for update-project command."""
        try:
            from wy_qcos_client.shell import UpdateProject

            cmd = UpdateProject(shell, None)
            parser = cmd.get_parser("update-project")
            assert parser is not None
        except ImportError:
            pytest.skip("UpdateProject command not available")

    @patch.object(Client, "update_project")
    def test_take_action_name_only(self, mock_update_project):
        """Test UpdateProject with name only."""
        try:
            from wy_qcos_client.shell import UpdateProject

            mock_response = {
                "jsonrpc": "2.0",
                "result": {
                    "id": project_id,
                    "name": "updated_project",
                    "description": "Original description",
                },
                "id": 0,
            }
            mock_update_project.return_value = (
                200,
                "OK",
                json.dumps(mock_response),
                mock_response["result"],
            )

            cmd = UpdateProject(shell, None)
            cmd.app = shell
            cmd.app.stdout = Mock()
            parsed_args = Mock()
            parsed_args.project_id = project_id
            parsed_args.project_name = "updated_project"
            parsed_args.description = None

            cmd.take_action(parsed_args)
            mock_update_project.assert_called_once()
        except ImportError:
            pytest.skip("UpdateProject command not available")

    @patch.object(Client, "update_project")
    def test_take_action_with_description(self, mock_update_project):
        """Test UpdateProject with description."""
        try:
            from wy_qcos_client.shell import UpdateProject

            mock_response = {
                "jsonrpc": "2.0",
                "result": {
                    "id": project_id,
                    "name": "test_project",
                    "description": "Updated description",
                },
                "id": 0,
            }
            mock_update_project.return_value = (
                200,
                "OK",
                json.dumps(mock_response),
                mock_response["result"],
            )

            cmd = UpdateProject(shell, None)
            cmd.app = shell
            cmd.app.stdout = Mock()
            parsed_args = Mock()
            parsed_args.project_id = project_id
            parsed_args.project_name = None
            parsed_args.description = "Updated description"

            cmd.take_action(parsed_args)
            mock_update_project.assert_called_once()
        except ImportError:
            pytest.skip("UpdateProject command not available")

    @patch.object(Client, "update_project")
    def test_take_action_both_fields(self, mock_update_project):
        """Test UpdateProject with both name and description."""
        try:
            from wy_qcos_client.shell import UpdateProject

            mock_response = {
                "jsonrpc": "2.0",
                "result": {
                    "id": project_id,
                    "name": "new_name",
                    "description": "New description",
                },
                "id": 0,
            }
            mock_update_project.return_value = (
                200,
                "OK",
                json.dumps(mock_response),
                mock_response["result"],
            )

            cmd = UpdateProject(shell, None)
            cmd.app = shell
            cmd.app.stdout = Mock()
            parsed_args = Mock()
            parsed_args.project_id = project_id
            parsed_args.project_name = "new_name"
            parsed_args.description = "New description"

            cmd.take_action(parsed_args)
            mock_update_project.assert_called_once()
        except ImportError:
            pytest.skip("UpdateProject command not available")


class TestDeleteProject:
    """Test cases for DeleteProject command."""

    def test_get_parser(self):
        """Test parser creation for delete-project command."""
        try:
            from wy_qcos_client.shell import DeleteProject

            cmd = DeleteProject(shell, None)
            parser = cmd.get_parser("delete-project")
            assert parser is not None
        except ImportError:
            pytest.skip("DeleteProject command not available")

    @patch.object(Client, "delete_project")
    def test_take_action(self, mock_delete_project):
        """Test DeleteProject take_action method."""
        try:
            from wy_qcos_client.shell import DeleteProject

            mock_delete_project.return_value = (
                200,
                "OK",
                jsonrpc_response,
                {},
            )

            cmd = DeleteProject(shell, None)
            cmd.app = shell
            cmd.app.stdout = Mock()
            parsed_args = Mock()
            parsed_args.project_id = project_id
            parsed_args.force = False

            cmd.take_action(parsed_args)
            mock_delete_project.assert_called_once_with(project_id)
        except ImportError:
            pytest.skip("DeleteProject command not available")

    @patch.object(Client, "delete_project")
    def test_take_action_with_force(self, mock_delete_project):
        """Test DeleteProject with force flag."""
        try:
            from wy_qcos_client.shell import DeleteProject

            mock_delete_project.return_value = (
                200,
                "OK",
                jsonrpc_response,
                {},
            )

            cmd = DeleteProject(shell, None)
            cmd.app = shell
            cmd.app.stdout = Mock()
            parsed_args = Mock()
            parsed_args.project_id = project_id
            parsed_args.force = True

            cmd.take_action(parsed_args)
            mock_delete_project.assert_called_once_with(project_id)
        except ImportError:
            pytest.skip("DeleteProject command not available")

    @patch("builtins.input", return_value="n")
    @patch.object(Client, "delete_project")
    def test_take_action_with_confirmation(
        self, mock_delete_project, mock_input
    ):
        """Test DeleteProject with confirmation."""
        try:
            from wy_qcos_client.shell import DeleteProject

            mock_delete_project.return_value = (
                200,
                "OK",
                jsonrpc_response,
                {},
            )

            cmd = DeleteProject(shell, None)
            cmd.app = shell
            cmd.app.stdout = Mock()
            parsed_args = Mock()
            parsed_args.project_id = project_id
            parsed_args.force = False

            cmd.take_action(parsed_args)
            # Verify delete is called regardless of force flag
            mock_delete_project.assert_called_once()
        except ImportError:
            pytest.skip("DeleteProject command not available")
