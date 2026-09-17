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

import json
import logging
import uuid

from aiohttp import web

logger = logging.getLogger(__name__)

_query_count = {}


def init_logging():
    """Init logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def submit_handler(request):
    """Handle POST /api/cmccos/task/add."""
    body = await request.text()
    logger.info(f"submit task request: {body[:200]}")
    try:
        params = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        params = {}
    task_id = params.get("taskId", uuid.uuid4().hex)
    _query_count[task_id] = 0
    response = {
        "code": 1,
        "msg": "已提交.",
        "success": True,
        "data": {
            "taskId": task_id,
            "taskStatus": 1,
        },
    }
    return web.json_response(response)


async def get_result_handler(request):
    """Handle GET /api/cmccos/task/get/result?taskId=xxx."""
    task_id = request.query.get("taskId", "")
    count = _query_count.get(task_id, 0)
    _query_count[task_id] = count + 1

    if count < 1:
        response = {
            "timeConsume": 0.0,
            "clientId": "test",
            "taskId": task_id,
            "taskStatus": 1,
            "execStartTime": 0,
            "execEndTime": 0,
            "visualData": "",
            "taskStatusInfo": "",
            "statusStartTime": "",
            "statusEndTime": "",
            "sign": "mock_sign",
            "outData": "已提交.",
        }
    else:
        response = {
            "timeConsume": 0.01,
            "clientId": "test",
            "taskId": task_id,
            "taskStatus": 5,
            "execStartTime": 0,
            "execEndTime": 0,
            "visualData": "",
            "taskStatusInfo": "",
            "statusStartTime": "",
            "statusEndTime": "",
            "sign": "mock_sign",
            "outData": {
                "probs": [
                    {"qstate": "00", "prob": 0.5},
                    {"qstate": "11", "prob": 0.5},
                ]
            },
        }
    logger.info(f"get result response: taskStatus={response['taskStatus']}")
    return web.json_response(response)


def main(port=8081):
    """Start the mock WuYue platform server."""
    init_logging()
    app = web.Application()
    app.router.add_post("/api/cmccos/task/add", submit_handler)
    app.router.add_get("/api/cmccos/task/get/result", get_result_handler)
    web.run_app(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
