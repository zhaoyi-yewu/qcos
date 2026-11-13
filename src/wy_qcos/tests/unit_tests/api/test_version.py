#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of MulanPSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Unit tests for version API routes."""

from unittest.mock import Mock, patch

from wy_qcos.api.posiq.routes_jsonrpc.version import version
from wy_qcos.api.schemas import GetVersionRequest, GetVersionResponse
from wy_qcos.common.constant import Constant


class TestVersion:
    """Test cases for version function."""

    @patch("wy_qcos.api.posiq.routes_jsonrpc.version.scheduler")
    @patch("wy_qcos.api.posiq.routes_jsonrpc.version.QcosVersion")
    def test_version_success(self, mock_qcos_version, mock_scheduler):
        """Test successful version retrieval."""
        # Mock QcosVersion
        mock_qcos_version.VERSION = "1.0.0"

        # Mock driver manager and drivers
        mock_driver = Mock()
        mock_driver.get_supported_code_types.return_value = ["QASM"]
        mock_driver.get_description.return_value = "Test driver"
        mock_driver.get_driver_options.return_value = {"option1": "value1"}
        mock_driver.get_supported_transpilers.return_value = ["transpiler1"]

        mock_driver_manager = Mock()
        mock_driver_manager.get_drivers.return_value = {"driver1": mock_driver}

        # Mock transpiler manager and transpilers
        mock_transpiler = Mock()
        mock_transpiler.get_alias_name.return_value = "Transpiler Alias"
        mock_transpiler.get_supported_code_types.return_value = ["QASM"]

        mock_transpiler_manager = Mock()
        mock_transpiler_manager.get_transpiler.return_value = mock_transpiler

        # Setup scheduler mocks
        mock_scheduler.get_driver_manager.return_value = mock_driver_manager
        mock_scheduler.get_transpiler_manager.return_value = (
            mock_transpiler_manager
        )

        # Call version function
        body = GetVersionRequest(details=True)
        result = version(body)

        # Verify result
        assert isinstance(result, GetVersionResponse)
        assert result.version == "1.0.0"
        assert result.api_version == Constant.API_VERSION_V1
        # capabilities is a dict, not an object
        assert "driver1" in result.capabilities["drivers"]
        assert "transpiler1" in result.capabilities["transpilers"]
        assert result.capabilities["drivers"]["driver1"]["driver_options"] == {
            "option1": "value1"
        }
        assert set(result.capabilities["schemas"]) == {
            "driver_options",
            "transpiler_options",
            "options",
            "qem_options",
            "qec_options",
            "extra_specs",
        }
        assert set(result.capabilities["schemas"]["driver_options"]) == {
            "driver1"
        }
        assert set(result.capabilities["schemas"]["transpiler_options"]) == {
            "transpiler1"
        }

    @patch("wy_qcos.api.posiq.routes_jsonrpc.version.scheduler")
    @patch("wy_qcos.api.posiq.routes_jsonrpc.version.QcosVersion")
    def test_version_no_drivers(self, mock_qcos_version, mock_scheduler):
        """Test version with no drivers."""
        mock_qcos_version.VERSION = "1.0.0"

        mock_driver_manager = Mock()
        mock_driver_manager.get_drivers.return_value = {}

        mock_transpiler_manager = Mock()

        mock_scheduler.get_driver_manager.return_value = mock_driver_manager
        mock_scheduler.get_transpiler_manager.return_value = (
            mock_transpiler_manager
        )

        body = GetVersionRequest(details=True)
        result = version(body)

        assert isinstance(result, GetVersionResponse)
        assert result.version == "1.0.0"
        assert result.capabilities["drivers"] == {}
        assert result.capabilities["transpilers"] == {}

    @patch("wy_qcos.api.posiq.routes_jsonrpc.version.scheduler")
    @patch("wy_qcos.api.posiq.routes_jsonrpc.version.QcosVersion")
    def test_version_driver_without_transpilers(
        self, mock_qcos_version, mock_scheduler
    ):
        """Test version with driver that has no transpilers."""
        mock_qcos_version.VERSION = "1.0.0"

        mock_driver = Mock()
        mock_driver.get_supported_code_types.return_value = ["QASM"]
        mock_driver.get_description.return_value = "Test driver"
        mock_driver.get_driver_options.return_value = {}
        mock_driver.get_supported_transpilers.return_value = []

        mock_driver_manager = Mock()
        mock_driver_manager.get_drivers.return_value = {"driver1": mock_driver}

        mock_transpiler_manager = Mock()

        mock_scheduler.get_driver_manager.return_value = mock_driver_manager
        mock_scheduler.get_transpiler_manager.return_value = (
            mock_transpiler_manager
        )

        body = GetVersionRequest(details=True)
        result = version(body)

        assert isinstance(result, GetVersionResponse)
        assert result.version == "1.0.0"
        assert "driver1" in result.capabilities["drivers"]
        assert (
            result.capabilities["driver_transpiler_mappings"]["driver1"]
            == set()
        )

    @patch("wy_qcos.api.posiq.routes_jsonrpc.version.scheduler")
    @patch("wy_qcos.api.posiq.routes_jsonrpc.version.QcosVersion")
    def test_version_multiple_drivers_shared_transpiler(
        self, mock_qcos_version, mock_scheduler
    ):
        """Test version with multiple drivers sharing a transpiler."""
        mock_qcos_version.VERSION = "1.0.0"

        # Driver 1
        mock_driver1 = Mock()
        mock_driver1.get_supported_code_types.return_value = ["QASM"]
        mock_driver1.get_description.return_value = "Driver 1"
        mock_driver1.get_driver_options.return_value = {}
        mock_driver1.get_supported_transpilers.return_value = [
            "shared_transpiler"
        ]

        # Driver 2
        mock_driver2 = Mock()
        mock_driver2.get_supported_code_types.return_value = ["QIR"]
        mock_driver2.get_description.return_value = "Driver 2"
        mock_driver2.get_driver_options.return_value = {}
        mock_driver2.get_supported_transpilers.return_value = [
            "shared_transpiler"
        ]

        mock_driver_manager = Mock()
        mock_driver_manager.get_drivers.return_value = {
            "driver1": mock_driver1,
            "driver2": mock_driver2,
        }

        # Shared transpiler
        mock_transpiler = Mock()
        mock_transpiler.get_alias_name.return_value = "Shared Transpiler"
        mock_transpiler.get_supported_code_types.return_value = ["QASM", "QIR"]

        mock_transpiler_manager = Mock()
        mock_transpiler_manager.get_transpiler.return_value = mock_transpiler

        mock_scheduler.get_driver_manager.return_value = mock_driver_manager
        mock_scheduler.get_transpiler_manager.return_value = (
            mock_transpiler_manager
        )

        body = GetVersionRequest(details=True)
        result = version(body)

        assert isinstance(result, GetVersionResponse)
        assert "driver1" in result.capabilities["drivers"]
        assert "driver2" in result.capabilities["drivers"]
        assert "shared_transpiler" in result.capabilities["transpilers"]
        assert (
            "shared_transpiler"
            in result.capabilities["driver_transpiler_mappings"]["driver1"]
        )
        assert (
            "shared_transpiler"
            in result.capabilities["driver_transpiler_mappings"]["driver2"]
        )

    @patch("wy_qcos.api.posiq.routes_jsonrpc.version.scheduler")
    @patch("wy_qcos.api.posiq.routes_jsonrpc.version.QcosVersion")
    def test_version_without_details(self, mock_qcos_version, mock_scheduler):
        """Test version retrieval without details parameter."""
        # Mock QcosVersion
        mock_qcos_version.VERSION = "1.0.0"

        # Mock driver manager and drivers
        mock_driver = Mock()
        mock_driver.get_supported_code_types.return_value = ["QASM"]
        mock_driver.get_description.return_value = "Test driver"
        mock_driver.get_driver_options.return_value = {"option1": "value1"}
        mock_driver.get_supported_transpilers.return_value = ["transpiler1"]

        mock_driver_manager = Mock()
        mock_driver_manager.get_drivers.return_value = {"driver1": mock_driver}

        # Mock transpiler manager and transpilers
        mock_transpiler = Mock()
        mock_transpiler.get_alias_name.return_value = "Transpiler Alias"
        mock_transpiler.get_supported_code_types.return_value = ["QASM"]

        mock_transpiler_manager = Mock()
        mock_transpiler_manager.get_transpiler.return_value = mock_transpiler

        # Setup scheduler mocks
        mock_scheduler.get_driver_manager.return_value = mock_driver_manager
        mock_scheduler.get_transpiler_manager.return_value = (
            mock_transpiler_manager
        )

        # Call version function without details parameter
        body = GetVersionRequest()
        result = version(body)

        # Verify result
        assert isinstance(result, GetVersionResponse)
        assert result.version == "1.0.0"
        assert result.api_version == Constant.API_VERSION_V1
        # capabilities should be None when details=False (default)
        assert result.capabilities is None
        # auth_mode should be present
        assert result.auth_mode is not None

    @patch("wy_qcos.api.posiq.routes_jsonrpc.version.scheduler")
    def test_version_plugin_failure_and_missing_metadata_degrade(
        self, mock_scheduler
    ):
        """Test schema export failures do not break the version response."""
        broken_driver = Mock()
        broken_driver.get_transpiler.return_value = None
        broken_driver.get_supported_transpilers.return_value = []
        broken_driver.get_supported_code_types.return_value = []
        broken_driver.get_description.return_value = "Broken driver"
        broken_driver.get_driver_options.return_value = {}
        broken_driver.get_alias_name.return_value = "故障驱动"
        broken_driver.get_driver_options_schema.side_effect = RuntimeError(
            "connection values must not be exposed"
        )
        broken_driver.get_qec_options_schema.return_value = None
        broken_driver.get_qec_options_metadata.return_value = {}

        missing_driver = Mock()
        missing_driver.get_transpiler.return_value = None
        missing_driver.get_supported_transpilers.return_value = []
        missing_driver.get_supported_code_types.return_value = []
        missing_driver.get_description.return_value = "Missing metadata"
        missing_driver.get_driver_options.return_value = {"safe": "default"}
        missing_driver.get_alias_name.return_value = "缺失元数据驱动"
        missing_driver.get_driver_options_schema.return_value = {
            "required_value": int
        }
        missing_driver.get_driver_options_metadata.return_value = {}
        missing_driver.get_qec_options_schema.return_value = None
        missing_driver.get_qec_options_metadata.return_value = {}

        mock_driver_manager = Mock()
        mock_driver_manager.get_drivers.return_value = {
            "broken": broken_driver,
            "missing": missing_driver,
        }
        mock_scheduler.get_driver_manager.return_value = mock_driver_manager
        mock_scheduler.get_transpiler_manager.return_value = Mock()

        result = version(GetVersionRequest(details=True))
        schemas = result.capabilities["schemas"]["driver_options"]
        assert schemas["broken"]["x-qcos-schema-status"] == "unavailable"
        required = schemas["missing"]["properties"]["required_value"]
        assert required["alias_name"] == "未命名（required_value）"
        assert result.capabilities["drivers"]["missing"]["driver_options"] == {
            "safe": "default"
        }

    @patch(
        "wy_qcos.api.posiq.routes_jsonrpc.version.build_capabilities_schemas"
    )
    def test_version_without_details_does_not_build_schemas(
        self, mock_build_schemas
    ):
        """Test details=False skips all schema construction."""
        result = version(GetVersionRequest(details=False))

        assert result.capabilities is None
        mock_build_schemas.assert_not_called()
