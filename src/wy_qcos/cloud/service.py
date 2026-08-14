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

import base64
import logging
import re

from wy_qcos.cloud.schemas import (
    COMPILER_CMSS,
    COMPILER_QUARKCIRCUIT,
    CompileData,
    CompileRequest,
    CompileResponse,
)
from wy_qcos.transpiler.high_performance import (
    CMSSVerifier,
    QuafuVerifier,
    VerifyParams,
)

logger = logging.getLogger(__name__)

# success / failure codes per cloud.md response table
CODE_SUCCESS = 1
CODE_FAIL = 0

# Response msg is capped at 128 chars by the schema. The verifier failure
# message is translated to Chinese and base64-encoded into msg; base64
# expands 3 bytes -> 4 chars, so the Chinese text is truncated to
# MSG_MAX_BYTES raw bytes before encoding to keep the result <= 128 chars.
MSG_MAX_LEN = 128
MSG_MAX_BYTES = MSG_MAX_LEN * 3 // 4

MSG_SUCCESS = "成功"
# invalid request parameters: missing/required field, wrong type,
# unsupported compiler, etc. (pydantic validation surfaces these in
# app.py; the service layer raises CompileError for the same class).
MSG_INVALID_PARAM = "请求参数非法"
MSG_QASM3_NOT_SUPPORTED = "不支持QASM3.0"
MSG_QASM_SYNTAX_ERROR = "qasm语法错误"
# catch-all for unexpected internal errors (cloud.md section 5: global
# exception capture); the response always carries code=0.
MSG_COMPILE_FAILED = "服务内部错误"
MSG_TOPOLOGY_INVALID = "真机拓扑结构无效"
MSG_VERIFY_FAILED = "电路校验未通过"

# Service-layer target_bits validation messages (compiler=quarkcircuit).
# A target bit is accepted when it is either <= bits_num OR appears among
# the qubit ids declared in singleParam / doubleParam. Only a bit that is
# both > bits_num and absent from those qubit ids is rejected (and a
# negative bit is always rejected). These are native Chinese (not
# translated from C++ English) and are base64-encoded into msg like the
# verifier failure messages.
MSG_TARGET_BIT_NEGATIVE = "拓扑校验错误：目标比特{}不能为负数"
MSG_TARGET_BIT_EXCEEDS_QUBITS = (
    "拓扑校验错误：目标比特{}超出真机比特数{}且不在声明的量子比特中"
)


