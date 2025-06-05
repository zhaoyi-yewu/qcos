#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import asyncio
import logging

from typing import Callable
from fastapi import FastAPI

logger = logging.getLogger(__name__)


def create_startup_handler(app: FastAPI) -> Callable:
    """
    Tasks to be performed when the server is starting.
    """
    async def start_app() -> None:
        loop = asyncio.get_event_loop()
        logger = logging.getLogger("asyncio")
        logger.setLevel(logging.ERROR)

        if logger.getEffectiveLevel() == logging.DEBUG:
            # On debug version we enable info that
            # coroutine is not called in a way await/await
            loop.set_debug(True)

    return start_app


def create_shutdown_handler(app: FastAPI) -> Callable:
    """
    Tasks to be performed when the server is exiting.
    """

    async def shutdown_handler() -> None:
        # await database.disconnect_from_db(app)
        # await HTTPClient.close_session()
        pass

    return shutdown_handler
