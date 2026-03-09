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
import logging
import uuid
from typing import ClassVar
from sqlalchemy.sql.schema import Table

from sqlalchemy import Column, String, DateTime, Boolean, event, ARRAY
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseTable

logger = logging.getLogger(__name__)


class User(BaseTable):
    """Users table."""

    __tablename__ = "users"
    __table__: ClassVar[Table]

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    username = Column(String(64), unique=True, index=True)
    hashed_password = Column(String(128))
    roles = Column(ARRAY(String(64)), index=True, default=list)
    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)
    last_login = Column(DateTime)
    password_changed_at = Column(DateTime)
    locked_until = Column(DateTime)


class Role(BaseTable):
    """Roles table."""

    __tablename__ = "roles"
    __table__: ClassVar[Table]

    name = Column(String(64), primary_key=True, unique=True, index=True)
    permissions = Column(ARRAY(String(64)), index=True, default=list)
    description = Column(String(256))


@event.listens_for(Role.__table__, "after_create")
def create_default_role(target, connection, **kw):
    default_name = "admin"
    default_permissions = ["all"]

    stmt = target.insert().values(
        name=default_name,
        permissions=default_permissions,
    )

    connection.execute(stmt)
    logger.info("The default super role has been created in the database")
