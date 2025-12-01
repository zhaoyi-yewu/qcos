#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.common.library import Library


PID_DIR = "/var/run/qcos"
PID_FILE = f"{PID_DIR}/driver-qboson-api-v2-server.pid"

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(cors_allowed_origins="*")
app = web.Application()
sio.attach(app)
task_id = str(Library.create_uuid(prefix=[0xF0]))


def init_logging():
    """init logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def auth_handler(request):
    """user auth handler."""
    logger.info("auth request received.")
    response_data = {
        "code": "0",
        "msg": "",
        "data": {"token": "eyJhbGc.08FaIo_t-aZ"},
    }
    return web.json_response(response_data)


async def submit_handler(request):
    """submit task handler."""
    logger.info("submit task request received.")
    response_data = {"code": "0", "msg": "", "data": {"task_id": task_id}}
    return web.json_response(response_data)


async def get_status_handler(request):
    """get task status handler."""
    logger.info("get task status request received.")
    response_data = {
        "code": "0",
        "msg": "",
        "data": {
            "task_status": 2,
            "qubo_value": [-109],
            "qubo_solution_data": [-109],
            "visual_data": [80],
        },
    }
    return web.json_response(response_data)


def main():
    init_logging()
    # kill existing process
    Library.kill_pid(PID_FILE)
    Library.mkdir(PID_DIR)
    Library.create_pid_file(PID_FILE)

    app.router.add_post("/sso/access_token/", auth_handler)
    app.router.add_post("/api/system/business/task/", submit_handler)
    app.router.add_get(
        f"/api/system/business/task/{task_id}/", get_status_handler
    )
    web.run_app(app, host="", port=18600)


if __name__ == "__main__":
    main()
