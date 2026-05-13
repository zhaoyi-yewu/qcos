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
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    func,
    TypeDecorator,
    String,
    inspect,
    MetaData,
    JSON,
    CHAR,
    ARRAY,
)
from sqlalchemy.orm import DeclarativeBase

from wy_qcos.common.constant import Constant

metadata = MetaData()


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, uuid.UUID)):
            return str(obj)
        return super().default(obj)


class Base(DeclarativeBase):
    """Base model."""

    def asdict(self):
        return {
            c.key: getattr(self, c.key, None)
            for c in inspect(self).mapper.column_attrs
        }

    def asjson(self):
        return json.dumps(self.asdict(), cls=MyEncoder)


class BaseTable(Base):
    """Base table."""

    __abstract__ = True

    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    __mapper_args__ = {"eager_defaults": True}


class ArrayType(TypeDecorator):
    """Platform-independent Array type."""

    impl = JSON
    cache_ok = True
    """Using cache."""

    def load_dialect_impl(self, dialect):
        """Load dialect impl."""
        if dialect.name == Constant.DB_DIALECT_POSTGRESQL:
            return dialect.type_descriptor(ARRAY(String(64)))
        else:
            return dialect.type_descriptor(JSON)

    def process_bind_param(self, value, dialect):
        """Process bind param."""
        if value is None:
            return []
        if dialect.name != Constant.DB_DIALECT_POSTGRESQL:
            return value if isinstance(value, list) else []
        return value

    def process_result_value(self, value, dialect):
        """Process result value."""
        if value is None:
            return []
        return (
            list(value) if isinstance(value, (list, set, tuple)) else [value]
        )


class GUID(TypeDecorator):
    """Platform-independent GUID type."""

    impl = CHAR
    cache_ok = True
    """Using cache."""

    def load_dialect_impl(self, dialect):
        """Load dialect impl."""
        if dialect.name == Constant.DB_DIALECT_POSTGRESQL:
            from sqlalchemy.dialects.postgresql import UUID

            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        """Process bind param."""
        if value is None:
            return value
        elif dialect.name == Constant.DB_DIALECT_POSTGRESQL:
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                # hexstring
                return "%.32x" % value.int


class DictList(TypeDecorator):
    """Dict list type."""

    impl = CHAR(1024)

    def process_bind_param(self, value, dialect):
        """Process bind param."""
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        """Process result value."""
        if value is None:
            return None
        return json.loads(value)
