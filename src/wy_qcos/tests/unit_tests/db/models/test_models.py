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
import json
from datetime import datetime

from wy_qcos.db.models import (
    LoginLog,
    ArrayType,
    GUID,
)
from wy_qcos.db.models.base import MyEncoder


class TestBaseModel:
    """Test Base model class."""

    def test_asdict(self, sample_user):
        """Test asdict method."""
        user_dict = sample_user.asdict()
        assert isinstance(user_dict, dict)
        assert user_dict["user_name"] == "testuser"
        assert user_dict["is_enabled"] is True
        assert "id" in user_dict

    def test_asjson(self, sample_user):
        """Test asjson method."""
        json_str = sample_user.asjson()
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["user_name"] == "testuser"
        assert data["is_enabled"] is True

    def test_asdict_with_relationships(self, sample_user_with_role):
        """Test asdict with user-role relationship."""
        user, _ = sample_user_with_role
        user_dict = user.asdict()
        assert isinstance(user_dict, dict)
        assert user_dict["user_name"] == "testuser"


class TestMyEncoder:
    """Test MyEncoder class."""

    def test_encode_datetime(self):
        """Test encoding datetime object."""
        encoder = MyEncoder()
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = encoder.default(dt)
        assert isinstance(result, str)
        assert "2024-01-01" in result

    def test_encode_uuid(self):
        """Test encoding UUID object."""
        encoder = MyEncoder()
        test_uuid = uuid.uuid4()
        result = encoder.default(test_uuid)
        assert isinstance(result, str)
        assert str(test_uuid) == result

    def test_encode_unknown_type(self):
        """Test encoding unsupported type raises error."""
        encoder = MyEncoder()
        with pytest.raises(TypeError):
            encoder.default({"key": "value"})


class TestUserModel:
    """Test User model class."""

    def test_user_creation(self, sample_user):
        """Test user creation."""
        assert sample_user.user_name == "testuser"
        assert sample_user.is_enabled is True
        assert sample_user.is_locked is False

    def test_user_roles_property(self, sample_user_with_role):
        """Test user roles property."""
        user, role = sample_user_with_role
        roles = user.roles
        assert isinstance(roles, list)
        assert len(roles) == 1
        assert role.role_name in roles

    def test_get_role_names(self, sample_user_with_role):
        """Test get_role_names method."""
        user, role = sample_user_with_role
        role_names = user.get_role_names()
        assert isinstance(role_names, list)
        assert role.role_name in role_names

    def test_get_role_names_empty(self, sample_user):
        """Test get_role_names with no roles."""
        role_names = sample_user.get_role_names()
        assert role_names == []

    def test_user_asdict(self, sample_user):
        """Test user asdict conversion."""
        user_dict = sample_user.asdict()
        assert user_dict["user_name"] == "testuser"
        assert user_dict["is_enabled"] is True
        assert user_dict["is_locked"] is False


class TestRoleModel:
    """Test Role model class."""

    def test_role_creation(self, sample_role):
        """Test role creation."""
        assert sample_role.role_name == "admin"
        assert sample_role.permissions == ["read", "write", "delete"]
        assert sample_role.description == "Administrator role"

    def test_role_asdict(self, sample_role):
        """Test role asdict conversion."""
        role_dict = sample_role.asdict()
        assert role_dict["role_name"] == "admin"
        assert role_dict["permissions"] == ["read", "write", "delete"]


class TestUserRoleModel:
    """Test UserRole model class."""

    def test_user_role_creation(self, sample_user_with_role):
        """Test user role creation."""
        user, role = sample_user_with_role
        assert len(user.user_roles) > 0
        user_role = user.user_roles[0]
        assert user_role.user_id == user.id
        assert user_role.role_id == role.id

    def test_user_role_asdict(self, sample_user_with_role):
        """Test user role asdict conversion."""
        user, _ = sample_user_with_role
        user_role = user.user_roles[0]
        ur_dict = user_role.asdict()
        assert ur_dict["user_id"] == user.id
        assert "id" in ur_dict


class TestLoginLogModel:
    """Test LoginLog model class."""

    def test_login_log_creation(self, sample_login_log):
        """Test login log creation."""
        assert sample_login_log.user_name == "testuser"
        assert sample_login_log.ip_address == "192.168.1.1"
        assert sample_login_log.login_status is True
        assert sample_login_log.user_agent == "Mozilla/5.0"

    def test_login_log_failed(self, in_memory_db):
        """Test login log with failed status."""
        log = LoginLog(
            id=str(uuid.uuid4()),
            user_name="testuser",
            ip_address="192.168.1.2",
            login_time=datetime.now(),
            login_status=False,
            failure_reason="Invalid password",
        )
        in_memory_db.add(log)
        in_memory_db.commit()
        assert log.login_status is False
        assert log.failure_reason == "Invalid password"

    def test_login_log_asdict(self, sample_login_log):
        """Test login log asdict conversion."""
        log_dict = sample_login_log.asdict()
        assert log_dict["user_name"] == "testuser"
        assert log_dict["login_status"] is True


