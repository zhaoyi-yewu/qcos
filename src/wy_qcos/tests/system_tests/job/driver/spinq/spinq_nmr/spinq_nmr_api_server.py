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


logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(cors_allowed_origins="*")
app = web.Application()
sio.attach(app)
task_code = "S-260114-0005"
options = None
dev_running_info = {
    "status": "online",
    "details": {
        "calibration": {
            "step": 0.1,
            "shot": 800,
        },
        "device_options_info": {"shot_gap": 0},
    },
}


def init_logging():
    """Init logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def auth_handler(request):
    """User auth handler."""
    logger.info("auth request received.")
    response_data = {
        "status": 200,
        "msg": "",
        "token": "eyJ0eXAiOiJKV1QiLCJhbGc",
        "name": "spinq_visitor_002",
        "hasPassword": True,
    }
    return web.json_response(response_data)


async def submit_handler(request):
    """Submit task handler."""
    logger.info("submit task request received.")
    response_data = {
        "status": 200,
        "msg": "",
        "task": {
            "tid": 52460,
            "tcode": "S-260114-0005",
            "tname": "newapitest1",
            "bitNum": 2,
            "clbitNum": 0,
            "simulator": False,
            "calcMatrix": False,
            "runSimu": True,
            "tstatus": "Q",
            "shots": 1024,
            "sourceType": "spinqit",
            "sourceOriginName": None,
            "sourceAddr": None,
            "sourceCode": None,
            "description": "newapi",
            "createdTime": "2026-01-14T06:17:50.438+0000",
            "startTime": None,
            "endTime": None,
            "errorMsg": None,
            "platformId": 6,
            "platformName": "3Qubit.....................",
            "platformCode": "triangulum_vp",
            "machineId": 9,
            "machineCode": "Triangulum-pro-2",
            "userId": 132,
            "userName": "spinq_visitor_002",
            "timecost": 3.0,
            "curQueueSize": 1,
            "percentageFinished": None,
        },
    }
    return web.json_response(response_data)


async def get_result_handler(request):
    """Get task result handler."""
    logger.info("get task result request received.")
    response_data = {
        "status": 200,
        "msg": "",
        "taskStatus": "S",
        "taskErrMsg": None,
        "run": {
            "realMatrix": None,
            "imagMatrix": None,
            "module": [0.38491875, 0.03018464, 0.02448768, 0.56040894],
        },
    }
    return web.json_response(response_data)


async def calibrate_handler(request):
    """Calibrate handler."""
    logger.info("calibrate device request received.")
    response_data = {
        "status": 200,
        "msg": "",
        "result": "calibrate request recvd.",
        "taskErrMsg": None,
    }
    return web.json_response(response_data)


async def set_device_options_handler(request):
    """Set device options handler."""
    logger.info("Set device options request received")
    if request.body_exists:
        data = await request.json()
        options = data.get("options", None)
        if options is not None and len(options) != 0:
            dev_running_info["details"]["device_options_info"] = options
            logger.info(f"options: {options}")

    response_data = {
        "status": 200,
        "msg": "",
        "result": "set device option request rcvd",
        "taskErrMsg": None,
    }
    return web.json_response(response_data)


async def fetch_running_info_handler(request):
    """fetch_running_info_handler handler."""
    logger.info("fetch_running_info_handlers request received.")
    response_data = {
        "status": 200,
        "msg": "",
        "result": dev_running_info,
        "taskErrMsg": None,
    }
    return web.json_response(response_data)


def main(port=18602):
    init_logging()

    app.router.add_post("/user/spinqit/login", auth_handler)
    app.router.add_post("/task/user/create", submit_handler)
    app.router.add_get(
        "/task/user/getTaskRunResultByTcode",
        get_result_handler,
    )
    app.router.add_post("/calibrate", calibrate_handler)
    app.router.add_post("/set_device_options", set_device_options_handler)
    app.router.add_post("/fetch_running_info", fetch_running_info_handler)
    web.run_app(app, host="", port=port)


if __name__ == "__main__":
    main()
