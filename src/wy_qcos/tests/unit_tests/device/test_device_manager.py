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

"""Unit tests for DeviceManager."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from wy_qcos.device.device_manager import DeviceManager


class TestDeviceManagerInit:
    """Test DeviceManager initialization."""

    def test_init(self):
        """Test DeviceManager init."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url") as mock_redis:
            mock_redis.return_value = MagicMock()
            mgr = DeviceManager(config, driver_manager)
            assert mgr.config == config
            assert mgr.driver_manager == driver_manager
            assert mgr.devices == {}
            mock_redis.assert_called_once_with(
                "redis://localhost:6379/0", decode_responses=True, protocol=2
            )


class TestDeviceManagerLoadDevices:
    """Test DeviceManager load_devices method."""

    def _make_manager(self, device_list=None, extra_configs=None):
        """Create a DeviceManager with mocked config."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        config.DEVICES.DEVICE_LIST = device_list or []
        config.get_extra_configs.return_value = extra_configs or {}
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url"):
            mgr = DeviceManager(config, driver_manager)
        return mgr

    def test_load_devices_empty_list(self):
        """Test load_devices with empty device list."""
        mgr = self._make_manager(device_list=[])
        mgr.load_devices()
        assert mgr.devices == {}

    def test_load_devices_no_config(self):
        """Test load_devices when device config is missing."""
        mgr = self._make_manager(device_list=["dev1"], extra_configs={})
        mgr.load_devices()
        assert mgr.devices == {}

    def test_load_devices_invalid_schema(self):
        """Test load_devices with invalid device config schema."""
        mgr = self._make_manager(
            device_list=["dev1"],
            extra_configs={"dev1": {"driver": 123}},  # driver should be str
        )
        mgr.load_devices()
        assert mgr.devices == {}

    def test_load_devices_driver_not_found(self):
        """Test load_devices when driver is not found."""
        mgr = self._make_manager(
            device_list=["dev1"],
            extra_configs={"dev1": {"driver": "dummy"}},
        )
        mgr.driver_manager.get_driver.return_value = None
        mgr.load_devices()
        assert mgr.devices == {}

    def test_load_devices_success(self):
        """Test load_devices successfully."""
        mock_driver = MagicMock()
        mock_driver.validate_driver_configs.return_value = (True, None)

        mgr = self._make_manager(
            device_list=["dev1"],
            extra_configs={
                "dev1": {
                    "driver": "dummy",
                    "alias_name": "Dev One",
                    "description": "Test device",
                    "enable": True,
                    "device_max_qubits": 10,
                }
            },
        )
        mgr.driver_manager.get_driver.return_value = mock_driver

        with patch("wy_qcos.device.device_manager.Device") as mock_device_cls:
            mock_device = MagicMock()
            mock_device_cls.return_value = mock_device
            mgr.load_devices()

            assert "dev1" in mgr.devices
            mock_device.set_alias_name.assert_called_once_with("Dev One")
            mock_device.set_description.assert_called_once_with("Test device")
            mock_device.set_max_qubits.assert_called_once_with(10)
            mock_device.set_enable.assert_called_once_with(True)

    def test_load_devices_driver_config_invalid(self):
        """Test load_devices with invalid driver config."""
        mock_driver = MagicMock()
        mock_driver.validate_driver_configs.return_value = (
            False,
            "Invalid config",
        )

        mgr = self._make_manager(
            device_list=["dev1"],
            extra_configs={"dev1": {"driver": "dummy"}},
        )
        mgr.driver_manager.get_driver.return_value = mock_driver

        mgr.load_devices()
        assert mgr.devices == {}

    def test_load_devices_with_device_monitor(self):
        """Test load_devices with device_monitor config."""
        mock_driver = MagicMock()
        mock_driver.validate_driver_configs.return_value = (True, None)

        mgr = self._make_manager(
            device_list=["dev1"],
            extra_configs={
                "dev1": {
                    "driver": "dummy",
                    "device_monitor": {"enable_device_monitor": True},
                }
            },
        )
        mgr.driver_manager.get_driver.return_value = mock_driver

        with patch("wy_qcos.device.device_manager.Device") as mock_device_cls:
            mock_device = MagicMock()
            mock_device_cls.return_value = mock_device
            mgr.load_devices()
            mock_device.set_enable_device_monitor.assert_called_once_with(True)


class TestDeviceManagerCheckRedisConnection:
    """Test DeviceManager check_redis_connection method."""

    def test_check_redis_connection_success(self):
        """Test check_redis_connection success."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url") as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis.return_value = mock_redis_instance
            mgr = DeviceManager(config, driver_manager)

            with patch.object(mgr.redis_instance, "ping", return_value=True):
                mgr.check_redis_connection()

    def test_check_redis_connection_timeout(self):
        """Test check_redis_connection timeout."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url") as mock_redis:
            mock_redis_instance = MagicMock()
            mock_redis.return_value = mock_redis_instance
            mgr = DeviceManager(config, driver_manager)

            with patch(
                "wy_qcos.device.device_manager.Library.loop_with_timeout",
                return_value=(False, "timeout", None),
            ):
                with pytest.raises(TimeoutError):
                    mgr.check_redis_connection()


class TestDeviceManagerInitDevices:
    """Test DeviceManager init_devices method."""

    def test_init_devices(self):
        """Test init_devices."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url"):
            mgr = DeviceManager(config, driver_manager)

        mock_device = MagicMock()
        mock_device.enable = True
        mock_device.get_enable_device_monitor.return_value = False
        mock_device.init_device.return_value = (True, None)
        mock_device.show_device_info.return_value = "Device Info"
        mgr.devices = {"dev1": mock_device}

        with patch.object(mgr, "check_redis_connection"):
            with patch.object(mgr, "subscribe_device_info"):
                mgr.init_devices()

        mock_device.set_status.assert_called_once_with(
            mock_device.DEVICE_STATUS_ONLINE
        )
        mock_device.init_device.assert_called_once()

    def test_init_devices_disabled(self):
        """Test init_devices with disabled device."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url"):
            mgr = DeviceManager(config, driver_manager)

        mock_device = MagicMock()
        mock_device.enable = False
        mock_device.init_device.return_value = (True, None)
        mock_device.show_device_info.return_value = "Device Info"
        mgr.devices = {"dev1": mock_device}

        with patch.object(mgr, "check_redis_connection"):
            with patch.object(mgr, "subscribe_device_info"):
                mgr.init_devices()

        mock_device.set_status.assert_called_once_with(
            mock_device.DEVICE_STATUS_OFFLINE
        )

    def test_init_devices_init_error(self):
        """Test init_devices with device init error."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url"):
            mgr = DeviceManager(config, driver_manager)

        mock_device = MagicMock()
        mock_device.enable = True
        mock_device.get_enable_device_monitor.return_value = False
        mock_device.init_device.return_value = (False, "Init failed")
        mock_device.show_device_info.return_value = "Device Info"
        mgr.devices = {"dev1": mock_device}

        with patch.object(mgr, "check_redis_connection"):
            with patch.object(mgr, "subscribe_device_info"):
                mgr.init_devices()

        mock_device.set_enable.assert_called_once_with(False)
        mock_device.set_status.assert_called_with(
            mock_device.DEVICE_STATUS_OFFLINE
        )


