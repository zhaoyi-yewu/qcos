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
#     WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""FastAPI application for the cloud compiler service.

Exposes a single REST endpoint POST /compiler/qasm/compile that
validates openqasm syntax and (for the self-developed cmss compiler)
compiles the circuit. The OpenAPI schema is available at
/openapi.json and the interactive docs at /docs (cloud.md
section 2: access the validation interface via openapi).

All exceptions are captured globally (cloud.md section 5): any
unexpected error is turned into a {code: 0, msg: ...} response so
the service never returns an HTTP 500.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from wy_qcos.cloud.schemas import CompileRequest, CompileResponse
from wy_qcos.cloud.service import (
    CODE_FAIL,
    MSG_COMPILE_FAILED,
    MSG_INVALID_PARAM,
    compile_qasm,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="qcos-compiler",
    description=(
        "Quantum compiler cloud service. Validates openqasm syntax and "
        "compiles circuits (self-developed cmss compiler) for cloud "
        "platform integration."
    ),
    version="0.1.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    """Global handler for request validation errors (cloud.md section 5).

    Returns a code=0 response with a descriptive message instead of
    the default HTTP 422 body, keeping the contract uniform.
    """
    errors = exc.errors()
    detail = "; ".join(
        f"{'.'.join(str(p) for p in e.get('loc', []))}: {e.get('msg', '')}"
        for e in errors
    )
    logger.warning(f"request validation failed: {detail}")
    response = CompileResponse(code=CODE_FAIL, msg=MSG_INVALID_PARAM)
    return JSONResponse(status_code=200, content=response.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Global catch-all handler (cloud.md section 5).

    Any unhandled exception is turned into a code=0 response so the
    service never surfaces a raw HTTP 500.
    """
    logger.error(f"unhandled exception: {exc}", exc_info=True)
    response = CompileResponse(code=CODE_FAIL, msg=MSG_COMPILE_FAILED)
    return JSONResponse(status_code=200, content=response.model_dump())


@app.post(
    "/compiler/qasm/compile",
    response_model=CompileResponse,
    summary="Validate and compile openqasm",
    response_description="Compilation result",
)
async def compile_endpoint(request: CompileRequest) -> CompileResponse:
    """Validate openqasm syntax and compile the circuit.

    - QASM2.0 syntax is validated with the self-developed cmss parser.
    - QASM3.0 is not supported.
    - When compiler is cmss the circuit is compiled and
      data.compiled is returned; otherwise only validation is
      performed.
    """
    return compile_qasm(request)