# The C++ QuafuVerifier emits English failure messages with embedded numeric
# parameters. This table maps each fixed message template (as a regex) to its
# Chinese translation; {} placeholders are filled positionally from the
# captured groups. A message that matches no template is returned verbatim
# (still base64-encoded downstream) so an unknown verifier message is never
# silently dropped.
_VERIFIER_MSG_TRANSLATIONS: list[tuple[re.Pattern[str], str]] = [
    # --- QASM syntax errors ---
    (
        re.compile(r"^QASM syntax error: OPENQASM declaration not found$"),
        "QASM语法错误：缺少OPENQASM声明",
    ),
    (
        re.compile(r"^QASM syntax error: incomplete OPENQASM declaration$"),
        "QASM语法错误：OPENQASM声明格式错误",
    ),
    (
        re.compile(r"^QASM syntax error: missing version number$"),
        "QASM语法错误：缺少版本号",
    ),
    (
        re.compile(r"^QASM syntax error: only OPENQASM 2\.0 is supported$"),
        "QASM语法错误：仅支持OPENQASM 2.0",
    ),
    (
        re.compile(r"^QASM syntax error: failed to parse circuit$"),
        "QASM语法错误：线路解析失败",
    ),
    (
        re.compile(
            r"^QASM syntax error: qubit (-?\d+) is measured more than once$"
        ),
        "QASM语法错误：比特{}被多次测量",
    ),
    (
        re.compile(
            r"^QASM syntax error: Measure gates must be at the end of "
            r"the circuit$"
        ),
        "QASM语法错误：Measure门需置于线路末尾",
    ),
    # --- topology errors ---
    (
        re.compile(r"^Topology error: circuit has no qubits$"),
        "拓扑校验错误：算力资源拓扑为空",
    ),
    (
        re.compile(
            r"^Topology error: target_bit (-?\d+) out of range \[0, (-?\d+)\)$"
        ),
        "拓扑校验错误：目标比特{}超出拓扑物理比特范围[0,{})",
    ),
    (
        re.compile(
            r"^Topology error: target qubits number mismatch with circuit$"
        ),
        "拓扑校验错误：自定义比特数和实际使用比特数不等",
    ),
    (
        re.compile(
            r"^Topology error: circuit requires (-?\d+) qubits, but chip "
            r"only has (-?\d+)$"
        ),
        "拓扑校验错误：线路需要{}个量子比特，超出芯片可用比特数{}",
    ),
    (
        re.compile(
            r"^Topology error: circuit requires (-?\d+) qubits, but largest "
            r"connected component only has (-?\d+)$"
        ),
        "拓扑校验错误：线路需要{}个量子比特，超出最大连通分量{}",
    ),
    (
        re.compile(
            r"^Topology error: circuit topology cannot be mapped onto "
            r"target_bits$"
        ),
        "拓扑校验错误：电路拓扑无法映射到自定义比特",
    ),
    (
        re.compile(
            r"^Topology error: target_bits do not form a connected graph$"
        ),
        "拓扑校验错误：自定义比特未构成连通图",
    ),
    # --- gate count / depth errors ---
    (
        re.compile(
            r"^Gate count error: (-?\d+) multi-qubit gates "
            r"exceed limit (-?\d+)$"
        ),
        "门数量校验错误：线路使用了{}个量子门，超过上限{}",
    ),
    (
        re.compile(
            r"^Gate count error: (-?\d+) two-qubit gates after decomposition "
            r"exceed limit (-?\d+)$"
        ),
        "门数量校验错误：分解后使用了{}个双比特门，超过上限{}",
    ),
    (
        re.compile(
            r"^Gate count error: total gate count "
            r"exceeds limit (-?\d+)$"
        ),
        "门数量校验错误：量子门总个数超过上限{}",
    ),
    (
        re.compile(
            r"^Depth error: circuit depth (-?\d+) "
            r"exceeds limit (-?\d+)$"
        ),
        "深度校验错误：线路深度为{}，超过上限{}",
    ),
]


def _translate_verifier_message(message: str) -> str:
    """Translate a C++ verifier failure message to Chinese.

    Matches message against the known verifier message templates. When a
    template matches, its captured numeric parameters are substituted into the
    Chinese translation positionally. When no template matches, the original
    message is returned unchanged so an unrecognized failure reason is still
    surfaced (it is base64-encoded downstream like any other).
    """
    for pattern, template in _VERIFIER_MSG_TRANSLATIONS:
        match = pattern.match(message)
        if match:
            return template.format(*match.groups())
    return message


def _encode_msg(message: str) -> str:
    """Base64-encode a Chinese verifier message for the response msg field.

    The message is UTF-8 encoded, then base64-encoded to an ASCII string so
    the response carries no raw non-ASCII bytes. Truncation (when needed) is
    applied to the Chinese text *before* encoding by :func:`_truncate_msg` so
    the emitted base64 is always valid and decodable.
    """
    return base64.b64encode(message.encode("utf-8")).decode("ascii")


class CompileError(Exception):
    """Raised when the compile request cannot be fulfilled.

    Carries the user-facing message that will be placed in the response
    msg field. The response code is always CODE_FAIL.
    """

    def __init__(self, msg: str):
        super().__init__(msg)
        self.msg = msg


def _truncate_msg(msg: str) -> str:
    """Truncate a verifier failure message so it fits the msg field.

    The schema caps msg at MSG_MAX_LEN chars. The verifier failure
    message is base64-encoded before being placed in the response (see
    :func:`_encode_msg`); base64 expands every 3 bytes to 4 chars, so the
    message is truncated on its UTF-8 byte length (MSG_MAX_BYTES) *before*
    encoding. Truncation never splits a multi-byte UTF-8 character. The
    verifier message is empty only when verification passes, so an empty
    message here (which should not happen on the failure path) falls back to
    the generic :data:`MSG_VERIFY_FAILED`.
    """
    if not msg:
        return MSG_VERIFY_FAILED
    encoded = msg.encode("utf-8")
    if len(encoded) <= MSG_MAX_BYTES:
        return msg
    # walk back to a UTF-8 boundary so no multi-byte char is split
    truncated = encoded[: MSG_MAX_BYTES - 1]
    while truncated and (truncated[-1] & 0xC0) == 0x80:
        truncated = truncated[:-1]
    return truncated.decode("utf-8", errors="ignore") + "…"