class TestTokenBlacklistModel:
    """Test TokenBlacklist model class."""

    def test_token_blacklist_creation(self, sample_token_blacklist):
        """Test token blacklist creation."""
        assert sample_token_blacklist.token_jti is not None
        assert isinstance(sample_token_blacklist.expires_at, datetime)

    def test_token_blacklist_asdict(self, sample_token_blacklist):
        """Test token blacklist asdict conversion."""
        token_dict = sample_token_blacklist.asdict()
        assert "token_jti" in token_dict
        assert "expires_at" in token_dict


class TestArrayType:
    """Test ArrayType custom type."""

    def test_array_type_load_dialect_impl_postgresql(self):
        """Test ArrayType dialect implementation for PostgreSQL."""
        from sqlalchemy.dialects.postgresql import dialect as pg_dialect

        array_type = ArrayType()
        mock_dialect = pg_dialect()
        impl = array_type.load_dialect_impl(mock_dialect)
        assert impl is not None

    def test_array_type_load_dialect_impl_sqlite(self):
        """Test ArrayType dialect implementation for SQLite."""
        from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect

        array_type = ArrayType()
        mock_dialect = sqlite_dialect()
        impl = array_type.load_dialect_impl(mock_dialect)
        assert impl is not None

    def test_array_type_process_bind_param_none(self):
        """Test ArrayType process_bind_param with None."""
        array_type = ArrayType()
        result = array_type.process_bind_param(None, None)
        assert result == []

    def test_array_type_process_bind_param_list(self):
        """Test ArrayType process_bind_param with list."""
        from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect

        array_type = ArrayType()
        mock_dialect = sqlite_dialect()
        result = array_type.process_bind_param(["a", "b"], mock_dialect)
        assert result == ["a", "b"]

    def test_array_type_process_result_value_none(self):
        """Test ArrayType process_result_value with None."""
        array_type = ArrayType()
        result = array_type.process_result_value(None, None)
        assert result == []

    def test_array_type_process_result_value_list(self):
        """Test ArrayType process_result_value with list."""
        array_type = ArrayType()
        result = array_type.process_result_value(["a", "b"], None)
        assert result == ["a", "b"]

    def test_array_type_process_result_value_tuple(self):
        """Test ArrayType process_result_value with tuple."""
        array_type = ArrayType()
        result = array_type.process_result_value(("a", "b"), None)
        assert result == ["a", "b"]

    def test_array_type_process_result_value_single_value(self):
        """Test ArrayType process_result_value with single value."""
        array_type = ArrayType()
        result = array_type.process_result_value("single", None)
        assert result == ["single"]


class TestGUIDType:
    """Test GUID custom type."""

    def test_guid_type_load_dialect_impl_postgresql(self):
        """Test GUID dialect implementation for PostgreSQL."""
        from sqlalchemy.dialects.postgresql import dialect as pg_dialect

        guid_type = GUID()
        mock_dialect = pg_dialect()
        impl = guid_type.load_dialect_impl(mock_dialect)
        assert impl is not None

    def test_guid_type_load_dialect_impl_sqlite(self):
        """Test GUID dialect implementation for SQLite."""
        from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect

        guid_type = GUID()
        mock_dialect = sqlite_dialect()
        impl = guid_type.load_dialect_impl(mock_dialect)
        assert impl is not None

    def test_guid_type_process_bind_param_none(self):
        """Test GUID process_bind_param with None."""
        guid_type = GUID()
        result = guid_type.process_bind_param(None, None)
        assert result is None

    def test_guid_type_process_bind_param_string(self):
        """Test GUID process_bind_param with string UUID."""
        from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect

        guid_type = GUID()
        mock_dialect = sqlite_dialect()
        test_uuid = str(uuid.uuid4())
        result = guid_type.process_bind_param(test_uuid, mock_dialect)
        assert isinstance(result, str)
        assert len(result) == 32

    def test_guid_type_process_bind_param_uuid_object(self):
        """Test GUID process_bind_param with UUID object."""
        from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect

        guid_type = GUID()
        mock_dialect = sqlite_dialect()
        test_uuid = uuid.uuid4()
        result = guid_type.process_bind_param(test_uuid, mock_dialect)
        assert isinstance(result, str)
        assert len(result) == 32