class TestDeviceManagerInitDb:
    """Test DeviceManager init_db method."""

    def test_init_db_existing_state(self):
        """Test init_db with existing device state."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url"):
            mgr = DeviceManager(config, driver_manager)

        mock_device = MagicMock()
        mock_device.name = "dev1"
        mgr.devices = {"dev1": mock_device}

        mock_repo = MagicMock()
        mock_repo.load_all_device_states.return_value = (
            True,
            None,
            {"dev1": "online"},
        )

        with patch(
            "wy_qcos.device.device_manager.create_db_session"
        ) as mock_session:
            mock_session.return_value.__enter__.return_value = MagicMock()
            with patch(
                "wy_qcos.device.device_manager.DeviceRepository",
                return_value=mock_repo,
            ):
                result = mgr.init_db(MagicMock())
                assert result == mock_repo
                mock_device.set_state.assert_called_once_with("online")

    def test_init_db_new_device(self):
        """Test init_db with new device."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url"):
            mgr = DeviceManager(config, driver_manager)

        mock_device = MagicMock()
        mock_device.name = "dev1"
        mgr.devices = {"dev1": mock_device}

        mock_repo = MagicMock()
        mock_repo.load_all_device_states.return_value = (True, None, {})
        mock_repo.upsert_device_state.return_value = (True, None, None)

        with patch(
            "wy_qcos.device.device_manager.create_db_session"
        ) as mock_session:
            mock_session.return_value.__enter__.return_value = MagicMock()
            with patch(
                "wy_qcos.device.device_manager.DeviceRepository",
                return_value=mock_repo,
            ):
                result = mgr.init_db(MagicMock())
                assert result == mock_repo
                mock_repo.upsert_device_state.assert_called_once()

    def test_init_db_load_error(self):
        """Test init_db with load error."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url"):
            mgr = DeviceManager(config, driver_manager)

        mock_device = MagicMock()
        mock_device.name = "dev1"
        mgr.devices = {"dev1": mock_device}

        mock_repo = MagicMock()
        mock_repo.load_all_device_states.return_value = (
            False,
            "DB error",
            None,
        )
        mock_repo.upsert_device_state.return_value = (True, None, None)

        with patch(
            "wy_qcos.device.device_manager.create_db_session"
        ) as mock_session:
            mock_session.return_value.__enter__.return_value = MagicMock()
            with patch(
                "wy_qcos.device.device_manager.DeviceRepository",
                return_value=mock_repo,
            ):
                result = mgr.init_db(MagicMock())
                assert result == mock_repo


class TestDeviceManagerDeviceAccessors:
    """Test DeviceManager device accessor methods."""

    def test_has_device(self):
        """Test has_device."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url"):
            mgr = DeviceManager(config, driver_manager)

        mgr.devices = {"dev1": MagicMock()}
        assert mgr.has_device("dev1") is True
        assert mgr.has_device("dev2") is False

    def test_get_device(self):
        """Test get_device."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url"):
            mgr = DeviceManager(config, driver_manager)

        mock_device = MagicMock()
        mgr.devices = {"dev1": mock_device}
        assert mgr.get_device("dev1") == mock_device
        assert mgr.get_device("dev2") is None

    def test_get_devices(self):
        """Test get_devices."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url"):
            mgr = DeviceManager(config, driver_manager)

        mgr.devices = {"dev1": MagicMock(), "dev2": MagicMock()}
        devices = mgr.get_devices()
        assert len(devices) == 2
        assert "dev1" in devices
        assert "dev2" in devices


