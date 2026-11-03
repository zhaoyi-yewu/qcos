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

"""Mock SpinQ Cloud REST API server for spinq_sqc_25 system tests.

The spinqit SDK (``SpinQCloudClient`` / ``SpinQSession``) talks to SpinQ
Cloud via plain HTTP using ``requests.Session``.  This aiohttp server
mimics the four endpoints exercised by ``DriverSpinqBase``:

  POST /user/spinqit/login
  GET  /platform/spinqit/getPlatformListV2
  POST /task/user/create
  GET  /task/user/getTaskRunResultByTcodeV2

plus the machine-spec endpoint used by ``fetch_running_info`` (device
monitor).  The application object is created **inside** ``main()`` so
that Windows multiprocessing spawn re-imports the module cleanly.
"""

import logging

from aiohttp import web

logger = logging.getLogger(__name__)

# -- mock data -----------------------------------------------------------

_TOKEN = "mock-spinq-cloud-token"
_TASK_CODE = "mock-task-code-0001"

# The circuit under test (simple-qasm.qasm) applies X to q[0] and q[1],
# so the expected measurement is "11" with 100% probability.
_RESULT_COUNTS = {"11": 1024}
_RESULT_PROBABILITIES = {"11": 1.0}
_RESULT_SHOTS = 1024

# 1-based coupling map (API format).  Keys/values are 1-based strings;
# the SDK converts to 0-based tuples.  We provide a minimal subset that
# includes qubits 0 and 1, which is sufficient for the 2-qubit test
# circuit.  The full 25-qubit topology lives in the st-conf.d config.
_COUPLING_MAP_1BASED = {
    "1": ["2"],
    "2": ["1", "3"],
    "3": ["2", "4"],
    "4": ["3"],
}

# Gate names understood by spinqit's ``find_gate`` (see
# spinqit.model.spinqCloud.gate.base_gate_list).  Unknown names are
# silently skipped by the SDK, so we list the gates the driver
# supports.
_SUPPORT_GATE_NAMES = [
    "H",
    "I",
    "X",
    "Y",
    "Z",
    "CNOT",
    "Rx",
    "Ry",
    "Rz",
    "T",
    "Td",
    "S",
    "Sd",
    "U",
]


def _init_logging():
    """Init logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# -- handlers ------------------------------------------------------------


async def login_handler(request: web.Request) -> web.Response:
    """POST /user/spinqit/login -- return an access token."""
    logger.info("login request received")
    return web.json_response({"token": _TOKEN})


async def get_platform_list_handler(request: web.Request) -> web.Response:
    """GET /platform/spinqit/getPlatformListV2 -- return platform list."""
    logger.info("getPlatformListV2 request received")
    platform = {
        "pcode": "sqc_25_vp",
        "pname": "SQC-25",
        "maxBitNum": 25,
        "countOnlineMachine": 1,
        "supportGateName": _SUPPORT_GATE_NAMES,
        "couplingMap": _COUPLING_MAP_1BASED,
        "simu": False,
    }
    return web.json_response({"items": [platform]})


async def create_task_handler(request: web.Request) -> web.Response:
    """POST /task/user/create -- create a task and return its code."""
    body = await request.text()
    logger.info("create task request received: %s", body[:200])
    return web.json_response({
        "status": 200,
        "msg": "success",
        "task": {"tcode": _TASK_CODE},
    })


async def get_task_result_handler(request: web.Request) -> web.Response:
    """GET /task/user/getTaskRunResultByTcodeV2 -- return run result."""
    task_code = request.query.get("taskCode", "")
    logger.info("getTaskRunResultByTcodeV2 request received: %s", task_code)
    return web.json_response({
        "taskStatus": "S",
        "run": {
            "module": _RESULT_PROBABILITIES,
            "count": _RESULT_COUNTS,
        },
        "shots": _RESULT_SHOTS,
    })


async def get_machine_spec_handler(request: web.Request) -> web.Response:
    """GET /machine/getLatestMachineSpec -- return machine spec."""
    machine_code = request.query.get("machineCode", "")
    logger.info("getLatestMachineSpec request received: %s", machine_code)
    return web.json_response({
        "status": 200,
        "item": {
            "maxBitNum": 25,
            "singleQubitSpec": {
                "1": {"t1": 120.0, "t2": 90.0, "f_ro": 0.98},
                "2": {"t1": 110.0, "t2": 85.0, "f_ro": 0.97},
            },
            "dualQubitsSpec": {
                "1_2": {"f_cz": 0.95},
            },
            "curCouplingMap": _COUPLING_MAP_1BASED,
            "latestReviseTime": "2026-08-27T00:00:00",
        },
    })


# -- entry point ---------------------------------------------------------


def main(port=18625):
    """Start the mock SpinQ Cloud API server."""
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
