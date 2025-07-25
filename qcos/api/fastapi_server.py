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

import logging

import fastapi_jsonrpc as jsonrpc
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.main import Server as UvicornServer

from qcos.api.posiq.routes_jsonrpc.routes import (
    device_api_v1, job_api_v1, system_api_v1)

logger = logging.getLogger(__name__)

app = jsonrpc.API()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.bind_entrypoint(device_api_v1)
app.bind_entrypoint(job_api_v1)
app.bind_entrypoint(system_api_v1)

# Monkey Patch uvicorn signal handler to detect the app is shutting down
app.state.exiting = False
app.state.timing = False
unicorn_exit_handler = UvicornServer.handle_exit


def handle_exit(*args, **kwargs):
    """
    Handle exit

    :param args: args
    :param kwargs: kwargs
    """
    app.state.exiting = True
    unicorn_exit_handler(*args, **kwargs)


UvicornServer.handle_exit = handle_exit
