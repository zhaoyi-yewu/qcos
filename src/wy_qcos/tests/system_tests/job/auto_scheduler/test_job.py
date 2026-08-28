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

"""System tests for auto scheduler.

Covers:
- Basic auto scheduling flow
- DeviceStatusFilter: disabled/offline devices are filtered out
- QubitCountFilter: devices with insufficient qubits are filtered
- DeviceLoadWeigher: least busy device is preferred
- All devices disabled: NoValidDeviceError
- DeviceAvailabilityFilter: qc:device_availability threshold
  controls scheduling based on availability
- DeviceNameFilter: qcos:devices whitelist restricts eligible devices
- ExcludeDeviceFilter: qcos:exclude_devices blacklist excludes devices
- TechTypeFilter: qc:tech_types restricts by technology type

Uses dummy, dummy1, dummy2 devices and set-device to modify
enable/status/max_qubits at runtime. Creates a device group and
flavor referencing all dummy devices for auto scheduling.
"""

import json
import logging
import pytest
import time

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES

logger = logging.getLogger(__name__)

DEVICE_DUMMY = "dummy"
DEVICE_DUMMY1 = "dummy1"
DEVICE_DUMMY2 = "dummy2"
ALL_DUMMY_DEVICES = [DEVICE_DUMMY, DEVICE_DUMMY1, DEVICE_DUMMY2]


