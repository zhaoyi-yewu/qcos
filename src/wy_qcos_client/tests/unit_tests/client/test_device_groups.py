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

import uuid
from unittest.mock import patch

from wy_qcos_client.client import Client


client = Client()

GROUP_ID = "00000000-0000-4000-8000-000000000001"
PROJECT_ID = "00000000-0000-4000-8000-000000000002"


class TestClientDeviceGroup:
    """Test cases for device group API methods in Client."""

    @classmethod
    def setup_class(cls):
        cls.return_values = (200, "OK", "text", "result")

    # --------------------------------------------------------------- #
    # create_device_group
    # --------------------------------------------------------------- #
    @patch.object(Client, "call_json_rpc")
    def test_create_device_group_basic(self, mock_call):
        mock_call.return_value = self.return_values
        client.create_device_group(name="test-group", device_names=None)
        call_args = mock_call.call_args[0]
        assert call_args[0] == client.job_url
        assert call_args[1] == "create_device_group"
        data = call_args[2]
        assert data["name"] == "test-group"
        assert data["is_public"] is True
        assert "description" not in data
        assert "device_names" not in data
        assert "project_id" not in data

    @patch.object(Client, "call_json_rpc")
    def test_create_device_group_all_params(self, mock_call):
        mock_call.return_value = self.return_values
        client.create_device_group(
            name="full-group",
            project_id=PROJECT_ID,
            description="desc",
            device_names=["dev1", "dev2"],
            is_public=False,
        )
        data = mock_call.call_args[0][2]
        assert data["name"] == "full-group"
        assert data["project_id"] == PROJECT_ID
        assert data["description"] == "desc"
        assert data["device_names"] == ["dev1", "dev2"]
        assert data["is_public"] is False

    @patch.object(Client, "call_json_rpc")
    def test_create_device_group_none_omitted(self, mock_call):
        mock_call.return_value = self.return_values
        client.create_device_group(
            name="basic",
            project_id=None,
            description=None,
            device_names=None,
            is_public=True,
        )
        data = mock_call.call_args[0][2]
        assert "project_id" not in data
        assert "description" not in data
        assert "device_names" not in data

    @patch.object(Client, "call_json_rpc")
    def test_create_device_group_empty_description(self, mock_call):
        mock_call.return_value = self.return_values
        client.create_device_group(name="x", description="", device_names=[])
        data = mock_call.call_args[0][2]
        assert "description" not in data

    # --------------------------------------------------------------- #
    # update_device_group
    # --------------------------------------------------------------- #
    @patch.object(Client, "call_json_rpc")
    def test_update_device_group_basic(self, mock_call):
        mock_call.return_value = self.return_values
        client.update_device_group(group_id=GROUP_ID)
        call_args = mock_call.call_args[0]
        assert call_args[1] == "update_device_group"
        data = call_args[2]
        assert data["group_id"] == GROUP_ID

    @patch.object(Client, "call_json_rpc")
    def test_update_device_group_all_params(self, mock_call):
        mock_call.return_value = self.return_values
        client.update_device_group(
            group_id=GROUP_ID,
            name="updated",
            description="new",
            device_names=["dev1"],
            is_public=False,
            project_id=PROJECT_ID,
        )
        data = mock_call.call_args[0][2]
        assert data["name"] == "updated"
        assert data["description"] == "new"
        assert data["device_names"] == ["dev1"]
        assert data["is_public"] is False
        assert data["project_id"] == PROJECT_ID

    @patch.object(Client, "call_json_rpc")
    def test_update_device_group_none_omitted(self, mock_call):
        mock_call.return_value = self.return_values
        client.update_device_group(
            group_id=GROUP_ID,
            name=None,
            description=None,
            device_names=None,
            is_public=None,
            project_id=None,
        )
        data = mock_call.call_args[0][2]
        assert data == {"group_id": GROUP_ID}

    @patch.object(Client, "call_json_rpc")
    def test_update_device_group_returns_values(self, mock_call):
        mock_call.return_value = (201, "Created", "resp", "data")
        sc, reason, text, result = client.update_device_group(GROUP_ID)
        assert sc == 201
        assert reason == "Created"

    # --------------------------------------------------------------- #
    # get_device_group
    # --------------------------------------------------------------- #
    @patch.object(Client, "call_json_rpc")
    def test_get_device_group(self, mock_call):
        mock_call.return_value = self.return_values
        client.get_device_group(GROUP_ID)
        mock_call.assert_called_once_with(
            client.job_url,
            "get_device_group",
            {"group_id": GROUP_ID},
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_device_group_uuid_object(self, mock_call):
        mock_call.return_value = self.return_values
        uid = uuid.UUID(GROUP_ID)
        client.get_device_group(uid)
        data = mock_call.call_args[0][2]
        assert data["group_id"] == GROUP_ID

    # --------------------------------------------------------------- #
    # get_device_groups
    # --------------------------------------------------------------- #
    @patch.object(Client, "call_json_rpc")
    def test_get_device_groups_no_filter(self, mock_call):
        mock_call.return_value = self.return_values
        client.get_device_groups()
        mock_call.assert_called_once_with(
            client.job_url, "get_device_groups", {}
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_device_groups_with_filter(self, mock_call):
        mock_call.return_value = self.return_values
        client.get_device_groups(filters={"group_name": "my-group"})
        data = mock_call.call_args[0][2]
        assert data["filters"] == {"group_name": "my-group"}

    @patch.object(Client, "call_json_rpc")
    def test_get_device_groups_none_filter(self, mock_call):
        mock_call.return_value = self.return_values
        client.get_device_groups(filters=None)
        data = mock_call.call_args[0][2]
        assert "filters" not in data

    # --------------------------------------------------------------- #
    # delete_device_groups (batch)
    # --------------------------------------------------------------- #
    @patch.object(Client, "call_json_rpc")
    def test_delete_device_groups_single(self, mock_call):
        mock_call.return_value = self.return_values
        client.delete_device_groups([GROUP_ID])
        mock_call.assert_called_once_with(
            client.job_url,
            "delete_device_groups",
            {"group_ids": [GROUP_ID]},
        )

    @patch.object(Client, "call_json_rpc")
    def test_delete_device_groups_multiple(self, mock_call):
        mock_call.return_value = self.return_values
        second_id = "00000000-0000-4000-8000-000000000003"
        client.delete_device_groups([GROUP_ID, second_id])
        data = mock_call.call_args[0][2]
        assert data["group_ids"] == [GROUP_ID, second_id]

    @patch.object(Client, "call_json_rpc")
    def test_delete_device_groups_uuid_object(self, mock_call):
        mock_call.return_value = self.return_values
        uid = uuid.UUID(GROUP_ID)
        client.delete_device_groups([uid])
        data = mock_call.call_args[0][2]
        assert data["group_ids"] == [GROUP_ID]

    @patch.object(Client, "call_json_rpc")
    def test_delete_device_groups_empty_list(self, mock_call):
        mock_call.return_value = self.return_values
        client.delete_device_groups([])
        data = mock_call.call_args[0][2]
        assert data["group_ids"] == []
