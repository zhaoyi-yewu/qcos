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
                "properties": {
                    "last_update": "2026-07-31 07:18:38",
                    "qubit_metrics": [
                        {
                            "df_10": 0.2200000000000002,
                            "df_21": 0.032265652635905084,
                            "df_read": 0.02510050251256235,
                            "discriminator": {
                                "center0": [
                                    521.7292704402514,
                                    -651.4580354187347,
                                ],
                                "center1": [
                                    2942.4879207787762,
                                    993.7286844578715,
                                ],
                                "center2": [
                                    3033.4977923104584,
                                    959.0548278835776,
                                ],
                                "measure_f0": 0.9965052631578948,
                                "measure_f1": 0.9942000000000002,
                                "radius0": 0.0,
                                "threshold": 0.5914074297050507,
                            },
                            "fc": 3.815,
                            "fc_read": 6.376,
                            "fread": 6.401100502512563,
                            "id": 0,
                            "measure_f0": 0.9965052631578948,
                            "measure_f1": 0.9942000000000002,
                            "name": "q19_23",
                            "pi": {
                                "alpha": -0.14428367228558192,
                                "amp": 0.8541535049462086,
                                "length": 20.0,
                                "zpa": 0.0,
                            },
                            "pi21": {
                                "alpha": 0.01,
                                "amp": 0.11026143347161343,
                                "length": 100.0,
                            },
                            "pi_amp": 0.8541535049462086,
                            "pi_coef": -0.14428367228558192,
                            "pi_w": 10.0,
                            "pih": {
                                "alpha": -0.18885049423322633,
                                "amp": 0.42254818440952013,
                                "length": 20.0,
                                "zpa": 0.0,
                            },
                            "read": {
                                "amp": 0.0707945784384138,
                                "length": 3000,
                                "ramp": 0.0707945784384138,
                                "rlength": 200.0,
                                "zpa": 0.027,
                            },
                            "read_amp": 0.0707945784384138,
                            "read_length": 3000,
                            "t1": 84.21596536170512,
                            "t2": 33.60258355394489,
                            "t2_star": 8.12091877074635,
                            "timing": {
                                "readin": 100,
                                "xy": 19.858148335907412,
                                "z": 9.440494856874984,
                            },
                            "xeb_fidelity": 0.9996443313300138,
                        },
                        {
                            "df_10": 0.14000000000000012,
                            "df_21": -0.044161127916445775,
                            "df_read": -0.04679548872180472,
                            "discriminator": {
                                "center0": [
                                    -214.1102450980396,
                                    -956.6123637254913,
                                ],
                                "center1": [
                                    819.0072112244873,
                                    -1378.986095238096,
                                ],
                                "center2": [
                                    781.2126936373666,
                                    -1494.8214001471138,
                                ],
                                "measure_f0": 0.9801916666666667,
                                "measure_f1": 0.9710625,
                                "radius0": 0.0,
                                "threshold": 0.5348854046555167,
                            },
                            "fc": 3.815,
                            "fc_read": 6.34,
                            "fread": 6.293204511278195,
                            "id": 1,
                            "measure_f0": 0.9801916666666667,
                            "measure_f1": 0.9710625,
                            "name": "q19_21",
                            "pi": {
                                "alpha": -0.08434959521652409,
                                "amp": 0.7669292514427,
                                "length": 20.0,
                                "zpa": 0.0,
                            },
                            "pi21": {
                                "alpha": 0.01,
                                "amp": 0.11873707648552219,
                                "length": 100.0,
                            },
                            "pi_amp": 0.7669292514427,
                            "pi_coef": -0.08434959521652409,
                            "pi_w": 10.0,
                            "pih": {
                                "alpha": -0.07942073465497622,
                                "amp": 0.3811588262277186,
                                "length": 20.0,
                                "zpa": 0.0,
                            },
                            "read": {
                                "amp": 0.1412537544622754,
                                "length": 3500,
                                "ramp": 0.1778279410038923,
                                "rlength": 200.0,
                                "zpa": -0.1,
                            },
                            "read_amp": 0.1412537544622754,
                            "read_length": 3500,
                            "t1": 74.54250331330798,
                            "t2": 6.82448989896111,
                            "t2_star": 4.090569959465846,
                            "timing": {
                                "readin": 100,
                                "xy": 21.62430688051149,
                                "z": 12.625427467945414,
                            },
                            "xeb_fidelity": 0.9997449208971048,
                        },
                    ],
                },
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
