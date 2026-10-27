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
import multiprocessing

import pytest

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.tests.system_tests.common.library import StLibrary
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS, SAMPLES
from .qboson_api_server import main

logger = logging.getLogger(__name__)

# Test device group and flavor names (cleaned up in teardown)
_TEST_GROUP_NAME = "st_qubo_group"
_TEST_FLAVOR_NAME = "st_qubo_flavor"
# Devices in the group — all qboson tiangong devices
_TEST_DEVICES = [
    "tiangong100",
    "tiangong550_v2",
    "tiangong1000_v2",
]


@pytest.mark.usefixtures("global_configs")
@pytest.mark.driver
class TestJob:
    """Test Job."""

    test_job_names = [
        "test_qboson_submit_job",
        "test_qboson_submit_job_enable_subqubo",
    ]

    @classmethod
    def setup_class(cls):
        """Initialize test environment."""
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]
        cls.timeout = GLOBAL_CONFIGS["timeout"]
        cls.interval = GLOBAL_CONFIGS["interval"]
        cls.samples_dir = GLOBAL_CONFIGS["samples_dir"]
        cls.api_host = "127.0.0.1"
        cls.api_port = 18600
        cls.rpc_process = multiprocessing.Process(
            target=main,
            daemon=True,
            kwargs={"port": cls.api_port},
        )
        cls.rpc_process.start()

        # Wait until the mock API server is ready
        connected = Library.wait_network_connection(
            cls.api_host,
            port=cls.api_port,
        )
        assert connected, (
            f"Failed to connect to qboson mock server at "
            f"{cls.api_host}:{cls.api_port}"
        )

        # Clean up stale test jobs
        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)

        # Clean up stale flavors / device groups from previous runs
        StLibrary.cleanup_test_flavors(cls.admin_client, [_TEST_FLAVOR_NAME])
        StLibrary.cleanup_test_device_groups(
            cls.admin_client, [_TEST_GROUP_NAME]
        )

        # Create a device group with multiple tiangong devices
        # so that flavor-based scheduling can distribute sub-QUBO
        # tasks across them.
        status, reason, text, _ = cls.admin_client.create_device_group(
            name=_TEST_GROUP_NAME,
            device_names=_TEST_DEVICES,
        )
        assert status == 200, f"Failed to create device group: {reason}"
        resp = json.loads(text)
        group_id = resp["result"]["id"]
        cls._group_id = group_id

        # Create a flavor pointing to the device group
        status, reason, text, _ = cls.admin_client.create_flavor(
            name=_TEST_FLAVOR_NAME,
            device_groups=[group_id],
        )
        assert status == 200, f"Failed to create flavor: {reason}"
        resp = json.loads(text)
        cls._flavor_id = resp["result"]["id"]

    @classmethod
    def teardown_class(cls):
        """Clean up test environment."""
        StLibrary.cleanup_test_jobs(cls.admin_client, cls.test_job_names)
        StLibrary.cleanup_test_flavors(cls.admin_client, [_TEST_FLAVOR_NAME])
        StLibrary.cleanup_test_device_groups(
            cls.admin_client, [_TEST_GROUP_NAME]
        )

        print("Stop tiangong server")
        cls.rpc_process.terminate()

    @pytest.mark.smoke
    def test_submit_job(self):
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_qboson_submit_job",
            "source_code_list": [SAMPLES["simple-qubo.json"]],
            "code_type": Constant.CODE_TYPE_QUBO,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "description: test_qboson_submit_job",
            "backend": "tiangong550_v2",
            "shots": 100,
            "circuit_aggregation": None,
            "driver_options": None,
            "transpiler": Constant.TRANSPILER_DUMMY,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client, job_info, self.timeout, self.interval
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

    @pytest.mark.slow
    def test_qboson_submit_job_enable_subqubo(self):
        """Test QUBO decomposition with enable_subqubo via flavor.

        Submits a large QUBO matrix (102x102) with
        enable_subqubo=True and a flavor that maps to multiple
        tiangong devices (tiangong100, tiangong550_v2,
        tiangong1000_v2). This triggers:
        - flavor-based auto scheduling across the device group
        - enable_subqubo routing to wirecut_flow
        - subqubo_schedule multi-device parallel decomposition
        - sub-QUBO tasks dispatched to multiple devices
        """
        job_info = {
            "job_id": str(Library.create_uuid(prefix=[0xF0])),
            "job_name": "test_qboson_submit_job_enable_subqubo",
            "source_code_list": [SAMPLES["qubo_102X102.json"]],
            "code_type": Constant.CODE_TYPE_QUBO,
            "job_type": Constant.JOB_TYPE_SAMPLING,
            "job_priority": Constant.DEFAULT_JOB_PRIORITY,
            "description": "test subqubo multi-device parallel",
            "backend": None,
            "flavor_id": self._flavor_id,
            "shots": 100,
            "circuit_aggregation": None,
            "driver_options": {"enable_subqubo": True},
            "transpiler": Constant.TRANSPILER_DUMMY,
            "transpiler_options": None,
            "profiling": None,
            "callbacks": None,
            "dry_run": False,
        }
        StLibrary.submit_job(self.admin_client, job_info)
        success, err_msg, job_results = StLibrary.wait_and_get_job_result(
            self.admin_client,
            job_info,
            self.timeout * 10,
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