def _parse_link_qubit(link_qubit: str) -> tuple[int, int]:
    """Parse a Q{a}-Q{b} link string into (a, b).

    "Q0-Q1" -> (0, 1), "Q10-Q23" -> (10, 23).

    Raises:
        CompileError: when the link string does not match the expected
            Q{a}-Q{b} pattern.
    """
    try:
        left, right = link_qubit.split("-")
    except ValueError as exc:
        logger.warning(f"invalid linkQubit: {link_qubit}")
        raise CompileError(MSG_TOPOLOGY_INVALID) from exc
    if not left.startswith("Q") or not right.startswith("Q"):
        logger.warning(f"invalid linkQubit: {link_qubit}")
        raise CompileError(MSG_TOPOLOGY_INVALID)
    try:
        return int(left[1:]), int(right[1:])
    except ValueError as exc:
        logger.warning(f"invalid linkQubit: {link_qubit}")
        raise CompileError(MSG_TOPOLOGY_INVALID) from exc


def _parse_qubit_name(qubit_name: str) -> int:
    """Parse a Q{n} qubit name into its physical qubit id n.

    "Q0" -> 0, "Q10" -> 10.

    Raises:
        CompileError: when the qubit name does not match the Q{n}
            pattern.
    """
    if not isinstance(qubit_name, str) or not qubit_name.startswith("Q"):
        logger.warning(f"invalid qubit name: {qubit_name}")
        raise CompileError(MSG_TOPOLOGY_INVALID)
    try:
        return int(qubit_name[1:])
    except ValueError as exc:
        logger.warning(f"invalid qubit name: {qubit_name}")
        raise CompileError(MSG_TOPOLOGY_INVALID) from exc


def _build_verify_params(params: dict) -> VerifyParams:
    """Build a VerifyParams from the flattened request dict.

    The dict stores fidelities directly (no error-rate conversion):

    - bits_num -> bits
    - basis_gates -> basis_gates
    - single_param (list of (qubit_id, fidelity)) ->
      single_qubit_fidelities: collected into a dict keyed by qubit
      id (qubit ids need not start at 0 or be contiguous), then expanded
      into a list[float] indexed by physical qubit id with length
      max(qubit_id) + 1; qubits absent from singleParam default to
      0.0. A physical qubit id may exceed bits_num (chip vendors can
      publish ids past the declared bit count), so the list is sized by
      the largest id rather than by bits_num; only negative ids are
      rejected. The C++ verifier consumes this list indexed by qubit id.
    - double_param (list of ((a, b), fidelity) coupling edges)
      -> coupling_list (both (a,b) and (b,a)) +
      edge_fidelities (one fidelity per directed edge).
    - target_bits -> target_bits (default empty when extend missing).

    Args:
        params: flattened request dict (see :func:`request_to_dict`).

    Returns:
        VerifyParams ready for QuafuVerifier.

    Raises:
        CompileError: when a singleParam qubit id is negative.
    """
    verify_params = VerifyParams()
    verify_params.bits = params["bits_num"]
    verify_params.basis_gates = list(params["basis_gates"])

    # single_param: list of (qubit_id, fidelity) -> single_qubit_fidelities.
    # Real-machine qubit ids are not guaranteed to start at 0, be
    # contiguous, or stay below bits_num (e.g. a 65-qubit chip exposing
    # Q66), so collect them into a dict keyed by qubit id first, then
    # expand into the list[float] the C++ verifier expects — indexed by
    # physical qubit id, length = max id + 1 (NOT bits_num, so an id past
    # bits_num is still a valid index), with absent qubits defaulting to
    # 0.0. Only a negative id is invalid.
    fidelity_map: dict[int, float] = {}
    for qubit_id, fidelity in params["single_param"]:
        if qubit_id < 0:
            logger.warning(f"qubit id[{qubit_id}] must be non-negative")
            raise CompileError(MSG_TOPOLOGY_INVALID)
        fidelity_map[qubit_id] = fidelity
    if fidelity_map:
        single_fidelities = [0.0] * (max(fidelity_map) + 1)
        for qubit_id, fidelity in fidelity_map.items():
            single_fidelities[qubit_id] = fidelity
    else:
        single_fidelities = []
    verify_params.single_qubit_fidelities = single_fidelities

    # double_param: list of ((a, b), fidelity) ->
    # coupling_list (both directions) + edge_fidelities (one per edge).
    coupling_list = []
    edge_fidelities = []
    for (a, b), fidelity in params["double_param"]:
        coupling_list.append((a, b))
        edge_fidelities.append(fidelity)
        coupling_list.append((b, a))
        edge_fidelities.append(fidelity)
    verify_params.coupling_list = coupling_list
    verify_params.edge_fidelities = edge_fidelities

    verify_params.target_bits = list(params.get("target_bits", []))
    return verify_params


