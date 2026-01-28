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

from unittest.mock import Mock

import pytest
from fastapi.exceptions import RequestValidationError
from pydantic_core import ValidationError

from wy_qcos.api.fastapi_server import (
    patched_invalid_params_from_validation_error,
)


class TestFastApiServer:
    def test_patched_invalid_params_from_validation_error(self):
        mock_client = Mock(spec=RequestValidationError)
        mock_client.errors.return_value = [
            {"loc": ("body",), "msg": "msg", "type": "type", "input": "input"},
            {"loc": ("body",)},
        ]
        with pytest.raises(ValidationError) as e:
            patched_invalid_params_from_validation_error(mock_client)
        assert "errors" in str(e)
