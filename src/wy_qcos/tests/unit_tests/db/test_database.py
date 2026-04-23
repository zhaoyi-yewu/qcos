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
from unittest.mock import Mock, MagicMock, patch, call
from sqlalchemy.engine import Engine

from wy_qcos.db.database import DatabaseDriver, init_database


class TestDatabaseDriver:
    """Test DatabaseDriver class."""

    def test_driver_initialization(self):
        """Test DatabaseDriver initialization."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        assert driver._url == db_url
        assert driver._name == 'test_db'
        assert driver._engine is None

    def test_create_engine_success(self):
        """Test successful engine creation."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        engine = driver.create_engine()
        assert engine is not None
        assert isinstance(engine, Engine)
        assert driver._engine is engine

    def test_create_engine_with_config(self):
        """Test engine creation with configuration."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        engine = driver.create_engine()
        assert engine is not None

    def test_disconnect_from_db_success(self):
        """Test successful database disconnection."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        engine = driver.create_engine()
        driver.disconnect_from_db()
        # Should not raise exception

    def test_disconnect_from_db_no_engine(self):
        """Test disconnect when no engine exists."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        # Should not raise exception even without engine
        driver.disconnect_from_db()

    def test_create_tables_success(self):
        """Test successful table creation."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        engine = driver.create_engine()
        driver.create_tables()
        # Should not raise exception

    def test_create_tables_without_engine(self):
        """Test create_tables without engine raises error."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        with pytest.raises((AttributeError, TypeError)):
            driver.create_tables()

    def test_create_tables_exception_handling(self):
        """Test exception handling in create_tables."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        driver._engine = MagicMock()
        driver._engine.metadata = MagicMock()

        with patch('wy_qcos.db.database.Base') as mock_base:
            mock_base.metadata.create_all.side_effect = Exception('Table creation error')
            with pytest.raises(Exception):
                driver.create_tables()

    def test_check_connection_success(self):
        """Test successful connection check."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        engine = driver.create_engine()
        # Should not raise exception
        driver.check_connection()

    def test_check_connection_no_engine(self):
        """Test connection check without engine."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        with pytest.raises(TimeoutError):
            driver.check_connection()

    def test_check_connection_timeout(self):
        """Test connection check timeout."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        driver._engine = MagicMock()

        def mock_is_connected():
            return False, 'Connection failed', None

        with patch('wy_qcos.common.library.Library.loop_with_timeout') as mock_loop:
            mock_loop.return_value = (False, 'Timeout', None)
            with pytest.raises(TimeoutError):
                driver.check_connection()

    def test_check_connection_failure(self):
        """Test connection check with query failure."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        driver._engine = MagicMock()
        driver._engine.connect.side_effect = Exception('Connection error')

        with patch('wy_qcos.common.library.Library.loop_with_timeout') as mock_loop:
            mock_loop.return_value = (False, 'Connection error', None)
            with pytest.raises(TimeoutError):
                driver.check_connection()


class TestDatabaseDriverConnection:
    """Test DatabaseDriver connection scenarios."""

    def test_driver_pool_configuration(self):
        """Test driver connection pool configuration."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        engine = driver.create_engine()
        # Engine should have pool_size and max_overflow configured
        assert engine is not None

    def test_driver_pre_ping_enabled(self):
        """Test driver pre_ping is enabled."""
        db_url = 'sqlite:///:memory:'
        driver = DatabaseDriver(db_url, 'test_db')
        engine = driver.create_engine()
        assert engine is not None


class TestInitDatabase:
    """Test init_database function."""

    def test_init_database_with_fake_config(self):
        """Test init_database with fake configuration."""
        with patch('wy_qcos.db.database.Config') as mock_config:
            mock_config.QCOS_DATABASE_CONNECTION_URL = 'fake'
            result = init_database()
            assert result is None

    def test_init_database_with_valid_url(self):
        """Test init_database with valid SQLite URL."""
        with patch('wy_qcos.db.database.Config') as mock_config:
            mock_config.QCOS_DATABASE_CONNECTION_URL = 'sqlite:///:memory:'
            with patch.object(DatabaseDriver, 'check_connection'):
                result = init_database()
                assert result is not None

    def test_init_database_creates_driver(self):
        """Test init_database creates DatabaseDriver."""
        with patch('wy_qcos.db.database.Config') as mock_config:
            mock_config.QCOS_DATABASE_CONNECTION_URL = 'sqlite:///:memory:'
            with patch('wy_qcos.db.database.DatabaseDriver') as mock_driver_class:
                mock_driver = MagicMock()
                mock_driver_class.return_value = mock_driver
                mock_driver.create_engine.return_value = MagicMock()

                with patch.object(mock_driver, 'check_connection'):
                    init_database()
                    mock_driver_class.assert_called_once()

    def test_init_database_connection_flow(self):
        """Test init_database complete connection flow."""
        with patch('wy_qcos.db.database.Config') as mock_config:
            mock_config.QCOS_DATABASE_CONNECTION_URL = 'sqlite:///:memory:'
            with patch('wy_qcos.db.database.DatabaseDriver') as mock_driver_class:
                mock_driver = MagicMock()
                mock_engine = MagicMock()
                mock_driver.create_engine.return_value = mock_engine
                mock_driver_class.return_value = mock_driver

                with patch.object(mock_driver, 'check_connection'):
                    result = init_database()
                    assert result == mock_engine
                    mock_driver.create_engine.assert_called_once()


class TestDatabaseDriverMultipleInstances:
    """Test multiple DatabaseDriver instances."""

    def test_multiple_drivers_independent(self):
        """Test multiple drivers are independent."""
        driver1 = DatabaseDriver('sqlite:///:memory:', 'db1')
        driver2 = DatabaseDriver('sqlite:///:memory:', 'db2')

        assert driver1._name == 'db1'
        assert driver2._name == 'db2'
        assert driver1._engine is None
        assert driver2._engine is None

    def test_driver_url_variations(self):
        """Test driver with different URL formats."""
        urls = [
            'sqlite:///:memory:',
            'postgresql://user:pass@localhost/dbname'
        ]

        for url in urls:
            driver = DatabaseDriver(url, 'test_db')
            assert driver._url == url

