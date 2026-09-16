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
import uuid
from unittest.mock import patch

import pytest

from wy_qcos_client.client import Client
from wy_qcos_client.common.errors import GenericException


client = Client()

FLAVOR_ID = "00000000-0000-4000-8000-000000000001"
PROJECT_ID = "00000000-0000-4000-8000-000000000002"
DEVICE_GROUP_ID = "00000000-0000-4000-8000-000000000003"
DEVICE_GROUPS = [DEVICE_GROUP_ID]


class TestClientFlavor:
    """Test cases for flavor management API methods in Client."""

    @classmethod
    def setup_class(cls):
        cls.return_values = (200, "OK", "text", "result")

    # --------------------------------------------------------------- #
    # create_flavor
    # --------------------------------------------------------------- #
    @patch.object(Client, "call_json_rpc")
    def test_create_flavor_basic(self, mock_call):
        mock_call.return_value = self.return_values
        status_code, reason, text, result = client.create_flavor(
            name="test-flavor", device_groups=DEVICE_GROUPS
        )
        assert status_code == 200
        mock_call.assert_called_once()
        call_args = mock_call.call_args[0]
        assert call_args[0] == client.flavor_url
        assert call_args[1] == "create_flavor"
        data = call_args[2]
        assert data["name"] == "test-flavor"
        assert data["is_public"] is True
        assert data["extra_properties"] is None
        assert data["device_groups"] == DEVICE_GROUPS

    @patch.object(Client, "call_json_rpc")
    def test_create_flavor_all_params(self, mock_call):
        mock_call.return_value = self.return_values
        client.create_flavor(
            name="full-flavor",
            project_id=PROJECT_ID,
            description="desc",
            is_public=False,
            min_qubits=2,
            max_qubits=32,
            gate_fidelity_1q_min=0.99,
            gate_fidelity_2q_min=0.995,
            extra_properties={"qc:devices": "dummy"},
            device_groups=DEVICE_GROUPS,
        )
        call_args = mock_call.call_args[0]
        data = call_args[2]
        assert data["name"] == "full-flavor"
        assert data["project_id"] == PROJECT_ID
        assert data["description"] == "desc"
        assert data["is_public"] is False
        assert data["min_qubits"] == 2
        assert data["max_qubits"] == 32
        assert data["gate_fidelity_1q_min"] == 0.99
        assert data["gate_fidelity_2q_min"] == 0.995
        assert data["extra_properties"] == {"qc:devices": "dummy"}

    @patch.object(Client, "call_json_rpc")
    def test_create_flavor_none_omitted(self, mock_call):
        """None params should be omitted from data."""
        mock_call.return_value = self.return_values
        client.create_flavor(
            name="basic",
            project_id=None,
            description=None,
            min_qubits=None,
            max_qubits=None,
            gate_fidelity_1q_min=None,
            gate_fidelity_2q_min=None,
            extra_properties=None,
            device_groups=DEVICE_GROUPS,
        )
        data = mock_call.call_args[0][2]
        assert "project_id" not in data
        assert "description" not in data
        assert "min_qubits" not in data
        assert "max_qubits" not in data
        assert "gate_fidelity_1q_min" not in data
        assert "gate_fidelity_2q_min" not in data
        assert data["extra_properties"] is None

    @patch.object(Client, "call_json_rpc")
    def test_create_flavor_empty_description_omitted(self, mock_call):
        """Empty description (falsy) should be omitted."""
        mock_call.return_value = self.return_values
        client.create_flavor(
            name="x", description="", device_groups=DEVICE_GROUPS
        )
        data = mock_call.call_args[0][2]
        assert "description" not in data

    # --------------------------------------------------------------- #
    # update_flavor
    # --------------------------------------------------------------- #
    @patch.object(Client, "call_json_rpc")
    def test_update_flavor_basic(self, mock_call):
        mock_call.return_value = self.return_values
        client.update_flavor(flavor_id=FLAVOR_ID, device_groups=DEVICE_GROUPS)
        call_args = mock_call.call_args[0]
        assert call_args[0] == client.flavor_url
        assert call_args[1] == "update_flavor"
        data = call_args[2]
        assert data["flavor_id"] == FLAVOR_ID

    @patch.object(Client, "call_json_rpc")
    def test_update_flavor_all_params(self, mock_call):
        mock_call.return_value = self.return_values
        client.update_flavor(
            flavor_id=FLAVOR_ID,
            name="updated",
            description="new desc",
            is_public=False,
            project_id=PROJECT_ID,
            min_qubits=4,
            max_qubits=64,
            gate_fidelity_1q_min=0.98,
            gate_fidelity_2q_min=0.97,
            extra_properties={"qc:devices": "new"},
            device_groups=DEVICE_GROUPS,
        )
        data = mock_call.call_args[0][2]
        assert data["flavor_id"] == FLAVOR_ID
        assert data["name"] == "updated"
        assert data["description"] == "new desc"
        assert data["is_public"] is False
        assert data["project_id"] == PROJECT_ID
        assert data["min_qubits"] == 4
        assert data["max_qubits"] == 64
        assert data["gate_fidelity_1q_min"] == 0.98
        assert data["gate_fidelity_2q_min"] == 0.97
        assert data["extra_properties"] == {"qc:devices": "new"}

    @patch.object(Client, "call_json_rpc")
    def test_update_flavor_none_clears(self, mock_call):
        mock_call.return_value = self.return_values
        client.update_flavor(
            flavor_id=FLAVOR_ID,
            name=None,
            description=None,
            is_public=None,
            project_id=None,
            min_qubits=None,
            max_qubits=None,
            gate_fidelity_1q_min=None,
            gate_fidelity_2q_min=None,
            extra_properties=None,
            device_groups=None,
        )
        data = mock_call.call_args[0][2]
        # explicit None clears nullable fields
        assert data["name"] is None
        assert data["description"] is None
        assert data["min_qubits"] is None
        assert data["max_qubits"] is None
        assert data["gate_fidelity_1q_min"] is None
        assert data["gate_fidelity_2q_min"] is None
        assert data["extra_properties"] is None
        assert data["device_groups"] is None

    @patch.object(Client, "call_json_rpc")
    def test_update_flavor_omit_skips(self, mock_call):
        mock_call.return_value = self.return_values
        client.update_flavor(
            flavor_id=FLAVOR_ID,
            device_groups=DEVICE_GROUPS,
        )
        data = mock_call.call_args[0][2]
        # omitted fields are not sent
        assert data == {
            "flavor_id": FLAVOR_ID,
            "device_groups": DEVICE_GROUPS,
        }

    @patch.object(Client, "call_json_rpc")
    def test_update_flavor_returns_values(self, mock_call):
        mock_call.return_value = (201, "Created", "resp", "data")
        sc, reason, text, result = client.update_flavor(
            FLAVOR_ID, device_groups=DEVICE_GROUPS
        )
        assert sc == 201
        assert reason == "Created"
        assert text == "resp"
        assert result == "data"

    # --------------------------------------------------------------- #
    # get_flavor
    # --------------------------------------------------------------- #
    @patch.object(Client, "call_json_rpc")
    def test_get_flavor(self, mock_call):
        mock_call.return_value = self.return_values
        client.get_flavor(FLAVOR_ID)
        mock_call.assert_called_once_with(
            client.flavor_url,
            "get_flavor",
            {"flavor_id": FLAVOR_ID},
        )

    @patch.object(Client, "call_json_rpc")
    def test_get_flavor_uuid_object(self, mock_call):
        """flavor_id as UUID object is converted to str."""
        mock_call.return_value = self.return_values
        uid = uuid.UUID(FLAVOR_ID)
        client.get_flavor(uid)
        data = mock_call.call_args[0][2]
        assert data["flavor_id"] == FLAVOR_ID

    # --------------------------------------------------------------- #
    # get_flavors
    # --------------------------------------------------------------- #
    @patch.object(Client, "call_json_rpc")
    def test_get_flavors_no_filter(self, mock_call):
        mock_call.return_value = self.return_values
        client.get_flavors()
        mock_call.assert_called_once_with(client.flavor_url, "get_flavors", {})

    @patch.object(Client, "call_json_rpc")
    def test_get_flavors_with_filter(self, mock_call):
        mock_call.return_value = self.return_values
        client.get_flavors(filters={"flavor_name": "g1.all"})
        data = mock_call.call_args[0][2]
        assert data["filters"] == {"flavor_name": "g1.all"}

    @patch.object(Client, "call_json_rpc")
    def test_get_flavors_none_filter(self, mock_call):
        mock_call.return_value = self.return_values
        client.get_flavors(filters=None)
        data = mock_call.call_args[0][2]
        assert "filters" not in data

    # --------------------------------------------------------------- #
    # delete_flavors (batch)
    # --------------------------------------------------------------- #
    @patch.object(Client, "call_json_rpc")
    def test_delete_flavors_single(self, mock_call):
        mock_call.return_value = self.return_values
        client.delete_flavors([FLAVOR_ID])
        mock_call.assert_called_once_with(
            client.flavor_url,
            "delete_flavors",
            {"flavor_ids": [FLAVOR_ID]},
        )

    @patch.object(Client, "call_json_rpc")
    def test_delete_flavors_multiple(self, mock_call):
        mock_call.return_value = self.return_values
        second_id = "00000000-0000-4000-8000-000000000002"
        client.delete_flavors([FLAVOR_ID, second_id])
        data = mock_call.call_args[0][2]
        assert data["flavor_ids"] == [FLAVOR_ID, second_id]

    @patch.object(Client, "call_json_rpc")
    def test_delete_flavors_uuid_object(self, mock_call):
        mock_call.return_value = self.return_values
        uid = uuid.UUID(FLAVOR_ID)
        client.delete_flavors([uid])
        data = mock_call.call_args[0][2]
        assert data["flavor_ids"] == [FLAVOR_ID]

    @patch.object(Client, "call_json_rpc")
    def test_delete_flavors_empty_list(self, mock_call):
        mock_call.return_value = self.return_values
        client.delete_flavors([])
        data = mock_call.call_args[0][2]
        assert data["flavor_ids"] == []

    # --------------------------------------------------------------- #
    # resolve_flavor_id
    # --------------------------------------------------------------- #
    def test_resolve_flavor_id_uuid(self):
        """Valid UUID should be returned directly."""
        result = Client.resolve_flavor_id(client, FLAVOR_ID)
        assert result == FLAVOR_ID

    def test_resolve_flavor_id_uuid_object(self):
        uid = uuid.UUID(FLAVOR_ID)
        result = Client.resolve_flavor_id(client, str(uid))
        assert result == str(uid)

    @patch.object(Client, "get_flavors")
    def test_resolve_flavor_id_by_name(self, mock_get):
        """Non-UUID identifier should be resolved via get_flavors."""
        resp = {
            "jsonrpc": "2.0",
            "result": [{"id": FLAVOR_ID, "name": "g1.all"}],
            "id": 0,
        }
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            resp["result"],
        )
        result = Client.resolve_flavor_id(client, "g1.all")
        assert result == FLAVOR_ID
        mock_get.assert_called_once_with(filters={"flavor_name": "g1.all"})

    @patch.object(Client, "get_flavors")
    def test_resolve_flavor_id_name_empty_result(self, mock_get):
        """Empty result list should raise GenericException."""
        resp = {
            "jsonrpc": "2.0",
            "result": [],
            "id": 0,
        }
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            resp["result"],
        )
        with pytest.raises(GenericException, match="not found"):
            Client.resolve_flavor_id(client, "missing-flavor")

    @patch.object(Client, "get_flavors")
    def test_resolve_flavor_id_error_response(self, mock_get):
        """Error in response should raise GenericException."""
        resp = {
            "jsonrpc": "2.0",
            "error": {
                "message": "Some error",
                "data": {"details": "detail msg"},
            },
            "id": 0,
        }
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            None,
        )
        with pytest.raises(GenericException, match="Some error"):
            Client.resolve_flavor_id(client, "bad-flavor")

    @patch.object(Client, "get_flavors")
    def test_resolve_flavor_id_http_error(self, mock_get):
        """Non-200 status should raise GenericException."""
        mock_get.return_value = (
            500,
            "Internal Error",
            "",
            None,
        )
        with pytest.raises(GenericException, match="Failed to fetch flavors"):
            Client.resolve_flavor_id(client, "err-flavor")

    @patch.object(Client, "get_flavors")
    def test_resolve_flavor_id_empty_result_no_error(self, mock_get):
        """Result key present but empty -> not found."""
        resp = {
            "jsonrpc": "2.0",
            "result": None,
            "id": 0,
        }
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            None,
        )
        with pytest.raises(GenericException, match="not found"):
            Client.resolve_flavor_id(client, "empty-flavor")
