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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import enum
import logging
import json
import time
import zerorpc

from qcos.common.library import Library

logger = logging.getLogger(__name__)


# SpinQ RPC Server simulator
rpc_listen_ip = "0.0.0.0"
rpc_listen_port = 4242
_shots = 0
PID_DIR = "/var/run/qcos"
PID_FILE = f"{PID_DIR}/driver-spinq-api-server.pid"


def init_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class TaskStatus(enum.Enum):
    """Task status"""

    finished = 0
    failed = 1
    running = 2
    queueing = 3
    not_found = 4


def request_login(username, password):
    """Request login

    Args:
        username: username
        password: password

    Returns:
        response
    """
    response = {
        "return_code": 0,
        "qubits_num": 25,
        "session_id": "1000000000000000000000000000000000000001",
        "chip_name": "chip_name",
        "coupling_list": [
            (0, 1),
            (1, 0),
            (1, 2),
            (2, 1),
            (0, 3),
            (3, 0),
            (1, 4),
            (2, 5),
            (5, 2),
            (3, 4),
            (4, 3),
            (4, 5),
            (5, 4),
        ],
    }
    logger.info(
        f"[request_login|request] username: {username}, password: {password}"
    )
    time.sleep(1)
    json_response = json.dumps(response)
    logger.info(f"[request_login|response] {json_response}")
    return json_response


def request_logout(username, session_id):
    """Request logout

    Args:
        username: username
        session_id: session_id
    """
    logger.info(
        f"[request_logout|request] username: {username}, "
        f"session_id: {session_id}"
    )
    _shots = 0


def push_task(task_name, task_gates, measures, task_desc, shots, session_id):
    """Push task

    Args:
        task_name: task name
        task_gates: task gates
        measures: measures
        task_desc: task description
        shots: shots
        session_id: session id

    Returns:
        response
    """
    status = 0
    task_id = 1000
    response = (status, task_id)
    _shots = shots
    time.sleep(5)
    logger.info(
        f"[push_task|request] task_name: {task_name}, "
        f"task_gates: {task_gates}, measures: {measures}, "
        f"task_desc: {task_desc}, shots: {shots}, session_id: {session_id}"
    )
    logger.info(f"[push_task|response] {response}")
    return response


def get_task_status(task_id, session_id):
    """Get task status

    Args:
        task_id: task_id
        session_id: session id

    Returns:
        response
    """

    task_status = TaskStatus.finished.value
    response = task_status
    logger.info(
        f"[get_task_status|request] task_id: {task_id}, "
        f"session_id: {session_id}"
    )
    time.sleep(2)
    logger.info(f"[get_task_status|response] {response}")
    return response


def get_task_result(task_id, session_id):
    """Get task result

    Args:
        task_id: task_id
        session_id: session id

    Returns:
        response
    """

    response = {"results": {"00": _shots}}
    logger.info(
        f"[get_task_result|request] task_id: {task_id}, "
        f"session_id: {session_id}"
    )
    time.sleep(2)
    json_response = json.dumps(response)
    logger.info(f"[get_task_result|response] {json_response}")
    return json_response


def main():
    # init logging
    init_logging()

    # kill existing process
    Library.kill_pid(PID_FILE)
    Library.mkdir(PID_DIR)
    Library.create_pid_file(PID_FILE)

    service = {
        "request_login": request_login,
        "request_logout": request_logout,
        "push_task": push_task,
        "get_task_status": get_task_status,
        "get_task_result": get_task_result,
    }
    server = zerorpc.Server(service, heartbeat=5)
    bind_address = f"tcp://{rpc_listen_ip}:{rpc_listen_port}"

    # 启动服务
    logger.info(f"SpinQ API Server simulator started on {bind_address}")
    logger.info("Press Ctrl+C to stop service ...")
    try:
        server.bind(bind_address)
        server.run()
    except KeyboardInterrupt:
        logger.info("\nServer is stopped")


if __name__ == "__main__":
    main()