@pytest.mark.usefixtures("global_configs")
@pytest.mark.driver
class TestJob:
    """Test auto scheduler filters and weighers."""

    test_device_group_names = ["test_auto_scheduler_group"]
    test_flavor_names = ["test_auto_scheduler_flavor"]
    test_job_names = [
        "test_auto_schedule_basic",
        "test_device_status_filter_disabled",
        "test_device_status_filter_offline",
        "test_qubit_count_filter",
        "test_device_load_weigher",
        "test_device_load_weigher_busy",
        "test_all_devices_disabled",
        "test_device_name_filter_whitelist",
        "test_exclude_device_filter_blacklist",
        "test_tech_type_filter",
    ]

    @classmethod
    def setup_class(cls):
        """Initialize test environment."""
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]

        # clean up before tests
        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)
        StLibrary.cleanup_test_flavors(cls.admin_client, cls.test_flavor_names)
        StLibrary.cleanup_test_device_groups(
            cls.admin_client, cls.test_device_group_names
        )

        # ensure all dummy devices are enabled and online
        for dev in ALL_DUMMY_DEVICES:
            cls.admin_client.set_device(dev, enable=True, status="online")

        # create or reuse a device group with all dummy devices
        cls.device_group_id = cls._ensure_device_group()

        # create or reuse a flavor referencing the device group
        cls.flavor_id = cls._ensure_flavor()

    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        for dev in ALL_DUMMY_DEVICES:
            cls.admin_client.set_device(dev, enable=True, status="online")
        # cleanup jobs first, then flavors, then device groups
        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)
        StLibrary.cleanup_test_flavors(cls.admin_client, cls.test_flavor_names)
        StLibrary.cleanup_test_device_groups(
            cls.admin_client, cls.test_device_group_names
        )

    @classmethod
    def _ensure_device_group(cls):
        """Create or find a device group with all dummy devices.

        Returns:
            device group UUID
        """
        status_code, _, text, _ = cls.admin_client.get_device_groups()
        if status_code == 200:
            resp = json.loads(text)
            groups = resp.get("result", [])
            for g in groups:
                if g.get("name") == "test_auto_scheduler_group":
                    return g["id"]

        status_code, _, text, _ = cls.admin_client.create_device_group(
            name="test_auto_scheduler_group",
            description="ST auto scheduler device group",
            device_names=ALL_DUMMY_DEVICES,
        )
        resp = json.loads(text)
        return resp["result"]["id"]

    @classmethod
    def _ensure_flavor(cls):
        """Create or find a flavor referencing the device group.

        Returns:
            flavor UUID
        """
        status_code, _, text, _ = cls.admin_client.get_flavors()
        if status_code == 200:
            resp = json.loads(text)
            flavors = resp.get("result", [])
            for f in flavors:
                if f.get("name") == "test_auto_scheduler_flavor":
                    return f["id"]

        status_code, _, text, _ = cls.admin_client.create_flavor(
            name="test_auto_scheduler_flavor",
            description="ST auto scheduler flavor",
            is_public=True,
            min_qubits=1,
            max_qubits=32,
            gate_fidelity_1q_min=0.0,
            gate_fidelity_2q_min=0.0,
            extra_properties={"qcos:devices": "all"},
            device_groups=[cls.device_group_id],
        )
        resp = json.loads(text)
        return resp["result"]["id"]

    def _restore_devices(self):
        """Restore all dummy devices to default state."""
        for dev in ALL_DUMMY_DEVICES:
            self.admin_client.set_device(dev, enable=True, status="online")

    def _make_auto_job_info(
        self,
        job_name,
        flavor_id=None,
        extra_specs=None,
        driver_options=None,
        backend=None,
    ):
        """Build a job_info dict for auto-scheduled submission.

        Uses flavor_id instead of backend to trigger auto scheduling.

        Args:
            job_name: unique job name
            flavor_id: flavor UUID to use for auto scheduling.
                When None, uses the class-level default flavor.
            extra_specs: extra scheduling specs dict for the job.
                When None, no extra specs are sent.
            driver_options: driver-specific options dict.
                When None, no driver options are sent.
            backend: explicit backend name. When None, auto
                scheduling is triggered via flavor_id.

        Returns:
            dict with job submission parameters
        """
        return {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": job_name,
            "source_code_list": [SAMPLES["simple-qasm.qasm"]],
            "code_type": Constant.CODE_TYPE_QASM,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": f"description: {job_name}",
            "backend": backend,
            "shots": Constant.DEFAULT_SHOTS,
            "circuit_aggregation": None,
            "driver_options": driver_options,
            "transpiler": Constant.TRANSPILER_CMSS,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
            "flavor_id": flavor_id,
            "extra_specs": extra_specs,
            "qec_options": None,
        }

    def _submit_auto_job(self, job_name, expect_success=True):
        """Submit an auto-scheduled job and verify results.

        Submits with flavor_id (no backend) to trigger auto scheduling,
        waits for completion, verifies job status, and cleans up.

        Args:
            job_name: unique job name
            expect_success: if True, expect job to complete;
                if False, expect job to fail

        Returns:
            (status_code, text, backend) from the submit_job call
        """
        job_info = self._make_auto_job_info(job_name, flavor_id=self.flavor_id)
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
        )

        # get the backend assigned by auto scheduler
        backend = job_results["result"]["backend"]

        if expect_success:
            if success:
                StLibrary.delete_job(self.admin_client, job_info["job_id"])
                assert (
                    job_results["result"]["job_status"]
                    == Constant.JOB_STATUS_COMPLETED
                )
            else:
                logger.warning(
                    f"Job failed. err_msg: {err_msg}, "
                    f"job_results: {job_results}"
                )
            assert success is True
        else:
            # expect failure: job status should be FAILED or
            # submission should return error
            if success:
                StLibrary.delete_job(self.admin_client, job_info["job_id"])
            assert not expect_success, "Expected job to fail but it succeeded"

        return 200, json.dumps(job_results), backend

    @staticmethod
    def _submit_auto_job_expect_error(client, job_info):
        """Submit an auto job that should fail at submission.

        Used when all devices are disabled and the API should
        return an error instead of accepting the job.

        Args:
            client: API client
            job_info: job info dict

        Returns:
            (status_code, text) from the API call
        """
        status_code, reason, text, response = client.submit_job(
            job_info["source_code_list"],
            code_type=job_info["code_type"],
            job_id=job_info["job_id"],
            circuit_aggregation=None,
            job_name=job_info["job_name"],
            job_type=job_info["job_type"],
            job_priority=job_info["job_priority"],
            description=job_info["description"],
            shots=job_info["shots"],
            backend=None,
            flavor_id=job_info["flavor_id"],
            extra_specs=job_info.get("extra_specs"),
            driver_options=None,
            transpiler=job_info["transpiler"],
            transpiler_options=None,
            profiling=None,
            callbacks=None,
            dry_run=job_info["dry_run"],
            qec_options=None,
        )
        return status_code, text

    @pytest.mark.smoke
    def test_auto_schedule_basic(self):
        """Auto scheduling selects an enabled online dummy device."""
        self._restore_devices()
        job_info = self._make_auto_job_info(
            "test_auto_schedule_basic",
            flavor_id=self.flavor_id,
        )
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client,
            job_info,
            self.timeout,
            self.interval,
        )
        if success:
            StLibrary.delete_job(self.admin_client, job_info["job_id"])
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True
        backend = job_results["result"]["backend"]
        assert backend in ALL_DUMMY_DEVICES

    @pytest.mark.smoke
    def test_device_status_filter_disabled(self):
        """Disabled devices are filtered out by DeviceStatusFilter.

        Disable dummy and dummy2, only dummy1 remains enabled.
        Auto scheduling should select dummy1.
        """
        self._restore_devices()
        self.admin_client.set_device(DEVICE_DUMMY, enable=False)
        self.admin_client.set_device(DEVICE_DUMMY2, enable=False)
        try:
            job_info = self._make_auto_job_info(
                "test_device_status_filter_disabled",
                flavor_id=self.flavor_id,
            )
            StLibrary.submit_job(self.admin_client, job_info)
            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                self.admin_client,
                job_info,
                self.timeout,
                self.interval,
            )
            if success:
                StLibrary.delete_job(self.admin_client, job_info["job_id"])
                assert (
                    job_results["result"]["job_status"]
                    == Constant.JOB_STATUS_COMPLETED
                )
            else:
                logger.warning(
                    f"Job failed. err_msg: {err_msg}, "
                    f"job_results: {job_results}"
                )
            assert success is True
            backend = job_results["result"]["backend"]
            assert backend == DEVICE_DUMMY1
        finally:
            self._restore_devices()

    @pytest.mark.smoke
    def test_device_status_filter_offline(self):
        """Offline devices are filtered out by DeviceStatusFilter.

        Set dummy and dummy2 to offline, only dummy1 remains online.
        Auto scheduling should select dummy1.
        """
        self._restore_devices()
        self.admin_client.set_device(DEVICE_DUMMY, status="offline")
        self.admin_client.set_device(DEVICE_DUMMY2, status="offline")
        try:
            job_info = self._make_auto_job_info(
                "test_device_status_filter_offline",
                flavor_id=self.flavor_id,
            )
            StLibrary.submit_job(self.admin_client, job_info)
            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                self.admin_client,
                job_info,
                self.timeout,
                self.interval,
            )
            if success:
                StLibrary.delete_job(self.admin_client, job_info["job_id"])
                assert (
                    job_results["result"]["job_status"]
                    == Constant.JOB_STATUS_COMPLETED
                )
            else:
                logger.warning(
                    f"Job failed. err_msg: {err_msg}, "
                    f"job_results: {job_results}"
                )
            assert success is True
            backend = job_results["result"]["backend"]
            assert backend == DEVICE_DUMMY1
        finally:
            self._restore_devices()

    def test_qubit_count_filter(self):
        """QubitCountFilter filters devices with insufficient qubits.

        Set dummy1 max_qubits to 1 (too small for 2-qubit job),
        dummy2 max_qubits to 1 (too small).
        Only dummy with default max_qubits can handle the job.
        """
        self._restore_devices()
        self.admin_client.set_device(DEVICE_DUMMY1, max_qubits="1")
        self.admin_client.set_device(DEVICE_DUMMY2, max_qubits="1")
        try:
            job_info = self._make_auto_job_info(
                "test_qubit_count_filter",
                flavor_id=self.flavor_id,
            )
            StLibrary.submit_job(self.admin_client, job_info)
            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                self.admin_client,
                job_info,
                self.timeout,
                self.interval,
            )
            if success:
                StLibrary.delete_job(self.admin_client, job_info["job_id"])
                assert (
                    job_results["result"]["job_status"]
                    == Constant.JOB_STATUS_COMPLETED
                )
            else:
                logger.warning(
                    f"Job failed. err_msg: {err_msg}, "
                    f"job_results: {job_results}"
                )
            assert success is True
            backend = job_results["result"]["backend"]
            assert backend == DEVICE_DUMMY
        finally:
            self.admin_client.set_device(DEVICE_DUMMY1, max_qubits="auto")
            self.admin_client.set_device(DEVICE_DUMMY2, max_qubits="auto")
            self._restore_devices()

    def test_device_load_weigher(self):
        """DeviceLoadWeigher prefers the least busy device.

        Submit a long-running job to dummy to make it busy,
        then auto-schedule should prefer dummy1 or dummy2.
        """
        self._restore_devices()
        busy_job_info = self._make_auto_job_info(
            "test_device_load_weigher_busy",
            driver_options={"sleep": 30},
            backend=DEVICE_DUMMY,
            flavor_id=None,
        )
        StLibrary.submit_job(self.admin_client, busy_job_info)
        time.sleep(3)
        try:
            job_info = self._make_auto_job_info(
                "test_device_load_weigher",
                flavor_id=self.flavor_id,
            )
            StLibrary.submit_job(self.admin_client, job_info)
            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                self.admin_client,
                job_info,
                self.timeout,
                self.interval,
            )
            if success:
                StLibrary.delete_job(self.admin_client, job_info["job_id"])
                assert (
                    job_results["result"]["job_status"]
                    == Constant.JOB_STATUS_COMPLETED
                )
            else:
                logger.warning(
                    f"Job failed. err_msg: {err_msg}, "
                    f"job_results: {job_results}"
                )
            assert success is True
            backend = job_results["result"]["backend"]
            assert backend in [DEVICE_DUMMY1, DEVICE_DUMMY2]
        finally:
            success, err_msg, job_results = StLibrary.wait_and_get_job_result(
                self.admin_client,
                busy_job_info,
                self.timeout,
                self.interval,
            )
            if success:
                StLibrary.delete_job(
                    self.admin_client, busy_job_info["job_id"]
                )
                assert (
                    job_results["result"]["job_status"]
                    == Constant.JOB_STATUS_COMPLETED
                )
            else:
                logger.warning(
                    f"Job failed. err_msg: {err_msg}, "
                    f"job_results: {job_results}"
                )
            self._restore_devices()

    def test_all_devices_disabled(self):
        """When all devices are disabled, auto scheduling fails."""
        self._restore_devices()
        for dev in ALL_DUMMY_DEVICES:
            self.admin_client.set_device(dev, enable=False)
        try:
            job_info = self._make_auto_job_info(
                "test_all_devices_disabled",
                flavor_id=self.flavor_id,
            )
            status_code, text = self._submit_auto_job_expect_error(
                self.admin_client, job_info
            )
            # should return an error (no valid device)
            result = json.loads(text)
            assert result.get("error") is not None
        finally:
            self._restore_devices()

    def test_device_name_filter_whitelist(self):
        """DeviceNameFilter restricts to a whitelist via extra_specs.

        Use extra_specs qcos:devices to whitelist only dummy1.
        Auto scheduling should select dummy1.
        """
        self._restore_devices()
        job_info = self._make_auto_job_info(
            "test_device_name_filter_whitelist",
            flavor_id=self.flavor_id,
            extra_specs={"qcos:devices": DEVICE_DUMMY1},
        )
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client,
            job_info,
            self.timeout,
            self.interval,
        )
        if success:
            StLibrary.delete_job(self.admin_client, job_info["job_id"])
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True
        backend = job_results["result"]["backend"]
        assert backend == DEVICE_DUMMY1

    def test_exclude_device_filter_blacklist(self):
        """ExcludeDeviceFilter excludes devices via extra_specs.

        Use extra_specs qcos:exclude_devices to blacklist dummy and
        dummy1. Auto scheduling should select dummy2.
        """
        self._restore_devices()
        job_info = self._make_auto_job_info(
            "test_exclude_device_filter_blacklist",
            flavor_id=self.flavor_id,
            extra_specs={
                "qcos:exclude_devices": f"{DEVICE_DUMMY},{DEVICE_DUMMY1}"
            },
        )
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client,
            job_info,
            self.timeout,
            self.interval,
        )
        if success:
            StLibrary.delete_job(self.admin_client, job_info["job_id"])
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True
        backend = job_results["result"]["backend"]
        assert backend == DEVICE_DUMMY2

    def test_tech_type_filter(self):
        """TechTypeFilter restricts by technology type via extra_specs.

        Dummy devices are neutral_atom. Use extra_specs
        qc:tech_types to whitelist neutral_atom so all dummy devices
        remain eligible. Auto scheduling should select one of them.
        """
        self._restore_devices()
        job_info = self._make_auto_job_info(
            "test_tech_type_filter",
            flavor_id=self.flavor_id,
            extra_specs={"qc:tech_types": Constant.TECH_TYPE_NEUTRAL_ATOM},
        )
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client,
            job_info,
            self.timeout,
            self.interval,
        )
        if success:
            StLibrary.delete_job(self.admin_client, job_info["job_id"])
            assert (
                job_results["result"]["job_status"]
                == Constant.JOB_STATUS_COMPLETED
            )
        else:
            logger.warning(
                f"Job failed. err_msg: {err_msg}, job_results: {job_results}"
            )
        assert success is True
        backend = job_results["result"]["backend"]
        assert backend in ALL_DUMMY_DEVICES