def _validate_target_bits(params: dict) -> str | None:
    """Validate extend.targetBits against the declared chip qubits.

    A target bit is accepted when it satisfies EITHER of:
      - bit <= bits_num (within the declared chip bit count), OR
      - bit appears among the qubit ids declared in singleParam or
        doubleParam (a real physical qubit on the chip).
    A bit that is both > bits_num and absent from those qubit ids is
    rejected; a negative bit is always rejected.

    Args:
        params: flattened request dict (see :func:`request_to_dict`).

    Returns:
        A Chinese error message (to be base64-encoded into msg) when a
        target bit is invalid, or None when all target bits are valid
        (or when no target bits were supplied).
    """
    target_bits = params.get("target_bits", [])
    if not target_bits:
        return None
    bits_num = params["bits_num"]
    # qubit ids actually declared on the chip: singleParam ids + both
    # endpoints of every doubleParam coupling edge.
    declared_qubits: set[int] = set()
    for qubit_id, _ in params["single_param"]:
        declared_qubits.add(qubit_id)
    for (a, b), _ in params["double_param"]:
        declared_qubits.add(a)
        declared_qubits.add(b)
    for bit in target_bits:
        if bit < 0:
            return MSG_TARGET_BIT_NEGATIVE.format(bit)
        if bit > bits_num and bit not in declared_qubits:
            return MSG_TARGET_BIT_EXCEEDS_QUBITS.format(bit, bits_num)
    return None


