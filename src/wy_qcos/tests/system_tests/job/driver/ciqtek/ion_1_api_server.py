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

import logging

from aiohttp import web
import socketio

from wy_qcos.common.library import Library


logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(cors_allowed_origins="*")
app = web.Application()
sio.attach(app)
task_id = str(Library.create_uuid(prefix=[0xF0]))
access_token = str(Library.create_uuid(prefix=[0xF0]))


def init_logging():
    """Init logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def get_token_handler(request):
    """Get token handler."""
    logger.info("get token request received.")
    response_data = {
        "code": 10000,
        "msg": "请求成功",
        "data": {
            "access_token": access_token,
            "expires_in": 7200,
        },
    }
    return web.json_response(response_data)


async def refresh_token_handler(request):
    """Refresh token handler."""
    logger.info("refresh token request received.")
    response_data = {
        "code": 10000,
        "msg": "请求成功",
        "data": {
            "access_token": access_token,
            "expires_in": 7200,
        },
    }
    return web.json_response(response_data)


async def submit_handler(request):
    """Submit task handler."""
    logger.info("submit task request received.")
    response_data = {
        "code": 10000,
        "msg": "请求成功",
        "data": {
            "experimentId": task_id,
        },
    }
    return web.json_response(response_data)


async def get_result_handler(request):
    """Get task result handler."""
    logger.info("get task result request received.")
    response_data = {
        "code": 10000,
        "msg": "请求成功",
        "data": {
            "experimentId": task_id,
            "outerExperimentId": "string",
            "status": 2,
            "message": "string",
            "deviceId": "string",
            "notifyUrl": "string",
            "operationPeriod": 10,
            "originalCaptureFile": "http://files.server.com/a/b/capture.tgz",
            "originalCount": 1000,
            "result": [
                {"name": "00", "value": 0.25},
                {"name": "01", "value": 0.25},
                {"name": "10", "value": 0.25},
                {"name": "11", "value": 0.25},
            ],
        },
    }
    return web.json_response(response_data)


def main(port=18605):
    init_logging()

    app.router.add_post("/control/v1/token", get_token_handler)
    app.router.add_post("/control/v1/token/refresh", refresh_token_handler)
    app.router.add_post("/control/v1/experiment/submit", submit_handler)
    app.router.add_get("/control/v1/experiment/get", get_result_handler)
    web.run_app(app, host="", port=port)


if __name__ == "__main__":
    main()
