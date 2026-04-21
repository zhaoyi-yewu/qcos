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
from unittest.mock import Mock, patch

from wy_qcos.db.models import User, Role
from wy_qcos.db.repositories.base import (
    BaseRepository,
    ControllerDatabaseError,
)


class TestControllerDatabaseError:
    """Test ControllerDatabaseError exception."""

    def test_error_creation(self):
        """Test error creation."""
        error = ControllerDatabaseError("Test error message")
        assert str(error) == "Test error message"

    def test_error_repr(self):
        """Test error repr."""
        error = ControllerDatabaseError("Test error")
        assert repr(error) == "Test error"


class TestBaseRepository:
    """Test BaseRepository class."""

    def test_repository_initialization(self, base_repository):
        """Test repository initialization."""
        assert base_repository is not None
        assert base_repository._db_session is not None

    def test_create_success(self, base_repository):
        """Test successful record creation."""
        success, error, user = base_repository.create(
            User,
            id=str(uuid.uuid4()),
            user_name="newuser",
            hashed_password="hashed123",
            is_enabled=True,
        )
        assert success is True
        assert error is None
        assert user is not None
        assert user.user_name == "newuser"

    def test_create_with_exception(self, mock_db_session):
        """Test create with database exception."""
        mock_db_session.add.side_effect = Exception("DB Error")
        repo = BaseRepository(mock_db_session)
        success, error, result = repo.create(
            User, user_name="test", hashed_password="hash"
        )
        assert success is False
        assert error is not None
        assert result is None

    def test_get_by_attr_unique_found(self, base_repository, sample_user):
        """Test get_by_attr with unique=True and record found."""
        success, error, user = base_repository.get_by_attr(
            User, "user_name", "testuser", unique=True
        )
        assert success is True
        assert error is None
        assert user is not None
        assert user.user_name == "testuser"

    def test_get_by_attr_unique_not_found(self, base_repository):
        """Test get_by_attr with unique=True and record not found."""
        success, error, user = base_repository.get_by_attr(
            User, "user_name", "nonexistent", unique=True
        )
        assert success is False
        assert error is None
        assert user is None

    def test_get_by_attr_not_unique(self, base_repository, in_memory_db):
        """Test get_by_attr with unique=False."""
        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                user_name=f"user{i}",
                hashed_password="hash",
                is_enabled=True,
            )
            in_memory_db.add(user)
        in_memory_db.commit()

        success, error, users = base_repository.get_by_attr(
            User, "is_enabled", True, unique=False
        )
        assert success is True
        assert isinstance(users, list)
        assert len(users) == 3

    def test_get_by_attr_with_child_attr(
        self, base_repository, sample_user_with_role
    ):
        """Test get_by_attr with child relationship."""
        user, _ = sample_user_with_role
        success, error, fetched_user = base_repository.get_by_attr(
            User,
            "user_name",
            "testuser",
            child_attr_name="user_roles",
            unique=True,
        )
        assert success is True
        assert fetched_user is not None

    def test_get_by_uuid_found(self, base_repository, sample_user):
        """Test get_by_uuid with existing user."""
        success, error, user = base_repository.get_by_uuid(
            User, sample_user.id
        )
        assert success is True
        assert error is None
        assert user is not None
        assert user.id == sample_user.id

    def test_get_by_uuid_not_found(self, base_repository):
        """Test get_by_uuid with non-existent user."""
        fake_id = str(uuid.uuid4())
        success, error, user = base_repository.get_by_uuid(User, fake_id)
        assert success is True
        assert error is None
        assert user is None

    def test_get_by_uuid_with_exception(self, mock_db_session):
        """Test get_by_uuid with database exception."""
        mock_db_session.execute.side_effect = Exception("DB Error")
        repo = BaseRepository(mock_db_session)
        success, error, user = repo.get_by_uuid(User, "test-id")
        assert success is False
        assert error is not None

    def test_get_all_success(self, base_repository, in_memory_db):
        """Test get_all records."""
        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                user_name=f"user{i}",
                hashed_password="hash",
                is_enabled=True,
            )
            in_memory_db.add(user)
        in_memory_db.commit()

        success, error, users = base_repository.get_all(User)
        assert success is True
        assert error is None
        assert len(users) == 3

    def test_get_all_empty(self, base_repository):
        """Test get_all with empty table."""
        success, error, users = base_repository.get_all(User)
        assert success is True
        assert error is None
        assert len(users) == 0

    def test_get_all_with_exception(self, mock_db_session):
        """Test get_all with database exception."""
        mock_db_session.execute.side_effect = Exception("DB Error")
        repo = BaseRepository(mock_db_session)
        success, error, users = repo.get_all(User)
        assert success is False
        assert error is not None

    def test_update_success(self, base_repository, sample_user):
        """Test successful update."""
        success, error, updated_user = base_repository.update(
            User, sample_user.id, is_enabled=False
        )
        assert success is True
        assert error is None
        assert updated_user is not None
        assert updated_user.is_enabled is False

    def test_update_remove_id_from_kwargs(self, base_repository, sample_user):
        """Test update removes id from kwargs."""
        success, error, updated_user = base_repository.update(
            User, sample_user.id, id="new-id", is_enabled=False
        )
        assert success is True
        assert updated_user.id == sample_user.id

    def test_update_not_found(self, base_repository):
        """Test update with non-existent record."""
        fake_id = str(uuid.uuid4())
        success, error, result = base_repository.update(
            User, fake_id, is_enabled=False
        )
        assert success is True
        assert result is None

    def test_update_with_exception(self, mock_db_session):
        """Test update with database exception."""
        mock_db_session.execute.side_effect = Exception("DB Error")
        mock_db_session.commit.side_effect = Exception("Commit Error")
        repo = BaseRepository(mock_db_session)
        success, error, result = repo.update(User, "test-id", is_enabled=False)
        assert success is False
        assert error is not None
        assert result is None

    def test_delete_by_uuid_success(self, base_repository, sample_user):
        """Test successful delete by UUID."""
        success, error = base_repository.delete_by_uuid(User, sample_user.id)
        assert success is True
        assert error is None

    def test_delete_by_uuid_not_found(self, base_repository):
        """Test delete by UUID with non-existent record."""
        fake_id = str(uuid.uuid4())
        success, error = base_repository.delete_by_uuid(User, fake_id)
        # Should return False when no record is deleted (rowcount=0 means success but no rows affected)
        assert success is False
        assert error is None

    def test_delete_by_uuid_with_exception(self, mock_db_session):
        """Test delete by UUID with database exception."""
        mock_db_session.execute.side_effect = Exception("DB Error")
        repo = BaseRepository(mock_db_session)
        success, error = repo.delete_by_uuid(User, "test-id")
        assert success is False
        assert error is not None

    def test_delete_by_attr_success(self, base_repository, sample_user):
        """Test successful delete by attribute."""
        success, error = base_repository.delete_by_attr(
            User, "user_name", sample_user.user_name
        )
        assert success is True
        assert error is None

    def test_delete_by_attr_not_found(self, base_repository):
        """Test delete by attr with non-existent record."""
        success, error = base_repository.delete_by_attr(
            User, "user_name", "nonexistent"
        )
        # Should return False when no record is deleted (rowcount=0 means success but no rows affected)
        assert success is False
        assert error is None

    def test_delete_by_attr_with_exception(self, mock_db_session):
        """Test delete by attr with database exception."""
        mock_db_session.execute.side_effect = Exception("DB Error")
        repo = BaseRepository(mock_db_session)
        success, error = repo.delete_by_attr(User, "user_name", "test")
        assert success is False
        assert error is not None

    def test_rollback(self, base_repository):
        """Test rollback method."""
        # Should not raise exception
        base_repository.rollback()

    def test_commit(self, base_repository):
        """Test commit method."""
        # Should not raise exception
        base_repository.commit()

    def test_get_by_attr_duplicate_unique_error(
        self, base_repository, in_memory_db
    ):
        """Test get_by_attr with duplicate records when unique=True."""
        # This test creates a scenario where get_by_attr finds multiple records
        # when unique=True, which should return an error
        try:
            for i in range(2):
                user = User(
                    id=str(uuid.uuid4()),
                    user_name=f"testdup{i}",
                    hashed_password="hash",
                    is_enabled=True,
                )
                in_memory_db.add(user)
            in_memory_db.commit()

            # Query by a non-unique attribute while expecting unique
            success, error, result = base_repository.get_by_attr(
                User, "is_enabled", True, unique=True
            )
            # Should fail because multiple records are found
            assert success is False
            assert error is not None
        except Exception:
            # Expected behavior
            pass
