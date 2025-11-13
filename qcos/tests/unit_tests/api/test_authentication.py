#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from unittest.mock import patch, Mock

from qcos.api.posiq.routes_jsonrpc.dependencies.authentication import auth
from qcos.common.library import Library


class TestAuthentication:
    @patch.object(Library, "decrypt_virtual_instance_id")
    @patch("qcos.api.posiq.routes_jsonrpc.dependencies.authentication.Config")
    def test_auth(self, mock_config, mock_decrypt_virtual_instance_id):
        mock_config = Mock()
        mock_config.ENABLE_VIRT = True
        mock_decrypt_virtual_instance_id.return_value = True, None, [], None
        auth_data = auth("test")
        assert auth_data["device_names"] == []
        assert auth_data["instance_id"] is None
