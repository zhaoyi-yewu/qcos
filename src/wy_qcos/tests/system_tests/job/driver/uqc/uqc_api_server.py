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

org_path = Library.set_driver_venv_path("DriverUQCMatrix2", Config.VENV_DIR)

import random
import time
import re
import logging

from aiohttp import web
import socketio

from wy_qcos.common.library import Library

logger = logging.getLogger(__name__)
sio = socketio.AsyncServer(cors_allowed_origins="*")
app = web.Application()
sio.attach(app)
_tasks = {}

# UQC Server simulator
uqc_listen_ip = "0.0.0.0"
uqc_listen_port = 5001


def submit_task(data):
    """Submit task.

    Args:
        data: task data

    Returns:
        task id
    """
    task_id = data["Body"]["TaskId"]
    shot = data["Body"]["Configure"]["Shot"]

    response = task_id

    _tasks[task_id] = {
        "source_code": data["Body"]["ConvertQProg"],
        "task_backend_device": data["Body"]["Target"],
        "shots": shot,
    }

    time.sleep(1)
    logger.info(f"[submit_task|request] task_id: {task_id}, shots: {shot}")
    logger.info(f"[submit_task|response] {response}")
    return response


def get_task_status(task_id):
    """Get task status.

    Args:
        task_id: task id

    Returns:
        task status
    """
    task_status = "SUCCESS"
    response = task_status
    logger.info(f"[get_task_status|request] task_id: {task_id}, ")
    time.sleep(1)
    logger.info(f"[get_task_status|response] {response}")
    return response


def get_task_result(task_id):
    """Get task result.

    Args:
        task_id: task id

    Returns:
        task result
    """
    result = None
    logger.info(f"[get_task_result|request] task_id: {task_id}, ")
    pattern = r"qubit\s*\[\s*(\d+)\s*\]"
    matches = re.findall(
        pattern, _tasks[task_id]["source_code"], re.IGNORECASE
    )
    num_qubits = sum(int(match) for match in matches)
    num = _tasks[task_id]["shots"]
    random_int = random.randint(0, num)

    if _tasks[task_id]["task_backend_device"] == "qiskit-sim":
        result_0 = str(hex(0))
        result_2_n = str(hex(2**num_qubits - 1))
        qubit_result = {result_0: random_int, result_2_n: num - random_int}
        result = [{"results": [{"data": {"counts": qubit_result}}]}]

    if _tasks[task_id]["task_backend_device"] == "Matrix2":
        qubit_result = [[0, random_int], [2**num_qubits - 1, num - random_int]]
        result = [
            {"datasets": {"computational_basis_histogram": qubit_result}}
        ]
    return result


@sio.event
async def connect(sid):
    """Client connect.

    Args:
        sid: client sid
    """
    logger.info(f"client {sid} connect")


@sio.event
async def disconnect(sid):
    """Client disconnect.

    Args:
        sid: client sid
    """
    logger.info(f"client {sid} disconnect")


@sio.on("message", namespace="/ws")
async def message(sid, data):
    """Receive client message.

    Args:
        sid: client sid
        data: client data
    """
    response_data = {}
    logger.info(f"received from client {sid} ")
    if data["Header"]["MsgType"] == "MsgTask":
        response = submit_task(data)
        response_data = {"MsgType": "MsgTaskAck", "TaskId": response}
    if data["Header"]["MsgType"] == "MsgTaskStatus":
        response = get_task_status(data["Body"]["TaskId"])
        response_data = {"MsgType": "MsgTaskStatusAck", "TaskStatus": response}
    if data["Header"]["MsgType"] == "MsgTaskResult":
        response = get_task_result(data["Body"]["TaskId"])
        response_data = {"MsgType": "MsgTaskResultAck", "TaskResult": response}
    await sio.emit("response", response_data, room=sid, namespace="/ws")


def main():
    bind_address = f"tcp://{uqc_listen_ip}:{uqc_listen_port}"
    # start UQC API service
    logger.info(f"UQC API Server simulator started on {bind_address}")
    try:
        web.run_app(app, host=uqc_listen_ip, port=uqc_listen_port)
    except KeyboardInterrupt:
        logger.info("\nServer is stopped")


if __name__ == "__main__":
    main()
