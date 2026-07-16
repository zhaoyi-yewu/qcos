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

from wy_qcos.flavor.flavor_manager import (
    DEFAULT_DEVICE_GROUP_QC_ALL_ID,
)
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("global_configs")
@pytest.mark.scheduler
class TestFlavor:
    """Test Flavor CRUD and auto scheduling."""

    test_flavor_names = [
        "st-test-flavor",
        "st-test-flavor-updated",
        "st-test-flavor-2",
    ]

    @classmethod
    def setup_class(cls):
        """Initialize test environment."""
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        # Clean up existing test flavors
        cls._cleanup_test_flavors()

    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        cls._cleanup_test_flavors()

    @classmethod
    def _cleanup_test_flavors(cls):
        """Clean up test flavors by name.

        Uses flavor_names multi-value filter to query all test
        flavors in one request, then deletes them by ID in batch.
        """
        try:
            status_code, reason, text, result = cls.admin_client.get_flavors(
                filters={"flavor_names": cls.test_flavor_names}
            )
            if status_code != 200:
                return
            resp = json.loads(text)
            flavors = resp.get("result", [])
            flavor_ids = [f["id"] for f in flavors]
            if flavor_ids:
                cls.admin_client.delete_flavors(flavor_ids)
                for f in flavors:
                    logger.info(
                        f"Cleaned up test flavor: {f.get('name')} "
                        f"(id: {f['id']})"
                    )
        except Exception as e:
            logger.warning(f"Failed to cleanup flavors: {e}")

    @property
    def test_flavor_name(self):
        """Backward-compat property for the primary test flavor name."""
        return self.test_flavor_names[0]

    @property
    def update_flavor_name(self):
        """Backward-compat property for the updated flavor name."""
        return self.test_flavor_names[1]

    def _ensure_flavor_exists(self, name=None):
        """Ensure test flavor exists, create if not.

        Args:
            name: flavor name, defaults to test_flavor_name

        Returns:
            flavor ID string
        """
        flavor_name = name or self.test_flavor_name
        status_code, reason, text, result = self.admin_client.get_flavors()
        if status_code == 200:
            try:
                resp = json.loads(text)
                flavors = resp.get("result", [])
                for flavor in flavors:
                    if flavor.get("name") == flavor_name:
                        return flavor["id"]
            except Exception as e:
                logger.warning(f"Failed to find existing flavor: {e}")

        # Create flavor
        status_code, reason, text, result = self.admin_client.create_flavor(
            name=flavor_name,
            description="ST test flavor",
            is_public=True,
            min_qubits=1,
            max_qubits=32,
            gate_fidelity_1q_min=0.99,
            gate_fidelity_2q_min=0.99,
            extra_properties={"qc:devices": "dummy"},
            device_groups=[DEFAULT_DEVICE_GROUP_QC_ALL_ID],
        )
        resp = json.loads(text)
        return resp["result"]["id"]

    @pytest.mark.smoke
    def test_create_flavor(self):
        """Test creating a flavor."""
        status_code, reason, text, result = self.admin_client.create_flavor(
            name=self.test_flavor_name,
            description="ST test flavor",
            is_public=True,
            min_qubits=1,
            max_qubits=32,
            gate_fidelity_1q_min=0.99,
            gate_fidelity_2q_min=0.99,
            extra_properties={"qc:devices": "dummy"},
            device_groups=[DEFAULT_DEVICE_GROUP_QC_ALL_ID],
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to create flavor: {err_msg}"
        resp = json.loads(text)
        flavor = resp["result"]
        assert flavor["name"] == self.test_flavor_name
        assert flavor["is_public"] is True
        assert flavor["min_qubits"] == 1
        assert flavor["max_qubits"] == 32
        assert flavor["gate_fidelity_1q_min"] == 0.99
        assert flavor["gate_fidelity_2q_min"] == 0.99
        assert flavor["extra_properties"] == {"qc:devices": "dummy"}

    @pytest.mark.smoke
    def test_get_flavors(self):
        """Test getting flavor list."""
        # First ensure a flavor exists
        self._ensure_flavor_exists()

        status_code, reason, text, result = self.admin_client.get_flavors()
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get flavors: {err_msg}"
        resp = json.loads(text)
        flavors = resp["result"]
        assert isinstance(flavors, list)
        assert len(flavors) > 0

    @pytest.mark.smoke
    def test_get_flavors_with_filter(self):
        """Test getting flavors with name filter."""
        self._ensure_flavor_exists()

        status_code, reason, text, result = self.admin_client.get_flavors(
            filters={"flavor_name": self.test_flavor_name}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get flavors with filter: {err_msg}"
        resp = json.loads(text)
        flavors = resp["result"]
        assert isinstance(flavors, list)
        # Default flavors should include g1.all etc.
        assert len(flavors) >= 1

    @pytest.mark.smoke
    def test_get_flavor(self):
        """Test getting a single flavor by ID."""
        flavor_id = self._ensure_flavor_exists()

        status_code, reason, text, result = self.admin_client.get_flavor(
            flavor_id
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get flavor: {err_msg}"
        resp = json.loads(text)
        flavor = resp["result"]
        assert flavor["id"] == flavor_id
        assert flavor["name"] == self.test_flavor_name

    @pytest.mark.smoke
    def test_get_flavor_not_found(self):
        """Test getting a non-existent flavor returns error."""
        nonexistent_id = str(uuid.uuid4())
        status_code, reason, text, result = self.admin_client.get_flavor(
            nonexistent_id
        )
        resp = json.loads(text)
        assert "error" in resp
        assert resp["error"] is not None

    def test_update_flavor(self):
        """Test updating a flavor."""
        flavor_id = self._ensure_flavor_exists()

        status_code, reason, text, result = self.admin_client.update_flavor(
            flavor_id=flavor_id,
            description="Updated description",
            max_qubits=64,
            gate_fidelity_2q_min=0.995,
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to update flavor: {err_msg}"
        resp = json.loads(text)
        flavor = resp["result"]
        assert flavor["description"] == "Updated description"
        assert flavor["max_qubits"] == 64
        assert flavor["gate_fidelity_2q_min"] == 0.995

    def test_update_flavor_name(self):
        """Test updating a flavor's name."""
        flavor_id = self._ensure_flavor_exists()

        status_code, reason, text, result = self.admin_client.update_flavor(
            flavor_id=flavor_id,
            name=self.update_flavor_name,
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to update flavor name: {err_msg}"
        resp = json.loads(text)
        flavor = resp["result"]
        assert flavor["name"] == self.update_flavor_name

        # revert name back
        self.admin_client.update_flavor(
            flavor_id=flavor_id,
            name=self.test_flavor_name,
        )

    def test_update_flavor_extra_properties_merge(self):
        """Test that updating extra_properties merges with existing."""
        flavor_id = self._ensure_flavor_exists()

        status_code, reason, text, result = self.admin_client.update_flavor(
            flavor_id=flavor_id,
            extra_properties={"qc:devices": "qutip_sim"},
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to merge extra_properties: {err_msg}"
        resp = json.loads(text)
        flavor = resp["result"]
        # extra_properties should contain merged value
        assert flavor["extra_properties"] == {"qc:devices": "qutip_sim"}

    def test_update_flavor_clear_fields(self):
        """Test that passing None clears nullable fields."""
        flavor_id = self._ensure_flavor_exists()

        # first set a description and max_qubits
        self.admin_client.update_flavor(
            flavor_id=flavor_id,
            description="to be cleared",
            max_qubits=64,
        )

        # clear description and max_qubits by passing None
        status_code, reason, text, result = self.admin_client.update_flavor(
            flavor_id=flavor_id,
            description=None,
            max_qubits=None,
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to clear fields: {err_msg}"
        resp = json.loads(text)
        flavor = resp["result"]
        assert flavor["description"] is None
        assert flavor["max_qubits"] is None

    def test_delete_flavors(self):
        """Test deleting a flavor (batch)."""
        flavor_id = self._ensure_flavor_exists()

        status_code, reason, text, result = self.admin_client.delete_flavors([
            flavor_id
        ])
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to delete flavor: {err_msg}"

        # Verify deletion
        status_code, reason, text, result = self.admin_client.get_flavor(
            flavor_id
        )
        resp = json.loads(text)
        assert "error" in resp

    def test_delete_flavors_not_found(self):
        """Test deleting a non-existent flavor returns error result."""
        nonexistent_id = str(uuid.uuid4())
        status_code, reason, text, result = self.admin_client.delete_flavors([
            nonexistent_id
        ])
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to delete flavors: {err_msg}"
        resp = json.loads(text)
        results = resp.get("result", {}).get("results", [])
        assert len(results) == 1
        assert results[0]["success"] is False

    def test_delete_flavors_batch(self):
        """Test batch deleting multiple flavors."""
        flavor_id_1 = self._ensure_flavor_exists()
        flavor_id_2 = self._ensure_flavor_exists(
            name=f"{self.test_flavor_name}-2"
        )

        status_code, reason, text, result = self.admin_client.delete_flavors([
            flavor_id_1,
            flavor_id_2,
        ])
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to batch delete flavors: {err_msg}"
        resp = json.loads(text)
        results = resp.get("result", {}).get("results", [])
        assert len(results) == 2
        for r in results:
            assert r["success"] is True

        for fid in [flavor_id_1, flavor_id_2]:
            status_code, reason, text, result = self.admin_client.get_flavor(
                fid
            )
            resp = json.loads(text)
            assert "error" in resp

    def test_get_flavors_with_ids_filter(self):
        """Test get_flavors with flavor_ids filter."""
        flavor_id = self._ensure_flavor_exists()

        status_code, reason, text, result = self.admin_client.get_flavors(
            filters={"flavor_ids": [flavor_id]}
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert success, f"Failed to get flavors with ids filter: {err_msg}"
        resp = json.loads(text)
        flavors = resp["result"]
        assert isinstance(flavors, list)
        assert len(flavors) >= 1
        assert any(f["id"] == flavor_id for f in flavors)

        self.admin_client.delete_flavors([flavor_id])

    def test_create_flavor_invalid_qubits(self):
        """Test creating a flavor with min_qubits > max_qubits fails."""
        status_code, reason, text, result = self.admin_client.create_flavor(
            name="st-test-flavor-invalid-qubits",
            description="invalid qubits range",
            is_public=True,
            min_qubits=32,
            max_qubits=1,
            gate_fidelity_1q_min=0.99,
            gate_fidelity_2q_min=0.99,
            extra_properties={"qc:devices": "dummy"},
            device_groups=[DEFAULT_DEVICE_GROUP_QC_ALL_ID],
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert not success, (
            f"Expected failure for invalid qubits range, "
            f"but got success: {err_msg}"
        )

    def test_create_flavor_invalid_fidelity(self):
        """Test creating a flavor with gate_fidelity > 1 fails."""
        status_code, reason, text, result = self.admin_client.create_flavor(
            name="st-test-flavor-invalid-fidelity",
            description="invalid fidelity",
            is_public=True,
            min_qubits=1,
            max_qubits=32,
            gate_fidelity_1q_min=1.5,
            gate_fidelity_2q_min=0.99,
            extra_properties={"qc:devices": "dummy"},
            device_groups=[DEFAULT_DEVICE_GROUP_QC_ALL_ID],
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert not success, (
            f"Expected failure for invalid fidelity, "
            f"but got success: {err_msg}"
        )

    def test_update_flavor_invalid_qubits(self):
        """Test updating a flavor with min_qubits > max_qubits fails."""
        flavor_id = self._ensure_flavor_exists()

        status_code, reason, text, result = self.admin_client.update_flavor(
            flavor_id=flavor_id,
            min_qubits=32,
            max_qubits=1,
        )
        success, err_msg = StLibrary.is_response_success(status_code, text)
        assert not success, (
            f"Expected failure for invalid qubits range, "
            f"but got success: {err_msg}"
        )
