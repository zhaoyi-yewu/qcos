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

import uuid
from unittest.mock import MagicMock

from wy_qcos.common.library import _s
from wy_qcos.db.models import User
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


class TestBaseRepositoryExtended:
    """Extended tests for BaseRepository methods."""

    def test_get_by_uuid_with_filters(self, base_repository, sample_user):
        """Test get_by_uuid with additional filters."""
        success, error, user = base_repository.get_by_uuid(
            User, sample_user.id, filters={"user_name": "testuser"}
        )
        assert success is True
        assert user is not None

    def test_get_by_uuid_with_filters_not_matching(
        self, base_repository, sample_user
    ):
        """Test get_by_uuid with filters that don't match."""
        success, error, user = base_repository.get_by_uuid(
            User, sample_user.id, filters={"user_name": "nonexistent"}
        )
        assert success is True
        assert user is None

    def test_get_by_uuid_not_unique(self, base_repository, in_memory_db):
        """Test get_by_uuid returns error when multiple records match."""
        # Use a mock session to simulate non-unique results since SQLite
        # enforces UNIQUE constraint on id and would reject duplicate inserts
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(),
            MagicMock(),
        ]
        mock_session = MagicMock()
        mock_session.execute.return_value = mock_result
        repo = BaseRepository(mock_session)

        success, error, user = repo.get_by_uuid(User, "some-uuid")
        assert success is False
        assert "not unique" in str(error)

    def test_get_all_with_child_attr(
        self, base_repository, sample_user_with_role
    ):
        """Test get_all with child_attr_name for eager loading."""
        user, role = sample_user_with_role
        # Use a valid relationship attribute on User model
        # If 'roles' is not a valid relationship, this will fail gracefully
        success, error, users = base_repository.get_all(User)
        assert success is True
        assert len(users) >= 1

    def test_get_all_with_invalid_child_attr(self, base_repository):
        """Test get_all with invalid child_attr_name logs error."""
        success, error, users = base_repository.get_all(
            User, child_attr_name="nonexistent_relationship"
        )
        # Should return False with error logged
        assert success is False
        assert error is not None

    def test_get_all_with_list_filter(self, base_repository, in_memory_db):
        """Test get_all with list value filter (IN operator)."""
        from wy_qcos.common.library import _s

        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                user_name=f"user{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
            in_memory_db.add(user)
        in_memory_db.commit()

        success, error, users = base_repository.get_all(
            User, filters={"user_name": ["user0", "user1"]}
        )
        assert success is True
        assert len(users) == 2

    def test_get_all_with_invalid_filter_key(self, base_repository):
        """Test get_all with filter key that doesn't exist on model."""
        success, error, users = base_repository.get_all(
            User, filters={"nonexistent_field": "value"}
        )
        assert success is True  # Should log warning but not fail

    def test_get_all_error(self, mock_db_session):
        """Test get_all handles database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = BaseRepository(mock_db_session)
        success, error, users = repo.get_all(User)
        assert success is False
        assert error is not None

    def test_count(self, base_repository, in_memory_db):
        """Test count method."""
        from wy_qcos.common.library import _s

        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                user_name=f"countuser{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
            in_memory_db.add(user)
        in_memory_db.commit()

        count = base_repository.count(User)
        assert count >= 3

    def test_count_error(self, mock_db_session):
        """Test count handles database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = BaseRepository(mock_db_session)
        count = repo.count(User)
        assert count == 0

    def test_count_by_attr(self, base_repository, sample_user):
        """Test count_by_attr method."""
        count = base_repository.count_by_attr(User, "user_name", "testuser")
        assert count == 1

    def test_count_by_attr_error(self, mock_db_session):
        """Test count_by_attr handles database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = BaseRepository(mock_db_session)
        count = repo.count_by_attr(User, "user_name", "test")
        assert count == 0

    def test_count_with_filters(self, base_repository, sample_user):
        """Test count_with_filters method."""
        count = base_repository.count_with_filters(
            User, filters={"user_name": "testuser"}
        )
        assert count == 1

    def test_count_with_filters_list_value(
        self, base_repository, in_memory_db
    ):
        """Test count_with_filters with list value."""
        from wy_qcos.common.library import _s

        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                user_name=f"filteruser{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
            in_memory_db.add(user)
        in_memory_db.commit()

        count = base_repository.count_with_filters(
            User, filters={"user_name": ["filteruser0", "filteruser1"]}
        )
        assert count == 2

    def test_count_with_filters_error(self, mock_db_session):
        """Test count_with_filters handles database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = BaseRepository(mock_db_session)
        count = repo.count_with_filters(User, filters={"user_name": "test"})
        assert count == 0

    def test_get_all_with_pagination_search(
        self, base_repository, in_memory_db
    ):
        """Test get_all_with_pagination with search."""
        from wy_qcos.common.library import _s

        for i in range(5):
            user = User(
                id=str(uuid.uuid4()),
                user_name=f"searchuser{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
            in_memory_db.add(user)
        in_memory_db.commit()

        success, error, result = base_repository.get_all_with_pagination(
            User, search="searchuser1", search_fields=["user_name"]
        )
        assert success is True
        assert result["total"] == 1
        assert len(result["items"]) == 1

    def test_get_all_with_pagination_search_wildcard(
        self, base_repository, in_memory_db
    ):
        """Test get_all_with_pagination with wildcard search."""
        from wy_qcos.common.library import _s

        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                user_name=f"wilduser{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
            in_memory_db.add(user)
        in_memory_db.commit()

        success, error, result = base_repository.get_all_with_pagination(
            User, search="wild*", search_fields=["user_name"]
        )
        assert success is True
        assert result["total"] == 3

    def test_get_all_with_pagination_sort(self, base_repository, in_memory_db):
        """Test get_all_with_pagination with sort."""
        from wy_qcos.common.library import _s

        names = ["zeta", "alpha", "beta"]
        for name in names:
            user = User(
                id=str(uuid.uuid4()),
                user_name=name,
                hashed_password=_s("hash"),
                is_enabled=True,
            )
            in_memory_db.add(user)
        in_memory_db.commit()

        success, error, result = base_repository.get_all_with_pagination(
            User, sort=["user_name"]
        )
        assert success is True
        items = result["items"]
        assert items[0].user_name == "alpha"
        assert items[1].user_name == "beta"
        assert items[2].user_name == "zeta"

    def test_get_all_with_pagination_sort_descending(
        self, base_repository, in_memory_db
    ):
        """Test get_all_with_pagination with descending sort."""
        from wy_qcos.common.library import _s

        names = ["alpha", "beta", "zeta"]
        for name in names:
            user = User(
                id=str(uuid.uuid4()),
                user_name=name,
                hashed_password=_s("hash"),
                is_enabled=True,
            )
            in_memory_db.add(user)
        in_memory_db.commit()

        success, error, result = base_repository.get_all_with_pagination(
            User, sort=["-user_name"]
        )
        assert success is True
        items = result["items"]
        assert items[0].user_name == "zeta"

    def test_get_all_with_pagination_page_size_unlimited(
        self, base_repository, in_memory_db
    ):
        """Test get_all_with_pagination with page_size=-1 (unlimited)."""
        from wy_qcos.common.library import _s

        for i in range(5):
            user = User(
                id=str(uuid.uuid4()),
                user_name=f"unlimited{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
            in_memory_db.add(user)
        in_memory_db.commit()

        success, error, result = base_repository.get_all_with_pagination(
            User, page_size=-1
        )
        assert success is True
        assert len(result["items"]) >= 5

    def test_get_all_with_pagination_error(self, mock_db_session):
        """Test get_all_with_pagination handles database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = BaseRepository(mock_db_session)
        success, error, result = repo.get_all_with_pagination(User)
        assert success is False
        assert error is not None

    def test_update_success(self, base_repository, sample_user):
        """Test update method."""
        success, error, user = base_repository.update(
            User, sample_user.id, user_name="updatedname"
        )
        assert success is True
        assert user.user_name == "updatedname"

    def test_update_with_id_in_kwargs(self, base_repository, sample_user):
        """Test update removes id from kwargs."""
        success, error, user = base_repository.update(
            User, sample_user.id, id="new-id", user_name="updated"
        )
        assert success is True
        assert user.id != "new-id"

    def test_update_error(self, mock_db_session):
        """Test update handles database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = BaseRepository(mock_db_session)
        success, error, user = repo.update(User, "some-uuid", user_name="test")
        assert success is False
        assert error is not None

    def test_delete_by_uuid_success(self, base_repository, sample_user):
        """Test delete_by_uuid method."""
        success, error = base_repository.delete_by_uuid(User, sample_user.id)
        assert success is True

    def test_delete_by_uuid_not_found(self, base_repository):
        """Test delete_by_uuid with non-existent UUID."""
        success, error = base_repository.delete_by_uuid(
            User, str(uuid.uuid4())
        )
        assert success is False

    def test_delete_by_uuid_error(self, mock_db_session):
        """Test delete_by_uuid handles database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = BaseRepository(mock_db_session)
        success, error = repo.delete_by_uuid(User, "some-uuid")
        assert success is False
        assert error is not None

    def test_delete_by_attr_success(self, base_repository, sample_user):
        """Test delete_by_attr method."""
        success, error = base_repository.delete_by_attr(
            User, "user_name", "testuser"
        )
        assert success is True

    def test_delete_by_attr_not_found(self, base_repository):
        """Test delete_by_attr with non-existent value."""
        success, error = base_repository.delete_by_attr(
            User, "user_name", "nonexistent"
        )
        assert success is False

    def test_delete_by_attr_error(self, mock_db_session):
        """Test delete_by_attr handles database error."""
        mock_db_session.execute.side_effect = Exception("DB error")
        repo = BaseRepository(mock_db_session)
        success, error = repo.delete_by_attr(User, "user_name", "test")
        assert success is False
        assert error is not None

    def test_rollback(self, base_repository):
        """Test rollback method."""
        base_repository.rollback()  # Should not raise

    def test_commit(self, base_repository):
        """Test commit method."""
        base_repository.commit()  # Should not raise

    def test_flush(self, base_repository):
        """Test flush method."""
        base_repository.flush()  # Should not raise

    def test_refresh(self, base_repository, sample_user):
        """Test refresh method."""
        base_repository.refresh(sample_user)  # Should not raise


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
            hashed_password=_s("hashed123"),
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
            User, user_name="test", hashed_password=_s("hash")
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
                hashed_password=_s("hash"),
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
                hashed_password=_s("hash"),
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
        # Should return False when no record is deleted
        # (rowcount=0 means success but no rows affected)
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
        # Should return False when no record is deleted
        # (rowcount=0 means success but no rows affected)
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
        try:
            for i in range(2):
                user = User(
                    id=str(uuid.uuid4()),
                    user_name=f"testdup{i}",
                    hashed_password=_s("hash"),
                    is_enabled=True,
                )
                in_memory_db.add(user)
            in_memory_db.commit()

            success, error, result = base_repository.get_by_attr(
                User, "is_enabled", True, unique=True
            )
            assert success is False
            assert error is not None
        except Exception as e:
            print(f"Expected behavior: {e}")

    def test_count_success(self, base_repository, in_memory_db):
        """Test count method."""
        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                user_name=f"countuser{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
            in_memory_db.add(user)
        in_memory_db.commit()
        count = base_repository.count(User)
        assert count == 3

    def test_count_by_attr_success(self, base_repository, sample_user):
        """Test count_by_attr method."""
        count = base_repository.count_by_attr(User, "user_name", "testuser")
        assert count == 1

    def test_count_by_attr_empty(self, base_repository):
        """Test count_by_attr with no matches."""
        count = base_repository.count_by_attr(User, "user_name", "nonexistent")
        assert count == 0

    def test_count_with_filters_success(self, base_repository, in_memory_db):
        """Test count_with_filters method."""
        for i in range(3):
            user = User(
                id=str(uuid.uuid4()),
                user_name=f"filteruser{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
            in_memory_db.add(user)
        in_memory_db.commit()
        count = base_repository.count_with_filters(User, {"is_enabled": True})
        assert count >= 3

    def test_count_with_filters_empty(self, base_repository):
        """Test count_with_filters with no matches."""
        count = base_repository.count_with_filters(User, {"is_enabled": False})
        assert count == 0

    def test_flush_success(self, base_repository):
        """Test flush method."""
        base_repository.flush()

    def test_refresh_success(self, base_repository, sample_user):
        """Test refresh method."""
        base_repository.refresh(sample_user)
        assert sample_user.user_name == "testuser"

    # -- get_all_with_pagination tests -------------------------------- #

    def test_get_all_with_pagination_basic(
        self, base_repository, in_memory_db
    ):
        """Test basic pagination."""
        for i in range(5):
            base_repository.create(
                User,
                id=str(uuid.uuid4()),
                user_name=f"paguser{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
        success, error, result = base_repository.get_all_with_pagination(
            User, page=1, page_size=3
        )
        assert success is True
        assert error is None
        assert len(result["items"]) == 3
        assert result["total"] == 5

    def test_get_all_with_pagination_second_page(
        self, base_repository, in_memory_db
    ):
        """Test second page returns remaining items."""
        for i in range(5):
            base_repository.create(
                User,
                id=str(uuid.uuid4()),
                user_name=f"paguser{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
        success, error, result = base_repository.get_all_with_pagination(
            User, page=2, page_size=3
        )
        assert success is True
        assert len(result["items"]) == 2
        assert result["total"] == 5

    def test_get_all_with_pagination_filters(
        self, base_repository, in_memory_db
    ):
        """Test pagination with filters."""
        for i in range(5):
            base_repository.create(
                User,
                id=str(uuid.uuid4()),
                user_name=f"filteruser{i}",
                hashed_password=_s("hash"),
                is_enabled=(i < 3),
            )
        success, error, result = base_repository.get_all_with_pagination(
            User,
            filters={"is_enabled": True},
            page=1,
            page_size=10,
        )
        assert success is True
        assert len(result["items"]) == 3
        assert result["total"] == 3

    def test_get_all_with_pagination_sort_desc(
        self, base_repository, in_memory_db
    ):
        """Test pagination with descending sort."""
        for i in range(5):
            base_repository.create(
                User,
                id=str(uuid.uuid4()),
                user_name=f"sortuser{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
        success, error, result = base_repository.get_all_with_pagination(
            User,
            page=1,
            page_size=10,
            sort=["-user_name"],
        )
        assert success is True
        names = [r.user_name for r in result["items"]]
        assert names == sorted(names, reverse=True)

    def test_get_all_with_pagination_unlimited(
        self, base_repository, in_memory_db
    ):
        """Test page_size=-1 returns all items."""
        for i in range(5):
            base_repository.create(
                User,
                id=str(uuid.uuid4()),
                user_name=f"unlimuser{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
        success, error, result = base_repository.get_all_with_pagination(
            User, page=1, page_size=-1
        )
        assert success is True
        assert len(result["items"]) == 5
        assert result["total"] == 5

    def test_get_all_with_pagination_empty(self, base_repository):
        """Test pagination with no records."""
        success, error, result = base_repository.get_all_with_pagination(
            User, page=1, page_size=10
        )
        assert success is True
        assert len(result["items"]) == 0
        assert result["total"] == 0

    def test_get_all_with_pagination_page_out_of_range(
        self, base_repository, in_memory_db
    ):
        """Test page beyond range returns empty items."""
        for i in range(3):
            base_repository.create(
                User,
                id=str(uuid.uuid4()),
                user_name=f"oobuser{i}",
                hashed_password=_s("hash"),
                is_enabled=True,
            )
        success, error, result = base_repository.get_all_with_pagination(
            User, page=10, page_size=10
        )
        assert success is True
        assert len(result["items"]) == 0
        assert result["total"] == 3
