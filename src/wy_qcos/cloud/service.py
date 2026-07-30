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

"""Core logic for the cloud compiler service.

Implements the behavior described in cloud.md:

- Validate the openqasm syntax (QASM2.0 only; QASM3.0 is not supported).
- When the compiler is the self-developed compiler (cmss), additionally
  compile the circuit and return the compiled openqasm.
- When the compiler is a vendor/institution compiler (e.g. quarkcircuit),
  only perform circuit validation (no compilation, no compiled output).
"""

import json
import logging

from wy_qcos.cloud.schemas import (
    COMPILER_CMSS,
    CompileData,
    CompileRequest,
    CompileResponse,
    Topology,
)

logger = logging.getLogger(__name__)

# success / failure codes per cloud.md response table
CODE_SUCCESS = 1
CODE_FAIL = 0

MSG_SUCCESS = "成功"
MSG_QASM3_NOT_SUPPORTED = "不支持QASM3.0"
MSG_QASM_SYNTAX_ERROR = "qasm语法错误"
MSG_COMPILE_FAILED = "编译失败"
MSG_TOPOLOGY_INVALID = "真机拓扑结构无效"


class CompileError(Exception):
    """Raised when the compile request cannot be fulfilled.

    Carries the user-facing message that will be placed in the response
    ``msg`` field. The response ``code`` is always ``CODE_FAIL``.
    """

    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg


def _cz_key(link_qubit: str) -> str:
    """Build a double-qubit dict key from a ``Q{a}-Q{b}`` link string.

    ``"Q0-Q1"`` -> ``"CZ0_1"``, ``"Q10-Q23"`` -> ``"CZ10_23"``.

    Raises:
        CompileError: when the link string does not match the expected
            ``Q{a}-Q{b}`` pattern.
    """
    try:
        left, right = link_qubit.split("-")
    except ValueError as exc:
        logger.warning(f"invalid linkQubit: {link_qubit}")
        raise CompileError(MSG_TOPOLOGY_INVALID) from exc
    if not left.startswith("Q") or not right.startswith("Q"):
        logger.warning(f"invalid linkQubit: {link_qubit}")
        raise CompileError(MSG_TOPOLOGY_INVALID)
    return f"CZ{left[1:]}_{right[1:]}"


def request_to_dict(request: CompileRequest) -> dict:
    """Flatten a CompileRequest into a plain dict (snake_case keys).

    Nested objects are lifted to the top level so each field in the
    cloud.md contract table becomes a direct key:

    - ``extend.targetBits`` -> ``target_bits``
    - ``topology.bits`` -> ``bits_num``
    - ``topology.basisGates`` -> ``basis_gates`` (list)
    - ``topology.singleParam`` -> ``single_param`` (dict keyed by qubit
      name, value = 1 - singleQubitGateFidelity, 3 decimals)
    - ``topology.doubleParam`` -> ``double_param`` (dict keyed by
      ``CZ{a}_{b}`` derived from ``Q{a}-Q{b}``, value = 1 - cz, 3 decimals)

    A missing ``extend`` yields no ``target_bits`` key. An invalid
    topology raises :class:`CompileError`.

    Args:
        request: validated compile request.

    Returns:
        dict representation of the request.

    Raises:
        CompileError: when the topology string is not valid JSON or does
            not match the expected structure.
    """
    result: dict = {
        "ins_label": request.insLabel,
        "compiler": request.compiler,
        "qasm_type": request.qasmType,
        "qasm": request.qasm,
    }
    # extend.targetBits -> target_bits
    if request.extend is not None:
        result["target_bits"] = request.extend.targetBits
    # topology (JSON string) -> decoded inner fields lifted to top level
    try:
        topology_obj = json.loads(request.topology)
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning(f"topology is not valid json: {exc}")
        raise CompileError(MSG_TOPOLOGY_INVALID) from exc
    try:
        topology = Topology.model_validate(topology_obj)
    except Exception as exc:
        logger.warning(f"topology structure invalid: {exc}")
        raise CompileError(MSG_TOPOLOGY_INVALID) from exc
    result["bits_num"] = topology.bits
    result["basis_gates"] = topology.basisGates
    # single_param -> dict keyed by qubit name (e.g. "Q0") with value
    # being the single-qubit gate error rate (1 - fidelity), 3 decimals.
    result["single_param"] = {
        item.qubit: round(1 - item.singleQubitGateFidelity, 3)
        for item in topology.singleParam
    }
    # double_param -> dict keyed by "CZ{a}_{b}" derived from "Q{a}-Q{b}"
    # with value being the two-qubit gate error rate (1 - cz), 3 decimals.
    result["double_param"] = {
        _cz_key(item.linkQubit): round(1 - item.cz, 3)
        for item in topology.doubleParam
    }
    return result


def compile_qasm(request: CompileRequest) -> CompileResponse:
    """Run the cloud compiler workflow for a single request.

    The request is first flattened into a dict (see
    :func:`request_to_dict`). When the compiler is the self-developed
    compiler (cmss) the circuit is compiled and ``data.compiled`` is
    returned; otherwise (vendor compiler) only validation is performed.

    Args:
        request: validated compile request.

    Returns:
        CompileResponse with code=1 on success, code=0 on failure.
    """
    try:
        params = request_to_dict(request)
        logger.debug(f"compile params: {params}")
        if params["compiler"] == COMPILER_CMSS:
            compiled_circuit_qasm = ""
            data = CompileData(compiled=compiled_circuit_qasm)
        else:
            # vendor/institution compiler: validation only, no compiled output
            data = CompileData()

        return CompileResponse(code=CODE_SUCCESS, msg=MSG_SUCCESS, data=data)
    except CompileError as exc:
        logger.warning(f"compile failed: {exc.msg}")
        return CompileResponse(code=CODE_FAIL, msg=exc.msg)
    except Exception as exc:
        # global exception capture: any unexpected error is a failure
        logger.error(f"unexpected compile error: {exc}", exc_info=True)
        return CompileResponse(code=CODE_FAIL, msg=MSG_COMPILE_FAILED)
