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

"""Unit tests for mcp_server module."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from wy_qcos.common.library import _s
from wy_qcos.api.mcp.mcp_server import (
    qcos_get_version,
    qcos_list_devices,
    qcos_get_device_detail,
    qcos_submit_job,
    qcos_list_jobs,
    qcos_get_job_status,
    qcos_get_job_result,
    qcos_cancel_jobs,
    qcos_delete_jobs,
    qcos_update_job,
    qcos_get_flavors,
    qcos_get_drivers,
    qcos_get_transpilers,
    qcos_get_projects,
    qcos_get_current_user,
    qcos_get_system_health,
    qcos_ping,
    qcos_system_info,
    qcos_create_flavor,
    qcos_update_flavor,
    qcos_get_flavor,
    qcos_delete_flavors,
    qcos_create_device_group,
    qcos_update_device_group,
    qcos_get_device_group,
    qcos_get_device_groups,
    qcos_delete_device_groups,
    qcos_set_device,
    qcos_calibrate_device,
    qcos_get_calibrate_results,
    qcos_get_users,
    qcos_get_roles,
    qcos_get_login_logs,
    qcos_clear_login_logs,
    qcos_show_mem,
    qcos_gc_mem,
    qcos_list_workers,
    qcos_restart_worker,
    qcos_get_api_stats,
    qcos_get_job_stats,
    qcos_get_driver,
    qcos_get_transpiler,
    qcos_get_project,
    qcos_create_project,
    qcos_update_project,
    qcos_delete_project,
    qcos_get_user,
    qcos_create_user,
    qcos_update_user,
    qcos_delete_user,
    qcos_change_password,
    qcos_get_role,
    qcos_create_role,
    qcos_update_role,
    qcos_delete_role,
    qcos_get_user_mgmt,
    qcos_set_user_mgmt,
    qcos_set_device_options,
    qcos_get_device_options,
)


class TestMcpToolsNoAuth:
    """Test MCP tools that don't require authentication."""

    @pytest.mark.asyncio
    async def test_qcos_get_version(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"version": "1.8.0", "api_version": "v1"}
            result = await qcos_get_version(details=True)
            data = json.loads(result)
            assert data["version"] == "1.8.0"
            mock_call.assert_called_once_with(
                "/version", "version", {"details": True}
            )

    @pytest.mark.asyncio
    async def test_qcos_get_version_no_details(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"version": "1.8.0"}
            result = await qcos_get_version(details=False)
            data = json.loads(result)
            assert data["version"] == "1.8.0"
            mock_call.assert_called_once_with(
                "/version", "version", {"details": False}
            )

    @pytest.mark.asyncio
    async def test_qcos_ping(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"message": "pong"}
            result = await qcos_ping(message="hello")
            data = json.loads(result)
            assert data["message"] == "pong"

    @pytest.mark.asyncio
    async def test_qcos_system_info(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"total_jobs_count": 42}
            result = await qcos_system_info()
            data = json.loads(result)
            assert data["total_jobs_count"] == 42

    @pytest.mark.asyncio
    async def test_qcos_get_system_health(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"system_healthy": True}
            result = await qcos_get_system_health()
            data = json.loads(result)
            assert data["system_healthy"] is True


