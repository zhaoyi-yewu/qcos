#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
from fastapi_jsonrpc import InvalidParams
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from uvicorn.main import Server as UvicornServer

from wy_qcos.api.posiq.routes_jsonrpc.routes import (
    base_api,
    driver_api_v1,
    device_api_v1,
    transpiler_api_v1,
    job_api_v1,
    system_api_v1,
)

logger = logging.getLogger(__name__)

app = jsonrpc.API()


def patched_invalid_params_from_validation_error(
    exc: ValidationError | RequestValidationError,
) -> InvalidParams:
    """Patched invalid_params_from_validation_error for fastapi_jsonrpc.

    Args:
        exc (Exception): exception

    Returns:
      jsonrpc.InvalidParams, jsonrpc
    """
    errors = []
    details = []
    for err in exc.errors():
        err.pop("url", None)
        if "loc" in err:
            if err["loc"][:1] == ("body",):
                err["loc"] = err["loc"][1:]
            else:
                err["loc"] = (f"<{err['loc'][0]}>",) + err["loc"][1:]
        errors.append(err)
        loc_list = [str(item) for item in err.get("loc", [])]
        details.append(
            f"{err.get('msg', '')}. Actual value: "
            f"{'.'.join(loc_list)}={err.get('input', '')}, "
            f"Except type: {err.get('type', '')}"
        )
    return InvalidParams(
        data={"details": "; ".join(details), "errors": errors}
    )


jsonrpc.invalid_params_from_validation_error = (
    patched_invalid_params_from_validation_error
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.bind_entrypoint(base_api)
app.bind_entrypoint(driver_api_v1)
app.bind_entrypoint(device_api_v1)
app.bind_entrypoint(transpiler_api_v1)
app.bind_entrypoint(job_api_v1)
app.bind_entrypoint(system_api_v1)

# Monkey Patch uvicorn signal handler to detect the app is shutting down
app.state.exiting = False
app.state.timing = False
unicorn_exit_handler = UvicornServer.handle_exit


def handle_exit(*args, **kwargs):
    """Handle exit."""
    app.state.exiting = True
    unicorn_exit_handler(*args, **kwargs)


UvicornServer.handle_exit = handle_exit  # type: ignore
