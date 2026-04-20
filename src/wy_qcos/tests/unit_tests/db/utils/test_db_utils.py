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
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from wy_qcos.db.utils.db_utils import (
    get_db_session,
    get_repository,
    create_db_session
)
from wy_qcos.db.repositories.base import BaseRepository
from wy_qcos.db.repositories.user import UserRepository


class TestGetDbSession:
    """Test get_db_session function."""

    def test_get_db_session_creation(self):
        """Test db session creation."""
        mock_app = MagicMock()
        mock_engine = MagicMock()
        mock_app.state._db_engine = mock_engine

        mock_request = MagicMock()
        mock_request.app = mock_app

        # Mock Session to avoid actual database connection
        with patch('wy_qcos.db.utils.db_utils.Session') as mock_session_class:
            mock_session_instance = MagicMock(spec=Session)
            mock_session_class.return_value = mock_session_instance

            gen = get_db_session(mock_request)
            session = next(gen)

            assert session is not None
            assert mock_session_class.called

    def test_get_db_session_cleanup(self):
        """Test db session cleanup on exit."""
        mock_app = MagicMock()
        mock_engine = MagicMock()
        mock_app.state._db_engine = mock_engine

        mock_request = MagicMock()
        mock_request.app = mock_app

        with patch('wy_qcos.db.utils.db_utils.Session') as mock_session_class:
            mock_session_instance = MagicMock(spec=Session)
            mock_session_class.return_value = mock_session_instance

            gen = get_db_session(mock_request)
            session = next(gen)

            try:
                gen.send(None)
            except StopIteration:
                pass

            mock_session_instance.close.assert_called_once()


class TestGetRepository:
    """Test get_repository function."""

    def test_get_repository_returns_function(self):
        """Test get_repository returns a function."""
        repo_getter = get_repository(UserRepository)
        assert callable(repo_getter)

    def test_get_repository_creation(self):
        """Test repository creation through get_repository."""
        repo_getter = get_repository(UserRepository)

        mock_session = MagicMock(spec=Session)
        result = repo_getter(db_session=mock_session)

        assert isinstance(result, UserRepository)
        assert result._db_session == mock_session

    def test_get_repository_with_base_repository(self):
        """Test get_repository with BaseRepository."""
        repo_getter = get_repository(BaseRepository)

        mock_session = MagicMock(spec=Session)
        result = repo_getter(db_session=mock_session)

        assert isinstance(result, BaseRepository)


class TestCreateDbSession:
    """Test create_db_session context manager."""

    def test_create_db_session_context(self):
        """Test context manager creation."""
        mock_engine = MagicMock()

        with patch('wy_qcos.db.utils.db_utils.Session') as mock_session_class:
            mock_session_instance = MagicMock(spec=Session)
            mock_session_class.return_value = mock_session_instance

            with create_db_session(mock_engine) as session:
                assert session is not None

    def test_create_db_session_cleanup(self):
        """Test context manager cleanup."""
        mock_engine = MagicMock()

        with patch('wy_qcos.db.utils.db_utils.Session') as mock_session_class:
            mock_session_instance = MagicMock(spec=Session)
            mock_session_class.return_value = mock_session_instance

            with create_db_session(mock_engine) as session:
                pass

            mock_session_instance.close.assert_called_once()

    def test_create_db_session_with_exception(self):
        """Test context manager cleanup on exception."""
        mock_engine = MagicMock()

        with patch('wy_qcos.db.utils.db_utils.Session') as mock_session_class:
            mock_session_instance = MagicMock(spec=Session)
            mock_session_class.return_value = mock_session_instance

            try:
                with create_db_session(mock_engine) as session:
                    raise ValueError('Test exception')
            except ValueError:
                pass

            mock_session_instance.close.assert_called_once()

    def test_create_db_session_expire_on_commit(self):
        """Test session is created with expire_on_commit=False."""
        mock_engine = MagicMock()

        with patch('wy_qcos.db.utils.db_utils.Session') as mock_session_class:
            mock_session_instance = MagicMock(spec=Session)
            mock_session_class.return_value = mock_session_instance

            with create_db_session(mock_engine) as session:
                # Verify Session was called with expire_on_commit=False
                mock_session_class.assert_called_once_with(
                    mock_engine,
                    expire_on_commit=False
                )

    def test_create_db_session_multiple_usage(self):
        """Test multiple context manager usage."""
        mock_engine = MagicMock()

        with patch('wy_qcos.db.utils.db_utils.Session') as mock_session_class:
            mock_session_instance1 = MagicMock(spec=Session)
            mock_session_instance2 = MagicMock(spec=Session)
            mock_session_class.side_effect = [
                mock_session_instance1,
                mock_session_instance2
            ]

            with create_db_session(mock_engine) as session1:
                assert session1 is not None

            with create_db_session(mock_engine) as session2:
                assert session2 is not None

            assert mock_session_instance1.close.called
            assert mock_session_instance2.close.called