class TestMcpToolsWithAuth:
    """Test MCP tools that require authentication."""

    @pytest.mark.asyncio
    async def test_qcos_list_devices(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"dev1": {"alias_name": "Device 1"}}
            result = await qcos_list_devices(details=True)
            data = json.loads(result)
            assert "dev1" in data
            mock_call.assert_called_once_with(
                "/v1/device", "get_devices", {"details": True}
            )

    @pytest.mark.asyncio
    async def test_qcos_get_device_detail(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"name": "dev1", "status": "online"}
            result = await qcos_get_device_detail(name="dev1", details=True)
            data = json.loads(result)
            assert data["name"] == "dev1"
            mock_call.assert_called_once_with(
                "/v1/device", "get_device", {"name": "dev1", "details": True}
            )

    @pytest.mark.asyncio
    async def test_qcos_submit_job(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"job_id": "job-123"}
            result = await qcos_submit_job(
                source_code=["OPENQASM 2.0;"],
                code_type="qasm",
                backend="dev1",
                shots=1024,
            )
            data = json.loads(result)
            assert data["job_id"] == "job-123"
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_qcos_submit_job_with_flavor(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"job_id": "job-456"}
            result = await qcos_submit_job(
                source_code=["OPENQASM 2.0;"],
                code_type="qasm",
                flavor_id="flavor-123",
                shots=2048,
            )
            data = json.loads(result)
            assert data["job_id"] == "job-456"

    @pytest.mark.asyncio
    async def test_qcos_list_jobs(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"items": [], "total": 0}
            result = await qcos_list_jobs()
            data = json.loads(result)
            assert "items" in data

    @pytest.mark.asyncio
    async def test_qcos_get_job_status(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"job_status": "RUNNING"}
            result = await qcos_get_job_status(job_id="job-123")
            data = json.loads(result)
            assert data["job_status"] == "RUNNING"

    @pytest.mark.asyncio
    async def test_qcos_get_job_result(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"counts": {"0": 512, "1": 512}}
            result = await qcos_get_job_result(job_id="job-123")
            data = json.loads(result)
            assert "counts" in data

    @pytest.mark.asyncio
    async def test_qcos_cancel_jobs(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"cancelled": ["job-123"]}
            result = await qcos_cancel_jobs(job_ids=["job-123"])
            data = json.loads(result)
            assert "cancelled" in data

    @pytest.mark.asyncio
    async def test_qcos_delete_jobs(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"deleted": ["job-123"]}
            result = await qcos_delete_jobs(job_ids=["job-123"])
            data = json.loads(result)
            assert "deleted" in data

    @pytest.mark.asyncio
    async def test_qcos_get_flavors(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"flavor1": {"name": "flavor1"}}
            result = await qcos_get_flavors()
            data = json.loads(result)
            assert "flavor1" in data

    @pytest.mark.asyncio
    async def test_qcos_get_drivers(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"driver1": {"name": "driver1"}}
            result = await qcos_get_drivers()
            data = json.loads(result)
            assert "driver1" in data

    @pytest.mark.asyncio
    async def test_qcos_get_transpilers(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"cmss": {"alias_name": "CMSS"}}
            result = await qcos_get_transpilers()
            data = json.loads(result)
            assert "cmss" in data

    @pytest.mark.asyncio
    async def test_qcos_get_projects(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"proj1": {"name": "proj1"}}
            result = await qcos_get_projects()
            data = json.loads(result)
            assert "proj1" in data

    @pytest.mark.asyncio
    async def test_qcos_get_current_user(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"user_name": "admin"}
            result = await qcos_get_current_user()
            data = json.loads(result)
            assert data["user_name"] == "admin"

    @pytest.mark.asyncio
    async def test_qcos_update_job(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {
                "job_id": "job-123",
                "job_name": "new-name",
            }
            result = await qcos_update_job(
                job_id="job-123", job_name="new-name"
            )
            data = json.loads(result)
            assert data["job_name"] == "new-name"
            mock_call.assert_called_once_with(
                "/v1/job",
                "update_job",
                {"job_id": "job-123", "job_name": "new-name"},
            )


class TestMcpFlavorTools:
    """Test flavor-related MCP tools."""

    @pytest.mark.asyncio
    async def test_qcos_create_flavor(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {
                "id": "flavor-123",
                "name": "test-flavor",
            }
            result = await qcos_create_flavor(
                name="test-flavor", device_groups=["dg-1"], min_qubits=1
            )
            data = json.loads(result)
            assert data["name"] == "test-flavor"
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_qcos_update_flavor(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"id": "flavor-123", "name": "updated"}
            result = await qcos_update_flavor(
                flavor_id="flavor-123", name="updated"
            )
            data = json.loads(result)
            assert data["name"] == "updated"

    @pytest.mark.asyncio
    async def test_qcos_get_flavor(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"id": "flavor-123", "name": "test"}
            result = await qcos_get_flavor(flavor_id="flavor-123")
            data = json.loads(result)
            assert data["name"] == "test"

    @pytest.mark.asyncio
    async def test_qcos_delete_flavors(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"deleted": ["flavor-123"]}
            result = await qcos_delete_flavors(flavor_ids=["flavor-123"])
            data = json.loads(result)
            assert "deleted" in data


class TestMcpDeviceGroupTools:
    """Test device group related MCP tools."""

    @pytest.mark.asyncio
    async def test_qcos_create_device_group(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"id": "dg-123", "name": "test-group"}
            result = await qcos_create_device_group(
                name="test-group", device_names=["dev1"]
            )
            data = json.loads(result)
            assert data["name"] == "test-group"

    @pytest.mark.asyncio
    async def test_qcos_update_device_group(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"id": "dg-123", "name": "updated"}
            result = await qcos_update_device_group(
                group_id="dg-123", name="updated"
            )
            data = json.loads(result)
            assert data["name"] == "updated"

    @pytest.mark.asyncio
    async def test_qcos_get_device_group(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"id": "dg-123", "name": "test"}
            result = await qcos_get_device_group(group_id="dg-123")
            data = json.loads(result)
            assert data["name"] == "test"

    @pytest.mark.asyncio
    async def test_qcos_get_device_groups(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"dg-1": {"name": "group1"}}
            result = await qcos_get_device_groups()
            data = json.loads(result)
            assert "dg-1" in data

    @pytest.mark.asyncio
    async def test_qcos_delete_device_groups(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"deleted": ["dg-123"]}
            result = await qcos_delete_device_groups(group_ids=["dg-123"])
            data = json.loads(result)
            assert "deleted" in data


class TestMcpDeviceOpsTools:
    """Test device operation MCP tools."""

    @pytest.mark.asyncio
    async def test_qcos_set_device(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"name": "dev1", "state": "online"}
            result = await qcos_set_device(device_name="dev1", state="online")
            data = json.loads(result)
            assert data["state"] == "online"

    @pytest.mark.asyncio
    async def test_qcos_calibrate_device(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"status": "started"}
            result = await qcos_calibrate_device(
                device_name="dev1", method="rabi"
            )
            data = json.loads(result)
            assert data["status"] == "started"

    @pytest.mark.asyncio
    async def test_qcos_get_calibrate_results(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"result": "success"}
            result = await qcos_get_calibrate_results(
                device_name="dev1", method="rabi"
            )
            data = json.loads(result)
            assert data["result"] == "success"

    @pytest.mark.asyncio
    async def test_qcos_set_device_options(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"status": "ok"}
            result = await qcos_set_device_options(
                device_name="dev1", method="rabi", options={"amp": 0.5}
            )
            data = json.loads(result)
            assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_qcos_get_device_options(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"options": {"amp": 0.5}}
            result = await qcos_get_device_options(
                device_name="dev1", method="rabi"
            )
            data = json.loads(result)
            assert "options" in data


class TestMcpUserRoleProjectTools:
    """Test user/role/project MCP tools."""

    @pytest.mark.asyncio
    async def test_qcos_get_users(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"user1": {"user_name": "user1"}}
            result = await qcos_get_users()
            data = json.loads(result)
            assert "user1" in data

    @pytest.mark.asyncio
    async def test_qcos_get_user(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"user_name": "admin"}
            result = await qcos_get_user(user_id="user-123")
            data = json.loads(result)
            assert data["user_name"] == "admin"

    @pytest.mark.asyncio
    async def test_qcos_create_user(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"user_name": "newuser"}
            result = await qcos_create_user(
                user_name="newuser", password=_s("pass123")
            )
            data = json.loads(result)
            assert data["user_name"] == "newuser"

    @pytest.mark.asyncio
    async def test_qcos_update_user(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"user_name": "updated"}
            result = await qcos_update_user(
                user_id="user-123", description="updated"
            )
            data = json.loads(result)
            assert data["user_name"] == "updated"

    @pytest.mark.asyncio
    async def test_qcos_delete_user(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"deleted": True}
            result = await qcos_delete_user(user_id="user-123")
            data = json.loads(result)
            assert data["deleted"] is True

    @pytest.mark.asyncio
    async def test_qcos_change_password(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"changed": True}
            result = await qcos_change_password(
                user_id="user-123", new_password=_s("newpass")
            )
            data = json.loads(result)
            assert data["changed"] is True

    @pytest.mark.asyncio
    async def test_qcos_get_roles(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"admin": {"role_name": "admin"}}
            result = await qcos_get_roles()
            data = json.loads(result)
            assert "admin" in data

    @pytest.mark.asyncio
    async def test_qcos_get_role(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"role_name": "admin"}
            result = await qcos_get_role(role_id="role-123")
            data = json.loads(result)
            assert data["role_name"] == "admin"

    @pytest.mark.asyncio
    async def test_qcos_create_role(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"role_name": "newrole"}
            result = await qcos_create_role(role_name="newrole")
            data = json.loads(result)
            assert data["role_name"] == "newrole"

    @pytest.mark.asyncio
    async def test_qcos_update_role(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"role_name": "updated"}
            result = await qcos_update_role(
                role_id="role-123", description="updated"
            )
            data = json.loads(result)
            assert data["role_name"] == "updated"

    @pytest.mark.asyncio
    async def test_qcos_delete_role(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"deleted": True}
            result = await qcos_delete_role(role_id="role-123")
            data = json.loads(result)
            assert data["deleted"] is True

    @pytest.mark.asyncio
    async def test_qcos_get_project(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"name": "proj1"}
            result = await qcos_get_project(project_id="proj-123")
            data = json.loads(result)
            assert data["name"] == "proj1"

    @pytest.mark.asyncio
    async def test_qcos_create_project(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"name": "newproj"}
            result = await qcos_create_project(project_name="newproj")
            data = json.loads(result)
            assert data["name"] == "newproj"

    @pytest.mark.asyncio
    async def test_qcos_update_project(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"name": "updated"}
            result = await qcos_update_project(
                project_id="proj-123", project_name="updated"
            )
            data = json.loads(result)
            assert data["name"] == "updated"

    @pytest.mark.asyncio
    async def test_qcos_delete_project(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"deleted": True}
            result = await qcos_delete_project(project_id="proj-123")
            data = json.loads(result)
            assert data["deleted"] is True

    @pytest.mark.asyncio
    async def test_qcos_get_user_mgmt(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"auth_mode": "jwt"}
            result = await qcos_get_user_mgmt()
            data = json.loads(result)
            assert data["auth_mode"] == "jwt"

    @pytest.mark.asyncio
    async def test_qcos_set_user_mgmt(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"auth_mode": "no"}
            result = await qcos_set_user_mgmt(auth_mode="no")
            data = json.loads(result)
            assert data["auth_mode"] == "no"


class TestMcpSystemTools:
    """Test system-related MCP tools."""

    @pytest.mark.asyncio
    async def test_qcos_get_login_logs(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"items": []}
            result = await qcos_get_login_logs()
            data = json.loads(result)
            assert "items" in data

    @pytest.mark.asyncio
    async def test_qcos_clear_login_logs(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"cleared": 10}
            result = await qcos_clear_login_logs()
            data = json.loads(result)
            assert data["cleared"] == 10

    @pytest.mark.asyncio
    async def test_qcos_show_mem(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"rss_mb": 128}
            result = await qcos_show_mem()
            data = json.loads(result)
            assert "rss_mb" in data

    @pytest.mark.asyncio
    async def test_qcos_gc_mem(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"collected": 100}
            result = await qcos_gc_mem(generations=2)
            data = json.loads(result)
            assert data["collected"] == 100

    @pytest.mark.asyncio
    async def test_qcos_list_workers(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"workers": []}
            result = await qcos_list_workers()
            data = json.loads(result)
            assert "workers" in data

    @pytest.mark.asyncio
    async def test_qcos_restart_worker(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"restarted": True}
            result = await qcos_restart_worker(worker_name="worker-1")
            data = json.loads(result)
            assert data["restarted"] is True

    @pytest.mark.asyncio
    async def test_qcos_get_api_stats(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"total_requests": 1000}
            result = await qcos_get_api_stats()
            data = json.loads(result)
            assert data["total_requests"] == 1000

    @pytest.mark.asyncio
    async def test_qcos_get_job_stats(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"completed": 100}
            result = await qcos_get_job_stats()
            data = json.loads(result)
            assert data["completed"] == 100

    @pytest.mark.asyncio
    async def test_qcos_get_driver(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"name": "driver1"}
            result = await qcos_get_driver(name="driver1")
            data = json.loads(result)
            assert data["name"] == "driver1"

    @pytest.mark.asyncio
    async def test_qcos_get_transpiler(self):
        with patch(
            "wy_qcos.api.mcp.mcp_server._jsonrpc_call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = {"name": "cmss"}
            result = await qcos_get_transpiler(name="cmss")
            data = json.loads(result)
            assert data["name"] == "cmss"