class TestDeviceManagerSubscribeDeviceInfo:
    """Test DeviceManager subscribe_device_info method."""

    def test_subscribe_device_info(self):
        """Test subscribe_device_info."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url"):
            mgr = DeviceManager(config, driver_manager)

        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        mock_device = MagicMock()
        mock_device.name = "dev1"

        # Simulate one message then stop
        messages = [
            {
                "type": "message",
                "channel": "/qcos/device_running_info/dev1",
                "data": '{"qubits": 10}',
            },
            {"type": "subscribe"},
        ]
        mock_pubsub.listen.return_value = iter(messages)

        # Run in a thread and stop after a short delay
        def run_subscribe():
            mgr.subscribe_device_info(mock_redis, mock_device)

        thread = threading.Thread(target=run_subscribe)
        thread.daemon = True
        thread.start()
        thread.join(timeout=1)

        mock_pubsub.subscribe.assert_called_once_with(
            "/qcos/device_running_info/dev1"
        )
        mock_device.set_device_running_info.assert_called_once_with({
            "qubits": 10
        })

    def test_subscribe_device_info_bytes_channel(self):
        """Test subscribe_device_info with bytes channel."""
        config = MagicMock()
        config.REDIS.REDIS_URL = "redis://localhost:6379/0"
        driver_manager = MagicMock()

        with patch("redis.Redis.from_url"):
            mgr = DeviceManager(config, driver_manager)

        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub

        mock_device = MagicMock()
        mock_device.name = "dev1"

        messages = [
            {
                "type": "message",
                "channel": b"/qcos/device_running_info/dev1",
                "data": '{"qubits": 10}',
            },
        ]
        mock_pubsub.listen.return_value = iter(messages)

        def run_subscribe():
            mgr.subscribe_device_info(mock_redis, mock_device)

        thread = threading.Thread(target=run_subscribe)
        thread.daemon = True
        thread.start()
        thread.join(timeout=1)

        mock_device.set_device_running_info.assert_called_once_with({
            "qubits": 10
        })
