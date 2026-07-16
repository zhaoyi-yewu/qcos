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
#     WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import json
from unittest.mock import Mock, patch

import pytest
from cliff.commandmanager import CommandManager

from wy_qcos_client.client import Client, _UNSET
from wy_qcos_client.common.errors import GenericException, InvalidArguments
from wy_qcos_client.common.qcos_version import QcosVersion
from wy_qcos_client.shell import (
    QcosShell,
    CommandHelper,
    CreateFlavor,
    UpdateFlavor,
    GetFlavor,
    GetFlavors,
    DeleteFlavors,
)

DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")

FLAVOR_ID = "00000000-0000-4000-8000-000000000001"
FLAVOR_ID_2 = "00000000-0000-4000-8000-000000000002"
PROJECT_ID = "00000000-0000-4000-8000-000000000002"

flavor_response = {
    "jsonrpc": "2.0",
    "result": {
        "id": FLAVOR_ID,
        "project_id": PROJECT_ID,
        "name": "test-flavor",
        "description": "test desc",
        "is_public": True,
        "min_qubits": 1,
        "max_qubits": 32,
        "gate_fidelity_1q_min": 0.99,
        "gate_fidelity_2q_min": 0.995,
        "extra_properties": {"qc:devices": "dummy"},
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    },
    "id": 0,
}

shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()


def make_shell_cmd(cmd_class):
    """Instantiate a shell command with app set up."""
    cmd = cmd_class(shell, None)
    cmd.app = shell
    cmd.app.stdout = Mock()
    return cmd


def make_parsed_args(**kwargs):
    """Build a Mock parsed_args with flavor-related attributes."""
    args = Mock()
    defaults = {
        "name": None,
        "flavor_id": None,
        "flavor_id_name": None,
        "flavor_ids": None,
        "flavor_name": None,
        "project_id": None,
        "description": None,
        "is_public": True,
        "min_qubits": None,
        "max_qubits": None,
        "gate_fidelity_1q_min": None,
        "gate_fidelity_2q_min": None,
        "property": None,
        "device_groups": None,
        # --unset-{key} flags for UpdateFlavor
        "unset_description": False,
        "unset_min_qubits": False,
        "unset_max_qubits": False,
        "unset_gate_fidelity_1q_min": False,
        "unset_gate_fidelity_2q_min": False,
        "unset_extra_properties": False,
        "unset_device_groups": False,
        "assume_yes": False,
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(args, k, v)
    return args


class TestCreateFlavor:
    """Test cases for CreateFlavor command."""

    def test_get_parser(self):
        cmd = CreateFlavor(shell, None)
        parser = cmd.get_parser("create-flavor")
        assert parser is not None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "create_flavor")
    def test_take_action_basic(self, mock_create, mock_check):
        mock_create.return_value = (
            200,
            "OK",
            json.dumps(flavor_response),
            flavor_response["result"],
        )
        mock_check.return_value = flavor_response["result"]
        cmd = make_shell_cmd(CreateFlavor)
        args = make_parsed_args(name="test-flavor")
        cmd.take_action(args)
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["name"] == "test-flavor"
        assert call_kwargs["extra_properties"] is None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "create_flavor")
    def test_take_action_all_params(self, mock_create, mock_check):
        mock_create.return_value = (
            200,
            "OK",
            json.dumps(flavor_response),
            flavor_response["result"],
        )
        mock_check.return_value = flavor_response["result"]
        cmd = make_shell_cmd(CreateFlavor)
        args = make_parsed_args(
            name="full",
            project_id=PROJECT_ID,
            description="desc",
            is_public=False,
            min_qubits=2,
            max_qubits=64,
            gate_fidelity_1q_min=0.99,
            gate_fidelity_2q_min=0.995,
            property=["qc:devices=dummy"],
        )
        cmd.take_action(args)
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["extra_properties"] == {"qc:devices": "dummy"}
        assert call_kwargs["is_public"] is False

    @patch.object(Client, "create_flavor")
    def test_take_action_invalid_property_no_equals(self, mock_create):
        cmd = make_shell_cmd(CreateFlavor)
        args = make_parsed_args(
            name="x",
            property=["qc:devicesdummy"],
        )
        with pytest.raises(InvalidArguments, match="namespace:key=value"):
            cmd.take_action(args)
        mock_create.assert_not_called()

    @patch.object(Client, "create_flavor")
    def test_take_action_invalid_property_no_colon(self, mock_create):
        cmd = make_shell_cmd(CreateFlavor)
        args = make_parsed_args(
            name="x",
            property=["qcdevices=dummy"],
        )
        with pytest.raises(InvalidArguments, match="namespace:name"):
            cmd.take_action(args)
        mock_create.assert_not_called()

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "create_flavor")
    def test_take_action_private_flag(self, mock_create, mock_check):
        mock_create.return_value = (
            200,
            "OK",
            json.dumps(flavor_response),
            flavor_response["result"],
        )
        mock_check.return_value = flavor_response["result"]
        cmd = make_shell_cmd(CreateFlavor)
        args = make_parsed_args(name="priv", is_public=False)
        cmd.take_action(args)
        assert mock_create.call_args.kwargs["is_public"] is False


