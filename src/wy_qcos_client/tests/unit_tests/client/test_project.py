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

from unittest.mock import patch

from wy_qcos_client.client import Client

client = Client()


class TestClientProject:
    """Test cases for project management API methods in Client."""

    @classmethod
    def setup_class(cls):
        cls.project_id = "00000000-0000-4000-8000-000000000002"
        cls.return_values = (200, "OK", "text", "result")

    @patch.object(Client, "call_json_rpc")
    def test_create_project_basic(self, mock_call_json_rpc):
        """Test create_project method with basic parameters."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.create_project(
            project_name="new_project"
        )
        assert status_code == 200
        assert reason == "OK"
        mock_call_json_rpc.assert_called_once()
        call_args = mock_call_json_rpc.call_args[0]
        assert call_args[0] == client.project_url
        assert call_args[1] == "create_project"
        data = call_args[2]
        assert data["project_name"] == "new_project"
        assert "description" not in data

    @patch.object(Client, "call_json_rpc")
    def test_create_project_with_description(self, mock_call_json_rpc):
        """Test create_project method with description."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.create_project(
            project_name="new_project",
            description="Project description",
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        assert data["project_name"] == "new_project"
        assert data["description"] == "Project description"

    @patch.object(Client, "call_json_rpc")
    def test_create_project_empty_description(self, mock_call_json_rpc):
        """Test create_project with empty description string."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.create_project(
            project_name="new_project",
            description="",
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        # Empty string should still be included
        assert data["description"] == ""

    @patch.object(Client, "call_json_rpc")
    def test_create_project_none_description(self, mock_call_json_rpc):
        """Test create_project with None description."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.create_project(
            project_name="new_project",
            description=None,
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        # None should not be included in data
        assert "description" not in data

    @patch.object(Client, "call_json_rpc")
    def test_get_project(self, mock_call_json_rpc):
        """Test get_project method."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_project(self.project_id)
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.project_url, "get_project", {"project_id": self.project_id}
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_projects_without_filter(self, mock_call_json_rpc):
        """Test get_projects method without filter."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_projects()
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.project_url, "get_projects", {}
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_projects_with_name_filter(self, mock_call_json_rpc):
        """Test get_projects method with name filter."""
        mock_call_json_rpc.return_value = self.return_values
        filters = {"name": "test_project"}
        status_code, reason, text, result = client.get_projects(
            filters=filters
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        assert call_args[1] == "get_projects"
        data = call_args[2]
        assert data["filters"] == filters
        assert data["filters"]["name"] == "test_project"

    @patch.object(Client, "call_json_rpc")
    def test_get_projects_with_multiple_filters(self, mock_call_json_rpc):
        """Test get_projects method with multiple filters."""
        mock_call_json_rpc.return_value = self.return_values
        filters = {"name": "test_project", "status": "active"}
        status_code, reason, text, result = client.get_projects(
            filters=filters
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        assert data["filters"] == filters

    @patch.object(Client, "call_json_rpc")
    def test_get_projects_with_empty_filter(self, mock_call_json_rpc):
        """Test get_projects method with empty filter dict."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_projects(filters={})
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        # Empty filter should not be included
        assert "filters" not in data

    @patch.object(Client, "call_json_rpc")
    def test_update_project_name_only(self, mock_call_json_rpc):
        """Test update_project method with name only."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.update_project(
            project_id=self.project_id,
            project_name="updated_project",
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        assert call_args[1] == "update_project"
        data = call_args[2]
        assert data["project_id"] == self.project_id
        assert data["project_name"] == "updated_project"
        assert "description" not in data

    @patch.object(Client, "call_json_rpc")
    def test_update_project_description_only(self, mock_call_json_rpc):
        """Test update_project method with description only."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.update_project(
            project_id=self.project_id,
            description="Updated description",
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        assert data["project_id"] == self.project_id
        assert data["description"] == "Updated description"
        assert "project_name" not in data

    @patch.object(Client, "call_json_rpc")
    def test_update_project_both_fields(self, mock_call_json_rpc):
        """Test update_project method with both name and description."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.update_project(
            project_id=self.project_id,
            project_name="updated_project",
            description="Updated description",
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        assert data["project_id"] == self.project_id
        assert data["project_name"] == "updated_project"
        assert data["description"] == "Updated description"

    @patch.object(Client, "call_json_rpc")
    def test_update_project_id_only(self, mock_call_json_rpc):
        """Test update_project method with only project_id."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.update_project(
            project_id=self.project_id
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        assert data["project_id"] == self.project_id
        assert "project_name" not in data
        assert "description" not in data

    @patch.object(Client, "call_json_rpc")
    def test_update_project_empty_description(self, mock_call_json_rpc):
        """Test update_project with empty description."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.update_project(
            project_id=self.project_id,
            description="",
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        # Empty string should be included
        assert data["description"] == ""

    @patch.object(Client, "call_json_rpc")
    def test_delete_project(self, mock_call_json_rpc):
        """Test delete_project method."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.delete_project(
            self.project_id
        )
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.project_url,
            "delete_project",
            {"project_id": self.project_id},
        )

    @patch.object(Client, "call_json_rpc")
    def test_delete_project_different_id(self, mock_call_json_rpc):
        """Test delete_project with different project ID."""
        mock_call_json_rpc.return_value = self.return_values
        different_id = "00000000-0000-4000-8000-000000000999"
        status_code, reason, text, result = client.delete_project(different_id)
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        data = call_args[2]
        assert data["project_id"] == different_id
