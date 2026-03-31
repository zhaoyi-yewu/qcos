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

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    JSON,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from wy_qcos.db.models.base import Base


class User(Base):
    """User database model."""

    __tablename__ = "users"

    # Primary key: auto-increment ID
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Business unique constraint: user name
    user_name = Column(String(50), unique=True, index=True, nullable=False)

    # FastAPI-Users base fields (password management)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)

    # Extended fields from existing model
    roles = Column(JSON, default=[])
    is_locked = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, default=datetime.now)
    locked_until = Column(DateTime, nullable=True)
    password_expiry_days = Column(Integer, default=0)
    failed_login_attempts = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    login_logs = relationship("LoginLog", back_populates="user")
    user_roles = relationship("UserRole", back_populates="user")


class Role(Base):
    """Role database model."""

    __tablename__ = "roles"

    # Primary key: auto-increment ID
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Business unique constraint: role name
    role_name = Column(String(50), unique=True, index=True, nullable=False)

    # Role permissions and metadata
    permissions = Column(JSON, default=[])
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user_roles = relationship("UserRole", back_populates="role")


class UserRole(Base):
    """User-Role many-to-many relationship model."""

    __tablename__ = "user_roles"

    # Primary key: auto-increment ID
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    # Creation timestamp
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class LoginLog(Base):
    """Login log database model."""

    __tablename__ = "login_logs"

    # Primary key: auto-increment ID
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # Login information
    user_name = Column(String(50), index=True, nullable=False)
    ip_address = Column(String(45), nullable=False)  # Support IPv6
    login_time = Column(DateTime, default=datetime.now)
    login_status = Column(String(20), nullable=False)  # success, failed
    user_agent = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="login_logs")
