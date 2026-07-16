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
import uuid

import pytest

from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("global_configs")
@pytest.mark.scheduler
class TestDeviceGroup:
    """Test DeviceGroup CRUD operations."""

    test_group_names = [
        "st-test-device-group",
        "st-test-device-group-2",
    ]

    @classmethod
    def setup_class(cls):
        """Initialize test environment."""
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls._cleanup_test_groups()

    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        cls._cleanup_test_groups()

    @classmethod
    def _cleanup_test_groups(cls):
        """Clean up test device groups by name.

        Uses group_names multi-value filter to query all test
        groups in one request, then deletes them by ID in batch.
        """
        try:
            status_code, reason, text, result = (
                cls.admin_client.get_device_groups(
                    filters={"group_names": cls.test_group_names}
                )
            )
            if status_code != 200:
                return
            resp = json.loads(text)
            groups = resp.get("result", [])
            group_ids = [g["id"] for g in groups]
            if group_ids:
                cls.admin_client.delete_device_groups(group_ids)
                for g in groups:
                    logger.info(
                        f"Cleaned up device group: "
                        f"{g.get('name')} (id: {g['id']})"
                    )
        except Exception as e:
            logger.warning(f"Failed to cleanup device groups: {e}")

    @property
    def test_group_name(self):
        """Backward-compat property for the primary test group name."""
        return self.test_group_names[0]

    def _ensure_group_exists(self, name=None):
        """Ensure test group exists, create if not.

        Returns:
            group ID string
        """
        group_name = name or self.test_group_name
        status_code, reason, text, result = (
            self.admin_client.get_device_groups()
        )
        if status_code == 200:
            try:
                resp = json.loads(text)
                groups = resp.get("result", [])
                for group in groups:
                    if group.get("name") == group_name:
                        return group["id"]
            except Exception as e:
                logger.warning(f"Failed to find existing group: {e}")

        status_code, reason, text, result = (
            self.admin_client.create_device_group(
                name=group_name,
                description="ST test device group",
                device_names=["dummy"],
                is_public=True,
            )
        )
        resp = json.loads(text)
        return resp["result"]["id"]

    @pytest.mark.smoke
    def test_create_device_group(self):
        """Test creating a device group."""
        status_code, reason, text, result = (
            self.admin_client.create_device_group(
                name=self.test_group_name,
                description="ST test device group",
                device_names=["dummy"],
                is_public=True,
            )
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to create device group: {err_msg}"
        resp = json.loads(text)
        group = resp["result"]
        assert group["name"] == self.test_group_name
        assert group["is_public"] is True
        assert group["device_names"] == ["dummy"]

    @pytest.mark.smoke
    def test_get_device_groups(self):
        """Test getting device group list."""
        self._ensure_group_exists()

        status_code, reason, text, result = (
            self.admin_client.get_device_groups()
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get device groups: {err_msg}"
        resp = json.loads(text)
        groups = resp["result"]
        assert isinstance(groups, list)
        assert len(groups) > 0

    @pytest.mark.smoke
    def test_get_device_groups_with_filter(self):
        """Test getting device groups with name filter."""
        self._ensure_group_exists()

        status_code, reason, text, result = (
            self.admin_client.get_device_groups(
                filters={"group_name": self.test_group_name}
            )
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get groups: {err_msg}"
        resp = json.loads(text)
        groups = resp["result"]
        assert isinstance(groups, list)
        assert len(groups) >= 1

    @pytest.mark.smoke
    def test_get_device_group(self):
        """Test getting a single device group by ID."""
        gid = self._ensure_group_exists()

        status_code, reason, text, result = self.admin_client.get_device_group(
            gid
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get device group: {err_msg}"
        resp = json.loads(text)
        group = resp["result"]
        assert group["id"] == gid
        assert group["name"] == self.test_group_name

    @pytest.mark.smoke
    def test_get_device_group_not_found(self):
        """Test getting a non-existent group returns error."""
        nonexistent_id = str(uuid.uuid4())
        status_code, reason, text, result = self.admin_client.get_device_group(
            nonexistent_id
        )
        resp = json.loads(text)
        assert "error" in resp
        assert resp["error"] is not None

    def test_update_device_group(self):
        """Test updating a device group."""
        gid = self._ensure_group_exists()

        status_code, reason, text, result = (
            self.admin_client.update_device_group(
                group_id=gid,
                description="Updated description",
                device_names=["dummy", "qutip_sim"],
            )
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to update group: {err_msg}"
        resp = json.loads(text)
        group = resp["result"]
        assert group["description"] == "Updated description"
        assert group["device_names"] == ["dummy", "qutip_sim"]

    def test_update_device_group_name(self):
        """Test updating a device group's name."""
        gid = self._ensure_group_exists()
        new_name = f"{self.test_group_name}-renamed"

        status_code, reason, text, result = (
            self.admin_client.update_device_group(group_id=gid, name=new_name)
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to update name: {err_msg}"
        resp = json.loads(text)
        assert resp["result"]["name"] == new_name

        # revert name
        self.admin_client.update_device_group(
            group_id=gid, name=self.test_group_name
        )

    def test_delete_device_groups(self):
        """Test deleting a device group (batch)."""
        gid = self._ensure_group_exists()

        status_code, reason, text, result = (
            self.admin_client.delete_device_groups([gid])
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to delete group: {err_msg}"

        # Verify deletion
        status_code, reason, text, result = self.admin_client.get_device_group(
            gid
        )
        resp = json.loads(text)
        assert "error" in resp

    def test_delete_device_groups_not_found(self):
        """Test deleting a non-existent group returns error result."""
        nonexistent_id = str(uuid.uuid4())
        status_code, reason, text, result = (
            self.admin_client.delete_device_groups([nonexistent_id])
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to delete groups: {err_msg}"
        resp = json.loads(text)
        results = resp.get("result", {}).get("results", [])
        assert len(results) == 1
        assert results[0]["success"] is False

    def test_delete_device_groups_batch(self):
        """Test batch deleting multiple device groups."""
        gid1 = self._ensure_group_exists()
        gid2 = self._ensure_group_exists(name=f"{self.test_group_name}-2")

        status_code, reason, text, result = (
            self.admin_client.delete_device_groups([gid1, gid2])
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to batch delete groups: {err_msg}"
        resp = json.loads(text)
        results = resp.get("result", {}).get("results", [])
        assert len(results) == 2
        for r in results:
            assert r["success"] is True

        # Verify both deleted
        for gid in [gid1, gid2]:
            status_code, reason, text, result = (
                self.admin_client.get_device_group(gid)
            )
            resp = json.loads(text)
            assert "error" in resp

    def test_get_device_groups_with_ids_filter(self):
        """Test get_device_groups with group_ids filter."""
        gid = self._ensure_group_exists()

        status_code, reason, text, result = (
            self.admin_client.get_device_groups(filters={"group_ids": [gid]})
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get groups with ids filter: {err_msg}"
        resp = json.loads(text)
        groups = resp["result"]
        assert isinstance(groups, list)
        assert len(groups) >= 1
        assert any(g["id"] == gid for g in groups)

        # Cleanup
        self.admin_client.delete_device_groups([gid])
