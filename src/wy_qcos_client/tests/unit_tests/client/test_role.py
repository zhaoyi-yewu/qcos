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


class TestClientRole:
    """Test cases for role management API methods in Client."""

    @classmethod
    def setup_class(cls):
        cls.role_id = "10000000-0000-4000-8000-000000000001"
        cls.return_values = (200, "OK", "text", "result")

    @patch.object(Client, "call_json_rpc")
    def test_create_role_basic(self, mock_call_json_rpc):
        """Test create_role method with basic parameters."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.create_role(
            role_name="test_role",
            permissions=["read", "write"],
        )
        assert status_code == 200
        call_args = mock_call_json_rpc.call_args[0]
        assert call_args[1] == "create_role"
        data = call_args[2]
        assert data["role_name"] == "test_role"
        assert data["permissions"] == ["read", "write"]

    @patch.object(Client, "call_json_rpc")
    def test_create_role_with_description(self, mock_call_json_rpc):
        """Test create_role method with description."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.create_role(
            role_name="test_role",
            permissions=["read"],
            description="Test role description",
        )
        assert status_code == 200
        data = mock_call_json_rpc.call_args[0][2]
        assert data["description"] == "Test role description"

    @patch.object(Client, "call_json_rpc")
    def test_get_role(self, mock_call_json_rpc):
        """Test get_role method."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_role(self.role_id)
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.user_url, "get_role", {"role_id": self.role_id}
        )

    @patch.object(Client, "call_json_rpc")
    def test_update_role_basic(self, mock_call_json_rpc):
        """Test update_role method with basic parameters."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.update_role(
            role_id=self.role_id,
            permissions=["read", "write", "delete"],
        )
        assert status_code == 200
        data = mock_call_json_rpc.call_args[0][2]
        assert data["role_id"] == self.role_id
        assert data["permissions"] == ["read", "write", "delete"]

    @patch.object(Client, "call_json_rpc")
    def test_update_role_with_description(self, mock_call_json_rpc):
        """Test update_role method with description."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.update_role(
            role_id=self.role_id,
            permissions=["admin"],
            description="Updated role",
        )
        assert status_code == 200
        data = mock_call_json_rpc.call_args[0][2]
        assert data["description"] == "Updated role"

    @patch.object(Client, "call_json_rpc")
    def test_delete_role(self, mock_call_json_rpc):
        """Test delete_role method."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.delete_role(self.role_id)
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.user_url, "delete_role", {"role_id": self.role_id}
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_roles(self, mock_call_json_rpc):
        """Test get_roles method."""
        mock_call_json_rpc.return_value = self.return_values
        status_code, reason, text, result = client.get_roles()
        assert status_code == 200
        mock_call_json_rpc.assert_called_once_with(
            client.user_url, "get_roles", {}
        )
