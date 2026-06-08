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

from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, model_serializer, model_validator


class UuidMixin(BaseModel):
    """Mixin providing UUID field conversion and JSON serialization.

    Subclasses configure behaviour via class variables:

    - ``_uuid_fields``: list of field names that hold UUID values.
    - ``_uuid_convert_mode``: conversion strategy applied in the
      ``model_validator(mode="before")`` step.

      Supported modes:

      - ``"to_str"``: UUID -> str
      - ``"to_uuid"``: str -> UUID
      - ``"to_str_with_int"``: UUID/int -> str
      - ``"to_uuid_with_int"``: str/int -> UUID
    """

    _uuid_fields: ClassVar[list[str]] = []
    _uuid_convert_mode: ClassVar[str] = "to_str"

    @model_validator(mode="before")
    @classmethod
    def convert_uuids(cls, data):
        """Convert UUID fields according to the configured mode."""
        if not isinstance(data, dict) or not cls._uuid_fields:
            return data
        for field in cls._uuid_fields:
            if field not in data or data[field] is None:
                continue
            value = data[field]
            mode = cls._uuid_convert_mode
            if mode == "to_str":
                if isinstance(value, UUID):
                    data[field] = str(value)
            elif mode == "to_uuid":
                if isinstance(value, str):
                    try:
                        data[field] = UUID(value)
                    except (ValueError, TypeError):
                        pass
            elif mode == "to_str_with_int":
                if isinstance(value, UUID):
                    data[field] = str(value)
                elif isinstance(value, int):
                    data[field] = str(UUID(int=value))
            elif mode == "to_uuid_with_int":
                if isinstance(value, str):
                    try:
                        data[field] = UUID(value)
                    except (ValueError, AttributeError):
                        pass
                elif isinstance(value, int):
                    data[field] = UUID(int=value)
        return data

    @model_serializer(mode="wrap", when_used="json")
    def _serialize_uuid_fields(self, handler):
        """Serialize UUID objects to strings for JSON output."""
        result = handler(self)
        if isinstance(result, dict):
            for key in list(result.keys()):
                if isinstance(result[key], UUID):
                    result[key] = str(result[key])
        return result
