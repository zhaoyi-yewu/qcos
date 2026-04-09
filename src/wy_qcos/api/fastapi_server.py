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

import fastapi_jsonrpc as jsonrpc
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi_jsonrpc import InvalidParams
from pydantic import ValidationError
from uvicorn.main import Server as UvicornServer

from wy_qcos.api.fastapi_coroutine import lifespan
from wy_qcos.api.posiq.routes_jsonrpc.routes import all_api
from wy_qcos.metrics.metrics_middleware import MetricsMiddleware

logger = logging.getLogger(__name__)

app = jsonrpc.API(lifespan=lifespan)


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
# Metrics Middleware to collect metrics
app.add_middleware(MetricsMiddleware)
# bind entrypoint
for api_entrypoint in all_api:
    app.bind_entrypoint(api_entrypoint)

# Monkey Patch uvicorn signal handler to detect the app is shutting down
app.state.exiting = False
app.state.timing = False


class QcosUvicornServer(UvicornServer):
    """QCOS Uvicorn Server."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("QcosUvicornServer initialized")

    def handle_exit(self, sig: int, frame) -> None:
        """Handle exit signal.

        Args:
            sig: signal
            frame: frame
        """
        logger.info(f"QcosUvicornServer received signal {sig}")
        app.state.exiting = True

        try:
            super().handle_exit(sig, frame)
        except Exception as e:
            logger.error(f"Error in QcosUvicornServer.handle_exit: {e}")
            raise