class TestUpdateFlavor:
    """Test cases for UpdateFlavor command."""

    def test_get_parser(self):
        cmd = UpdateFlavor(shell, None)
        parser = cmd.get_parser("update-flavor")
        assert parser is not None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "update_flavor")
    @patch.object(Client, "resolve_flavor_id")
    def test_take_action_basic(self, mock_resolve, mock_update, mock_check):
        mock_resolve.return_value = FLAVOR_ID
        mock_update.return_value = (
            200,
            "OK",
            json.dumps(flavor_response),
            flavor_response["result"],
        )
        mock_check.return_value = flavor_response["result"]
        cmd = make_shell_cmd(UpdateFlavor)
        args = make_parsed_args(flavor_id="test-flavor")
        cmd.take_action(args)
        mock_resolve.assert_called_once()
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["flavor_id"] == FLAVOR_ID

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "update_flavor")
    @patch.object(Client, "resolve_flavor_id")
    def test_take_action_with_properties(
        self, mock_resolve, mock_update, mock_check
    ):
        mock_resolve.return_value = FLAVOR_ID
        mock_update.return_value = (
            200,
            "OK",
            json.dumps(flavor_response),
            flavor_response["result"],
        )
        mock_check.return_value = flavor_response["result"]
        cmd = make_shell_cmd(UpdateFlavor)
        args = make_parsed_args(
            flavor_id=FLAVOR_ID,
            name="updated",
            description="new",
            is_public=True,
            project_id=PROJECT_ID,
            min_qubits=4,
            max_qubits=64,
            gate_fidelity_1q_min=0.98,
            gate_fidelity_2q_min=0.97,
            property=["qc:devices=new"],
        )
        cmd.take_action(args)
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["extra_properties"] == {"qc:devices": "new"}

    @patch.object(Client, "resolve_flavor_id")
    def test_take_action_invalid_property_format(self, mock_resolve):
        mock_resolve.return_value = FLAVOR_ID
        cmd = make_shell_cmd(UpdateFlavor)
        args = make_parsed_args(
            flavor_id=FLAVOR_ID,
            property=["noequals"],
        )
        with pytest.raises(InvalidArguments, match="namespace:key=value"):
            cmd.take_action(args)

    @patch.object(Client, "resolve_flavor_id")
    def test_take_action_invalid_property_key(self, mock_resolve):
        mock_resolve.return_value = FLAVOR_ID
        cmd = make_shell_cmd(UpdateFlavor)
        args = make_parsed_args(
            flavor_id=FLAVOR_ID,
            property=["nokey=value"],
        )
        with pytest.raises(InvalidArguments, match="namespace:name"):
            cmd.take_action(args)

    @patch.object(Client, "resolve_flavor_id")
    def test_take_action_resolve_raises(self, mock_resolve):
        mock_resolve.side_effect = GenericException("not found")
        cmd = make_shell_cmd(UpdateFlavor)
        args = make_parsed_args(flavor_id="missing")
        with pytest.raises(GenericException):
            cmd.take_action(args)

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "update_flavor")
    @patch.object(Client, "resolve_flavor_id")
    def test_take_action_unset_clears_fields(
        self, mock_resolve, mock_update, mock_check
    ):
        mock_resolve.return_value = FLAVOR_ID
        mock_update.return_value = (
            200,
            "OK",
            json.dumps(flavor_response),
            flavor_response["result"],
        )
        mock_check.return_value = flavor_response["result"]
        cmd = make_shell_cmd(UpdateFlavor)
        args = make_parsed_args(
            flavor_id=FLAVOR_ID,
            unset_description=True,
            unset_min_qubits=True,
            unset_max_qubits=True,
            unset_gate_fidelity_1q_min=True,
            unset_gate_fidelity_2q_min=True,
            unset_extra_properties=True,
            unset_device_groups=True,
        )
        cmd.take_action(args)
        call_kwargs = mock_update.call_args.kwargs
        # --unset-{key} passes None (unset) for those fields
        assert call_kwargs["description"] is None
        assert call_kwargs["min_qubits"] is None
        assert call_kwargs["max_qubits"] is None
        assert call_kwargs["gate_fidelity_1q_min"] is None
        assert call_kwargs["gate_fidelity_2q_min"] is None
        assert call_kwargs["extra_properties"] is None
        assert call_kwargs["device_groups"] is None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "update_flavor")
    @patch.object(Client, "resolve_flavor_id")
    def test_take_action_omit_passes_sentinel(
        self, mock_resolve, mock_update, mock_check
    ):
        mock_resolve.return_value = FLAVOR_ID
        mock_update.return_value = (
            200,
            "OK",
            json.dumps(flavor_response),
            flavor_response["result"],
        )
        mock_check.return_value = flavor_response["result"]
        cmd = make_shell_cmd(UpdateFlavor)
        # only name provided; other fields omitted
        args = make_parsed_args(flavor_id=FLAVOR_ID, name="updated")
        cmd.take_action(args)
        call_kwargs = mock_update.call_args.kwargs
        # omitted fields receive the _UNSET sentinel
        assert call_kwargs["description"] is _UNSET
        assert call_kwargs["min_qubits"] is _UNSET
        assert call_kwargs["max_qubits"] is _UNSET
        assert call_kwargs["gate_fidelity_1q_min"] is _UNSET
        assert call_kwargs["gate_fidelity_2q_min"] is _UNSET
        assert call_kwargs["extra_properties"] is _UNSET
        assert call_kwargs["device_groups"] is _UNSET


