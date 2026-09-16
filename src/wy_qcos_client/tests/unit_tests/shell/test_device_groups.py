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

from cliff.commandmanager import CommandManager

from wy_qcos_client.client import Client, _UNSET
from wy_qcos_client.common.qcos_version import QcosVersion
from wy_qcos_client.shell import (
    QcosShell,
    CommandHelper,
    CreateDeviceGroup,
    UpdateDeviceGroup,
    GetDeviceGroup,
    GetDeviceGroups,
    DeleteDeviceGroups,
)

DESCRIPTION = "QCOS command line interface"
VERSION = QcosVersion.VERSION
command_manager = CommandManager("qcos")

GROUP_ID = "00000000-0000-4000-8000-000000000001"
GROUP_ID_2 = "00000000-0000-4000-8000-000000000003"

group_response = {
    "jsonrpc": "2.0",
    "result": {
        "id": GROUP_ID,
        "project_id": "00000000-0000-4000-8000-000000000002",
        "name": "test-group",
        "description": "test desc",
        "device_names": ["dummy", "qutip_sim"],
        "is_public": True,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    },
    "id": 0,
}

shell = QcosShell(DESCRIPTION, VERSION, command_manager)
shell.client = Client()


def make_shell_cmd(cmd_class):
    cmd = cmd_class(shell, None)
    cmd.app = shell
    cmd.app.stdout = Mock()
    return cmd


def make_parsed_args(**kwargs):
    args = Mock()
    defaults = {
        "name": None,
        "group_id": None,
        "group_ids": None,
        "group_name": None,
        "project_id": None,
        "description": None,
        "is_public": True,
        "device_names": None,
        # --unset-{key} flags for UpdateDeviceGroup
        "unset_description": False,
        "unset_device_names": False,
        "assume_yes": False,
    }
    defaults.update(kwargs)
    for k, v in defaults.items():
        setattr(args, k, v)
    return args


class TestCreateDeviceGroup:
    """Test cases for CreateDeviceGroup command."""

    def test_get_parser(self):
        cmd = CreateDeviceGroup(shell, None)
        parser = cmd.get_parser("create-device-group")
        assert parser is not None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "create_device_group")
    def test_take_action_basic(self, mock_create, mock_check):
        mock_create.return_value = (
            200,
            "OK",
            json.dumps(group_response),
            group_response["result"],
        )
        mock_check.return_value = group_response["result"]
        cmd = make_shell_cmd(CreateDeviceGroup)
        args = make_parsed_args(name="test-group", device_names=["dev1"])
        cmd.take_action(args)
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["name"] == "test-group"
        assert call_kwargs["device_names"] == ["dev1"]

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "create_device_group")
    def test_take_action_all_params(self, mock_create, mock_check):
        mock_create.return_value = (
            200,
            "OK",
            json.dumps(group_response),
            group_response["result"],
        )
        mock_check.return_value = group_response["result"]
        cmd = make_shell_cmd(CreateDeviceGroup)
        args = make_parsed_args(
            name="full",
            project_id="proj-1",
            description="desc",
            is_public=False,
            device_names=["dev1"],
        )
        cmd.take_action(args)
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["device_names"] == ["dev1"]
        assert call_kwargs["is_public"] is False


class TestUpdateDeviceGroup:
    """Test cases for UpdateDeviceGroup command."""

    def test_get_parser(self):
        cmd = UpdateDeviceGroup(shell, None)
        parser = cmd.get_parser("update-device-group")
        assert parser is not None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "update_device_group")
    def test_take_action_basic(self, mock_update, mock_check):
        mock_update.return_value = (
            200,
            "OK",
            json.dumps(group_response),
            group_response["result"],
        )
        mock_check.return_value = group_response["result"]
        cmd = make_shell_cmd(UpdateDeviceGroup)
        args = make_parsed_args(group_id=GROUP_ID, name="updated")
        cmd.take_action(args)
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["group_id"] == GROUP_ID
        assert call_kwargs["name"] == "updated"

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "update_device_group")
    def test_take_action_with_devices(self, mock_update, mock_check):
        mock_update.return_value = (
            200,
            "OK",
            json.dumps(group_response),
            group_response["result"],
        )
        mock_check.return_value = group_response["result"]
        cmd = make_shell_cmd(UpdateDeviceGroup)
        args = make_parsed_args(
            group_id=GROUP_ID, device_names=["dev1", "dev2"]
        )
        cmd.take_action(args)
        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["device_names"] == ["dev1", "dev2"]

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "update_device_group")
    def test_take_action_unset_clears_fields(self, mock_update, mock_check):
        mock_update.return_value = (
            200,
            "OK",
            json.dumps(group_response),
            group_response["result"],
        )
        mock_check.return_value = group_response["result"]
        cmd = make_shell_cmd(UpdateDeviceGroup)
        args = make_parsed_args(
            group_id=GROUP_ID,
            unset_description=True,
            unset_device_names=True,
        )
        cmd.take_action(args)
        call_kwargs = mock_update.call_args.kwargs
        # --unset-{key} passes None (unset) for those fields
        assert call_kwargs["description"] is None
        assert call_kwargs["device_names"] is None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "update_device_group")
    def test_take_action_omit_passes_sentinel(self, mock_update, mock_check):
        mock_update.return_value = (
            200,
            "OK",
            json.dumps(group_response),
            group_response["result"],
        )
        mock_check.return_value = group_response["result"]
        cmd = make_shell_cmd(UpdateDeviceGroup)
        # only name provided; description/device_names omitted
        args = make_parsed_args(group_id=GROUP_ID, name="updated")
        cmd.take_action(args)
        call_kwargs = mock_update.call_args.kwargs
        # omitted fields receive the _UNSET sentinel
        assert call_kwargs["description"] is _UNSET
        assert call_kwargs["device_names"] is _UNSET


