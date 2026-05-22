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
import pytest

from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES
from wy_qcos_client.client import Client

logger = logging.getLogger(__name__)


@pytest.mark.usefixtures("global_configs")
class TestVirtualInstanceAuth:
    """Virtual instance authentication system tests."""

    @classmethod
    def setup_class(cls):
        """Initialize test environment."""
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.virtual_instance_client = GLOBAL_CONFIGS["virtual_instance_client"]
        cls.client = GLOBAL_CONFIGS["client"]
        cls.api_host = GLOBAL_CONFIGS.get("api_host", "127.0.0.1")
        cls.api_port = GLOBAL_CONFIGS.get(
            "api_port", Config.API_SERVER.API_SERVER_LISTEN_PORT
        )
        cls.password_salt = GLOBAL_CONFIGS.get("password_salt", "")
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]

        # Store original auth mode for restoration
        cls.original_auth_mode = StLibrary.get_auth_mode(cls.admin_client)
        StLibrary.set_auth_mode(
            cls.admin_client,
            cls.virtual_instance_client,
            cls.original_auth_mode,
            Constant.AUTH_MODE_VIRTUAL_INSTANCE,
        )

    @classmethod
    def teardown_class(cls):
        """Cleanup after all tests."""
        current_auth_mode = StLibrary.get_auth_mode(cls.admin_client)
        StLibrary.set_auth_mode(
            cls.admin_client,
            cls.virtual_instance_client,
            current_auth_mode,
            cls.original_auth_mode,
        )

    def _create_job_info(self, job_id, job_name, backend, description):
        """Create job info dictionary for testing.

        Args:
            job_id: Unique job identifier
            job_name: Human readable job name
            backend: Backend device name
            description: Job description

        Returns:
            Dictionary with job configuration
        """
        return {
            "job_id": job_id,
            "job_name": job_name,
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": description,
            "shots": Constant.DEFAULT_SHOTS,
            "backend": backend,
            "circuit_aggregation": None,
            "driver_options": {},
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": {},
            "profiling": [],
            "callbacks": [],
            "dry_run": False,
        }

    @pytest.mark.smoke
    def test_virtual_instance_auth_mode_switch_and_operations(self):
        """Test switching to virtual_instance auth mode."""
        # Assumes auth_mode is already virtual_instance
        virtual_auth_client = self.virtual_instance_client
        try:
            device_names = ["dummy"]
            instance_id = "test_instance_001"

            success, err_msg, encrypted_instance_id = (
                Library.encrypt_virtual_instance_id(
                    device_names,
                    instance_id,
                    salt=self.password_salt,
                    encode=True,
                )
            )
            assert success is True
            assert encrypted_instance_id is not None

            virtual_auth_client.request_headers = {
                "x-qcos-virtual-instance-id": encrypted_instance_id,
            }

            # user can access to dummy device
            device = StLibrary.get_device(virtual_auth_client, "dummy")
            assert device is not None
            assert device["name"] == "dummy"

            # Test submit-job operation
            job_info = {
                "job_id": str(Library.create_uuid(prefix=[0xF0])),
                "job_name": "test_vi_job",
                "source_code_list": [SAMPLES["simple-qasm.qasm"]],
                "code_type": Constant.CODE_TYPE_QASM,
                "job_type": Constant.JOB_TYPE_SAMPLING,
                "job_priority": Constant.DEFAULT_JOB_PRIORITY,
                "circuit_aggregation": None,
                "description": "Test job with virtual instance auth",
                "shots": 1000,
                "backend": "dummy",
                "driver_options": {},
                "transpiler": Constant.TRANSPILER_CMSS,
                "transpiler_options": {},
                "profiling": [],
                "callbacks": [],
                "dry_run": False,
            }

            result_dict = StLibrary.submit_job(virtual_auth_client, job_info)
            assert result_dict["job_id"] == job_info["job_id"]

            # Wait for job to complete and check result
            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                virtual_auth_client, job_info, self.timeout, self.interval
            )
            if success:
                StLibrary.delete_job(virtual_auth_client, job_info["job_id"])
                assert (
                    job_results["result"]["job_status"]
                    == Constant.JOB_STATUS_COMPLETED
                )
            else:
                logger.warning(
                    "Job failed. err_msg: {}, job_results: {}".format(
                        err_msg, job_results
                    )
                )
            assert success is True

        finally:
            # Cleanup
            virtual_auth_client.request_headers = None

    @pytest.mark.smoke
    def test_virtual_instance_admin_access(self):
        """Test virtual instance admin access (all/all).

        Admin access in virtual instance mode is indicated by:
        - device_names = ["all"]
        - instance_id = "all"
        """
        # Assumes auth_mode is already virtual_instance
        admin_vi_client = self.virtual_instance_client
        try:
            admin_device_names = ["all"]
            admin_instance_id = "all"

            success, err_msg, encrypted_instance_id = (
                Library.encrypt_virtual_instance_id(
                    admin_device_names,
                    admin_instance_id,
                    salt=self.password_salt,
                    encode=True,
                )
            )
            assert success is True

            admin_vi_client.request_headers = {
                "x-qcos-virtual-instance-id": encrypted_instance_id,
            }

            # Admin (all/all) should have full access to devices
            devices = StLibrary.get_devices(admin_vi_client)
            assert len(devices) > 0
            # Extract device names from result
            if isinstance(devices, dict):
                device_names = list(devices.keys())
            else:
                device_names = [d["name"] for d in devices]
            assert "dummy" in device_names
        finally:
            # Cleanup
            admin_vi_client.request_headers = None

    @pytest.mark.smoke
    def test_auth_mode_get_and_restore(self):
        """Test getting auth mode and restoring it.

        System operates in virtual_instance mode by default.
        """
        # Verify consistent responses from get_user_mgmt
        status_code_1, _, text_1, _ = (
            self.virtual_instance_client.get_user_mgmt()
        )
        status_code_2, _, text_2, _ = (
            self.virtual_instance_client.get_user_mgmt()
        )

        success_1, error_msg_1 = StLibrary.is_response_success(
            status_code_1, text_1
        )
        success_2, error_msg_2 = StLibrary.is_response_success(
            status_code_2, text_2
        )
        assert success_1, f"First call failed: {error_msg_1}"
        assert success_2, f"Second call failed: {error_msg_2}"

        result_1 = json.loads(text_1).get("result", {})
        result_2 = json.loads(text_2).get("result", {})

        if "auth_mode" in result_1 and "auth_mode" in result_2:
            assert result_1["auth_mode"] == result_2["auth_mode"]
            assert result_1["auth_mode"] == Constant.AUTH_MODE_VIRTUAL_INSTANCE

        # Verify other fields are present if result is not empty
        if result_1:
            assert "password_expiry_days" in result_1
            assert "max_login_attempts" in result_1
            assert "lockout_duration_minutes" in result_1

    @pytest.mark.smoke
    def test_virtual_instance_single_device_isolation(self):
        """Test virtual instance with single device isolation.

        1. Create client with device_names=["dummy"] and instance_id="1"
        2. Verify can only list dummy device
        3. Verify can submit and list jobs for dummy backend
        """
        vi_client = None
        try:
            # Assumes auth_mode is already virtual_instance
            dummy_device_names = ["dummy"]
            dummy_instance_id = "test_instance_1"

            success, err_msg, encrypted_instance_id = (
                Library.encrypt_virtual_instance_id(
                    dummy_device_names,
                    dummy_instance_id,
                    salt=self.password_salt,
                    encode=True,
                )
            )
            assert success is True

            vi_client = Client(
                api_server_ip=self.api_host,
                api_server_port=self.api_port,
            )
            vi_client.request_headers = {
                "x-qcos-virtual-instance-id": encrypted_instance_id,
            }

            # Test list devices - should only show dummy
            devices = StLibrary.get_devices(vi_client)
            if isinstance(devices, dict):
                device_names = list(devices.keys())
            else:
                device_names = [d["name"] for d in devices]
            assert "dummy" in device_names
            # Should only have dummy device accessible
            assert len(device_names) == 1
            # Test get device - should work for dummy
            device = StLibrary.get_device(vi_client, "dummy")
            assert device["name"] == "dummy"

            # Test submit job with dummy backend
            job_info = self._create_job_info(
                str(Library.create_uuid(prefix=[0xF0])),
                "test_vi_single_device_job",
                Constant.DEVICE_DUMMY,
                "Test job with single device VI",
            )

            result_dict = StLibrary.submit_job(vi_client, job_info)
            assert result_dict["job_id"] == job_info["job_id"]
            assert result_dict["backend"] == Constant.DEVICE_DUMMY
            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                vi_client, job_info, self.timeout, self.interval
            )
            if success:
                StLibrary.delete_job(vi_client, job_info["job_id"])
                assert (
                    job_results["result"]["job_status"]
                    == Constant.JOB_STATUS_COMPLETED
                )
            assert success is True
        finally:
            # Cleanup
            if vi_client:
                vi_client.request_headers = None

    @pytest.mark.smoke
    def test_virtual_instance_two_clients_different_devices(self):
        """Test 2 virtual instance clients with different device isolation.

        1. Create 2 clients: one for dummy, one for qutip_sim
        2. Verify each client only sees its assigned device
        3. Verify job isolation
        """
        dummy_vi_client = None
        qutip_vi_client = None
        try:
            # Assumes auth_mode is already virtual_instance

            # Create dummy device client
            dummy_device_names = ["dummy"]
            dummy_instance_id = "test_instance_2a"
            success, err_msg, dummy_vi_id = (
                Library.encrypt_virtual_instance_id(
                    dummy_device_names,
                    dummy_instance_id,
                    salt=self.password_salt,
                    encode=True,
                )
            )
            assert success is True

            dummy_vi_client = Client(
                api_server_ip=self.api_host,
                api_server_port=self.api_port,
            )
            dummy_vi_client.request_headers = {
                "x-qcos-virtual-instance-id": dummy_vi_id,
            }

            # Create qutip_sim device client
            qutip_device_names = ["qutip_sim"]
            qutip_instance_id = "test_instance_2b"  # Different from dummy
            success, err_msg, qutip_vi_id = (
                Library.encrypt_virtual_instance_id(
                    qutip_device_names,
                    qutip_instance_id,
                    salt=self.password_salt,
                    encode=True,
                )
            )
            assert success is True

            qutip_vi_client = Client(
                api_server_ip=self.api_host,
                api_server_port=self.api_port,
            )
            qutip_vi_client.request_headers = {
                "x-qcos-virtual-instance-id": qutip_vi_id,
            }

            # Verify device isolation - dummy client
            dummy_devices = StLibrary.get_devices(dummy_vi_client)
            if isinstance(dummy_devices, dict):
                dummy_device_names_list = list(dummy_devices.keys())
            else:
                dummy_device_names_list = [d["name"] for d in dummy_devices]
            assert dummy_device_names_list == ["dummy"]
            # Verify device isolation - qutip client
            qutip_devices = StLibrary.get_devices(qutip_vi_client)
            if isinstance(qutip_devices, dict):
                qutip_device_names_list = list(qutip_devices.keys())
            else:
                qutip_device_names_list = [d["name"] for d in qutip_devices]
            assert qutip_device_names_list == ["qutip_sim"]

            # Submit job from dummy client
            dummy_job_info = self._create_job_info(
                str(Library.create_uuid(prefix=[0xF0])),
                "test_vi_dummy_device_job",
                Constant.DEVICE_DUMMY,
                "Test job with dummy device VI",
            )

            result_dict = StLibrary.submit_job(dummy_vi_client, dummy_job_info)
            assert result_dict["backend"] == Constant.DEVICE_DUMMY

            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                dummy_vi_client, dummy_job_info, self.timeout, self.interval
            )
            if success:
                StLibrary.delete_job(dummy_vi_client, dummy_job_info["job_id"])
                assert (
                    job_results["result"]["job_status"]
                    == Constant.JOB_STATUS_COMPLETED
                )
            else:
                logger.warning(
                    "Dummy job failed. err_msg: {}, job_results: {}".format(
                        err_msg, job_results
                    )
                )
            assert success is True

            # Submit job from qutip client
            qutip_job_info = self._create_job_info(
                str(Library.create_uuid(prefix=[0xF0])),
                "test_vi_qutip_device_job",
                "qutip_sim",
                "Test job with qutip device VI",
            )
            result_dict = StLibrary.submit_job(qutip_vi_client, qutip_job_info)
            assert result_dict["backend"] == "qutip_sim"

            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                qutip_vi_client, qutip_job_info, self.timeout, self.interval
            )
            if success:
                StLibrary.delete_job(qutip_vi_client, qutip_job_info["job_id"])
                assert (
                    job_results["result"]["job_status"]
                    == Constant.JOB_STATUS_COMPLETED
                )
            else:
                logger.warning(
                    "Qutip job failed. err_msg: {}, job_results: {}".format(
                        err_msg, job_results
                    )
                )
            assert success is True

        finally:
            # Cleanup
            if dummy_vi_client:
                dummy_vi_client.request_headers = None
            if qutip_vi_client:
                qutip_vi_client.request_headers = None

    @pytest.mark.smoke
    def test_virtual_instance_two_clients_multiple_devices(self):
        """Test 2 virtual instance clients with multiple devices each.

        1. Create 2 clients with multi-device access
        2. Verify each client sees all assigned devices
        3. Verify job isolation with different instance IDs
        """
        vi_client_1 = None
        vi_client_2 = None
        try:
            # Assumes auth_mode is already virtual_instance

            # Create client 1 with both devices
            device_names_1 = ["dummy", "qutip_sim"]
            instance_id_1 = "test_instance_3"
            success, err_msg, vi_id_1 = Library.encrypt_virtual_instance_id(
                device_names_1,
                instance_id_1,
                salt=self.password_salt,
                encode=True,
            )
            assert success is True

            vi_client_1 = Client(
                api_server_ip=self.api_host,
                api_server_port=self.api_port,
            )
            vi_client_1.request_headers = {
                "x-qcos-virtual-instance-id": vi_id_1,
            }

            # Create client 2 with both devices
            device_names_2 = ["dummy", "qutip_sim"]
            instance_id_2 = "test_instance_4"
            success, err_msg, vi_id_2 = Library.encrypt_virtual_instance_id(
                device_names_2,
                instance_id_2,
                salt=self.password_salt,
                encode=True,
            )
            assert success is True

            vi_client_2 = Client(
                api_server_ip=self.api_host,
                api_server_port=self.api_port,
            )
            vi_client_2.request_headers = {
                "x-qcos-virtual-instance-id": vi_id_2,
            }

            # Verify both clients see both devices if device is available
            devices_1 = StLibrary.get_devices(vi_client_1)
            if isinstance(devices_1, dict):
                device_names_list_1 = sorted(devices_1.keys())
            else:
                device_names_list_1 = sorted([d["name"] for d in devices_1])
            assert device_names_list_1 == ["dummy", "qutip_sim"]
            devices_2 = StLibrary.get_devices(vi_client_2)
            if isinstance(devices_2, dict):
                device_names_list_2 = sorted(devices_2.keys())
            else:
                device_names_list_2 = sorted([d["name"] for d in devices_2])
            assert device_names_list_2 == ["dummy", "qutip_sim"]

            # Submit jobs from both clients with different devices
            job_info_1 = self._create_job_info(
                str(Library.create_uuid(prefix=[0xF0])),
                "test_vi_multi_device_job_1",
                Constant.DEVICE_DUMMY,
                "Test job client 1 with dummy device",
            )

            result_dict = StLibrary.submit_job(vi_client_1, job_info_1)
            assert result_dict["backend"] == Constant.DEVICE_DUMMY

            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                vi_client_1, job_info_1, self.timeout, self.interval
            )
            if success:
                StLibrary.delete_job(vi_client_1, job_info_1["job_id"])
                assert (
                    job_results["result"]["job_status"]
                    == Constant.JOB_STATUS_COMPLETED
                )
            else:
                logger.warning(
                    "Client 1 job failed. err_msg: {}, job_results: {}".format(
                        err_msg, job_results
                    )
                )
            assert success is True

            job_info_2 = self._create_job_info(
                str(Library.create_uuid(prefix=[0xF0])),
                "test_vi_multi_device_job_2",
                "qutip_sim",
                "Test job client 2 with qutip device",
            )
            result_dict = StLibrary.submit_job(vi_client_2, job_info_2)
            assert result_dict["backend"] == "qutip_sim"

            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                vi_client_2, job_info_2, self.timeout, self.interval
            )
            if success:
                StLibrary.delete_job(vi_client_2, job_info_2["job_id"])
                assert (
                    job_results["result"]["job_status"]
                    == Constant.JOB_STATUS_COMPLETED
                )
            else:
                logger.warning(
                    "Client 2 job failed. err_msg: {}, job_results: {}".format(
                        err_msg, job_results
                    )
                )
            assert success is True
        finally:
            # Cleanup
            if vi_client_1:
                vi_client_1.request_headers = None
            if vi_client_2:
                vi_client_2.request_headers = None

    @pytest.mark.smoke
    def test_virtual_instance_admin_list_all_devices(self):
        """Test virtual_instance admin (all/all) lists all devices.

        Assumes auth_mode is already virtual_instance.
        """
        # Use the admin virtual_instance_client (all/all)
        devices = StLibrary.get_devices(self.virtual_instance_client)

        # Verify devices list is not empty
        assert len(devices) > 0

        # Should have access to multiple devices
        if isinstance(devices, dict):
            device_names = list(devices.keys())
        else:
            device_names = [d["name"] for d in devices]
        # At minimum should include dummy
        assert "dummy" in device_names

    @pytest.mark.smoke
    def test_virtual_instance_device_access_control(self):
        """Test that vi client cannot submit job to unauthorized device.

        1. Create client with device_names=["dummy"] (only dummy device)
        2. Attempt to submit job to qutip_sim (unauthorized device)
        3. Verify the submission fails with access denied error
        """
        vi_client = None
        try:
            # Assumes auth_mode is already virtual_instance
            dummy_device_names = ["dummy"]
            instance_id = "test_instance_access_control"

            success, err_msg, encrypted_instance_id = (
                Library.encrypt_virtual_instance_id(
                    dummy_device_names,
                    instance_id,
                    salt=self.password_salt,
                    encode=True,
                )
            )
            assert success is True

            vi_client = Client(
                api_server_ip=self.api_host,
                api_server_port=self.api_port,
            )
            vi_client.request_headers = {
                "x-qcos-virtual-instance-id": encrypted_instance_id,
            }

            # Verify client only has access to dummy device
            devices = StLibrary.get_devices(vi_client)
            if isinstance(devices, dict):
                device_names = list(devices.keys())
            else:
                device_names = [d["name"] for d in devices]
            assert device_names == ["dummy"]

            # Try to submit job to unauthorized device (qutip_sim)
            job_info = self._create_job_info(
                str(Library.create_uuid(prefix=[0xF0])),
                "test_access_control_job",
                "qutip_sim",
                "Attempt to use unauthorized device",
            )

            # This submission should fail with access denied error
            try:
                StLibrary.submit_job(vi_client, job_info)
                # If we reach here, the submission succeeded (unexpected)
                # This would be a security issue
                assert False, (
                    "Job submission should have failed for unauthorized device"
                )
            except AssertionError as e:
                # Expected: job submission fails with error
                error_msg = str(e)
                assert (
                    "Unauthorized" in error_msg
                    or "forbidden" in error_msg
                    or "no such device" in error_msg.lower()
                    or "not" in error_msg.lower()
                    or "access" in error_msg.lower()
                ), "Expected access control error, got: {}".format(error_msg)

        finally:
            # Cleanup
            if vi_client:
                vi_client.request_headers = None
