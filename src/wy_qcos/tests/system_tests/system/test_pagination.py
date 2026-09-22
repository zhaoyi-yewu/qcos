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

"""System tests for list API pagination, sort and filter."""

import json
import logging

import pytest

from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("global_configs")
@pytest.mark.scheduler
class TestListApiPagination:
    """Test pagination, sort and filter on list APIs."""

    @classmethod
    def setup_class(cls):
        """Initialize test environment."""
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]

    # -- get_drivers pagination/sort/filter --------------------------- #

    @pytest.mark.smoke
    def test_get_drivers_pagination(self):
        """Test get_drivers with pagination."""
        status_code, reason, text, result = self.admin_client.get_drivers(
            pagination={"page": 1, "page_size": 1}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get drivers with pagination: {err_msg}"
        resp = json.loads(text)
        result_data = resp.get("result", {})
        assert "items" in result_data
        assert result_data["page"] == 1
        assert result_data["page_size"] == 1
        assert result_data["total"] >= 0

    def test_get_drivers_sort(self):
        """Test get_drivers with sort."""
        status_code, reason, text, result = self.admin_client.get_drivers(
            sort=["name"]
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get drivers with sort: {err_msg}"

    def test_get_drivers_filter(self):
        """Test get_drivers with filter."""
        status_code, reason, text, result = self.admin_client.get_drivers(
            filters={"tech_type": "sim"}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get drivers with filter: {err_msg}"

    def test_get_drivers_backward_compatible(self):
        """Test get_drivers without pagination returns original format."""
        status_code, reason, text, result = self.admin_client.get_drivers()
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get drivers without pagination: {err_msg}"

    # -- get_devices pagination/sort/filter --------------------------- #

    @pytest.mark.smoke
    def test_get_devices_pagination(self):
        """Test get_devices with pagination."""
        status_code, reason, text, result = self.admin_client.get_devices(
            pagination={"page": 1, "page_size": 1}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get devices with pagination: {err_msg}"
        resp = json.loads(text)
        result_data = resp.get("result", {})
        assert "items" in result_data
        assert result_data["page"] == 1

    def test_get_devices_filter(self):
        """Test get_devices with filter."""
        status_code, reason, text, result = self.admin_client.get_devices(
            filters={"enable": "true"}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get devices with filter: {err_msg}"

    # -- get_transpilers pagination/sort/filter ---------------------- #

    @pytest.mark.smoke
    def test_get_transpilers_pagination(self):
        """Test get_transpilers with pagination."""
        status_code, reason, text, result = self.admin_client.get_transpilers(
            pagination={"page": 1, "page_size": 1}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get transpilers with pagination: {err_msg}"
        resp = json.loads(text)
        result_data = resp.get("result", {})
        assert "items" in result_data

    def test_get_transpilers_filter(self):
        """Test get_transpilers with filter."""
        status_code, reason, text, result = self.admin_client.get_transpilers(
            filters={"enable": "true"}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get transpilers with filter: {err_msg}"

    # -- list_workers pagination/sort/filter -------------------------- #

    @pytest.mark.smoke
    def test_list_workers_pagination(self):
        """Test list_workers with pagination."""
        status_code, reason, text, result = self.admin_client.list_workers(
            pagination={"page": 1, "page_size": 1}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to list workers with pagination: {err_msg}"

    # -- get_jobs pagination/sort/filter ----------------------------- #

    @pytest.mark.smoke
    def test_get_jobs_pagination(self):
        """Test get_jobs with pagination."""
        status_code, reason, text, result = self.admin_client.get_jobs(
            pagination={"page": 1, "page_size": 1}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get jobs with pagination: {err_msg}"
        resp = json.loads(text)
        result_data = resp.get("result", {})
        assert "items" in result_data
        assert result_data["page"] == 1
        assert result_data["page_size"] == 1

    def test_get_jobs_sort(self):
        """Test get_jobs with sort."""
        status_code, reason, text, result = self.admin_client.get_jobs(
            sort=["-created_at"]
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get jobs with sort: {err_msg}"

    def test_get_jobs_filter(self):
        """Test get_jobs with generic --filter."""
        status_code, reason, text, result = self.admin_client.get_jobs(
            filters={"job_status": "COMPLETED"}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get jobs with filter: {err_msg}"

    def test_get_jobs_page_size_negative_one(self):
        """Test get_jobs with page_size=-1 (unlimited)."""
        status_code, reason, text, result = self.admin_client.get_jobs(
            pagination={"page": 1, "page_size": -1}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get jobs with page_size=-1: {err_msg}"
        resp = json.loads(text)
        result_data = resp.get("result", {})
        assert result_data["total_pages"] == 1

    def test_get_jobs_backward_compatible(self):
        """Test get_jobs without pagination returns list."""
        status_code, reason, text, result = self.admin_client.get_jobs()
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get jobs without pagination: {err_msg}"

    # -- get_flavors pagination/sort/filter --------------------------- #

    @pytest.mark.smoke
    def test_get_flavors_pagination(self):
        """Test get_flavors with pagination."""
        status_code, reason, text, result = self.admin_client.get_flavors(
            pagination={"page": 1, "page_size": 1}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get flavors with pagination: {err_msg}"
        resp = json.loads(text)
        result_data = resp.get("result", {})
        assert "items" in result_data

    # -- get_device_groups pagination/sort/filter -------------------- #

    @pytest.mark.smoke
    def test_get_device_groups_pagination(self):
        """Test get_device_groups with pagination."""
        status_code, reason, text, result = (
            self.admin_client.get_device_groups(
                pagination={"page": 1, "page_size": 1}
            )
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, (
            f"Failed to get device groups with pagination: {err_msg}"
        )
        resp = json.loads(text)
        result_data = resp.get("result", {})
        assert "items" in result_data

    # -- get_projects pagination/sort/filter -------------------------- #

    @pytest.mark.smoke
    def test_get_projects_pagination(self):
        """Test get_projects with pagination."""
        status_code, reason, text, result = self.admin_client.get_projects(
            pagination={"page": 1, "page_size": 1}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get projects with pagination: {err_msg}"
        resp = json.loads(text)
        result_data = resp.get("result", {})
        assert "items" in result_data

    # -- get_users pagination/sort/filter ---------------------------- #

    @pytest.mark.smoke
    def test_get_users_pagination(self):
        """Test get_users with pagination."""
        status_code, reason, text, result = self.admin_client.get_users(
            pagination={"page": 1, "page_size": 1}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get users with pagination: {err_msg}"
        resp = json.loads(text)
        result_data = resp.get("result", {})
        assert "items" in result_data

    # -- get_roles pagination/sort/filter ---------------------------- #

    @pytest.mark.smoke
    def test_get_roles_pagination(self):
        """Test get_roles with pagination."""
        status_code, reason, text, result = self.admin_client.get_roles(
            pagination={"page": 1, "page_size": 1}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get roles with pagination: {err_msg}"
        resp = json.loads(text)
        result_data = resp.get("result", {})
        assert "items" in result_data

    # -- get_login_logs pagination/sort/filter ----------------------- #

    @pytest.mark.smoke
    def test_get_login_logs_pagination(self):
        """Test get_login_logs with pagination."""
        status_code, reason, text, result = self.admin_client.get_login_logs(
            pagination={"page": 1, "page_size": 1}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get login logs with pagination: {err_msg}"
        resp = json.loads(text)
        result_data = resp.get("result", {})
        assert "items" in result_data

    def test_get_login_logs_page_size_negative_one(self):
        """Test get_login_logs with page_size=-1."""
        status_code, reason, text, result = self.admin_client.get_login_logs(
            pagination={"page": 1, "page_size": -1}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, (
            f"Failed to get login logs with page_size=-1: {err_msg}"
        )
        resp = json.loads(text)
        result_data = resp.get("result", {})
        assert result_data["total_pages"] == 1
