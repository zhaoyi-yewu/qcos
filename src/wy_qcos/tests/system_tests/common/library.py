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
import logging
import time

import wy_qcos.api.posiq.routes_jsonrpc.errors as jsonrpc_errors
from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos.common.library import Library

logger = logging.getLogger(__name__)


class StLibrary:
    """ST Library."""

    @staticmethod
    def is_response_success(status_code, text):
        """Check if call_json_rpc response is successful.

        A successful response must satisfy:
        1. status_code == 200
        2. No error field in the JSON response

        Args:
            status_code: HTTP status code
            text: Response text containing JSON

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        if status_code != 200:
            return False, f"HTTP status code is {status_code}, not 200"

        try:
            response_dict = json.loads(text)
            if "error" in response_dict and response_dict["error"]:
                error_dict = response_dict["error"]
                error_msg = error_dict.get("message", "Unknown error")
                error_details = error_dict.get("data", {}).get("details", "")
                if error_details:
                    error_msg = f"{error_msg}: {error_details}"
                return False, error_msg
            return True, ""
        except json.JSONDecodeError as e:
            return False, f"Failed to parse JSON: {str(e)}"

    @staticmethod
    def submit_job(client, job_info):
        job_id = job_info["job_id"]
        job_name = job_info["job_name"]
        source_code_list = job_info["source_code_list"]
        code_type = job_info["code_type"]
        circuit_aggregation = job_info["circuit_aggregation"]
        job_type = job_info["job_type"]
        job_priority = job_info["job_priority"]
        description = job_info["description"]
        shots = job_info["shots"]
        backend = job_info["backend"]
        driver_options = job_info["driver_options"]
        transpiler = job_info["transpiler"]
        transpiler_options = job_info["transpiler_options"]
        profiling = job_info["profiling"]
        callbacks = job_info["callbacks"]
        dry_run = job_info["dry_run"]
        status_code, reason, text, response = client.submit_job(
            source_code_list,
            code_type=code_type,
            job_id=job_id,
            circuit_aggregation=circuit_aggregation,
            job_name=job_name,
            job_type=job_type,
            job_priority=job_priority,
            description=description,
            shots=shots,
            backend=backend,
            driver_options=driver_options,
            transpiler=transpiler,
            transpiler_options=transpiler_options,
            profiling=profiling,
            callbacks=callbacks,
            dry_run=dry_run,
        )
        if status_code != HttpCode.SUCCESS_OK:
            raise AssertionError(
                f"Job submission failed with status {status_code}. "
                f"Reason: {reason}. Response: {text}"
            )
        json_results = json.loads(text)
        error_results = json_results.get("error", {})
        if error_results:
            raise AssertionError(
                f"Job submission failed with status {status_code}. "
                f"Reason: {reason}. Response: {text}"
            )

        result = json_results["result"]

        # check results from submit_job
        assert result["job_id"] == job_id
        assert result["job_name"] == job_name
        assert result["job_type"] == job_type
        assert result["job_priority"] == job_priority
        assert result["description"] == description
        assert result["shots"] == shots
        assert result["backend"] == backend
        assert result["driver_options"] == driver_options
        assert result["transpiler"] == transpiler
        assert result["transpiler_options"] == transpiler_options
        assert result["profiling"] == profiling
        assert result["callbacks"] == callbacks
        assert result["dry_run"] == dry_run
        return result

    @staticmethod
    def wait_and_get_job_result(client, job_info, timeout=30, interval=5):
        # wait for job status to COMPLETED
        success, err_msg, _ = Library.loop_with_timeout(
            StLibrary.get_job_status,
            timeout,
            interval,
            client,
            job_info["job_id"],
        )
        # wait for additional time for job to finish resource cleanup
        time.sleep(5)

        # check results
        job_result = StLibrary.get_job_results(client, job_info["job_id"])

        return success, err_msg, job_result

    @staticmethod
    def get_job_results(client, job_id):
        status_code, reason, text, response = client.get_job_results(job_id)
        assert status_code == HttpCode.SUCCESS_OK
        job_result = json.loads(text)
        job_error = job_result.get("error", {})
        error_code = job_error.get("code", 0)
        assert error_code == 0
        return job_result

    @staticmethod
    def get_job_status(client, job_id):
        _status_code, _reason, _text, _response = client.get_job_status(job_id)
        job_result = json.loads(_text)
        job_status = job_result["result"]["job_status"]
        expect_task_status = [
            Constant.JOB_STATUS_COMPLETED,
            Constant.JOB_STATUS_FAILED,
            Constant.JOB_STATUS_CANCELLED,
        ]
        if job_status in expect_task_status:
            return True, None, None
        err_msg = (
            f"Job status not in {expect_task_status}, "
            f"and current status: {job_status}"
        )
        return False, err_msg, None

    @staticmethod
    def delete_job(client, job_id):
        status_code, reason, text, response = client.delete_jobs([job_id])
        assert status_code == HttpCode.SUCCESS_OK

        # check if job deleted
        status_code, reason, text, response = client.get_job_results(job_id)
        assert status_code == HttpCode.SUCCESS_OK
        job_result = json.loads(text)
        job_error = job_result.get("error", {})
        error_code = job_error.get("code", 0)
        assert error_code == jsonrpc_errors.NotFoundError.CODE

    @staticmethod
    def get_devices(client):
        status_code, reason, text, response = client.get_devices()
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0
        devices = result["result"]
        return devices

    @staticmethod
    def get_device(client, device_name, details=False):
        status_code, reason, text, response = client.get_device(
            device_name, details
        )
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0
        device = result["result"]
        return device

    @staticmethod
    def get_drivers(client):
        status_code, reason, text, response = client.get_drivers()
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0
        drivers = result["result"]
        return drivers

    @staticmethod
    def get_driver(client, driver_name):
        status_code, reason, text, response = client.get_driver(driver_name)
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0
        driver = result["result"]
        return driver

    @staticmethod
    def get_transpilers(client):
        status_code, reason, text, response = client.get_transpilers()
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0
        transpilers = result["result"]
        return transpilers

    @staticmethod
    def get_transpiler(client, transpiler_name):
        status_code, reason, text, response = client.get_transpiler(
            transpiler_name
        )
        assert status_code == HttpCode.SUCCESS_OK
        result = json.loads(text)
        error = result.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0
        transpiler = result["result"]
        return transpiler

    @staticmethod
    def login(client, username, password):
        """User login."""
        status_code, reason, text, result = client.login(username, password)
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Login failed: {status_code} {reason} {text}"
        )

        # Parse JSON response from text
        response = json.loads(text) if text else {}

        error = response.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0, (
            f"Login error: {error_code} - {error.get('message')} - {response}"
        )
        login_result = response.get("result", response)
        return login_result

    @staticmethod
    def logout(client):
        """User logout."""
        status_code, reason, text, result = client.logout()
        assert status_code == HttpCode.SUCCESS_OK

        # Parse JSON response from text
        response = json.loads(text) if text else {}

        error = response.get("error", {})
        error_code = error.get("code", 0)
        assert error_code == 0

    @staticmethod
    def create_project(client, project_name, description=None):
        """Create project."""
        status_code, reason, text, result = client.create_project(
            project_name, description
        )
        assert status_code == HttpCode.SUCCESS_OK
        assert result is not None
        project_info = json.loads(text)["result"]
        assert project_info.get("name") == project_name
        _description = project_info.get("description", None)
        if _description:
            assert _description == _description
        project_id = project_info.get("id")
        assert project_id is not None
        return project_info

    @staticmethod
    def update_project(
        client, project_id, updated_name=None, description=None
    ):
        """Update project."""
        status_code, reason, text, result = client.update_project(
            project_id, updated_name, description
        )
        assert status_code == HttpCode.SUCCESS_OK
        project_info = json.loads(text)["result"]
        if updated_name:
            assert project_info.get("name") == updated_name
        if description:
            assert project_info.get("description") == description
        return project_info

    @staticmethod
    def get_project(client, project_id):
        """Get project."""
        status_code, reason, text, result = client.get_project(project_id)
        assert status_code == HttpCode.SUCCESS_OK
        assert result is not None
        project_info = json.loads(text).get("result", None)
        error_info = json.loads(text).get("error", {})
        return project_info, error_info

    @staticmethod
    def get_projects(client):
        """Get projects."""
        status_code, reason, text, result = client.get_projects()
        assert status_code == HttpCode.SUCCESS_OK
        assert result is not None
        projects = json.loads(text)["result"]
        return projects

    @staticmethod
    def delete_project(client, project_id):
        """Delete project."""
        status_code, reason, text, result = client.delete_project(project_id)
        assert status_code == HttpCode.SUCCESS_OK
        project_info = json.loads(text)["result"]
        assert project_id == project_info.get("id")

    @staticmethod
    def create_user(client, user_data):
        """Create user."""
        user_name = user_data.get("user_name")
        password = user_data.get("password")
        roles = user_data.get("roles", [])
        description = user_data.get("description")
        password_expiry_days = user_data.get("password_expiry_days")
        is_enabled = user_data.get("is_enabled", True)
        is_locked = user_data.get("is_locked", True)

        status_code, reason, text, result = client.create_user(
            user_name,
            password,
            roles,
            description=description,
            password_expiry_days=password_expiry_days,
            is_enabled=is_enabled,
            is_locked=is_locked,
        )
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Create user failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        user = response.get("result", response)
        return user, error

    @staticmethod
    def update_user(
        client,
        user_id,
        roles=None,
        description=None,
        password_expiry_days=None,
        is_enabled=None,
        is_locked=None,
    ):
        """Update user."""
        status_code, reason, text, result = client.update_user(
            user_id,
            roles=roles,
            description=description,
            password_expiry_days=password_expiry_days,
            is_enabled=is_enabled,
            is_locked=is_locked,
        )

        assert status_code == HttpCode.SUCCESS_OK
        user_info = json.loads(text)["result"]
        if roles:
            assert user_info.get("roles") == roles
        if description:
            assert user_info.get("description") == description
        if password_expiry_days:
            assert (
                user_info.get("password_expiry_days") == password_expiry_days
            )
        if is_enabled is not None:
            assert user_info.get("is_enabled") == is_enabled
        if is_locked is not None:
            assert user_info.get("is_locked") == is_locked
        return user_info

    @staticmethod
    def get_user(client, username, is_name=False):
        """Get user info."""
        user_id = username
        if is_name:
            user_id = client.resolve_user_id(client, username)
        status_code, reason, text, result = client.get_user(user_id)
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Get user failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        msg = f"Get user error: {error_code}"
        assert error_code == 0, msg
        user = response.get("result", response)
        return user

    @staticmethod
    def get_users(client):
        """Get all users."""
        status_code, reason, text, result = client.get_users()
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Get users failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        msg = f"Get users error: {error_code}"
        assert error_code == 0, msg
        users = response.get("result", response)
        return users

    @staticmethod
    def get_me(client):
        """Get user info."""
        status_code, reason, text, result = client.get_me()
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Get current user failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        msg = f"Get current user error: {error_code}"
        assert error_code == 0, msg
        user = response.get("result", response)
        return user

    @staticmethod
    def delete_user(client, username, is_name=False, force=False):
        """Delete user."""
        user_id = username
        if is_name:
            user_id = client.resolve_user_id(client, username)
        status_code, reason, text, result = client.delete_user(user_id, force)
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Delete user failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        msg = f"Delete user error: {error_code}"
        assert error_code == 0, msg

    @staticmethod
    def create_role(client, role_data):
        """Create role."""
        role_name = role_data.get("role_name")
        permissions = role_data.get("permissions", [])
        description = role_data.get("description")

        status_code, reason, text, result = client.create_role(
            role_name, permissions, description=description
        )
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Create role failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        msg = f"Create role error: {error_code}"
        assert error_code == 0, msg
        role = response.get("result", response)
        return role

    @staticmethod
    def get_role(client, role_name, is_name=False):
        """Get role info."""
        role_id = role_name
        if is_name:
            role_id = client.resolve_role_id(client, role_name)
        status_code, reason, text, result = client.get_role(role_id)
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Get role failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        msg = f"Get role error: {error_code}"
        assert error_code == 0, msg
        role = response.get("result", response)
        return role

    @staticmethod
    def get_roles(client):
        """Get all roles."""
        status_code, reason, text, result = client.get_roles()
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Get roles failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        msg = f"Get roles error: {error_code}"
        assert error_code == 0, msg
        roles = response.get("result", response)
        return roles

    @staticmethod
    def delete_role(client, role_name, is_name=False):
        """Delete role."""
        role_id = role_name
        if is_name:
            role_id = client.resolve_role_id(client, role_name)
        status_code, reason, text, result = client.delete_role(role_id)
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Delete role failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        msg = f"Delete role error: {error_code}"
        assert error_code == 0, msg

    @staticmethod
    def change_password(
        client, username, old_password, new_password, is_name=False
    ):
        """Change user password."""
        user_id = username
        if is_name:
            user_id = client.resolve_user_id(client, username)
        status_code, reason, text, result = client.change_password(
            user_id, old_password, new_password
        )
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Change password failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        msg = f"Change password error: {error_code}"
        assert error_code == 0, msg

    @staticmethod
    def get_user_roles(client, username):
        """Get all roles for user."""
        status_code, reason, text, result = client.get_user_roles(username)
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Get user roles failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        msg = f"Get user roles error: {error_code}"
        assert error_code == 0, msg
        roles = response.get("result", response)
        return roles

    @staticmethod
    def get_login_logs(
        client, username=None, user_id=None, limit=100, offset=0
    ):
        """Get login logs."""
        status_code, reason, text, result = client.get_login_logs(
            user_id=user_id, user_name=username, limit=limit, offset=offset
        )
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Get login logs failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        msg = f"Get login logs error: {error_code}"
        assert error_code == 0, msg
        logs = response.get("result", response)
        return logs

    @staticmethod
    def clear_login_logs(client, user_id=None, user_name=None):
        """Clear login logs (all or for a specific user)."""
        status_code, reason, text, result = client.clear_login_logs(
            user_id=user_id, user_name=user_name
        )
        assert status_code == HttpCode.SUCCESS_OK, (
            f"Clear login logs failed: {status_code} {reason} {text}"
        )
        response = json.loads(text) if text else {}
        error = response.get("error", {})
        error_code = error.get("code", 0)
        msg = f"Clear login logs error: {error_code}"
        assert error_code == 0, msg
        result = response.get("result", response)
        return result

    @staticmethod
    def get_auth_mode(admin_client):
        """Get current authentication mode.

        Args:
            admin_client: Admin client for API calls

        Returns:
            The current auth mode
        """
        current_auth_mode = Constant.AUTH_MODE_NO
        try:
            status_code, _, text, _ = admin_client.get_user_mgmt()
            if status_code == 200:
                response_dict = json.loads(text)
                result_dict = response_dict.get("result", {})
                error_dict = response_dict.get("error", {})
                error_details = error_dict.get("data", {}).get("details", "")
                if error_dict and "Unauthorized access" in error_details:
                    current_auth_mode = Constant.AUTH_MODE_VIRTUAL_INSTANCE
                else:
                    current_auth_mode = result_dict.get(
                        "auth_mode", Constant.AUTH_MODE_NO
                    )
        except Exception:  # noqa: S110
            pass
        logger.info("Current auth_mode: {}".format(current_auth_mode))
        return current_auth_mode

    @staticmethod
    def set_auth_mode(
        admin_client, virtual_instance_client, current_auth_mode, set_auth_mode
    ):
        """Set auth mode.

        Args:
            admin_client: Admin client for API calls
            virtual_instance_client: Virtual instance client for API calls
            current_auth_mode: current auth mode
            set_auth_mode: auth mode to set
        """
        logger.info(f"Set to auth_mode: {set_auth_mode}")
        try:
            if current_auth_mode == Constant.AUTH_MODE_VIRTUAL_INSTANCE:
                virtual_instance_client.set_user_mgmt(set_auth_mode)
            else:
                admin_client.set_user_mgmt(set_auth_mode)
        except Exception:  # noqa: S110
            pass
