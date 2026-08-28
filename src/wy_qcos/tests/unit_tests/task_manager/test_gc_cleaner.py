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

"""Unit tests for GcCleaner."""

import gc
import pytest

from unittest.mock import MagicMock, patch

from wy_qcos.task_manager.gc_cleaner import GcCleaner


class TestGcCleaner:
    """Tests for GcCleaner periodic GC service."""

    def test_init_defaults(self):
        """GcCleaner initializes with default config."""
        cleaner = GcCleaner()
        assert cleaner._running is False
        assert cleaner._interval_days is not None

    @pytest.mark.asyncio
    @patch("wy_qcos.task_manager.gc_cleaner.AsyncIOScheduler")
    async def test_start_disabled(self, mock_scheduler_cls):
        """start() does nothing when GC_INTERVAL == -1."""
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler

        cleaner = GcCleaner()
        cleaner._interval_days = -1
        await cleaner.start()
        assert cleaner._running is True
        # scheduler should not have been started
        mock_scheduler.start.assert_not_called()

    @pytest.mark.asyncio
    @patch("wy_qcos.task_manager.gc_cleaner.AsyncIOScheduler")
    async def test_start_normal(self, mock_scheduler_cls):
        """start() adds a job when interval is positive."""
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler

        cleaner = GcCleaner()
        cleaner._interval_days = 1
        await cleaner.start()
        assert cleaner._running is True
        mock_scheduler.start.assert_called_once()
        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args
        assert call_kwargs.kwargs.get("id") == "gc_clean"
        assert call_kwargs.kwargs.get("replace_existing") is True

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """start() returns early if already running."""
        cleaner = GcCleaner()
        cleaner._running = True
        cleaner._scheduler = MagicMock()
        await cleaner.start()
        cleaner._scheduler.start.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """stop() returns early if not running."""
        cleaner = GcCleaner()
        cleaner._running = False
        cleaner._scheduler = MagicMock()
        await cleaner.stop()
        cleaner._scheduler.shutdown.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_running(self):
        """stop() shuts down scheduler when running."""
        cleaner = GcCleaner()
        cleaner._running = True
        cleaner._scheduler = MagicMock()
        await cleaner.stop()
        cleaner._scheduler.shutdown.assert_called_once_with(wait=True)
        assert cleaner._running is False

    @pytest.mark.asyncio
    async def test_stop_shutdown_error(self):
        """stop() logs warning if shutdown raises."""
        cleaner = GcCleaner()
        cleaner._running = True
        cleaner._scheduler = MagicMock()
        cleaner._scheduler.shutdown.side_effect = Exception("shutdown err")
        await cleaner.stop()
        assert cleaner._running is False

    def test_do_gc_not_running(self):
        """_do_gc returns early if not running."""
        cleaner = GcCleaner()
        cleaner._running = False
        with patch.object(gc, "collect") as mock_collect:
            cleaner._do_gc()
            mock_collect.assert_not_called()

    @patch("wy_qcos.task_manager.gc_cleaner.Library.malloc_trim")
    @patch("wy_qcos.task_manager.gc_cleaner.gc.collect")
    def test_do_gc_normal(self, mock_collect, mock_trim):
        """_do_gc runs gc.collect and malloc_trim when running."""
        mock_collect.return_value = 42
        mock_trim.return_value = 0

        cleaner = GcCleaner()
        cleaner._running = True
        cleaner._do_gc()

        mock_collect.assert_called_once_with(2)
        mock_trim.assert_called_once_with(0)

    @patch("wy_qcos.task_manager.gc_cleaner.Library.malloc_trim")
    @patch("wy_qcos.task_manager.gc_cleaner.gc.collect")
    def test_do_gc_trim_none(self, mock_collect, mock_trim):
        """_do_gc handles malloc_trim returning None."""
        mock_collect.return_value = 0
        mock_trim.return_value = None

        cleaner = GcCleaner()
        cleaner._running = True
        cleaner._do_gc()

        mock_collect.assert_called_once_with(2)
        mock_trim.assert_called_once_with(0)

    @patch("wy_qcos.task_manager.gc_cleaner.Library.malloc_trim")
    @patch("wy_qcos.task_manager.gc_cleaner.gc.collect")
    def test_do_gc_exception(self, mock_collect, mock_trim):
        """_do_gc logs error on exception."""
        mock_collect.side_effect = Exception("gc error")

        cleaner = GcCleaner()
        cleaner._running = True
        # should not raise
        cleaner._do_gc()

        mock_collect.assert_called_once_with(2)
