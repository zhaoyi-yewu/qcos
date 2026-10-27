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

# Track matrix sizes per task_id so get_status can return a
# solutionVector of matching length for subqubo sub-tasks.
_task_info: dict = {}


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
        "code": "0",
        "msg": "",
        "data": {"token": "eyJhbGc.08FaIo_t-aZ"},
    }
    return web.json_response(response_data)


async def submit_handler(request):
    """Submit task handler.

    Parses the uploaded CSV file to determine the matrix dimension
    so that get_status can return a solutionVector of matching
    length. Each call generates a unique task_id.
    """
    logger.info("submit task request received.")
    matrix_size = 0
    try:
        form = await request.post()
        file_field = form.get("file")
        if file_field and hasattr(file_field, "file"):
            content = file_field.file.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            first_line = content.strip().split("\n")[0].strip()
            if first_line:
                matrix_size = len(first_line.split(","))
    except Exception as e:
        logger.warning(f"Failed to parse matrix size: {e}")
    new_task_id = str(Library.create_uuid(prefix=[0xF0]))
    _task_info[new_task_id] = {"matrix_size": matrix_size}
    response_data = {
        "code": "0",
        "msg": "",
        "data": {"task_id": new_task_id},
    }
    return web.json_response(response_data)


async def get_status_handler(request):
    """Get task status handler.

    Returns COMPLETED with a solutionVector whose length matches the
    matrix dimension recorded at submit time. Falls back to a small
    default vector if the task_id is unknown.
    """
    task_id = request.match_info.get("task_id", "")
    logger.info(f"get task status request received: {task_id}")
    info = _task_info.get(task_id, {})
    matrix_size = info.get("matrix_size", 2)
    solution = [1] * matrix_size if matrix_size > 0 else [1, -1]
    response_data = {
        "code": "0",
        "msg": "",
        "data": {
            "task_status": 2,
            "solution_values": [-109],
            "solution_data": [solution],
            "visual_data": [80],
        },
    }
    return web.json_response(response_data)


def main(port=18600):
    init_logging()

    app.router.add_post("/sso/access_token/", auth_handler)
    app.router.add_post("/api/system/business/task/", submit_handler)
    app.router.add_get(
        "/api/system/business/task/{task_id}/", get_status_handler
    )
    web.run_app(app, host="", port=port)


if __name__ == "__main__":
    main()
