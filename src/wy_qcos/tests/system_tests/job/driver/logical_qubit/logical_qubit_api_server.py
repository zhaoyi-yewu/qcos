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

org_path = Library.set_driver_venv_path(
    "logical_qubit", Config.DEFAULT.VENV_DIR
)

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


async def get_backends_handler(request):
    """User auth handler."""
    logger.info("auth request received.")
    response_data = {
        "backends": [
            {
                "name": "MQ02",
                "status": "active",
                "qubits": 72,
                "type": "real_qpu",
                "chip_architecture": "72bit",
                "supported_modes": ["circuit", "script"],
                "supported_measurement_types": ["measure"],
                "qpu_idle_eta_seconds": 143,
                "qpu_expected_idle_at": "2026-07-30T08:12:41",
                "health_fail_count": 0,
                "last_health_check_at": "2026-07-30T08:10:18",
            }
        ],
    }
    return web.json_response(response_data)


async def submit_handler(request):
    """Submit task handler."""
    logger.info("submit task request received.")
    response_data = {
        "status": "finished",
        "job_id": "2024041917095371986",
        "task_id": "task_16d227fdfa5d418c",
        "queue_position": 0,
    }
    return web.json_response(response_data)


async def get_result_handler(request):
    """Get task result handler."""
    logger.info("get task result request received.")
    response_data = {
        "task_id": "task_16d227fdfa5d418c",
        "status": "completed",
        "progress": 100,
        "created_at": "2026-09-01T02:52:18",
        "started_at": "2026-09-01T02:52:19",
        "completed_at": "2026-09-01T02:52:20",
        "queue_position": None,
        "result": {
            "success": True,
            "counts": {
                "010": 29,
                "001": 26,
                "100": 32,
                "110": 8,
                "000": 2,
                "011": 2,
                "101": 1,
            },
            "shots": 100,
            "result_format": "counts",
            "metadata": {
                "backend_name": "QZ01",
                "date": "2026-09-01T10:52:22.367408Z",
            },
            "readout_correction_requested": False,
            "readout_correction_applied": False,
        },
        "error": None,
        "error_type": None,
        "error_traceback": None,
        "retry_count": 0,
        "worker_id": "worker1",
        "dispatch_state": "committed",
        "task_eta_seconds": 0,
        "expected_finish_at": "2026-09-01T02:52:20.550480",
        "execution_time": 1.04509,
        "cost": 5.5,
        "currency": "CNY",
    }
    return web.json_response(response_data)


def main(port=18607):
    init_logging()

    app.router.add_get("/api/v1/qpus", get_backends_handler)
    app.router.add_get("/backends", get_backends_handler)
    app.router.add_post(
        "/api/v1/tasks/async",
        submit_handler,
    )
    app.router.add_get(
        "/api/v1/tasks/async/task_16d227fdfa5d418c", get_result_handler
    )

    web.run_app(app, host="", port=port)


if __name__ == "__main__":
    main()