class TestGetDeviceGroup:
    """Test cases for GetDeviceGroup command."""

    def test_get_parser(self):
        cmd = GetDeviceGroup(shell, None)
        parser = cmd.get_parser("get-device-group")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_device_group")
    def test_take_action(self, mock_get, mock_check, mock_table):
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(group_response),
            group_response["result"],
        )
        mock_check.return_value = group_response["result"]
        mock_table.return_value = (
            ("Field", "Value"),
            ("name", "test-group"),
        )
        cmd = make_shell_cmd(GetDeviceGroup)
        args = make_parsed_args(group_id=GROUP_ID)
        result = cmd.take_action(args)
        assert result is not None


class TestGetDeviceGroups:
    """Test cases for GetDeviceGroups command."""

    def test_get_parser(self):
        cmd = GetDeviceGroups(shell, None)
        parser = cmd.get_parser("list-device-groups")
        assert parser is not None

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_device_groups")
    def test_take_action(self, mock_get, mock_check, mock_table):
        groups_list = [
            group_response["result"],
            {
                **group_response["result"],
                "id": GROUP_ID_2,
                "name": "second",
            },
        ]
        resp = {"jsonrpc": "2.0", "result": groups_list, "id": 0}
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            groups_list,
        )
        mock_check.return_value = groups_list
        mock_table.return_value = (
            ["id", "name"],
            [["id1", "name1"], ["id2", "name2"]],
        )
        cmd = make_shell_cmd(GetDeviceGroups)
        args = make_parsed_args(group_ids=[], group_names=None)
        result = cmd.take_action(args)
        assert result is not None

    @patch("builtins.print")
    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_device_groups")
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
        cmd = make_shell_cmd(GetDeviceGroups)
        args = make_parsed_args(group_ids=[], group_names=None)
        cmd.take_action(args)
        mock_print.assert_called_with("No device groups found")

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_device_groups")
    def test_take_action_with_group_ids_filter(
        self, mock_get, mock_check, mock_table
    ):
        """GetDeviceGroups should pass group_ids filter to client."""
        groups_list = [group_response["result"]]
        resp = {"jsonrpc": "2.0", "result": groups_list, "id": 0}
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            groups_list,
        )
        mock_check.return_value = groups_list
        mock_table.return_value = (["id", "name"], [["id1", "name1"]])
        cmd = make_shell_cmd(GetDeviceGroups)
        args = make_parsed_args(group_ids=[GROUP_ID, GROUP_ID_2])
        cmd.take_action(args)
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["filters"]["group_ids"] == [
            GROUP_ID,
            GROUP_ID_2,
        ]

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_device_groups")
    def test_take_action_with_group_name_filter(
        self, mock_get, mock_check, mock_table
    ):
        """GetDeviceGroups should pass group_name filter to client."""
        groups_list = [group_response["result"]]
        resp = {"jsonrpc": "2.0", "result": groups_list, "id": 0}
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            groups_list,
        )
        mock_check.return_value = groups_list
        mock_table.return_value = (["id", "name"], [["id1", "name1"]])
        cmd = make_shell_cmd(GetDeviceGroups)
        args = make_parsed_args(group_names=["test-group"])
        cmd.take_action(args)
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["filters"]["group_names"] == ["test-group"]

    @patch.object(CommandHelper, "get_table_list_data")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_device_groups")
    def test_take_action_no_filter(self, mock_get, mock_check, mock_table):
        """GetDeviceGroups with no filter should call client with None."""
        groups_list = [group_response["result"]]
        resp = {"jsonrpc": "2.0", "result": groups_list, "id": 0}
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            groups_list,
        )
        mock_check.return_value = groups_list
        mock_table.return_value = (["id", "name"], [["id1", "name1"]])
        cmd = make_shell_cmd(GetDeviceGroups)
        args = make_parsed_args(group_ids=[], group_names=None)
        cmd.take_action(args)
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["filters"] is None


