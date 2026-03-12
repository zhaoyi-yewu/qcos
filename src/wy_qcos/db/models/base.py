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

from sqlalchemy import Column, DateTime, func
from fastapi.encoders import jsonable_encoder
from sqlalchemy import inspect, MetaData
from sqlalchemy.orm import as_declarative

metadata = MetaData()


@as_declarative(metadata=metadata)
class Base:
    """Base model."""

    def asdict(self):
        return {
            c.key: getattr(self, c.key, None)
            for c in inspect(self).mapper.column_attrs
        }

    def asjson(self):
        return jsonable_encoder(self.asdict())


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