class TestGetFlavor:
    """Test cases for GetFlavor command."""

    def test_get_parser(self):
        cmd = GetFlavor(shell, None)
        parser = cmd.get_parser("get-flavor")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_flavor")
    @patch.object(Client, "resolve_flavor_id")
    def test_take_action(self, mock_resolve, mock_get, mock_check, mock_table):
        mock_resolve.return_value = FLAVOR_ID
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(flavor_response),
            flavor_response["result"],
        )
        mock_check.return_value = flavor_response["result"]
        mock_table.return_value = (
            ("Field", "Value"),
            ("name", "test-flavor"),
        )
        cmd = make_shell_cmd(GetFlavor)
        args = make_parsed_args(flavor_id="test-flavor")
        result = cmd.take_action(args)
        assert result is not None
        mock_resolve.assert_called_once()

    @patch.object(Client, "resolve_flavor_id")
    def test_take_action_resolve_raises(self, mock_resolve):
        mock_resolve.side_effect = GenericException("not found")
        cmd = make_shell_cmd(GetFlavor)
        args = make_parsed_args(flavor_id="missing")
        with pytest.raises(GenericException):
            cmd.take_action(args)


class TestGetFlavors:
    """Test cases for GetFlavors command."""

    def test_get_parser(self):
        cmd = GetFlavors(shell, None)
        parser = cmd.get_parser("list-flavors")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_flavors")
    def test_take_action(self, mock_get, mock_check, mock_table):
        flavors_list = [
            flavor_response["result"],
            {
                **flavor_response["result"],
                "id": FLAVOR_ID_2,
                "name": "second",
            },
        ]
        resp = {"jsonrpc": "2.0", "result": flavors_list, "id": 0}
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            flavors_list,
        )
        mock_check.return_value = flavors_list
        mock_table.return_value = (
            ["id", "name"],
            [["id1", "name1"], ["id2", "name2"]],
        )
        cmd = make_shell_cmd(GetFlavors)
        args = make_parsed_args(flavor_ids=[], flavor_names=None)
        result = cmd.take_action(args)
        assert result is not None

    @patch("builtins.print")
    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_flavors")
    def test_take_action_empty(
        self, mock_get, mock_check, mock_table, mock_print
    ):
        resp = {"jsonrpc": "2.0", "result": [], "id": 0}
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            [],
        )
        mock_check.return_value = []
        mock_table.return_value = ([], [])
        cmd = make_shell_cmd(GetFlavors)
        args = make_parsed_args(flavor_ids=[], flavor_names=None)
        cmd.take_action(args)
        mock_print.assert_called_with("No flavors found")

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_flavors")
    def test_take_action_with_flavor_ids_filter(
        self, mock_get, mock_check, mock_table
    ):
        """GetFlavors should pass flavor_ids filter to client."""
        flavors_list = [flavor_response["result"]]
        resp = {"jsonrpc": "2.0", "result": flavors_list, "id": 0}
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            flavors_list,
        )
        mock_check.return_value = flavors_list
        mock_table.return_value = (["id", "name"], [["id1", "name1"]])
        cmd = make_shell_cmd(GetFlavors)
        args = make_parsed_args(flavor_ids=[FLAVOR_ID, FLAVOR_ID_2])
        cmd.take_action(args)
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["filters"]["flavor_ids"] == [
            FLAVOR_ID,
            FLAVOR_ID_2,
        ]

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_flavors")
    def test_take_action_with_flavor_name_filter(
        self, mock_get, mock_check, mock_table
    ):
        """GetFlavors should pass flavor_names filter to client."""
        flavors_list = [flavor_response["result"]]
        resp = {"jsonrpc": "2.0", "result": flavors_list, "id": 0}
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            flavors_list,
        )
        mock_check.return_value = flavors_list
        mock_table.return_value = (["id", "name"], [["id1", "name1"]])
        cmd = make_shell_cmd(GetFlavors)
        args = make_parsed_args(flavor_names=["test-flavor"])
        cmd.take_action(args)
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["filters"]["flavor_names"] == ["test-flavor"]

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_flavors")
    def test_take_action_no_filter(self, mock_get, mock_check, mock_table):
        """GetFlavors with no filter should call client with None."""
        flavors_list = [flavor_response["result"]]
        resp = {"jsonrpc": "2.0", "result": flavors_list, "id": 0}
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            flavors_list,
        )
        mock_check.return_value = flavors_list
        mock_table.return_value = (["id", "name"], [["id1", "name1"]])
        cmd = make_shell_cmd(GetFlavors)
        args = make_parsed_args(flavor_ids=[], flavor_names=None)
        cmd.take_action(args)
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["filters"] is None


