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

"""Unit tests for ProxySection configuration model."""

from wy_qcos.common.config import Config, ConfigModel, ProxySection


class TestProxySection:
    """Verify ProxySection defaults and field types."""

    def test_default_prometheus_base_url(self):
        section = ProxySection()
        assert section.PROMETHEUS_BASE_URL == "http://127.0.0.1:9090"

    def test_default_alertmanager_base_url(self):
        section = ProxySection()
        assert section.ALERTMANAGER_BASE_URL == "http://127.0.0.1:9093"

    def test_field_types_are_str(self):
        section = ProxySection()
        assert isinstance(section.PROMETHEUS_BASE_URL, str)
        assert isinstance(section.ALERTMANAGER_BASE_URL, str)

    def test_allows_empty_string_override(self):
        """Empty string disables the proxy endpoint (design §3.2)."""
        section = ProxySection(
            PROMETHEUS_BASE_URL="", ALERTMANAGER_BASE_URL=""
        )
        assert section.PROMETHEUS_BASE_URL == ""
        assert section.ALERTMANAGER_BASE_URL == ""

    def test_extra_fields_forbidden(self):
        """ProxySection follows the project-wide extra='forbid' policy."""
        import pydantic
        import pytest

        with pytest.raises(pydantic.ValidationError):
            ProxySection(UNKNOWN_FIELD="x")


class TestConfigRegistersProxy:
    """Verify PROXY is wired into ConfigModel and Config."""

    def test_config_model_has_proxy_section(self):
        model = ConfigModel()
        assert isinstance(model.PROXY, ProxySection)
        assert model.PROXY.PROMETHEUS_BASE_URL == "http://127.0.0.1:9090"

    def test_config_class_attribute(self):
        Config.initialize()
        assert hasattr(Config, "PROXY")
        assert isinstance(Config.PROXY, ProxySection)

    def test_proxy_in_valid_sections(self):
        assert "PROXY" in Config.VALID_SECTIONS

    def test_proxy_section_defaults_via_config(self):
        Config.initialize()
        assert Config.PROXY.PROMETHEUS_BASE_URL == "http://127.0.0.1:9090"
        assert Config.PROXY.ALERTMANAGER_BASE_URL == "http://127.0.0.1:9093"
