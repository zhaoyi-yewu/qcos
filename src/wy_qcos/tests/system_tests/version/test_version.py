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

"""System tests for version APIs."""

import json
import pytest

from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos.common.qcos_version import QcosVersion
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
class TestVersion:
    """Test version API endpoints."""

    @classmethod
    def setup_class(cls):
        """Set up the test class."""
        cls.admin_client = GLOBAL_CONFIGS["admin_client"]

    @classmethod
    def teardown_class(cls):
        """Tear down the test class."""
        pass

    def test_version(self):
        """Test retrieving version information."""
        status_code, reason, text, result = self.admin_client.version()
        assert status_code == HttpCode.SUCCESS_OK
        json_results = json.loads(text)
        result = json_results["result"]
        assert result["version"] == QcosVersion.VERSION
        assert result["api_version"] == Constant.API_VERSION_V1
        assert not result.get("capabilities", None)

        # with option: details
        status_code, reason, text, result = self.admin_client.version(
            details=True
        )
        assert status_code == HttpCode.SUCCESS_OK
        json_results = json.loads(text)
        result = json_results["result"]
        assert result["version"] == QcosVersion.VERSION
        assert result["api_version"] == Constant.API_VERSION_V1
        assert result.get("capabilities", None)
        assert not result["capabilities"]["drivers"]["DriverDummy"][
            "driver_options"
        ]["enable_wirecut"]
        schemas = result["capabilities"]["schemas"]
        assert set(schemas) == {
            "driver_options",
            "transpiler_options",
            "options",
            "qem_options",
            "qec_options",
            "extra_specs",
        }
        dummy_schema = schemas["driver_options"]["DriverDummy"]
        assert dummy_schema["$schema"] == (
            "http://json-schema.org/draft-07/schema#"
        )
        assert dummy_schema["properties"]["qes"]["alias_name"]
        assert (
            schemas["qec_options"]["DriverDummy"]["additionalProperties"]
            is True
        )
        json.dumps(schemas, ensure_ascii=False)