class TestDeleteDeviceGroups:
    """Test cases for DeleteDeviceGroups command."""

    def test_get_parser(self):
        cmd = DeleteDeviceGroups(shell, None)
        parser = cmd.get_parser("delete-device-groups")
        assert parser is not None

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "resolve_device_group_id")
    @patch.object(Client, "delete_device_groups")
    def test_take_action_single_assume_yes(
        self, mock_delete, mock_resolve, mock_check
    ):
        mock_resolve.return_value = GROUP_ID
        delete_resp = {
            "jsonrpc": "2.0",
            "result": {"results": [{"group_id": GROUP_ID, "success": True}]},
            "id": 0,
        }
        mock_delete.return_value = (
            200,
            "OK",
            json.dumps(delete_resp),
            delete_resp["result"],
        )
        mock_check.return_value = delete_resp["result"]
        cmd = make_shell_cmd(DeleteDeviceGroups)
        args = make_parsed_args(group_ids=GROUP_ID, assume_yes=True)
        cmd.take_action(args)
        mock_delete.assert_called_once_with([GROUP_ID])

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "resolve_device_group_id")
    @patch.object(Client, "delete_device_groups")
    def test_take_action_multiple_assume_yes(
        self, mock_delete, mock_resolve, mock_check
    ):
        mock_resolve.side_effect = [GROUP_ID, GROUP_ID_2]
        delete_resp = {
            "jsonrpc": "2.0",
            "result": {
                "results": [
                    {"group_id": GROUP_ID, "success": True},
                    {"group_id": GROUP_ID_2, "success": True},
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
        cmd = make_shell_cmd(DeleteDeviceGroups)
        args = make_parsed_args(
            group_ids=f"{GROUP_ID},{GROUP_ID_2}",
            assume_yes=True,
        )
        cmd.take_action(args)
        mock_delete.assert_called_once_with([GROUP_ID, GROUP_ID_2])

    @patch("builtins.input", return_value="y")
    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "resolve_device_group_id")
    @patch.object(Client, "delete_device_groups")
    def test_take_action_confirm_yes(
        self, mock_delete, mock_resolve, mock_check, mock_input
    ):
        mock_resolve.return_value = GROUP_ID
        delete_resp = {
            "jsonrpc": "2.0",
            "result": {"results": [{"group_id": GROUP_ID, "success": True}]},
            "id": 0,
        }
        mock_delete.return_value = (
            200,
            "OK",
            json.dumps(delete_resp),
            delete_resp["result"],
        )
        mock_check.return_value = delete_resp["result"]
        cmd = make_shell_cmd(DeleteDeviceGroups)
        args = make_parsed_args(group_ids=GROUP_ID, assume_yes=False)
        cmd.take_action(args)
        mock_input.assert_called_once()
        mock_delete.assert_called_once()

    @patch("builtins.input", return_value="n")
    @patch.object(Client, "resolve_device_group_id")
    @patch.object(Client, "delete_device_groups")
    def test_take_action_confirm_no(
        self, mock_delete, mock_resolve, mock_input
    ):
        mock_resolve.return_value = GROUP_ID
        cmd = make_shell_cmd(DeleteDeviceGroups)
        args = make_parsed_args(group_ids=GROUP_ID, assume_yes=False)
        result = cmd.take_action(args)
        assert result is None
        mock_delete.assert_not_called()

    @patch.object(CommandHelper, "check_results")
    @patch.object(Client, "get_device_groups")
    @patch.object(Client, "delete_device_groups")
    def test_take_action_all(self, mock_delete, mock_get, mock_check):
        """delete-device-groups all should fetch all IDs then delete."""
        groups_list = [
            {"id": GROUP_ID, "name": "g1"},
            {"id": GROUP_ID_2, "name": "g2"},
        ]
        resp = {"jsonrpc": "2.0", "result": groups_list, "id": 0}
        mock_get.return_value = (
            200,
            "OK",
            json.dumps(resp),
            groups_list,
        )
        mock_check.return_value = groups_list
        delete_resp = {
            "jsonrpc": "2.0",
            "result": {
                "results": [
                    {"group_id": GROUP_ID, "success": True},
                    {"group_id": GROUP_ID_2, "success": True},
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
        cmd = make_shell_cmd(DeleteDeviceGroups)
        args = make_parsed_args(group_ids="all", assume_yes=True)
        cmd.take_action(args)
        mock_delete.assert_called_once_with([GROUP_ID, GROUP_ID_2])


class TestCommandRegistration:
    """Test that device group commands are registered."""

    def test_commands_registered(self):
        from wy_qcos_client.shell import command_manager as cm

        assert "create-device-group" in cm.commands
        assert "update-device-group" in cm.commands
        assert "get-device-group" in cm.commands
        assert "list-device-groups" in cm.commands
        assert "delete-device-groups" in cm.commands