def request_to_dict(request: CompileRequest) -> dict:
    """Flatten a CompileRequest into a plain dict (snake_case keys).

    Nested objects are lifted to the top level so each field in the
    cloud.md contract table becomes a direct key:

    - extend.targetBits -> target_bits
    - topology.bits -> bits_num
    - topology.basisGates -> basis_gates (list)
    - topology.singleParam -> single_param (list of
      (qubit_id, fidelity) tuples; qubit id derived from the
      Q{n} qubit name, fidelity passed through unchanged)
    - topology.doubleParam -> double_param (list of
      ((a, b), fidelity) tuples; coupling edge derived from the
      Q{a}-Q{b} linkQubit string, cz fidelity passed through unchanged)

    A missing extend yields no target_bits key. The topology
    object is already validated by pydantic at the request boundary;
    this function only raises :class:`CompileError` for malformed qubit
    names / linkQubit strings inside an otherwise-valid topology.

    Args:
        request: validated compile request.

    Returns:
        dict representation of the request.

    Raises:
        CompileError: when a singleParam.qubit name does not match
            Q{n} or a doubleParam.linkQubit does not match
            Q{a}-Q{b}.
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
    # topology is already a parsed Topology object (pydantic validates
    # the JSON object at the request boundary); lift its inner fields.
    topology = request.topology
    result["bits_num"] = topology.bits
    result["basis_gates"] = topology.basisGates
    # singleParam: object list -> list of (qubit_id, fidelity), keyed to
    # physical qubit id derived from the "Q{n}" name.
    single_param: list[tuple[int, float]] = []
    for item in topology.singleParam:
        qubit_id = _parse_qubit_name(item.qubit)
        single_param.append((qubit_id, item.singleQubitGateFidelity))
    # doubleParam: object list -> list of ((a, b), fidelity) coupling
    # edges derived from the "Q{a}-Q{b}" linkQubit string.
    double_param: list[tuple[tuple[int, int], float]] = []
    for item in topology.doubleParam:
        edge = _parse_link_qubit(item.linkQubit)
        double_param.append((edge, item.cz))
    result["single_param"] = single_param
    result["double_param"] = double_param
    return result


def _log_request_params(params: dict) -> None:
    """Log the input parameters of a compile request at INFO level.

    The qasm source is never logged (only its length); everything else
    is logged in English so the container logs stay grep-friendly.
    """
    qasm = params.get("qasm", "")
    single_count = len(params.get("single_param", []))
    double_count = len(params.get("double_param", []))
    logger.info(
        "compile request received: ins_label=%s compiler=%s qasm_type=%s "
        "qasm_len=%d bits_num=%s basis_gates=%s single_param_count=%d "
        "double_param_count=%d target_bits=%s",
        params.get("ins_label"),
        params.get("compiler"),
        params.get("qasm_type"),
        len(qasm),
        params.get("bits_num"),
        params.get("basis_gates"),
        single_count,
        double_count,
        params.get("target_bits"),
    )


def _run_verifier(
    verifier_cls: type,
    params: dict,
) -> CompileResponse:
    """Run circuit verification with the given verifier class.

    Builds verify params, validates target bits, runs the verifier,
    and returns a CompileResponse with the result. Used by both
    quarkcircuit (QuafuVerifier) and cmss (CMSSVerifier) compilers.
    """
    compiler = params["compiler"]
    verify_params = _build_verify_params(params)
    target_bit_error = _validate_target_bits(params)
    if target_bit_error is not None:
        logger.warning(
            "compile failed: compiler=%s reason=target_bits "
            "validation failed: %s",
            compiler,
            target_bit_error,
        )
        return CompileResponse(
            code=CODE_FAIL,
            msg=_encode_msg(_truncate_msg(target_bit_error)),
        )
    verifier = verifier_cls(verify_params)
    verify_result = verifier.verify(params["qasm"])
    if verify_result.passed:
        logger.info(
            "compile succeeded: compiler=%s qasm_type=%s",
            compiler,
            params["qasm_type"],
        )
        return CompileResponse(
            code=CODE_SUCCESS, msg=MSG_SUCCESS, data=CompileData()
        )
    else:
        logger.warning(
            "compile failed: compiler=%s "
            "reason=circuit verification failed: %s",
            compiler,
            verify_result.message,
        )
        translated = _translate_verifier_message(verify_result.message)
        return CompileResponse(
            code=CODE_FAIL,
            msg=_encode_msg(_truncate_msg(translated)),
        )


def compile_qasm(request: CompileRequest) -> CompileResponse:
    """Run the cloud compiler workflow for a single request.

    The request is first flattened into a dict (see
    :func:`request_to_dict`). Then the compiler name selects the path:

    - quarkcircuit: validate the circuit with :class:`QuafuVerifier`
      and return the result (code=1 if it passes, code=0 with the
      verifier's failure message otherwise).
    - cmss: validate the circuit with :class:`CMSSVerifier`
      and return the result (code=1 if it passes, code=0 with the
      verifier failure message otherwise).
    - any other compiler name: returns code=0 with an
      "invalid request parameter" message.

    Args:
        request: validated compile request.

    Returns:
        CompileResponse with code=1 on success, code=0 on failure.
    """
    try:
        params = request_to_dict(request)
        _log_request_params(params)
        compiler = params["compiler"]

        if compiler == COMPILER_QUARKCIRCUIT:
            return _run_verifier(QuafuVerifier, params)
        elif compiler == COMPILER_CMSS:
            return _run_verifier(CMSSVerifier, params)
        else:
            logger.warning(
                "compile failed: compiler=%s reason=unsupported compiler",
                compiler,
            )
            return CompileResponse(code=CODE_FAIL, msg=MSG_INVALID_PARAM)
    except CompileError as exc:
        logger.warning(
            "compile failed: compiler=%s reason=%s",
            request.compiler,
            exc.msg,
        )
        return CompileResponse(code=CODE_FAIL, msg=exc.msg)
    except Exception as exc:
        # global exception capture: any unexpected error is a failure
        logger.error(
            "compile failed: compiler=%s reason=unexpected error: %s",
            request.compiler,
            exc,
            exc_info=True,
        )
        return CompileResponse(code=CODE_FAIL, msg=MSG_COMPILE_FAILED)