class TestDeleteFlavors:
    """Test cases for DeleteFlavors command."""

    def test_get_parser(self):
        cmd = DeleteFlavors(shell, None)
        parser = cmd.get_parser("delete-flavors")
        assert parser is not None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "resolve_flavor_id")
    @patch.object(Client, "delete_flavors")
    def test_take_action_single_assume_yes(
        self, mock_delete, mock_resolve, mock_check
    ):
        mock_resolve.return_value = FLAVOR_ID
        delete_resp = {
            "jsonrpc": "2.0",
            "result": {"results": [{"flavor_id": FLAVOR_ID, "success": True}]},
            "id": 0,
        }
        mock_delete.return_value = (
            200,
            "OK",
            json.dumps(delete_resp),
            delete_resp["result"],
        )
        mock_check.return_value = delete_resp["result"]
        cmd = make_shell_cmd(DeleteFlavors)
        args = make_parsed_args(flavor_ids=FLAVOR_ID, assume_yes=True)
        cmd.take_action(args)
        mock_delete.assert_called_once_with([FLAVOR_ID])

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "resolve_flavor_id")
    @patch.object(Client, "delete_flavors")
    def test_take_action_multiple_assume_yes(
        self, mock_delete, mock_resolve, mock_check
    ):
        mock_resolve.side_effect = [FLAVOR_ID, FLAVOR_ID_2]
        delete_resp = {
            "jsonrpc": "2.0",
            "result": {
                "results": [
                    {"flavor_id": FLAVOR_ID, "success": True},
                    {"flavor_id": FLAVOR_ID_2, "success": True},
                ]
            },
            "id": 0,
        }
        mock_delete.return_value = (
            200,
            "OK",
            json.dumps(delete_resp),
            delete_resp["result"],
        )
        mock_check.return_value = delete_resp["result"]
        cmd = make_shell_cmd(DeleteFlavors)
        args = make_parsed_args(
            flavor_ids=f"{FLAVOR_ID},{FLAVOR_ID_2}",
            assume_yes=True,
        )
        cmd.take_action(args)
        mock_delete.assert_called_once_with([FLAVOR_ID, FLAVOR_ID_2])

    @patch("builtins.input", return_value="y")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "resolve_flavor_id")
    @patch.object(Client, "delete_flavors")
    def test_take_action_confirm_yes(
        self, mock_delete, mock_resolve, mock_check, mock_input
    ):
        mock_resolve.return_value = FLAVOR_ID
        delete_resp = {
            "jsonrpc": "2.0",
            "result": {"results": [{"flavor_id": FLAVOR_ID, "success": True}]},
            "id": 0,
        }
        mock_delete.return_value = (
            200,
            "OK",
            json.dumps(delete_resp),
            delete_resp["result"],
        )
        mock_check.return_value = delete_resp["result"]
        cmd = make_shell_cmd(DeleteFlavors)
        args = make_parsed_args(flavor_ids=FLAVOR_ID, assume_yes=False)
        cmd.take_action(args)
        mock_input.assert_called_once()
        mock_delete.assert_called_once()

    @patch("builtins.input", return_value="n")
    @patch.object(Client, "resolve_flavor_id")
    @patch.object(Client, "delete_flavors")
    def test_take_action_confirm_no(
        self, mock_delete, mock_resolve, mock_input
    ):
        mock_resolve.return_value = FLAVOR_ID
        cmd = make_shell_cmd(DeleteFlavors)
        args = make_parsed_args(flavor_ids=FLAVOR_ID, assume_yes=False)
        result = cmd.take_action(args)
        assert result is None
        mock_delete.assert_not_called()

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_flavors")
    @patch.object(Client, "delete_flavors")
    def test_take_action_all(self, mock_delete, mock_get, mock_check):
        """delete-flavors all should fetch all IDs then delete."""
        flavors_list = [
            {"id": FLAVOR_ID, "name": "f1"},
            {"id": FLAVOR_ID_2, "name": "f2"},
        ]
        resp = {"jsonrpc": "2.0", "result": flavors_list, "id": 0}
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            flavors_list,
        )
        mock_check.return_value = flavors_list
        delete_resp = {
            "jsonrpc": "2.0",
            "result": {
                "results": [
                    {"flavor_id": FLAVOR_ID, "success": True},
                    {"flavor_id": FLAVOR_ID_2, "success": True},
                ]
            },
            "id": 0,
        }
        mock_delete.return_value = (
            200,
            "OK",
            json.dumps(delete_resp),
            delete_resp["result"],
        )
        cmd = make_shell_cmd(DeleteFlavors)
        args = make_parsed_args(flavor_ids="all", assume_yes=True)
        cmd.take_action(args)
        mock_delete.assert_called_once_with([FLAVOR_ID, FLAVOR_ID_2])

    @patch.object(Client, "resolve_flavor_id")
    def test_take_action_resolve_raises(self, mock_resolve):
        mock_resolve.side_effect = GenericException("not found")
        cmd = make_shell_cmd(DeleteFlavors)
        args = make_parsed_args(flavor_ids="missing", assume_yes=True)
        with pytest.raises(GenericException):
            cmd.take_action(args)


class TestCommandRegistration:
    """Test that flavor commands are registered."""

    def test_flavor_commands_registered(self):
        from wy_qcos_client.shell import command_manager as cm

        assert "create-flavor" in cm.commands
        assert "update-flavor" in cm.commands
        assert "get-flavor" in cm.commands
        assert "list-flavors" in cm.commands
        assert "delete-flavors" in cm.commands
