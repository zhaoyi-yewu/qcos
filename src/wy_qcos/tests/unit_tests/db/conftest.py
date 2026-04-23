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

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from wy_qcos.db.models import Base, User, Role, UserRole, LoginLog, TokenBlacklist
from wy_qcos.db.repositories.base import BaseRepository
from wy_qcos.db.repositories.user import UserRepository
from wy_qcos.db.repositories.role import RoleRepository


@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    session = MagicMock(spec=Session)
    return session


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def base_repository(in_memory_db):
    """Create a BaseRepository instance with in-memory database."""
    return BaseRepository(in_memory_db)


@pytest.fixture
def user_repository(in_memory_db):
    """Create a UserRepository instance with in-memory database."""
    return UserRepository(in_memory_db)


@pytest.fixture
def role_repository(in_memory_db):
    """Create a RoleRepository instance with in-memory database."""
    return RoleRepository(in_memory_db)


@pytest.fixture
def sample_user(in_memory_db):
    """Create a sample user in the database."""
    user = User(
        id=str(uuid.uuid4()),
        user_name='testuser',
        hashed_password='hashed_password_123',
        is_enabled=True,
        is_locked=False,
        password_changed_at=datetime.now()
    )
    in_memory_db.add(user)
    in_memory_db.commit()
    in_memory_db.refresh(user)
    return user


@pytest.fixture
def sample_role(in_memory_db):
    """Create a sample role in the database."""
    role = Role(
        id=str(uuid.uuid4()),
        role_name='admin',
        permissions=['read', 'write', 'delete'],
        description='Administrator role'
    )
    in_memory_db.add(role)
    in_memory_db.commit()
    in_memory_db.refresh(role)
    return role


@pytest.fixture
def sample_user_with_role(in_memory_db, sample_user, sample_role):
    """Create a user with assigned role."""
    user_role = UserRole(
        id=str(uuid.uuid4()),
        user_id=sample_user.id,
        role_id=sample_role.id
    )
    in_memory_db.add(user_role)
    in_memory_db.commit()
    return sample_user, sample_role


@pytest.fixture
def sample_login_log(in_memory_db):
    """Create a sample login log."""
    log = LoginLog(
        id=str(uuid.uuid4()),
        user_name='testuser',
        ip_address='192.168.1.1',
        login_time=datetime.now(),
        login_status=True,
        user_agent='Mozilla/5.0'
    )
    in_memory_db.add(log)
    in_memory_db.commit()
    in_memory_db.refresh(log)
    return log


@pytest.fixture
def sample_token_blacklist(in_memory_db):
    """Create a sample token blacklist entry."""
    token = TokenBlacklist(
        id=str(uuid.uuid4()),
        token_jti=str(uuid.uuid4()),
        expires_at=datetime.now()
    )
    in_memory_db.add(token)
    in_memory_db.commit()
    in_memory_db.refresh(token)
    return token

