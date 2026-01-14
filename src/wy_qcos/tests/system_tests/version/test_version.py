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
import pytest

from wy_qcos.common.config import Config
from wy_qcos.common.constant import HttpCode
from wy_qcos.common.qcos_version import QcosVersion
from wy_qcos.tests.system_tests.conftest import GLOBAL_CONFIGS


@pytest.mark.usefixtures("global_configs")
class TestVersion:
    @classmethod
    def setup_class(cls):
        cls.client = GLOBAL_CONFIGS["client"]

    @classmethod
    def teardown_class(cls):
        pass

    def test_version(self):
        status_code, reason, text, result = self.client.version()
        assert status_code == HttpCode.SUCCESS_OK
        json_results = json.loads(text)
        result = json_results["result"]
        assert result["version"] == QcosVersion.VERSION
        assert result["api_version"] == Config.API_VERSION_V1
        assert not result["capabilities"]["drivers"]["DriverDummy"][
            "driver_options"
        ]["enable_wirecut"]
