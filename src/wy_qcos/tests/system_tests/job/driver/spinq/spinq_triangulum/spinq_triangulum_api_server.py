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

# ruff: noqa: S105

"""Mock SpinQ Cloud REST API server for spinq_triangulum system tests.

Mimics the SpinQ Cloud API endpoints exercised by
DriverSpinQTriangulum.  Triangulum is a 3-qubit NMR device with
singleQubitSpec containing freq only (no t1/t2/f_ro),
curCouplingMap=null (falls back to designedCouplingMap), and
dualQubitsSpec=null.
"""

import logging

from aiohttp import web

logger = logging.getLogger(__name__)

# -- mock data -----------------------------------------------------------

_TOKEN = "mock-triangulum-token"
_TASK_CODE = "mock-triangulum-task-0001"

_RESULT_COUNTS = {"11": 1024}
_RESULT_PROBABILITIES = {"11": 1.0}
_RESULT_SHOTS = 1024

# 3-qubit NMR topology (1-based, fully connected)
_COUPLING_MAP_1BASED = {
    "1": [2, 3],
    "2": [1, 3],
    "3": [1, 2],
}

_SUPPORT_GATE_NAMES = [
    "H",
    "I",
    "X",
    "Y",
    "Z",
    "U",
    "Rx",
    "Ry",
    "Rz",
    "T",
    "Td",
    "CNOT",
    "CZ",
]


def _init_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# -- handlers ------------------------------------------------------------


async def login_handler(request: web.Request) -> web.Response:
    logger.info("login request received")
    return web.json_response({"token": _TOKEN})


async def get_platform_list_handler(request: web.Request) -> web.Response:
    logger.info("getPlatformListV2 request received")
    platform = {
        "pcode": "triangulum_vp",
        "pname": "Triangulum",
        "maxBitNum": 3,
        "countOnlineMachine": 1,
        "supportGateName": _SUPPORT_GATE_NAMES,
        "couplingMap": _COUPLING_MAP_1BASED,
        "simu": False,
    }
    return web.json_response({"items": [platform]})


async def create_task_handler(request: web.Request) -> web.Response:
    body = await request.text()
    logger.info("create task request received: %s", body[:200])
    return web.json_response({
        "status": 200,
        "msg": "success",
        "task": {"tcode": _TASK_CODE},
    })


async def get_task_result_handler(request: web.Request) -> web.Response:
    task_code = request.query.get("taskCode", "")
    logger.info("getTaskRunResultByTcodeV2: %s", task_code)
    return web.json_response({
        "taskStatus": "S",
        "run": {
            "module": _RESULT_PROBABILITIES,
            "count": _RESULT_COUNTS,
        },
        "shots": _RESULT_SHOTS,
    })


async def get_machine_spec_handler(request: web.Request) -> web.Response:
    machine_code = request.query.get("machineCode", "")
    logger.info("getLatestMachineSpec: %s", machine_code)
    return web.json_response({
        "status": 200,
        "item": {
            "maxBitNum": 3,
            "singleQubitSpec": {
                "1": {"freq": 35944856.75},
                "2": {"freq": 35946089.75},
                "3": {"freq": 35946951.75},
            },
            "dualQubitsSpec": None,
            "curCouplingMap": None,
            "designedCouplingMap": _COUPLING_MAP_1BASED,
            "latestReviseTime": "2026-10-31T05:31:55",
        },
    })


# -- entry point ---------------------------------------------------------


def main(port=18627):
    _init_logging()
    app = web.Application()
    app.router.add_post("/user/spinqit/login", login_handler)
    app.router.add_get(
        "/platform/spinqit/getPlatformListV2", get_platform_list_handler
    )
    app.router.add_post("/task/user/create", create_task_handler)
    app.router.add_get(
        "/task/user/getTaskRunResultByTcodeV2", get_task_result_handler
    )
    app.router.add_get(
        "/machine/getLatestMachineSpec", get_machine_spec_handler
    )
    web.run_app(app, host="", port=port)


if __name__ == "__main__":
    main()
