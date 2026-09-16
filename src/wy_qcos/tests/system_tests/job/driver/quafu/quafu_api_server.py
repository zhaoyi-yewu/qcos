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

# ruff: noqa: E402
# load driver venv
from wy_qcos.common.config import Config
from wy_qcos.common.library import Library

org_path = Library.set_driver_venv_path("DriverQuafu", Config.DEFAULT.VENV_DIR)

import logging
from aiohttp import web
import socketio


logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(cors_allowed_origins="*")
app = web.Application()
sio.attach(app)
# Quafu Server simulator
task_id = str(Library.create_uuid(prefix=[0xF0]))


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
    response_data = 1
    return web.json_response(response_data)


async def submit_handler(request):
    """Submit task handler."""
    logger.info("submit task request received.")
    return web.json_response(222)


async def get_status_handler(request):
    """Get task status handler."""
    logger.info("get task status request received.")
    response_data = {"status": "Finished"}
    return web.json_response(response_data)


async def get_result_handler(request):
    """Get task result handler."""
    logger.info("get task result request received.")
    response_data = {
        "count": {
            "0000": 399,
            "0001": 19,
            "0010": 18,
            "0011": 29,
            "0100": 4,
            "0101": 1,
            "0110": 3,
            "0111": 34,
            "1000": 38,
            "1001": 4,
            "1010": 4,
            "1011": 16,
            "1100": 38,
            "1101": 11,
            "1110": 45,
            "1111": 361,
        },
        "corrected": {},
        "transpiled": """
                OPENQASM 2.0;
                include "qelib1.inc";
                qreg q[4];
                creg c[4];
                h q[0];
                cx q[0],q[1];
                cx q[1],q[2];
                cx q[2],q[3];
                barrier q[0],q[1],q[2],q[3];
                measure q -> c;

                """,
        "status": "Finished",
        "tid": 2024041917095371986,
        "error": "",
        "finished": "2024-04-19-17-09-48",
        "qlisp": """[('H', 'Q0'),
            ('Cnot', ('Q0', 'Q1')),
            ('Cnot', ('Q1', 'Q2')),
            ('Cnot', ('Q2', 'Q3')),
            ('Barrier', ('Q0', 'Q1', 'Q2', 'Q3')),
            (('Measure', 0), 'Q0'),
            (('Measure', 1), 'Q1'),
            (('Measure', 2), 'Q2'),
            (('Measure', 3), 'Q3')]""",
    }
    return web.json_response(response_data)


def main(port=18606):
    init_logging()

    app.router.add_get("/task/verify", auth_handler)
    app.router.add_post(
        "/task/run/",
        submit_handler,
    )
    app.router.add_get("/task/status/{task_id}", get_status_handler)
    app.router.add_get("/task/result/222", get_result_handler)

    web.run_app(app, host="", port=port)


if __name__ == "__main__":
    main()
